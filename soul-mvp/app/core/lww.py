"""
LWW (Last Write Wins) 语义辅助函数
"""
import time
from typing import Any, Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session


def now_ms() -> int:
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)


def lww_upsert(
    session: Session,
    table_name: str,
    pk_field: str,
    pk_value: str,
    data: Dict[str, Any],
    updated_at_ts: Optional[int] = None
) -> None:
    """
    LWW语义的upsert操作
    
    Args:
        session: SQLAlchemy会话
        table_name: 表名
        pk_field: 主键字段名
        pk_value: 主键值
        data: 要插入/更新的数据
        updated_at_ts: 更新时间戳，默认使用当前时间
    """
    if updated_at_ts is None:
        updated_at_ts = now_ms()
    
    # 添加更新时间戳
    data['updated_at_ts'] = updated_at_ts
    
    # 构建字段和值的占位符
    fields = list(data.keys())
    values = list(data.values())
    placeholders = [f":{field}" for field in fields]
    
    # 构建UPSERT SQL (PostgreSQL语法)
    sql = f"""
    INSERT INTO {table_name} ({', '.join(fields)})
    VALUES ({', '.join(placeholders)})
    ON CONFLICT ({pk_field}) 
    DO UPDATE SET 
        {', '.join([f"{field} = EXCLUDED.{field}" for field in fields if field != pk_field])}
    WHERE {table_name}.updated_at_ts <= EXCLUDED.updated_at_ts
    """
    
    # 准备参数字典
    params = dict(zip(fields, values))
    
    session.execute(text(sql), params)
    session.commit()


def lww_get_latest(
    session: Session,
    table_name: str,
    pk_field: str,
    pk_value: str
) -> Optional[Dict[str, Any]]:
    """
    获取LWW语义下的最新记录
    
    Args:
        session: SQLAlchemy会话
        table_name: 表名
        pk_field: 主键字段名
        pk_value: 主键值
        
    Returns:
        最新记录字典，如果不存在返回None
    """
    sql = f"""
    SELECT * FROM {table_name} 
    WHERE {pk_field} = :pk_value
    ORDER BY updated_at_ts DESC, {pk_field} ASC
    LIMIT 1
    """
    
    result = session.execute(text(sql), {"pk_value": pk_value}).fetchone()
    
    if result:
        return dict(result._mapping)
    return None


def lww_list_by_soul(
    session: Session,
    table_name: str,
    soul_id: str,
    limit: Optional[int] = None
) -> list[Dict[str, Any]]:
    """
    按soul_id获取LWW语义下的记录列表
    
    Args:
        session: SQLAlchemy会话
        table_name: 表名
        soul_id: Soul ID
        limit: 限制数量
        
    Returns:
        记录列表
    """
    sql = f"""
    SELECT * FROM {table_name} 
    WHERE soul_id = :soul_id
    ORDER BY updated_at_ts DESC, soul_id ASC
    """
    
    if limit:
        sql += f" LIMIT {limit}"
    
    results = session.execute(text(sql), {"soul_id": soul_id}).fetchall()
    
    return [dict(row._mapping) for row in results]
