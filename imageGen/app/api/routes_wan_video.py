"""
Wan 文本到视频API路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..data.models import (
    WanVideoRequest, WanVideoResponse, 
    WanSelfieRequest, WanSelfieResponse
)
from ..data.dal import get_db
from ..api.deps import verify_soul_id, verify_user_id, verify_cue, verify_city_key, verify_mood
from ..logic.service_wan_video import get_wan_video_service

router = APIRouter(prefix="/wan-video", tags=["Wan文本到视频"])


@router.get("/", response_model=WanVideoResponse)
async def generate_wan_video(
    soul_id: str = Depends(verify_soul_id),
    cue: str = Depends(verify_cue),
    user_id: str = Depends(verify_user_id),
    db: Session = Depends(get_db)
):
    """
    生成Soul风格视频（文本到视频，自动生成GIF）
    
    Args:
        soul_id: Soul ID
        cue: 提示词
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        视频生成结果（包含MP4和GIF）
    """
    try:
        wan_service = get_wan_video_service()
        result = await wan_service.get_or_create_variant(db, soul_id, cue, user_id)
        
        return WanVideoResponse(
            mp4_url=result["mp4_url"],
            gif_url=result.get("gif_url", ""),
            variant_id=result["variant_id"],
            pk_id=result["pk_id"],
            cache_hit=result.get("cache_hit", False)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成失败: {str(e)}"
        )


@router.post("/selfie", response_model=WanSelfieResponse)
async def create_wan_selfie(
    selfie_request: WanSelfieRequest,
    db: Session = Depends(get_db)
):
    """
    创建Soul自拍视频
    
    Args:
        selfie_request: 自拍请求
        db: 数据库会话
        
    Returns:
        自拍视频生成结果
    """
    try:
        # 验证参数
        soul_id = verify_soul_id(selfie_request.soul_id)
        city_key = verify_city_key(selfie_request.city_key)
        mood = verify_mood(selfie_request.mood)
        user_id = verify_user_id(selfie_request.user_id)
        
        wan_service = get_wan_video_service()
        result = await wan_service.create_selfie(
            db, soul_id, city_key, mood, user_id
        )
        
        return WanSelfieResponse(
            mp4_url=result["mp4_url"],
            gif_url=result.get("gif_url", ""),
            variant_id=result["variant_id"],
            pk_id=result["pk_id"],
            landmark_key=result["landmark_key"]
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"自拍视频生成失败: {str(e)}"
        )


@router.post("/generate-direct")
async def generate_wan_video_direct(
    positive_prompt: str,
    negative_prompt: str = "",
    seed: Optional[int] = None,
    generate_gif: bool = True
):
    """
    直接生成视频（不经过Soul风格处理，用于测试）
    
    Args:
        positive_prompt: 正面提示词
        negative_prompt: 负面提示词
        seed: 随机种子
        generate_gif: 是否同时生成GIF
        
    Returns:
        视频生成结果
    """
    try:
        from ..data.models import VideoResponse
        
        wan_service = get_wan_video_service()
        result = await wan_service.generate_video_from_text(
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            generate_gif=generate_gif
        )
        
        # 转换为VideoResponse格式（兼容现有前端）
        return VideoResponse(
            mp4_path=result["mp4_path"],
            mp4_url=result["mp4_url"],
            video_filename=result["video_filename"],
            video_size_mb=result["video_size_mb"],
            video_generation_seconds=result["video_generation_seconds"],
            num_frames=0,  # Wan API不返回帧数信息
            fps=8,  # 默认帧率
            gif_path=result.get("gif_path"),
            gif_url=result.get("gif_url"),
            gif_filename=result.get("gif_filename"),
            gif_size_mb=result.get("gif_size_mb"),
            gif_conversion_seconds=result.get("gif_conversion_seconds"),
            total_seconds=result["total_seconds"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成失败: {str(e)}"
        )

