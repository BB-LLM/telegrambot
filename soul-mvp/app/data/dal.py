"""
数据访问层 (DAL) - 基于主键的CRUD操作
"""
import json
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import os
from dotenv import load_dotenv

from .models import (
    SoulBase, SoulStyleProfileBase, PromptKeyBase, VariantBase,
    UserSeenBase, LandmarkLogBase, WorkLockBase, IdempotencyBase
)
from ..core.lww import lww_upsert, lww_get_latest, lww_list_by_soul, now_ms
from ..core.ids import generate_ulid, generate_pk_id

# 加载环境变量
load_dotenv()

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mvpdbuser:mvpdbpw@localhost:5432/mvpdb")

# 创建数据库引擎
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _convert_bytea_fields(data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    转换BYTEA字段从memoryview到bytes
    
    Args:
        data: 数据字典
        fields: 需要转换的字段列表
        
    Returns:
        转换后的数据字典
    """
    for field in fields:
        if data.get(field) is not None and isinstance(data[field], memoryview):
            data[field] = bytes(data[field])
    return data


class SoulDAL:
    """Soul数据访问层"""
    
    @staticmethod
    def create(db: Session, soul_data: SoulBase) -> SoulBase:
        """创建Soul记录"""
        lww_upsert(db, "soul", "soul_id", soul_data.soul_id, soul_data.dict())
        return soul_data
    
    @staticmethod
    def get_by_id(db: Session, soul_id: str) -> Optional[SoulBase]:
        """根据ID获取Soul"""
        result = lww_get_latest(db, "soul", "soul_id", soul_id)
        return SoulBase(**result) if result else None
    
    @staticmethod
    def list_all(db: Session) -> List[SoulBase]:
        """获取所有Soul"""
        sql = "SELECT * FROM soul ORDER BY updated_at_ts DESC"
        results = db.execute(text(sql)).fetchall()
        return [SoulBase(**dict(row._mapping)) for row in results]


class SoulStyleProfileDAL:
    """Soul风格配置数据访问层"""
    
    @staticmethod
    def upsert(db: Session, style_data: SoulStyleProfileBase) -> SoulStyleProfileBase:
        """创建或更新风格配置"""
        data = style_data.dict()
        data['lora_ids_json'] = json.dumps(data['lora_ids_json'])
        data['palette_json'] = json.dumps(data['palette_json'])
        data['negatives_json'] = json.dumps(data['negatives_json'])
        data['extra_json'] = json.dumps(data['extra_json'])
        
        lww_upsert(db, "soul_style_profile", "soul_id", style_data.soul_id, data)
        return style_data
    
    @staticmethod
    def get_by_soul_id(db: Session, soul_id: str) -> Optional[SoulStyleProfileBase]:
        """根据Soul ID获取风格配置"""
        result = lww_get_latest(db, "soul_style_profile", "soul_id", soul_id)
        if result:
            # SQLAlchemy的JSONB字段已经自动解析为Python对象，不需要json.loads
            return SoulStyleProfileBase(**result)
        return None


class PromptKeyDAL:
    """提示词键数据访问层"""
    
    @staticmethod
    def create(db: Session, pk_data: PromptKeyBase) -> PromptKeyBase:
        """创建提示词键"""
        data = pk_data.dict()
        data['meta_json'] = json.dumps(data['meta_json'])
        
        lww_upsert(db, "prompt_key", "pk_id", pk_data.pk_id, data)
        return pk_data
    
    @staticmethod
    def get_by_id(db: Session, pk_id: str) -> Optional[PromptKeyBase]:
        """根据ID获取提示词键"""
        result = lww_get_latest(db, "prompt_key", "pk_id", pk_id)
        if result:
            # SQLAlchemy的JSONB字段已经自动解析为Python对象，不需要json.loads
            # 处理BYTEA字段：将memoryview转换为bytes
            result = _convert_bytea_fields(result, ['key_embed'])
            return PromptKeyBase(**result)
        return None
    
    @staticmethod
    def list_by_soul(db: Session, soul_id: str) -> List[PromptKeyBase]:
        """根据Soul ID获取提示词键列表"""
        results = lww_list_by_soul(db, "prompt_key", soul_id)
        # SQLAlchemy的JSONB字段已经自动解析为Python对象，不需要json.loads
        # 处理BYTEA字段：将memoryview转换为bytes
        for result in results:
            _convert_bytea_fields(result, ['key_embed'])
        return [PromptKeyBase(**result) for result in results]
    
    @staticmethod
    def find_similar(db: Session, soul_id: str, key_hash: str) -> Optional[PromptKeyBase]:
        """查找相似的提示词键"""
        sql = """
        SELECT * FROM prompt_key 
        WHERE soul_id = :soul_id AND key_hash = :key_hash
        ORDER BY updated_at_ts DESC
        LIMIT 1
        """
        result = db.execute(text(sql), {"soul_id": soul_id, "key_hash": key_hash}).fetchone()
        if result:
            data = dict(result._mapping)
            data = _convert_bytea_fields(data, ['key_embed'])
            return PromptKeyBase(**data)
        return None


class VariantDAL:
    """变体数据访问层"""
    
    @staticmethod
    def create(db: Session, variant_data: VariantBase) -> VariantBase:
        """创建变体"""
        data = variant_data.dict()
        data['meta_json'] = json.dumps(data['meta_json'])
        
        lww_upsert(db, "variant", "variant_id", variant_data.variant_id, data)
        return variant_data
    
    @staticmethod
    def get_by_id(db: Session, variant_id: str) -> Optional[VariantBase]:
        """根据ID获取变体"""
        result = lww_get_latest(db, "variant", "variant_id", variant_id)
        if result:
            # SQLAlchemy的JSONB字段已经自动解析为Python对象，不需要json.loads
            return VariantBase(**result)
        return None
    
    @staticmethod
    def list_by_pk_id(db: Session, pk_id: str) -> List[VariantBase]:
        """根据提示词键ID获取变体列表"""
        sql = """
        SELECT * FROM variant 
        WHERE pk_id = :pk_id
        ORDER BY updated_at_ts DESC
        """
        results = db.execute(text(sql), {"pk_id": pk_id}).fetchall()
        
        variants = []
        for result in results:
            data = dict(result._mapping)
            # SQLAlchemy的JSONB字段已经自动解析为Python对象，不需要json.loads
            variants.append(VariantBase(**data))
        
        return variants
    
    @staticmethod
    def list_unseen_by_pk_id(db: Session, pk_id: str, user_id: str) -> List[VariantBase]:
        """根据提示词键ID获取用户未看过的变体列表"""
        sql = """
        SELECT v.* FROM variant v
        LEFT JOIN user_seen us ON v.variant_id = us.variant_id AND us.user_id = :user_id
        WHERE v.pk_id = :pk_id AND us.variant_id IS NULL
        ORDER BY v.updated_at_ts DESC
        """
        results = db.execute(text(sql), {"pk_id": pk_id, "user_id": user_id}).fetchall()
        
        variants = []
        for result in results:
            data = dict(result._mapping)
            # SQLAlchemy的JSONB字段已经自动解析为Python对象，不需要json.loads
            variants.append(VariantBase(**data))
        
        return variants
    
    @staticmethod
    def list_by_soul(db: Session, soul_id: str, limit: Optional[int] = None) -> List[VariantBase]:
        sql = """
        SELECT * FROM variant 
        WHERE soul_id = :soul_id
        ORDER BY updated_at_ts DESC
        """
        if limit:
            sql += f" LIMIT {limit}"
        
        results = db.execute(text(sql), {"soul_id": soul_id}).fetchall()
        
        variants = []
        for result in results:
            data = dict(result._mapping)
            # SQLAlchemy的JSONB字段已经自动解析为Python对象，不需要json.loads
            variants.append(VariantBase(**data))
        
        return variants


class UserSeenDAL:
    """用户已看记录数据访问层"""
    
    @staticmethod
    def mark_seen(db: Session, user_id: str, variant_id: str) -> None:
        """标记用户已看"""
        data = {
            "user_id": user_id,
            "variant_id": variant_id,
            "seen_at_ts": now_ms()
        }
        
        sql = """
        INSERT INTO user_seen (user_id, variant_id, seen_at_ts)
        VALUES (:user_id, :variant_id, :seen_at_ts)
        ON CONFLICT (user_id, variant_id) 
        DO UPDATE SET seen_at_ts = EXCLUDED.seen_at_ts
        """
        
        db.execute(text(sql), data)
        db.commit()
    
    @staticmethod
    def get_seen_variants(db: Session, user_id: str) -> set[str]:
        """获取用户已看的变体ID集合"""
        sql = "SELECT variant_id FROM user_seen WHERE user_id = :user_id"
        results = db.execute(text(sql), {"user_id": user_id}).fetchall()
        return {row[0] for row in results}
    
    @staticmethod
    def is_seen(db: Session, user_id: str, variant_id: str) -> bool:
        """检查用户是否已看过变体"""
        sql = """
        SELECT 1 FROM user_seen 
        WHERE user_id = :user_id AND variant_id = :variant_id
        LIMIT 1
        """
        result = db.execute(text(sql), {"user_id": user_id, "variant_id": variant_id}).fetchone()
        return result is not None


class LandmarkLogDAL:
    """地标日志数据访问层"""
    
    @staticmethod
    def log_usage(db: Session, log_data: LandmarkLogBase) -> None:
        """记录地标使用"""
        data = log_data.dict()
        user_id = data.get('user_id', '')
        
        sql = """
        INSERT INTO landmark_log (soul_id, city_key, landmark_key, user_id, used_at_ts)
        VALUES (:soul_id, :city_key, :landmark_key, :user_id, :used_at_ts)
        ON CONFLICT (soul_id, city_key, landmark_key, user_id) 
        DO UPDATE SET used_at_ts = EXCLUDED.used_at_ts
        """
        
        db.execute(text(sql), data)
        db.commit()
    
    @staticmethod
    def get_used_landmarks(db: Session, soul_id: str, city_key: str, user_id: Optional[str] = None) -> List[str]:
        """获取已使用的地标"""
        sql = """
        SELECT landmark_key FROM landmark_log 
        WHERE soul_id = :soul_id AND city_key = :city_key
        """
        params = {"soul_id": soul_id, "city_key": city_key}
        
        if user_id:
            sql += " AND user_id = :user_id"
            params["user_id"] = user_id
        
        results = db.execute(text(sql), params).fetchall()
        return [row[0] for row in results]


class WorkLockDAL:
    """工作锁数据访问层"""
    
    @staticmethod
    def acquire_lock(db: Session, lock_key: str, owner_id: str, ttl_seconds: int = 300) -> bool:
        """获取锁"""
        expires_at_ts = now_ms() + (ttl_seconds * 1000)
        
        sql = """
        INSERT INTO work_lock (lock_key, owner_id, expires_at_ts, updated_at_ts)
        VALUES (:lock_key, :owner_id, :expires_at_ts, :updated_at_ts)
        ON CONFLICT (lock_key) 
        DO UPDATE SET 
            owner_id = EXCLUDED.owner_id,
            expires_at_ts = EXCLUDED.expires_at_ts,
            updated_at_ts = EXCLUDED.updated_at_ts
        WHERE work_lock.expires_at_ts < :current_ts
        """
        
        try:
            result = db.execute(text(sql), {
                "lock_key": lock_key,
                "owner_id": owner_id,
                "expires_at_ts": expires_at_ts,
                "updated_at_ts": now_ms(),
                "current_ts": now_ms()
            })
            db.commit()
            return result.rowcount > 0
        except SQLAlchemyError:
            db.rollback()
            return False
    
    @staticmethod
    def release_lock(db: Session, lock_key: str, owner_id: str) -> bool:
        """释放锁"""
        sql = """
        DELETE FROM work_lock 
        WHERE lock_key = :lock_key AND owner_id = :owner_id
        """
        
        try:
            result = db.execute(text(sql), {"lock_key": lock_key, "owner_id": owner_id})
            db.commit()
            return result.rowcount > 0
        except SQLAlchemyError:
            db.rollback()
            return False


class IdempotencyDAL:
    """幂等性数据访问层"""
    
    @staticmethod
    def get_result(db: Session, idem_key: str) -> Optional[Dict[str, Any]]:
        """获取幂等性结果"""
        sql = """
        SELECT result_json FROM idempotency 
        WHERE idem_key = :idem_key
        ORDER BY updated_at_ts DESC
        LIMIT 1
        """
        
        result = db.execute(text(sql), {"idem_key": idem_key}).fetchone()
        if result:
            # 检查是否已经是Python对象
            result_data = result[0]
            if isinstance(result_data, str):
                return json.loads(result_data)
            else:
                # SQLAlchemy的JSONB字段已经自动解析为Python对象
                return result_data
        return None
    
    @staticmethod
    def store_result(db: Session, idem_key: str, result: Dict[str, Any]) -> None:
        """存储幂等性结果"""
        sql = """
        INSERT INTO idempotency (idem_key, result_json, updated_at_ts)
        VALUES (:idem_key, :result_json, :updated_at_ts)
        ON CONFLICT (idem_key) 
        DO UPDATE SET 
            result_json = EXCLUDED.result_json,
            updated_at_ts = EXCLUDED.updated_at_ts
        WHERE idempotency.updated_at_ts <= EXCLUDED.updated_at_ts
        """
        
        db.execute(text(sql), {
            "idem_key": idem_key,
            "result_json": json.dumps(result),
            "updated_at_ts": now_ms()
        })
        db.commit()
