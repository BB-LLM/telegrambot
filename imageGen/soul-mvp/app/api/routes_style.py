"""
风格配置API路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..data.models import StyleRequest, SoulStyleProfileBase
from ..data.dal import SoulStyleProfileDAL, SoulDAL
from ..core.lww import now_ms
from .deps import get_database, verify_soul_id

router = APIRouter(prefix="/style", tags=["风格配置"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_or_update_style(
    style_request: StyleRequest,
    db: Session = Depends(get_database)
):
    """
    创建或更新Soul风格配置
    
    Args:
        style_request: 风格配置请求
        db: 数据库会话
        
    Returns:
        成功消息
    """
    # 验证Soul是否存在
    soul = SoulDAL.get_by_id(db, style_request.soul_id)
    if not soul:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Soul '{style_request.soul_id}' 不存在"
        )
    
    # 创建风格配置
    style_data = SoulStyleProfileBase(
        soul_id=style_request.soul_id,
        base_model_ref=style_request.base_model_ref,
        lora_ids_json=style_request.lora_ids,
        palette_json=style_request.palette,
        negatives_json=style_request.negatives,
        motion_module=style_request.motion_module,
        extra_json={},
        updated_at_ts=now_ms()
    )
    
    # 保存到数据库
    SoulStyleProfileDAL.upsert(db, style_data)
    
    return {
        "message": f"Soul '{style_request.soul_id}' 风格配置已更新",
        "soul_id": style_request.soul_id,
        "base_model_ref": style_request.base_model_ref,
        "lora_count": len(style_request.lora_ids)
    }


@router.get("/{soul_id}")
async def get_style(
    soul_id: str = Depends(verify_soul_id),
    db: Session = Depends(get_database)
):
    """
    获取Soul风格配置
    
    Args:
        soul_id: Soul ID
        db: 数据库会话
        
    Returns:
        风格配置信息
    """
    style = SoulStyleProfileDAL.get_by_soul_id(db, soul_id)
    if not style:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Soul '{soul_id}' 的风格配置不存在"
        )
    
    return {
        "soul_id": style.soul_id,
        "base_model_ref": style.base_model_ref,
        "lora_ids": style.lora_ids_json,
        "palette": style.palette_json,
        "negatives": style.negatives_json,
        "motion_module": style.motion_module,
        "extra": style.extra_json,
        "updated_at_ts": style.updated_at_ts
    }


@router.delete("/{soul_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_style(
    soul_id: str = Depends(verify_soul_id),
    db: Session = Depends(get_database)
):
    """
    删除Soul风格配置
    
    Args:
        soul_id: Soul ID
        db: 数据库会话
    """
    style = SoulStyleProfileDAL.get_by_soul_id(db, soul_id)
    if not style:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Soul '{soul_id}' 的风格配置不存在"
        )
    
    # 删除风格配置
    sql = "DELETE FROM soul_style_profile WHERE soul_id = :soul_id"
    db.execute(sql, {"soul_id": soul_id})
    db.commit()
    
    return None


@router.get("/", response_model=List[dict])
async def list_styles(
    db: Session = Depends(get_database)
):
    """
    获取所有Soul的风格配置列表
    
    Args:
        db: 数据库会话
        
    Returns:
        风格配置列表
    """
    # 获取所有Soul
    souls = SoulDAL.list_all(db)
    
    # 获取每个Soul的风格配置
    styles = []
    for soul in souls:
        style = SoulStyleProfileDAL.get_by_soul_id(db, soul.soul_id)
        if style:
            styles.append({
                "soul_id": style.soul_id,
                "display_name": soul.display_name,
                "base_model_ref": style.base_model_ref,
                "lora_count": len(style.lora_ids_json),
                "has_motion_module": style.motion_module is not None,
                "updated_at_ts": style.updated_at_ts
            })
    
    return styles
