"""
应用配置管理
"""
import os
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """应用配置类"""
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://mvpdbuser:mvpdbpw@localhost:5432/mvpdb")
    
    # GCS配置
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "artifacts-dev-soulmedia")
    GCS_PROJECT_ID: str = os.getenv("GCS_PROJECT_ID", "your-project-id")
    GCS_CREDENTIALS_PATH: Optional[str] = os.getenv("GCS_CREDENTIALS_PATH")
    
    # API配置
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_WORKERS: int = int(os.getenv("API_WORKERS", "1"))
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    
    # 开发配置
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # AI模型配置
    MODEL_CACHE_DIR: str = os.getenv("MODEL_CACHE_DIR", "/tmp/models")
    CIVITAI_API_KEY: Optional[str] = os.getenv("CIVITAI_API_KEY")
    
    # Stable Diffusion XL 模型配置
    SDXL_MODEL_PATH: str = os.getenv("SDXL_MODEL_PATH", "app/model/sdXL_v10VAEFix.safetensors")
    SDXL_OUTPUT_DIR: str = os.getenv("SDXL_OUTPUT_DIR", "generated_images")
    SDXL_NUM_INFERENCE_STEPS: int = int(os.getenv("SDXL_NUM_INFERENCE_STEPS", "5"))
    SDXL_WIDTH: int = int(os.getenv("SDXL_WIDTH", "1024"))
    SDXL_HEIGHT: int = int(os.getenv("SDXL_HEIGHT", "1024"))
    SDXL_GUIDANCE_SCALE: float = float(os.getenv("SDXL_GUIDANCE_SCALE", "7.5"))
    
    # GIF生成配置
    GIF_FRAME_COUNT: int = int(os.getenv("GIF_FRAME_COUNT", "8"))
    GIF_DURATION: float = float(os.getenv("GIF_DURATION", "0.5"))
    
    # SVD (Stable Video Diffusion) 图生视频配置
    SVD_MODEL_ID: str = os.getenv("SVD_MODEL_ID", "stabilityai/stable-video-diffusion-img2vid-xt")
    SVD_OUTPUT_DIR: str = os.getenv("SVD_OUTPUT_DIR", "generated_videos")
    SVD_NUM_FRAMES: int = int(os.getenv("SVD_NUM_FRAMES", "25"))
    SVD_DECODE_CHUNK_SIZE: int = int(os.getenv("SVD_DECODE_CHUNK_SIZE", "8"))
    SVD_MOTION_BUCKET_ID: int = int(os.getenv("SVD_MOTION_BUCKET_ID", "100"))
    SVD_NOISE_AUG_STRENGTH: float = float(os.getenv("SVD_NOISE_AUG_STRENGTH", "0.1"))
    SVD_FPS: int = int(os.getenv("SVD_FPS", "7"))
    SVD_IMAGE_WIDTH: int = int(os.getenv("SVD_IMAGE_WIDTH", "1024"))
    SVD_IMAGE_HEIGHT: int = int(os.getenv("SVD_IMAGE_HEIGHT", "576"))
    # 预估生成时间（秒/帧）- 用于计算预估时间
    SVD_ESTIMATED_SECONDS_PER_FRAME: float = float(os.getenv("SVD_ESTIMATED_SECONDS_PER_FRAME", "2.0"))
    
    # 设备配置
    FORCE_CPU: bool = os.getenv("FORCE_CPU", "False").lower() == "true"
    DEVICE_MEMORY_FRACTION: float = float(os.getenv("DEVICE_MEMORY_FRACTION", "0.8"))
    
    # 缓存配置
    PROMPT_SIMILARITY_THRESHOLD: float = float(os.getenv("PROMPT_SIMILARITY_THRESHOLD", "0.85"))
    PHASH_DEDUPE_THRESHOLD: int = int(os.getenv("PHASH_DEDUPE_THRESHOLD", "5"))
    
    # 锁配置
    LOCK_TTL_SECONDS: int = int(os.getenv("LOCK_TTL_SECONDS", "300"))
    
    # 任务队列配置
    MAX_CONCURRENT_TASKS: int = int(os.getenv("MAX_CONCURRENT_TASKS", "1"))
    
    @classmethod
    def get_database_url(cls) -> str:
        """获取数据库URL"""
        return cls.DATABASE_URL
    
    @classmethod
    def get_gcs_config(cls) -> dict:
        """获取GCS配置"""
        return {
            "bucket_name": cls.GCS_BUCKET_NAME,
            "project_id": cls.GCS_PROJECT_ID,
            "credentials_path": cls.GCS_CREDENTIALS_PATH
        }
    
    @classmethod
    def is_development(cls) -> bool:
        """是否为开发环境"""
        return cls.ENVIRONMENT == "development"
    
    @classmethod
    def get_ai_model_config(cls) -> dict:
        """获取AI模型配置"""
        return {
            "model_path": cls.SDXL_MODEL_PATH,
            "output_dir": cls.SDXL_OUTPUT_DIR,
            "num_inference_steps": cls.SDXL_NUM_INFERENCE_STEPS,
            "width": cls.SDXL_WIDTH,
            "height": cls.SDXL_HEIGHT,
            "guidance_scale": cls.SDXL_GUIDANCE_SCALE,
            "gif_frame_count": cls.GIF_FRAME_COUNT,
            "gif_duration": cls.GIF_DURATION,
            "force_cpu": cls.FORCE_CPU,
            "device_memory_fraction": cls.DEVICE_MEMORY_FRACTION
        }
    
    @classmethod
    def get_svd_config(cls) -> dict:
        """获取SVD图生视频配置"""
        return {
            "model_id": cls.SVD_MODEL_ID,
            "output_dir": cls.SVD_OUTPUT_DIR,
            "num_frames": cls.SVD_NUM_FRAMES,
            "decode_chunk_size": cls.SVD_DECODE_CHUNK_SIZE,
            "motion_bucket_id": cls.SVD_MOTION_BUCKET_ID,
            "noise_aug_strength": cls.SVD_NOISE_AUG_STRENGTH,
            "fps": cls.SVD_FPS,
            "image_width": cls.SVD_IMAGE_WIDTH,
            "image_height": cls.SVD_IMAGE_HEIGHT,
            "estimated_seconds_per_frame": cls.SVD_ESTIMATED_SECONDS_PER_FRAME,
            "force_cpu": cls.FORCE_CPU
        }
    
    @classmethod
    def is_production(cls) -> bool:
        """是否为生产环境"""
        return cls.ENVIRONMENT == "production"


# 全局配置实例
config = Config()
