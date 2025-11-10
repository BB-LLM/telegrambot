"""
数据库功能测试脚本
"""
import asyncio
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from app.data.dal import (
    SoulDAL, SoulStyleProfileDAL, PromptKeyDAL, VariantDAL,
    UserSeenDAL, LandmarkLogDAL, WorkLockDAL, IdempotencyDAL
)
from app.data.models import (
    SoulBase, SoulStyleProfileBase, PromptKeyBase, VariantBase,
    UserSeenBase, LandmarkLogBase, WorkLockBase, IdempotencyBase
)
from app.core.lww import now_ms
from app.core.ids import generate_ulid, generate_pk_id
from app.data.dal import get_db


def test_soul_operations():
    """测试Soul相关操作"""
    print("测试Soul操作...")
    
    db = next(get_db())
    
    # 创建Soul
    soul_data = SoulBase(
        soul_id="test_nova",
        display_name="Test Nova",
        updated_at_ts=now_ms()
    )
    
    SoulDAL.create(db, soul_data)
    print("OK Soul创建成功")
    
    # 获取Soul
    retrieved_soul = SoulDAL.get_by_id(db, "test_nova")
    assert retrieved_soul is not None
    assert retrieved_soul.soul_id == "test_nova"
    print("OK Soul获取成功")
    
    # 获取所有Soul
    all_souls = SoulDAL.list_all(db)
    assert len(all_souls) >= 1
    print("OK Soul列表获取成功")


def test_style_profile_operations():
    """测试风格配置操作"""
    print("测试风格配置操作...")
    
    db = next(get_db())
    
    # 创建风格配置
    style_data = SoulStyleProfileBase(
        soul_id="test_nova",
        base_model_ref="dreamshaper_8",
        lora_ids_json=["anime_style@v1", "pastel_colors@v2"],
        palette_json={"primary": "#FFB6C1", "secondary": "#87CEEB"},
        negatives_json=["blurry", "low quality"],
        motion_module="animate_diff_v1",
        extra_json={"strength": 0.8},
        updated_at_ts=now_ms()
    )
    
    SoulStyleProfileDAL.upsert(db, style_data)
    print("OK 风格配置创建成功")
    
    # 获取风格配置
    retrieved_style = SoulStyleProfileDAL.get_by_soul_id(db, "test_nova")
    assert retrieved_style is not None
    assert retrieved_style.soul_id == "test_nova"
    assert len(retrieved_style.lora_ids_json) == 2
    print("OK 风格配置获取成功")


def test_prompt_key_operations():
    """测试提示词键操作"""
    print("测试提示词键操作...")
    
    db = next(get_db())
    
    # 创建提示词键
    key_hash = "abc123def456"
    pk_id = generate_pk_id("test_nova", key_hash)
    
    pk_data = PromptKeyBase(
        pk_id=pk_id,
        soul_id="test_nova",
        key_norm="penguin in garden",
        key_hash=key_hash,
        key_embed=b"fake_embedding_data",
        meta_json={"canonical_prompt": "a penguin in a beautiful garden"},
        updated_at_ts=now_ms()
    )
    
    PromptKeyDAL.create(db, pk_data)
    print("OK 提示词键创建成功")
    
    # 获取提示词键
    retrieved_pk = PromptKeyDAL.get_by_id(db, pk_id)
    assert retrieved_pk is not None
    assert retrieved_pk.pk_id == pk_id
    print("OK 提示词键获取成功")
    
    # 查找相似键
    similar_pk = PromptKeyDAL.find_similar(db, "test_nova", key_hash)
    assert similar_pk is not None
    print("OK 相似键查找成功")


def test_variant_operations():
    """测试变体操作"""
    print("测试变体操作...")
    
    db = next(get_db())
    
    # 创建变体
    variant_id = generate_ulid()
    pk_id = generate_pk_id("test_nova", "abc123def456")
    
    variant_data = VariantBase(
        variant_id=variant_id,
        pk_id=pk_id,
        soul_id="test_nova",
        asset_url="https://example.com/image.gif",
        storage_key="gs://bucket/path/image.gif",
        seed=12345,
        phash=67890,
        meta_json={"frame_count": 12, "duration": 1.0},
        updated_at_ts=now_ms()
    )
    
    VariantDAL.create(db, variant_data)
    print("OK 变体创建成功")
    
    # 获取变体
    retrieved_variant = VariantDAL.get_by_id(db, variant_id)
    assert retrieved_variant is not None
    assert retrieved_variant.variant_id == variant_id
    print("OK 变体获取成功")


def test_user_seen_operations():
    """测试用户已看操作"""
    print("测试用户已看操作...")
    
    db = next(get_db())
    
    variant_id = generate_ulid()
    user_id = "user123"
    
    # 标记已看
    UserSeenDAL.mark_seen(db, user_id, variant_id)
    print("OK 用户已看标记成功")
    
    # 检查是否已看
    is_seen = UserSeenDAL.is_seen(db, user_id, variant_id)
    assert is_seen is True
    print("OK 用户已看检查成功")
    
    # 获取已看变体
    seen_variants = UserSeenDAL.get_seen_variants(db, user_id)
    assert variant_id in seen_variants
    print("OK 用户已看变体获取成功")


def test_landmark_log_operations():
    """测试地标日志操作"""
    print("测试地标日志操作...")
    
    db = next(get_db())
    
    # 记录地标使用
    log_data = LandmarkLogBase(
        soul_id="test_nova",
        city_key="paris",
        landmark_key="eiffel_tower",
        user_id="user123",
        used_at_ts=now_ms()
    )
    
    LandmarkLogDAL.log_usage(db, log_data)
    print("OK 地标使用记录成功")
    
    # 获取已使用地标
    used_landmarks = LandmarkLogDAL.get_used_landmarks(db, "test_nova", "paris", "user123")
    assert "eiffel_tower" in used_landmarks
    print("OK 已使用地标获取成功")


def test_work_lock_operations():
    """测试工作锁操作"""
    print("测试工作锁操作...")
    
    db = next(get_db())
    
    lock_key = "test_nova|penguin"
    owner_id = generate_ulid()
    
    # 获取锁
    acquired = WorkLockDAL.acquire_lock(db, lock_key, owner_id, 60)
    assert acquired is True
    print("OK 工作锁获取成功")
    
    # 释放锁
    released = WorkLockDAL.release_lock(db, lock_key, owner_id)
    assert released is True
    print("OK 工作锁释放成功")


def test_idempotency_operations():
    """测试幂等性操作"""
    print("测试幂等性操作...")
    
    db = next(get_db())
    
    idem_key = f"test_{generate_ulid()}"
    result_data = {"status": "success", "variant_id": generate_ulid()}
    
    # 存储结果
    IdempotencyDAL.store_result(db, idem_key, result_data)
    print("OK 幂等性结果存储成功")
    
    # 获取结果
    retrieved_result = IdempotencyDAL.get_result(db, idem_key)
    assert retrieved_result is not None
    assert retrieved_result["status"] == "success"
    print("OK 幂等性结果获取成功")


def run_all_tests():
    """运行所有测试"""
    print("开始数据库功能测试...\n")
    
    try:
        test_soul_operations()
        print()
        
        test_style_profile_operations()
        print()
        
        test_prompt_key_operations()
        print()
        
        test_variant_operations()
        print()
        
        test_user_seen_operations()
        print()
        
        test_landmark_log_operations()
        print()
        
        test_work_lock_operations()
        print()
        
        test_idempotency_operations()
        print()
        
        print("SUCCESS 所有测试通过！数据库功能正常。")
        
    except Exception as e:
        print(f"ERROR 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
