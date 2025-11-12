"""
后台任务管理系统
"""
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import json


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"   # 已取消


class TaskType(Enum):
    """任务类型枚举"""
    STYLE_GENERATION = "style_generation"
    SELFIE_GENERATION = "selfie_generation"


class BackgroundTask:
    """后台任务类"""
    
    def __init__(self, task_id: str, task_type: TaskType, params: Dict[str, Any]):
        self.task_id = task_id
        self.task_type = task_type
        self.params = params
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.progress = 0
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.cancelled = False
        self.cancel_event = asyncio.Event()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "params": self.params
        }
    
    async def cancel(self):
        """取消任务"""
        self.cancelled = True
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()
        self.cancel_event.set()


class TaskManager:
    """任务管理器"""
    
    def __init__(self, max_concurrent: int = 2):
        self.tasks: Dict[str, BackgroundTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._queue_processor: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def _ensure_background_tasks(self):
        """确保后台任务已经在事件循环中运行"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                # 如果事件循环尚未运行，暂时跳过，等待在运行中的上下文再次调用
                return
        self._loop = loop
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = loop.create_task(self._cleanup_old_tasks())
        if self._queue_processor is None or self._queue_processor.done():
            self._queue_processor = loop.create_task(self._queue_processor_loop())
    
    async def _queue_processor_loop(self):
        """队列处理器循环 - 按顺序处理任务"""
        while True:
            try:
                # 从队列获取任务
                task_id, coro_func, args, kwargs = await self.task_queue.get()
                
                # 使用信号量限制并发
                async with self.semaphore:
                    await self._run_task(self.tasks[task_id], coro_func, *args, **kwargs)
                
                # 标记任务完成
                self.task_queue.task_done()
            except Exception as e:
                print(f"队列处理器出错: {e}")
    
    async def _cleanup_old_tasks(self):
        """清理旧任务"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                cutoff_time = datetime.now() - timedelta(hours=1)
                
                tasks_to_remove = []
                for task_id, task in self.tasks.items():
                    if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                        and task.created_at < cutoff_time):
                        tasks_to_remove.append(task_id)
                
                for task_id in tasks_to_remove:
                    if task_id in self.tasks:
                        del self.tasks[task_id]
                    if task_id in self.running_tasks:
                        del self.running_tasks[task_id]
                
                # 只在清理了任务时打印日志
                if len(tasks_to_remove) > 0:
                    print(f"清理了 {len(tasks_to_remove)} 个旧任务")
                
            except Exception as e:
                print(f"清理任务时出错: {e}")
    
    def create_task(self, task_type: TaskType, params: Dict[str, Any]) -> str:
        """创建新任务"""
        self._ensure_background_tasks()
        task_id = str(uuid.uuid4())
        task = BackgroundTask(task_id, task_type, params)
        self.tasks[task_id] = task
        return task_id
    
    async def start_task(self, task_id: str, coro_func, *args, **kwargs):
        """启动任务（加入队列）"""
        self._ensure_background_tasks()
        if task_id not in self.tasks:
            raise ValueError(f"任务 {task_id} 不存在")
        
        task = self.tasks[task_id]
        if task.status != TaskStatus.PENDING:
            raise ValueError(f"任务 {task_id} 状态不是 PENDING")
        
        # 更新任务状态为等待中
        task.status = TaskStatus.PENDING  # 保持PENDING状态直到从队列取出
        
        # 将任务加入队列
        await self.task_queue.put((task_id, coro_func, args, kwargs))
        
        # 队列处理器会自动处理这个任务
        print(f"任务 {task_id} 已加入队列（队列长度: {self.task_queue.qsize()}）")
    
    async def _run_task(self, task: BackgroundTask, coro_func, *args, **kwargs):
        """运行任务"""
        try:
            # 检查是否被取消
            if task.cancelled:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                return
            
            # 更新任务状态为运行中
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            if task.task_id not in self.running_tasks:
                self.running_tasks[task.task_id] = None  # 标记为运行中
            
            # 执行任务
            result = await coro_func(task, *args, **kwargs)
            
            # 检查是否被取消
            if task.cancelled:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                return
            
            # 任务完成
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100
            task.result = result
            
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            task.error = "任务被取消"
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(e)
            print(f"任务 {task.task_id} 执行失败: {e}")
        finally:
            # 清理运行中的任务记录
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        print(f"正在取消任务: {task_id}")
        
        # 标记任务为取消
        await task.cancel()
        
        # 如果任务正在运行，取消异步任务
        if task_id in self.running_tasks:
            running_task = self.running_tasks[task_id]
            print(f"取消正在运行的异步任务: {task_id}")
            running_task.cancel()
            try:
                await running_task
            except asyncio.CancelledError:
                print(f"异步任务已成功取消: {task_id}")
                pass
        
        print(f"任务取消完成: {task_id}")
        return True
    
    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if task:
            return task.to_dict()
        return None
    
    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """列出任务"""
        tasks = []
        for task in self.tasks.values():
            if status_filter is None or task.status == status_filter:
                tasks.append(task.to_dict())
        
        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x["created_at"], reverse=True)
        return tasks
    
    def get_running_tasks_count(self) -> int:
        """获取正在运行的任务数量"""
        return len(self.running_tasks)


# 全局任务管理器实例
task_manager = TaskManager()
