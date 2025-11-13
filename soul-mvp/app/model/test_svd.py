import torch
import imageio
from pathlib import Path

from diffusers import StableVideoDiffusionPipeline
from diffusers.utils import load_image, export_to_video

# 检查设备
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"使用设备: {device}")

pipe = StableVideoDiffusionPipeline.from_pretrained(
  r"stabilityai/stable-video-diffusion-img2vid-xt", torch_dtype=torch.float16, variant="fp16"
)
# pipe.enable_model_cpu_offload()
pipe.to(device)
# pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead", fullgraph=True)

# Load the conditioning image
image = load_image("D:/app/vscode/project/soul/generated_images/nova_01K7ZJKMG1S3GXKH8B7TBSGC09_207525.png")
image = image.resize((1024, 576))

generator = torch.manual_seed(42)
frames = pipe(image, decode_chunk_size=8, generator=generator, num_frames=25, motion_bucket_id=100, noise_aug_strength=0.1).frames[0]

# 生成MP4视频
mp4_path = "generated.mp4"
export_to_video(frames, mp4_path, fps=7)
print(f"MP4视频已生成: {mp4_path}")

# 将MP4转换为GIF
def convert_mp4_to_gif(mp4_path: str, gif_path: str = None, fps: int = 7):
    """
    将MP4视频转换为GIF动画
    
    Args:
        mp4_path: MP4视频文件路径
        gif_path: 输出GIF文件路径，如果为None则自动生成
        fps: GIF帧率（默认与视频相同）
    """
    if gif_path is None:
        gif_path = str(Path(mp4_path).with_suffix('.gif'))
    
    print(f"正在将 {mp4_path} 转换为 {gif_path}...")
    
    try:
        # 读取MP4视频
        reader = imageio.get_reader(mp4_path)
        
        # 获取视频信息
        fps_actual = reader.get_meta_data().get('fps', fps)
        
        # 读取所有帧
        frames_list = []
        for frame in reader:
            frames_list.append(frame)
        reader.close()
        
        # 保存为GIF
        # 使用fps参数控制播放速度
        imageio.mimsave(
            gif_path,
            frames_list,
            fps=fps_actual,
            loop=0  # 0表示无限循环
        )
        
        print(f"GIF转换完成: {gif_path}")
        print(f"  - 帧数: {len(frames_list)}")
        print(f"  - 帧率: {fps_actual} fps")
        print(f"  - 文件大小: {Path(gif_path).stat().st_size / 1024 / 1024:.2f} MB")
        
        return gif_path
        
    except Exception as e:
        print(f"GIF转换失败: {e}")
        raise

# 执行MP4转GIF
gif_path = convert_mp4_to_gif(mp4_path, fps=7)
print(f"\n完成！GIF文件: {gif_path}")