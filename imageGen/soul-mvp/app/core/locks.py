"""
进程内锁机制
"""
import asyncio
from typing import Dict, Set, Optional
from contextlib import asynccontextmanager
from .ids import generate_ulid


class InProcessLock:
    """进程内锁管理器"""
    
    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock_owners: Dict[str, str] = {}
    
    async def acquire(self, lock_key: str, owner_id: Optional[str] = None) -> bool:
        """
        获取锁
        
        Args:
            lock_key: 锁键
            owner_id: 锁拥有者ID，默认生成ULID
            
        Returns:
            是否成功获取锁
        """
        if owner_id is None:
            owner_id = generate_ulid()
        
        if lock_key not in self._locks:
            self._locks[lock_key] = asyncio.Lock()
        
        acquired = await self._locks[lock_key].acquire()
        if acquired:
            self._lock_owners[lock_key] = owner_id
        
        return acquired
    
    async def release(self, lock_key: str) -> None:
        """释放锁"""
        if lock_key in self._locks:
            self._locks[lock_key].release()
            if lock_key in self._lock_owners:
                del self._lock_owners[lock_key]
    
    def get_owner(self, lock_key: str) -> Optional[str]:
        """获取锁的拥有者"""
        return self._lock_owners.get(lock_key)
    
    def is_locked(self, lock_key: str) -> bool:
        """检查锁是否被占用"""
        return lock_key in self._lock_owners


# 全局锁实例
global_lock = InProcessLock()


@asynccontextmanager
async def with_lock(lock_key: str, owner_id: Optional[str] = None):
    """
    锁上下文管理器
    
    Usage:
        async with with_lock("nova|penguin"):
            # 执行需要锁保护的代码
            pass
    """
    acquired = await global_lock.acquire(lock_key, owner_id)
    if not acquired:
        raise RuntimeError(f"Failed to acquire lock: {lock_key}")
    
    try:
        yield
    finally:
        await global_lock.release(lock_key)
