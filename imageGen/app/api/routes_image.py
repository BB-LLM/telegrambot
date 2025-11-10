"""
图像生成API路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..data.models import ImageRequest, ImageResponse, SelfieRequest, SelfieResponse
from ..data.dal import get_db
from ..api.deps import verify_soul_id, verify_user_id, verify_cue, verify_city_key, verify_mood
from ..logic.service_image import ImageGenerationService

router = APIRouter(prefix="/image", tags=["图像生成"])

# 全局服务实例
image_service = ImageGenerationService()


@router.post("/mark-seen")
async def mark_variant_seen(
    variant_id: str,
    user_id: str = Depends(verify_user_id),
    db: Session = Depends(get_db)
):
    """
    标记变体为已看
    
    Args:
        variant_id: 变体ID
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        成功消息
    """
    from ..data.dal import UserSeenDAL
    
    try:
        UserSeenDAL.mark_seen(db, user_id, variant_id)
        return {"message": "变体已标记为已看", "variant_id": variant_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"标记失败: {str(e)}"
        )


@router.get("/", response_model=ImageResponse)
async def generate_image(
    soul_id: str = Depends(verify_soul_id),
    cue: str = Depends(verify_cue),
    user_id: str = Depends(verify_user_id),
    db: Session = Depends(get_db)
):
    """
    生成Soul风格图像
    
    Args:
        soul_id: Soul ID
        cue: 提示词
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        图像生成结果
    """
    try:
        result = await image_service.get_or_create_variant(db, soul_id, cue, user_id)
        
        return ImageResponse(
            url=result["url"],
            variant_id=result["variant_id"],
            pk_id=result["pk_id"]
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


@router.post("/selfie", response_model=SelfieResponse)
async def create_selfie(
    selfie_request: SelfieRequest,
    db: Session = Depends(get_db)
):
    """
    创建Soul自拍
    
    Args:
        selfie_request: 自拍请求
        db: 数据库会话
        
    Returns:
        自拍生成结果
    """
    try:
        # 验证参数
        soul_id = verify_soul_id(selfie_request.soul_id)
        city_key = verify_city_key(selfie_request.city_key)
        mood = verify_mood(selfie_request.mood)
        user_id = verify_user_id(selfie_request.user_id)
        
        result = await image_service.create_selfie(
            db, soul_id, city_key, mood, user_id
        )
        
        return SelfieResponse(
            url=result["url"],
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
            detail=f"自拍生成失败: {str(e)}"
        )


@router.get("/variants/{pk_id}")
async def get_variants_by_key(
    pk_id: str,
    db: Session = Depends(get_db)
):
    """
    获取指定提示词键的所有变体
    
    Args:
        pk_id: 提示词键ID
        db: 数据库会话
        
    Returns:
        变体列表
    """
    try:
        from ..data.dal import VariantDAL
        
        variants = VariantDAL.list_by_pk_id(db, pk_id)
        
        return {
            "pk_id": pk_id,
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "url": v.asset_url,
                    "created_at": v.updated_at_ts,
                    "meta": v.meta_json
                }
                for v in variants
            ],
            "total_count": len(variants)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取变体失败: {str(e)}"
        )


@router.get("/user/{user_id}/seen")
async def get_user_seen_variants(
    user_id: str = Depends(verify_user_id),
    db: Session = Depends(get_db)
):
    """
    获取用户已看过的变体
    
    Args:
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        已看变体列表
    """
    try:
        from ..data.dal import UserSeenDAL
        
        seen_variants = UserSeenDAL.get_seen_variants(db, user_id)
        
        return {
            "user_id": user_id,
            "seen_variants": list(seen_variants),
            "total_count": len(seen_variants)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取已看变体失败: {str(e)}"
        )