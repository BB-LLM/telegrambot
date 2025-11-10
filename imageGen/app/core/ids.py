"""
ULID生成器
"""
import time
import random
import secrets


def generate_ulid() -> str:
    """
    生成ULID (Universally Unique Lexicographically Sortable Identifier)
    
    Returns:
        26字符的ULID字符串
    """
    # 时间戳部分 (10个字符，48位，毫秒精度)
    timestamp = int(time.time() * 1000)
    timestamp_chars = _encode_timestamp(timestamp)
    
    # 随机部分 (16个字符，80位)
    random_bytes = secrets.randbits(80)
    random_chars = _encode_random(random_bytes)
    
    return timestamp_chars + random_chars


def _encode_timestamp(timestamp: int) -> str:
    """编码时间戳为10个字符"""
    chars = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    result = ""
    
    for _ in range(10):
        result = chars[timestamp % 32] + result
        timestamp //= 32
    
    return result


def _encode_random(random_bits: int) -> str:
    """编码随机数为16个字符"""
    chars = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    result = ""
    
    for _ in range(16):
        result = chars[random_bits % 32] + result
        random_bits //= 32
    
    return result


def generate_idempotency_key() -> str:
    """生成幂等性键"""
    return f"idem_{generate_ulid()}"


def generate_lock_key(soul_id: str, key_norm: str) -> str:
    """生成工作锁键"""
    return f"{soul_id}|{key_norm}"


def generate_pk_id(soul_id: str, key_hash: str) -> str:
    """生成提示词键ID"""
    return f"{soul_id}:{key_hash}"
