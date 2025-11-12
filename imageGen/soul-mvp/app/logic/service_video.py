"""
图生视频服务 - SVD (Stable Video Diffusion)
"""
import os
import asyncio
import time
import gc
from typing import Optional, Dict, Any
from pathlib import Path
import torch
import imageio
from PIL import Image
from diffusers import StableVideoDiffusionPipeline
from diffusers.utils import load_image, export_to_video

from ..config import config
from ..core.locks import with_lock
from ..core.ids import generate_ulid

# 全局锁键 - 防止同时生成图片和视频
GLOBAL_GENERATION_LOCK_KEY = "global:generation"


class VideoGenerationService:
    """图生视频服务"""
    
    def __init__(self):
        """初始化视频生成服务"""
        svd_config = config.get_svd_config()
        
        # 输出目录
        self.output_dir = Path(svd_config["output_dir"])
        if not self.output_dir.is_absolute():
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.output_dir = Path(project_root) / self.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置参数
        self.model_id = svd_config["model_id"]
        self.num_frames = svd_config["num_frames"]
        self.decode_chunk_size = svd_config["decode_chunk_size"]
        self.motion_bucket_id = svd_config["motion_bucket_id"]
        self.noise_aug_strength = svd_config["noise_aug_strength"]
        self.fps = svd_config["fps"]
        self.image_width = svd_config["image_width"]
        self.image_height = svd_config["image_height"]
        self.estimated_seconds_per_frame = svd_config["estimated_seconds_per_frame"]
        
        # 设备配置
        if svd_config["force_cpu"]:
            self.device = "cpu"
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 内存配置
        self.device_memory_fraction = config.DEVICE_MEMORY_FRACTION
        
        print(f"视频生成服务使用设备: {self.device}")
        if self.device == "cuda" and torch.cuda.is_available():
            print(f"GPU显存限制: {self.device_memory_fraction * 100:.0f}%")
        
        # Pipeline将在首次使用时懒加载
        self._pipeline = None
    
    def _clear_gpu_memory(self):
        """清理GPU显存"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()
            # 再次清理以确保释放
            torch.cuda.empty_cache()
    
    @property
    def pipeline(self) -> StableVideoDiffusionPipeline:
        """获取SVD Pipeline（懒加载）"""
        if self._pipeline is None:
            print("正在加载SVD模型...")
            
            # 在加载新模型前清理显存（图片生成模型可能还在显存中）
            self._clear_gpu_memory()
            
            torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
            
            # 如果使用GPU且配置了内存限制，设置内存分数
            if self.device == "cuda" and torch.cuda.is_available():
                pass
            
            self._pipeline = StableVideoDiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch_dtype,
                variant="fp16" if self.device == "cuda" else None
            )
            
            self._pipeline.to(self.device)
            print("SVD模型加载完成")
        
        return self._pipeline
    
    def estimate_generation_time(self, num_frames: Optional[int] = None) -> Dict[str, Any]:
        """
        估算生成时间
        
        Args:
            num_frames: 帧数，如果为None则使用配置的默认值
            
        Returns:
            预估时间信息
        """
        if num_frames is None:
            num_frames = self.num_frames
        
        # 视频生成时间 = 帧数 * 每帧预估时间
        video_generation_seconds = num_frames * self.estimated_seconds_per_frame
        
        # MP4转GIF时间估算（通常很快，约1-2秒）
        gif_conversion_seconds = 2.0
        
        total_seconds = video_generation_seconds + gif_conversion_seconds
        
        return {
            "estimated_seconds": total_seconds,
            "estimated_minutes": round(total_seconds / 60, 1),
            "video_generation_seconds": video_generation_seconds,
            "gif_conversion_seconds": gif_conversion_seconds,
            "num_frames": num_frames
        }
    
    async def generate_video_from_image(
        self,
        image_path: str,
        output_filename: Optional[str] = None,
        num_frames: Optional[int] = None,
        generate_gif: bool = True
    ) -> Dict[str, Any]:
        """
        从图像生成视频和GIF
        
        Args:
            image_path: 输入图像路径
            output_filename: 输出文件名（不含扩展名），如果为None则自动生成
            num_frames: 生成帧数，如果为None则使用配置值
            generate_gif: 是否同时生成GIF，默认True
            
        Returns:
            生成结果信息
        """
        # 使用全局锁防止同时生成图片和视频
        async with with_lock(GLOBAL_GENERATION_LOCK_KEY):
            # 在开始视频生成前清理GPU显存（图片生成模型可能还在显存中）
            # 这样可以确保有足够的显存加载SVD模型
            print("清理GPU显存，准备加载视频生成模型...")
            if torch.cuda.is_available():
                self._clear_gpu_memory()
                # 显示当前显存使用情况
                allocated = torch.cuda.memory_allocated() / 1024**3
                reserved = torch.cuda.memory_reserved() / 1024**3
                print(f"GPU显存 - 已分配: {allocated:.2f} GB, 已保留: {reserved:.2f} GB")
            
            start_time = time.time()
            
            # 处理图像路径：如果是相对路径，转换为绝对路径
            if not os.path.isabs(image_path):
                # 相对于项目根目录
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                image_path = os.path.join(project_root, image_path)
            
            # 检查输入文件
            if not os.path.exists(image_path):
                # 尝试再次查找（可能是路径解析问题）
                # 如果路径中包含generated_images，确保它存在
                if 'generated_images' in image_path:
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    alt_path = os.path.join(project_root, 'generated_images', os.path.basename(image_path))
                    if os.path.exists(alt_path):
                        image_path = alt_path
                    else:
                        raise FileNotFoundError(f"输入图像不存在: {image_path}\n尝试的路径: {alt_path}")
                else:
                    raise FileNotFoundError(f"输入图像不存在: {image_path}")
            
            # 生成输出文件名
            if output_filename is None:
                output_filename = f"video_{generate_ulid()}"
            
            if num_frames is None:
                num_frames = self.num_frames
            
            # 加载并调整图像大小
            print(f"正在加载图像: {image_path}")
            image = load_image(image_path)
            image = image.resize((self.image_width, self.image_height))
            
            # 生成视频帧
            print(f"正在生成 {num_frames} 帧视频...")
            generator = torch.manual_seed(int(time.time()) % 2147483647)
            
            frames = self.pipeline(
                image,
                decode_chunk_size=self.decode_chunk_size,
                generator=generator,
                num_frames=num_frames,
                motion_bucket_id=self.motion_bucket_id,
                noise_aug_strength=self.noise_aug_strength
            ).frames[0]
            
            # 保存MP4
            mp4_path = self.output_dir / f"{output_filename}.mp4"
            export_to_video(frames, str(mp4_path), fps=self.fps)
            print(f"MP4视频已生成: {mp4_path}")
            
            video_generation_time = time.time() - start_time
            
            result = {
                "mp4_path": str(mp4_path),
                "mp4_url": f"/static/videos/{mp4_path.name}",
                "video_filename": mp4_path.name,
                "video_size_mb": round(mp4_path.stat().st_size / 1024 / 1024, 2),
                "video_generation_seconds": round(video_generation_time, 2),
                "num_frames": num_frames,
                "fps": self.fps
            }
            
            # 转换为GIF
            if generate_gif:
                print("正在将MP4转换为GIF...")
                gif_start_time = time.time()
                
                gif_path = await self._convert_mp4_to_gif(str(mp4_path))
                
                gif_conversion_time = time.time() - gif_start_time
                
                result.update({
                    "gif_path": str(gif_path),
                    "gif_url": f"/static/videos/{gif_path.name}",
                    "gif_filename": gif_path.name,
                    "gif_size_mb": round(gif_path.stat().st_size / 1024 / 1024, 2),
                    "gif_conversion_seconds": round(gif_conversion_time, 2)
                })
                
                print(f"GIF已生成: {gif_path}")
            
            total_time = time.time() - start_time
            result["total_seconds"] = round(total_time, 2)
            
            # 生成完成后清理显存中的临时数据
            if torch.cuda.is_available():
                # 清理推理过程中的临时张量
                self._clear_gpu_memory()
            
            return result
    
    async def _convert_mp4_to_gif(self, mp4_path: str, gif_path: Optional[str] = None) -> Path:
        """
        将MP4转换为GIF
        
        Args:
            mp4_path: MP4文件路径
            gif_path: 输出GIF路径，如果为None则自动生成
            
        Returns:
            GIF文件路径
        """
        if gif_path is None:
            gif_path = str(Path(mp4_path).with_suffix('.gif'))
        
        gif_path_obj = Path(gif_path)
        
        try:
            # 读取MP4视频
            reader = imageio.get_reader(mp4_path)
            
            # 获取视频信息
            fps_actual = reader.get_meta_data().get('fps', self.fps)
            
            # 读取所有帧
            frames_list = []
            for frame in reader:
                frames_list.append(frame)
            reader.close()
            
            # 保存为GIF
            imageio.mimsave(
                str(gif_path_obj),
                frames_list,
                fps=fps_actual,
                loop=0  # 0表示无限循环
            )
            
            return gif_path_obj
            
        except Exception as e:
            raise RuntimeError(f"GIF转换失败: {e}")


# 全局服务实例
_video_service: Optional[VideoGenerationService] = None


def get_video_service() -> VideoGenerationService:
    """获取视频生成服务实例（单例）"""
    global _video_service
    if _video_service is None:
        _video_service = VideoGenerationService()
    return _video_service

