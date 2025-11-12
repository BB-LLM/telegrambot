"""
图生视频API路由
"""
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from ..data.models import VideoRequest, VideoResponse, VideoEstimateResponse
from ..logic.service_video import get_video_service

router = APIRouter(prefix="/video", tags=["图生视频"])


@router.get("/estimate", response_model=VideoEstimateResponse)
async def estimate_generation_time(
    num_frames: Optional[int] = None
):
    """
    预估视频生成时间
    
    Args:
        num_frames: 帧数，如果为None则使用配置的默认值
        
    Returns:
        预估时间信息
    """
    try:
        video_service = get_video_service()
        estimate = video_service.estimate_generation_time(num_frames)
        
        return VideoEstimateResponse(**estimate)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预估失败: {str(e)}"
        )


@router.post("/generate", response_model=VideoResponse)
async def generate_video(
    video_request: VideoRequest
):
    """
    从图像生成视频和GIF
    
    Args:
        video_request: 视频生成请求
        
    Returns:
        视频生成结果
    """
    try:
        video_service = get_video_service()
        
        result = await video_service.generate_video_from_image(
            image_path=video_request.image_path,
            num_frames=video_request.num_frames,
            generate_gif=video_request.generate_gif
        )
        
        return VideoResponse(**result)
    
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RuntimeError as e:
        # 如果是锁被占用，说明有其他任务正在运行
        if "lock" in str(e).lower() or "acquire" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="系统正在处理其他生成任务，请稍后再试"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成失败: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成失败: {str(e)}"
        )


@router.post("/generate-from-variant")
async def generate_video_from_variant(
    variant_id: str,
    num_frames: Optional[int] = None,
    generate_gif: bool = True
):
    """
    从已生成的变体图像生成视频
    
    Args:
        variant_id: 变体ID
        num_frames: 生成帧数
        generate_gif: 是否同时生成GIF
        
    Returns:
        视频生成结果
    """
    try:
        from ..data.dal import VariantDAL, get_db
        
        db = next(get_db())
        
        # 获取变体信息
        variant = VariantDAL.get_by_id(db, variant_id)
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"变体不存在: {variant_id}"
            )
        
        # 优先从meta_json中获取local_filepath（这是实际的文件路径）
        image_path = None
        if variant.meta_json and isinstance(variant.meta_json, dict):
            image_path = variant.meta_json.get('local_filepath')
        
        # 如果没有local_filepath，从asset_url构建路径
        if not image_path:
            asset_url = variant.asset_url
            if asset_url.startswith("http"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="暂不支持从URL生成视频，请使用本地文件路径"
                )
            
            # 将 /generated/xxx.png 转换为 generated_images/xxx.png
            if asset_url.startswith('/generated/'):
                filename = asset_url.replace('/generated/', '')
                from ..config import config
                image_path = os.path.join(config.SDXL_OUTPUT_DIR, filename)
            elif asset_url.startswith('/'):
                image_path = asset_url[1:]  # 移除前导斜杠
            else:
                image_path = asset_url
        
        # 如果还是无法确定路径，尝试使用storage_key
        if not image_path or not os.path.exists(image_path):
            if variant.storage_key:
                from ..config import config
                # storage_key可能包含完整路径，尝试直接使用
                image_path = os.path.join(config.SDXL_OUTPUT_DIR, variant.storage_key.split('/')[-1])
        
        video_service = get_video_service()
        result = await video_service.generate_video_from_image(
            image_path=image_path,
            num_frames=num_frames,
            generate_gif=generate_gif
        )
        
        return VideoResponse(**result)
    
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成失败: {str(e)}"
        )

