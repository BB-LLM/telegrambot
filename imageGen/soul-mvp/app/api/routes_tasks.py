"""
后台任务API路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..data.dal import get_db
from ..api.deps import verify_soul_id, verify_user_id, verify_cue, verify_city_key, verify_mood
from ..logic.service_image import ImageGenerationService

router = APIRouter(prefix="/tasks", tags=["后台任务"])

# 全局服务实例
image_service = ImageGenerationService()


class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    task_type: str
    status: str
    progress: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    params: Optional[dict] = None


class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    tasks: List[TaskResponse]
    total_count: int


@router.post("/generate", response_model=TaskResponse)
async def start_background_generation(
    soul_id: str = Depends(verify_soul_id),
    cue: str = Depends(verify_cue),
    user_id: str = Depends(verify_user_id),
    db: Session = Depends(get_db)
):
    """
    启动后台图像生成任务
    
    Args:
        soul_id: Soul ID
        cue: 提示词
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        任务信息
    """
    try:
        task_id = await image_service.start_background_generation(db, soul_id, cue, user_id)
        task_status = image_service.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="任务创建失败"
            )
        
        return TaskResponse(**task_status)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动任务失败: {str(e)}"
        )


@router.post("/selfie", response_model=TaskResponse)
async def start_background_selfie(
    soul_id: str = Depends(verify_soul_id),
    city_key: str = Depends(verify_city_key),
    mood: str = Depends(verify_mood),
    user_id: str = Depends(verify_user_id),
    db: Session = Depends(get_db)
):
    """
    启动后台自拍生成任务
    
    Args:
        soul_id: Soul ID
        city_key: 城市键
        mood: 情绪
        user_id: 用户ID
        db: 数据库会话
        
    Returns:
        任务信息
    """
    try:
        task_id = await image_service.start_background_selfie(db, soul_id, city_key, mood, user_id)
        task_status = image_service.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="任务创建失败"
            )
        
        return TaskResponse(**task_status)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动自拍任务失败: {str(e)}"
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    task_status = image_service.get_task_status(task_id)
    
    if not task_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在"
        )
    
    return TaskResponse(**task_status)


@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """
    取消任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        取消结果
    """
    success = await image_service.cancel_task(task_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在或无法取消"
        )
    
    return {"message": f"任务 {task_id} 已取消", "task_id": task_id}


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    列出任务
    
    Args:
        status: 状态过滤 (pending, running, completed, failed, cancelled)
        limit: 限制数量
        offset: 偏移量
        
    Returns:
        任务列表
    """
    try:
        tasks = image_service.list_tasks(status)
        
        # 应用分页
        total_count = len(tasks)
        tasks = tasks[offset:offset + limit]
        
        task_responses = [TaskResponse(**task) for task in tasks]
        
        return TaskListResponse(
            tasks=task_responses,
            total_count=total_count
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务列表失败: {str(e)}"
        )


@router.get("/stats/summary")
async def get_task_stats():
    """
    获取任务统计信息
    
    Returns:
        任务统计
    """
    try:
        from ..core.task_manager import TaskStatus
        
        stats = {}
        for status in TaskStatus:
            tasks = image_service.list_tasks(status.value)
            stats[status.value] = len(tasks)
        
        # 添加运行中任务数量
        stats["running_count"] = image_service.task_manager.get_running_tasks_count()
        
        return {
            "task_counts": stats,
            "total_tasks": sum(stats.values())
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务统计失败: {str(e)}"
        )
