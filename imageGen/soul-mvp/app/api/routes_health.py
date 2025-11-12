"""
健康检查API路由
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..data.models import HealthResponse
from ..core.lww import now_ms
from .deps import get_database, get_config
from ..config import Config

router = APIRouter(tags=["健康检查"])


@router.get("/healthz", response_model=HealthResponse)
async def health_check(
    db: Session = Depends(get_database),
    config: Config = Depends(get_config)
):
    """
    健康检查端点
    
    Args:
        db: 数据库会话
        config: 应用配置
        
    Returns:
        健康状态信息
    """
    # 检查数据库连接
    database_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        database_status = f"unhealthy: {str(e)}"
    
    # 检查存储连接（GCS）
    storage_status = "healthy"
    try:
        # 这里可以添加GCS连接检查
        # 暂时标记为健康
        pass
    except Exception as e:
        storage_status = f"unhealthy: {str(e)}"
    
    return HealthResponse(
        status="healthy" if database_status == "healthy" and storage_status == "healthy" else "unhealthy",
        timestamp=now_ms(),
        database=database_status,
        storage=storage_status
    )


@router.get("/ready")
async def readiness_check(
    db: Session = Depends(get_database)
):
    """
    就绪检查端点
    
    Args:
        db: 数据库会话
        
    Returns:
        就绪状态
    """
    try:
        # 检查数据库连接
        db.execute(text("SELECT 1"))
        
        # 检查必要的表是否存在
        tables = [
            "soul", "soul_style_profile", "prompt_key", 
            "variant", "user_seen", "landmark_log", 
            "work_lock", "idempotency"
        ]
        
        for table in tables:
            db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
        
        return {"status": "ready", "timestamp": now_ms()}
        
    except Exception as e:
        return {
            "status": "not_ready", 
            "timestamp": now_ms(),
            "error": str(e)
        }


@router.get("/live")
async def liveness_check():
    """
    存活检查端点
    
    Returns:
        存活状态
    """
    return {
        "status": "alive",
        "timestamp": now_ms()
    }
