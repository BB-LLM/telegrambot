"""
幂等性处理辅助函数
"""
import json
from typing import Any, Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from .ids import generate_idempotency_key
from .lww import now_ms


def get_idempotency_result(
    session: Session,
    idem_key: str
) -> Optional[Dict[str, Any]]:
    """
    获取幂等性结果
    
    Args:
        session: SQLAlchemy会话
        idem_key: 幂等性键
        
    Returns:
        幂等性结果，如果不存在返回None
    """
    sql = """
    SELECT result_json FROM idempotency 
    WHERE idem_key = :idem_key
    ORDER BY updated_at_ts DESC
    LIMIT 1
    """
    
    result = session.execute(text(sql), {"idem_key": idem_key}).fetchone()
    
    if result:
        return json.loads(result[0])
    return None


def store_idempotency_result(
    session: Session,
    idem_key: str,
    result: Dict[str, Any],
    updated_at_ts: Optional[int] = None
) -> None:
    """
    存储幂等性结果
    
    Args:
        session: SQLAlchemy会话
        idem_key: 幂等性键
        result: 结果数据
        updated_at_ts: 更新时间戳
    """
    if updated_at_ts is None:
        updated_at_ts = now_ms()
    
    sql = """
    INSERT INTO idempotency (idem_key, result_json, updated_at_ts)
    VALUES (:idem_key, :result_json, :updated_at_ts)
    ON CONFLICT (idem_key) 
    DO UPDATE SET 
        result_json = EXCLUDED.result_json,
        updated_at_ts = EXCLUDED.updated_at_ts
    WHERE idempotency.updated_at_ts <= EXCLUDED.updated_at_ts
    """
    
    session.execute(text(sql), {
        "idem_key": idem_key,
        "result_json": json.dumps(result),
        "updated_at_ts": updated_at_ts
    })
    session.commit()


def with_idempotency(
    session: Session,
    idem_key: Optional[str] = None,
    key_generator: Optional[callable] = None
):
    """
    幂等性装饰器/上下文管理器
    
    Args:
        session: SQLAlchemy会话
        idem_key: 幂等性键，如果为None则生成
        key_generator: 键生成函数
        
    Usage:
        @with_idempotency(session, "my_key")
        def my_function():
            return {"result": "data"}
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成幂等性键
            if idem_key is None:
                if key_generator:
                    current_idem_key = key_generator(*args, **kwargs)
                else:
                    current_idem_key = generate_idempotency_key()
            else:
                current_idem_key = idem_key
            
            # 检查是否已有结果
            existing_result = get_idempotency_result(session, current_idem_key)
            if existing_result:
                return existing_result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 存储结果
            store_idempotency_result(session, current_idem_key, result)
            
            return result
        
        return wrapper
    return decorator
