"""
API依赖注入
"""
from typing import Generator
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, Header
from ..data.dal import get_db
from ..config import config


def get_database() -> Generator[Session, None, None]:
    """获取数据库会话依赖"""
    db = get_db()
    try:
        yield next(db)
    finally:
        pass


def get_idempotency_key(
    idempotency_key: str = Header(None, alias="Idempotency-Key")
) -> str:
    """获取幂等性键依赖"""
    return idempotency_key


def verify_soul_id(soul_id: str) -> str:
    """验证Soul ID"""
    if not soul_id or soul_id.strip() == "":
        raise HTTPException(status_code=400, detail="soul_id不能为空")
    
    # 检查Soul ID格式
    if not soul_id.isalnum() or len(soul_id) > 50:
        raise HTTPException(status_code=400, detail="soul_id格式无效")
    
    return soul_id.strip().lower()


def verify_user_id(user_id: str) -> str:
    """验证用户ID"""
    if not user_id or user_id.strip() == "":
        raise HTTPException(status_code=400, detail="user_id不能为空")
    
    # 检查用户ID格式
    if len(user_id) > 100:
        raise HTTPException(status_code=400, detail="user_id长度不能超过100字符")
    
    return user_id.strip()


def verify_cue(cue: str) -> str:
    """验证提示词"""
    if not cue or cue.strip() == "":
        raise HTTPException(status_code=400, detail="cue不能为空")
    
    # 检查提示词长度
    if len(cue) > 500:
        raise HTTPException(status_code=400, detail="cue长度不能超过500字符")
    
    return cue.strip()


def verify_city_key(city_key: str) -> str:
    """验证城市键"""
    if not city_key or city_key.strip() == "":
        raise HTTPException(status_code=400, detail="city_key不能为空")
    
    # 支持的城市列表
    supported_cities = ["paris", "tokyo", "newyork", "london", "rome"]
    if city_key.lower() not in supported_cities:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的城市: {city_key}。支持的城市: {', '.join(supported_cities)}"
        )
    
    return city_key.strip().lower()


def verify_mood(mood: str) -> str:
    """验证情绪"""
    if not mood or mood.strip() == "":
        raise HTTPException(status_code=400, detail="mood不能为空")
    
    # 支持的情绪列表
    supported_moods = ["happy", "sad", "excited", "calm", "mysterious", "playful"]
    if mood.lower() not in supported_moods:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的情绪: {mood}。支持的情绪: {', '.join(supported_moods)}"
        )
    
    return mood.strip().lower()


def get_config():
    """获取配置依赖"""
    return config
