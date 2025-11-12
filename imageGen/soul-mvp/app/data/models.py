"""
Pydantic数据模型
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SoulBase(BaseModel):
    """Soul基础模型"""
    soul_id: str = Field(..., description="Soul ID，如nova、valentina")
    display_name: str = Field(..., description="显示名称")
    updated_at_ts: int = Field(..., description="更新时间戳")


class SoulStyleProfileBase(BaseModel):
    """Soul风格配置基础模型"""
    soul_id: str = Field(..., description="Soul ID")
    base_model_ref: str = Field(..., description="基础模型引用")
    lora_ids_json: List[str] = Field(..., description="LoRA ID列表")
    palette_json: Dict[str, Any] = Field(..., description="调色板配置")
    negatives_json: List[str] = Field(..., description="负面提示词")
    motion_module: Optional[str] = Field(None, description="动画模块")
    extra_json: Dict[str, Any] = Field(default_factory=dict, description="额外配置")
    updated_at_ts: int = Field(..., description="更新时间戳")


class PromptKeyBase(BaseModel):
    """提示词键基础模型"""
    pk_id: str = Field(..., description="提示词键ID")
    soul_id: str = Field(..., description="Soul ID")
    key_norm: str = Field(..., description="标准化提示词")
    key_hash: str = Field(..., description="提示词哈希")
    key_embed: Optional[bytes] = Field(None, description="嵌入向量")
    meta_json: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    updated_at_ts: int = Field(..., description="更新时间戳")


class VariantBase(BaseModel):
    """变体基础模型"""
    variant_id: str = Field(..., description="变体ID")
    pk_id: str = Field(..., description="提示词键ID")
    soul_id: str = Field(..., description="Soul ID")
    asset_url: str = Field(..., description="资源URL")
    storage_key: str = Field(..., description="存储键")
    seed: Optional[int] = Field(None, description="随机种子")
    phash: Optional[int] = Field(None, description="感知哈希")
    meta_json: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    updated_at_ts: int = Field(..., description="更新时间戳")


class UserSeenBase(BaseModel):
    """用户已看记录基础模型"""
    user_id: str = Field(..., description="用户ID")
    variant_id: str = Field(..., description="变体ID")
    seen_at_ts: int = Field(..., description="查看时间戳")


class LandmarkLogBase(BaseModel):
    """地标日志基础模型"""
    soul_id: str = Field(..., description="Soul ID")
    city_key: str = Field(..., description="城市键")
    landmark_key: str = Field(..., description="地标键")
    user_id: Optional[str] = Field(None, description="用户ID")
    used_at_ts: int = Field(..., description="使用时间戳")


class WorkLockBase(BaseModel):
    """工作锁基础模型"""
    lock_key: str = Field(..., description="锁键")
    owner_id: str = Field(..., description="拥有者ID")
    expires_at_ts: int = Field(..., description="过期时间戳")
    updated_at_ts: int = Field(..., description="更新时间戳")


class IdempotencyBase(BaseModel):
    """幂等性基础模型"""
    idem_key: str = Field(..., description="幂等性键")
    result_json: Dict[str, Any] = Field(..., description="结果JSON")
    updated_at_ts: int = Field(..., description="更新时间戳")


# API请求/响应模型
class ImageRequest(BaseModel):
    """图像生成请求"""
    soul_id: str = Field(..., description="Soul ID")
    cue: str = Field(..., description="提示词")
    user_id: str = Field(..., description="用户ID")


class ImageResponse(BaseModel):
    """图像生成响应"""
    url: str = Field(..., description="图像URL")
    variant_id: str = Field(..., description="变体ID")
    pk_id: str = Field(..., description="提示词键ID")


class SelfieRequest(BaseModel):
    """自拍请求"""
    soul_id: str = Field(..., description="Soul ID")
    city_key: str = Field(..., description="城市键")
    mood: str = Field(..., description="情绪")
    user_id: str = Field(..., description="用户ID")


class SelfieResponse(BaseModel):
    """自拍响应"""
    url: str = Field(..., description="图像URL")
    variant_id: str = Field(..., description="变体ID")
    pk_id: str = Field(..., description="提示词键ID")
    landmark_key: str = Field(..., description="地标键")


class StyleRequest(BaseModel):
    """风格配置请求"""
    soul_id: str = Field(..., description="Soul ID")
    base_model_ref: str = Field(..., description="基础模型引用")
    lora_ids: List[str] = Field(..., description="LoRA ID列表")
    palette: Dict[str, Any] = Field(..., description="调色板")
    negatives: List[str] = Field(..., description="负面提示词")
    motion_module: Optional[str] = Field(None, description="动画模块")


class ReferenceRequest(BaseModel):
    """参考图像请求"""
    soul_id: str = Field(..., description="Soul ID")
    url: str = Field(..., description="参考图像URL")


class VideoRequest(BaseModel):
    """图生视频请求"""
    image_path: str = Field(..., description="输入图像路径")
    num_frames: Optional[int] = Field(None, description="生成帧数，默认使用配置值")
    generate_gif: bool = Field(True, description="是否同时生成GIF")


class VideoResponse(BaseModel):
    """图生视频响应"""
    mp4_path: str = Field(..., description="MP4文件路径")
    mp4_url: str = Field(..., description="MP4访问URL")
    video_filename: str = Field(..., description="视频文件名")
    video_size_mb: float = Field(..., description="视频文件大小（MB）")
    video_generation_seconds: float = Field(..., description="视频生成耗时（秒）")
    num_frames: int = Field(..., description="生成的帧数")
    fps: int = Field(..., description="帧率")
    gif_path: Optional[str] = Field(None, description="GIF文件路径")
    gif_url: Optional[str] = Field(None, description="GIF访问URL")
    gif_filename: Optional[str] = Field(None, description="GIF文件名")
    gif_size_mb: Optional[float] = Field(None, description="GIF文件大小（MB）")
    gif_conversion_seconds: Optional[float] = Field(None, description="GIF转换耗时（秒）")
    total_seconds: float = Field(..., description="总耗时（秒）")


class VideoEstimateResponse(BaseModel):
    """视频生成时间预估响应"""
    estimated_seconds: float = Field(..., description="预估总时间（秒）")
    estimated_minutes: float = Field(..., description="预估总时间（分钟）")
    video_generation_seconds: float = Field(..., description="视频生成预估时间（秒）")
    gif_conversion_seconds: float = Field(..., description="GIF转换预估时间（秒）")
    num_frames: int = Field(..., description="帧数")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="状态")
    timestamp: int = Field(..., description="时间戳")
    database: str = Field(..., description="数据库状态")
    storage: str = Field(..., description="存储状态")


class WanVideoRequest(BaseModel):
    """Wan文本到视频请求（自动生成GIF）"""
    soul_id: str = Field(..., description="Soul ID")
    cue: str = Field(..., description="提示词")
    user_id: str = Field(..., description="用户ID")


class WanVideoResponse(BaseModel):
    """Wan文本到视频响应"""
    mp4_url: str = Field(..., description="MP4访问URL")
    gif_url: Optional[str] = Field(None, description="GIF访问URL")
    variant_id: str = Field(..., description="变体ID")
    pk_id: str = Field(..., description="提示词键ID")
    cache_hit: bool = Field(..., description="是否命中缓存")


class WanSelfieRequest(BaseModel):
    """Wan自拍视频请求（自动生成GIF）"""
    soul_id: str = Field(..., description="Soul ID")
    city_key: str = Field(..., description="城市键")
    mood: str = Field(..., description="情绪")
    user_id: str = Field(..., description="用户ID")


class WanSelfieResponse(BaseModel):
    """Wan自拍视频响应"""
    mp4_url: str = Field(..., description="MP4访问URL")
    gif_url: Optional[str] = Field(None, description="GIF访问URL")
    variant_id: str = Field(..., description="变体ID")
    pk_id: str = Field(..., description="提示词键ID")
    landmark_key: str = Field(..., description="地标键")