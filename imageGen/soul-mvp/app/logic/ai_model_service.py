"""
AI模型服务 - 集成本地文生图pipeline
"""
import os
import asyncio
import random
import hashlib
import gc
from typing import Dict, Any, Optional, List
from pathlib import Path
import torch
from diffusers import StableDiffusionXLPipeline
from PIL import Image
import numpy as np

from ..core.lww import now_ms
from ..core.ids import generate_ulid
from ..config import config


class AIModelService:
    """AI模型服务"""
    
    def __init__(self):
        """初始化AI模型服务"""
        # 从配置文件获取参数
        ai_config = config.get_ai_model_config()
        
        self.model_path = ai_config["model_path"]
        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(self.model_path):
            # 相对于项目根目录 (app/logic -> app -> project_root)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.model_path = os.path.join(project_root, self.model_path)
        
        self.output_dir = Path(ai_config["output_dir"])
        # 如果是相对路径，转换为绝对路径
        if not self.output_dir.is_absolute():
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.output_dir = Path(project_root) / self.output_dir
        self.output_dir.mkdir(exist_ok=True)
        
        # 模型参数
        self.num_inference_steps = ai_config["num_inference_steps"]
        self.width = ai_config["width"]
        self.height = ai_config["height"]
        self.guidance_scale = ai_config["guidance_scale"]
        self.gif_frame_count = ai_config["gif_frame_count"]
        self.gif_duration = ai_config["gif_duration"]
        
        # 设备配置
        if ai_config["force_cpu"]:
            self.device = "cpu"
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"AI模型服务使用设备: {self.device}")
        
        # 初始化pipeline
        self.pipeline = None
        self._initialize_pipeline()
    
    def _initialize_pipeline(self):
        """初始化pipeline"""
        try:
            print("正在加载AI模型...")
            
            # 检查模型文件是否存在
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"模型文件不存在: {self.model_path}")
            
            print(f"模型文件路径: {self.model_path}")
            print(f"模型文件大小: {os.path.getsize(self.model_path) / (1024*1024):.1f} MB")
            
            self.pipeline = StableDiffusionXLPipeline.from_single_file(
                self.model_path,
                torch_dtype=torch.float32  # 强制使用float32
            )
            self.pipeline.to(self.device)
            print("AI模型加载完成！")
        except Exception as e:
            print(f"AI模型加载失败: {e}")
            print("将使用模拟模式运行")
            self.pipeline = None  # 设置为None，使用模拟模式
    
    async def generate_image(
        self,
        positive_prompt: str,
        negative_prompt: str,
        soul_id: str,
        variant_id: str,
        seed: Optional[int] = None,
        num_inference_steps: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> Dict[str, Any]:
        """
        生成图像
        
        Args:
            positive_prompt: 正面提示词
            negative_prompt: 负面提示词
            soul_id: Soul ID
            variant_id: 变体ID
            seed: 随机种子
            num_inference_steps: 推理步数
            width: 图像宽度
            height: 图像高度
            
        Returns:
            生成结果信息
        """
        if self.pipeline is None:
            print("警告：AI模型未加载，使用模拟模式生成图像")
            # 使用配置的默认值
            actual_width = width or self.width
            actual_height = height or self.height
            return await self._simulate_image_generation(
                positive_prompt, negative_prompt, soul_id, variant_id, seed, actual_width, actual_height
            )
        
        # 使用配置的默认值
        actual_num_inference_steps = num_inference_steps or self.num_inference_steps
        actual_width = width or self.width
        actual_height = height or self.height
        
        # 生成随机种子
        if seed is None:
            seed = random.randint(1000, 999999)
        
        # 生成图像文件名
        filename = f"{soul_id}_{variant_id}_{seed}.png"
        filepath = self.output_dir / filename
        
        try:
            # 检查取消
            if cancellation_token and cancellation_token.is_set():
                raise asyncio.CancelledError("Task was cancelled")
            
            # 使用asyncio.to_thread来运行生成任务（支持取消）
            if cancellation_token:
                # 创建一个可取消的任务
                task = asyncio.create_task(
                    asyncio.to_thread(
                        self._generate_image_sync,
                        positive_prompt,
                        negative_prompt,
                        seed,
                        actual_num_inference_steps,
                        actual_width,
                        actual_height,
                        str(filepath),
                        cancellation_token
                    )
                )
                
                # 创建一个取消任务
                cancel_task = asyncio.create_task(cancellation_token.wait())
                
                try:
                    # 等待任务完成或取消
                    done, pending = await asyncio.wait(
                        [task, cancel_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # 如果取消令牌被设置，取消任务
                    if cancellation_token.is_set():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        raise asyncio.CancelledError("Task was cancelled")
                    
                    # 获取结果
                    result = await task
                finally:
                    # 清理取消任务
                    cancel_task.cancel()
                    try:
                        await cancel_task
                    except asyncio.CancelledError:
                        pass
            else:
                # 没有取消令牌，直接运行
                result = await asyncio.to_thread(
                    self._generate_image_sync,
                    positive_prompt,
                    negative_prompt,
                    seed,
                    actual_num_inference_steps,
                    actual_width,
                    actual_height,
                    str(filepath),
                    None
                )
            
            return result
            
        except Exception as e:
            print(f"图像生成失败: {e}")
            raise
    
    def _generate_image_sync(
        self,
        positive_prompt: str,
        negative_prompt: str,
        seed: int,
        num_inference_steps: int,
        width: int,
        height: int,
        filepath: str,
        cancellation_token: Optional[asyncio.Event] = None
    ) -> Dict[str, Any]:
        """
        同步生成图像（在线程池中运行）
        """
        # 检查取消状态
        if cancellation_token and cancellation_token.is_set():
            raise asyncio.CancelledError("Task was cancelled")
        
        # 设置随机种子
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
        
        # 检查取消状态
        if cancellation_token and cancellation_token.is_set():
            raise asyncio.CancelledError("Task was cancelled")
        
        # 生成图像
        image = self.pipeline(
            prompt=positive_prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            width=width,
            height=height,
            guidance_scale=self.guidance_scale,
            generator=torch.Generator(device=self.device).manual_seed(seed)
        ).images[0]
        
        # 检查取消状态
        if cancellation_token and cancellation_token.is_set():
            raise asyncio.CancelledError("Task was cancelled")
        
        # 保存图像
        image.save(filepath)
        
        # 验证文件是否成功保存
        if not os.path.exists(filepath):
            raise RuntimeError(f"Failed to save image to {filepath}")
        
        # 计算感知哈希
        phash = self._calculate_phash(image)
        
        # 获取文件信息
        file_size = os.path.getsize(filepath)
        
        # 图片生成完成后清理GPU显存中的临时张量
        # 这样可以释放显存给后续的视频生成任务使用
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()
            # 再次清理以确保释放
            torch.cuda.empty_cache()
        
        return {
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "file_size": file_size,
            "width": image.width,
            "height": image.height,
            "seed": seed,
            "phash": phash,
            "generation_time_ms": 0  # 实际实现中可以测量时间
        }
    
    def _calculate_phash(self, image: Image.Image) -> int:
        """
        计算感知哈希
        
        Args:
            image: PIL图像对象
            
        Returns:
            感知哈希值
        """
        # 转换为numpy数组
        img_array = np.array(image.convert('L'))  # 转换为灰度图
        
        # 简单的哈希计算（实际项目中可以使用更复杂的算法）
        # 这里使用图像的平均值作为简化的哈希
        avg_value = np.mean(img_array)
        phash = int(avg_value * 1000000) % 1000000
        
        return phash
    
    async def _simulate_image_generation(
        self,
        positive_prompt: str,
        negative_prompt: str,
        soul_id: str,
        variant_id: str,
        seed: int,
        width: int,
        height: int
    ) -> Dict[str, Any]:
        """
        模拟图像生成（当AI模型不可用时）
        """
        import time
        
        # 模拟生成时间
        await asyncio.sleep(0.1)
        
        # 生成文件名
        filename = f"{soul_id}_{variant_id}_{seed}.png"
        filepath = self.output_dir / filename
        
        # 创建一个简单的占位图像
        from PIL import Image, ImageDraw, ImageFont
        
        # 创建白色背景图像
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        # 添加文本
        try:
            # 尝试使用默认字体
            font = ImageFont.load_default()
        except:
            font = None
        
        # 绘制提示词文本
        text_lines = [
            f"Soul: {soul_id}",
            f"Variant: {variant_id[:8]}...",
            f"Seed: {seed}",
            "",
            "AI Model Not Available",
            "Simulation Mode"
        ]
        
        y_offset = 50
        for line in text_lines:
            if font:
                draw.text((50, y_offset), line, fill='black', font=font)
            else:
                draw.text((50, y_offset), line, fill='black')
            y_offset += 30
        
        # 保存图像
        image.save(str(filepath))
        
        # 验证文件是否成功保存
        if not filepath.exists():
            raise RuntimeError(f"Failed to save image to {filepath}")
        
        # 计算文件信息
        file_size = os.path.getsize(filepath)
        phash = self._calculate_phash(image)
        
        return {
            "filepath": str(filepath),
            "filename": filename,
            "file_size": file_size,
            "width": width,
            "height": height,
            "seed": seed,
            "phash": phash,
            "generation_time_ms": 100
        }
    
    async def generate_gif_from_images(
        self,
        image_paths: List[str],
        output_path: str,
        duration: float = 0.5
    ) -> Dict[str, Any]:
        """
        从多张图像生成GIF
        
        Args:
            image_paths: 图像路径列表
            output_path: 输出GIF路径
            duration: 每帧持续时间（秒）
            
        Returns:
            生成结果信息
        """
        try:
            # 加载图像
            images = []
            for path in image_paths:
                img = Image.open(path)
                images.append(img)
            
            # 生成GIF
            images[0].save(
                output_path,
                save_all=True,
                append_images=images[1:],
                duration=int(duration * 1000),  # 转换为毫秒
                loop=0
            )
            
            # 获取文件信息
            file_size = os.path.getsize(output_path)
            
            return {
                "filepath": output_path,
                "filename": os.path.basename(output_path),
                "file_size": file_size,
                "frame_count": len(images),
                "duration": duration,
                "total_duration": duration * len(images)
            }
            
        except Exception as e:
            print(f"GIF生成失败: {e}")
            raise
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        清理旧文件
        
        Args:
            max_age_hours: 最大保留时间（小时）
        """
        import time
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for file_path in self.output_dir.glob("*.png"):
            if current_time - file_path.stat().st_mtime > max_age_seconds:
                try:
                    file_path.unlink()
                    print(f"已删除旧文件: {file_path}")
                except Exception as e:
                    print(f"删除文件失败 {file_path}: {e}")


# 全局AI模型服务实例
_ai_service: Optional[AIModelService] = None


def get_ai_service() -> AIModelService:
    """获取AI模型服务实例"""
    global _ai_service
    
    if _ai_service is None:
        _ai_service = AIModelService()
    
    return _ai_service


async def generate_soul_image(
    soul_id: str,
    positive_prompt: str,
    negative_prompt: str,
    variant_id: Optional[str] = None,
    seed: Optional[int] = None,
    cancellation_token: Optional[asyncio.Event] = None
) -> Dict[str, Any]:
    """
    生成Soul图像
    
    Args:
        soul_id: Soul ID
        positive_prompt: 正面提示词
        negative_prompt: 负面提示词
        variant_id: 变体ID
        seed: 随机种子
        
    Returns:
        生成结果信息
    """
    if variant_id is None:
        variant_id = generate_ulid()
    
    ai_service = get_ai_service()
    
    result = await ai_service.generate_image(
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
        soul_id=soul_id,
        variant_id=variant_id,
        seed=seed,
        cancellation_token=cancellation_token
    )
    
    return result


async def generate_soul_gif(
    soul_id: str,
    image_paths: List[str],
    variant_id: Optional[str] = None,
    duration: float = 0.5
) -> Dict[str, Any]:
    """
    生成Soul GIF
    
    Args:
        soul_id: Soul ID
        image_paths: 图像路径列表
        variant_id: 变体ID
        duration: 每帧持续时间
        
    Returns:
        生成结果信息
    """
    if variant_id is None:
        variant_id = generate_ulid()
    
    ai_service = get_ai_service()
    
    # 生成GIF文件名
    filename = f"{soul_id}_{variant_id}.gif"
    output_path = os.path.join(ai_service.output_dir, filename)
    
    result = await ai_service.generate_gif_from_images(
        image_paths=image_paths,
        output_path=output_path,
        duration=duration
    )
    
    return result
