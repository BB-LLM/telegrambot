"""
完整核心功能测试套件
"""
import asyncio
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from app.logic.service_image import ImageGenerationService
from app.logic.prompt_cache import PromptCache, PromptBuilder
from app.logic.place_chooser import PlaceChooser
from app.data.dal import get_db, SoulDAL, SoulStyleProfileDAL
from app.data.models import SoulBase, SoulStyleProfileBase
from app.core.lww import now_ms


async def setup_test_data(db):
    """设置测试数据"""
    print("设置测试数据...")
    
    # 创建Nova Soul
    nova_soul = SoulBase(
        soul_id="nova",
        display_name="Nova",
        updated_at_ts=now_ms()
    )
    SoulDAL.create(db, nova_soul)
    
    # 创建Nova风格配置
    nova_style = SoulStyleProfileBase(
        soul_id="nova",
        base_model_ref="dreamshaper_8",
        lora_ids_json=["anime_style@v1", "pastel_colors@v2", "cute_character@v1"],
        palette_json={"primary": "#FFB6C1", "secondary": "#87CEEB"},
        negatives_json=["blurry", "low quality", "realistic", "photorealistic"],
        motion_module="animate_diff_v1",
        extra_json={"strength": 0.8},
        updated_at_ts=now_ms()
    )
    SoulStyleProfileDAL.upsert(db, nova_style)
    
    # 创建Valentina Soul
    valentina_soul = SoulBase(
        soul_id="valentina",
        display_name="Valentina",
        updated_at_ts=now_ms()
    )
    SoulDAL.create(db, valentina_soul)
    
    # 创建Valentina风格配置
    valentina_style = SoulStyleProfileBase(
        soul_id="valentina",
        base_model_ref="realistic_vision_v5",
        lora_ids_json=["realistic_portrait@v2", "elegant_style@v1"],
        palette_json={"primary": "#8B4513", "secondary": "#2F4F4F"},
        negatives_json=["cartoon", "anime", "childish", "bright"],
        motion_module="static_diff_v1",
        extra_json={"strength": 0.9},
        updated_at_ts=now_ms()
    )
    SoulStyleProfileDAL.upsert(db, valentina_style)
    
    print("测试数据设置完成")


async def test_prompt_cache():
    """测试提示词缓存功能"""
    print("\n=== 测试提示词缓存功能 ===")
    
    db = next(get_db())
    cache = PromptCache()
    
    try:
        # 测试1: 风格标签提取
        print("\n1. 测试风格标签提取")
        nova_tags = cache._get_soul_style_tags(db, "nova")
        valentina_tags = cache._get_soul_style_tags(db, "valentina")
        print(f"Nova风格标签: {nova_tags}")
        print(f"Valentina风格标签: {valentina_tags}")
        
        # 测试2: 提示词标准化
        print("\n2. 测试提示词标准化")
        cue1 = "penguin in garden"
        normalized1 = cache.normalize_cue(cue1, "nova", db)
        print(f"原始提示词: {cue1}")
        print(f"标准化后: {normalized1}")
        
        cue2 = "penguin garden"
        normalized2 = cache.normalize_cue(cue2, "nova", db)
        print(f"原始提示词: {cue2}")
        print(f"标准化后: {normalized2}")
        
        # 测试3: 缓存键生成
        print("\n3. 测试缓存键生成")
        key_norm, key_hash, pk_id = cache.generate_cache_key("penguin in garden", "nova", db)
        print(f"缓存键: {pk_id}")
        print(f"键哈希: {key_hash}")
        
        print("OK 提示词缓存功能测试完成")
        
    except Exception as e:
        print(f"ERROR 提示词缓存测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_prompt_builder():
    """测试提示词构建器"""
    print("\n=== 测试提示词构建器 ===")
    
    db = next(get_db())
    builder = PromptBuilder()
    
    try:
        # 测试1: Nova提示词构建
        print("\n1. 测试Nova提示词构建")
        positive, negative = builder.build_prompt("nova", "penguin in garden", db)
        print(f"Nova正面提示词: {positive}")
        print(f"Nova负面提示词: {negative}")
        
        # 测试2: Valentina提示词构建
        print("\n2. 测试Valentina提示词构建")
        positive, negative = builder.build_prompt("valentina", "penguin in garden", db)
        print(f"Valentina正面提示词: {positive}")
        print(f"Valentina负面提示词: {negative}")
        
        # 测试3: 自拍提示词构建
        print("\n3. 测试自拍提示词构建")
        selfie_positive, selfie_negative = builder.build_selfie_prompt(
            "nova", "paris", "eiffel_tower", "happy", db
        )
        print(f"自拍正面提示词: {selfie_positive}")
        print(f"自拍负面提示词: {selfie_negative}")
        
        print("OK 提示词构建器测试完成")
        
    except Exception as e:
        print(f"ERROR 提示词构建器测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_place_chooser():
    """测试地标选择功能"""
    print("\n=== 测试地标选择功能 ===")
    
    chooser = PlaceChooser()
    
    try:
        # 测试1: 城市支持检查
        print("\n1. 测试城市支持检查")
        print(f"巴黎是否支持: {chooser.is_city_supported('paris')}")
        print(f"东京是否支持: {chooser.is_city_supported('tokyo')}")
        print(f"北京是否支持: {chooser.is_city_supported('beijing')}")
        
        # 测试2: 地标列表获取
        print("\n2. 测试地标列表获取")
        paris_landmarks = chooser.get_city_landmarks("paris")
        tokyo_landmarks = chooser.get_city_landmarks("tokyo")
        print(f"巴黎地标: {paris_landmarks}")
        print(f"东京地标: {tokyo_landmarks}")
        
        # 测试3: 地标描述获取
        print("\n3. 测试地标描述获取")
        description1 = chooser.get_landmark_description("eiffel_tower")
        description2 = chooser.get_landmark_description("tokyo_tower")
        print(f"埃菲尔铁塔描述: {description1}")
        print(f"东京塔描述: {description2}")
        
        print("OK 地标选择功能测试完成")
        
    except Exception as e:
        print(f"ERROR 地标选择功能测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_image_generation():
    """测试图像生成功能"""
    print("\n=== 测试图像生成功能 ===")
    
    # 获取数据库会话
    db = next(get_db())
    
    # 确保有测试数据
    await setup_test_data(db)
    
    # 创建服务实例
    service = ImageGenerationService()
    
    try:
        # 测试1: 灵魂风格图像生成
        print("\n1. 测试灵魂风格图像生成")
        result1 = await service.get_or_create_variant(
            db, "nova", "penguin in garden", "user1"
        )
        print(f"结果1: {result1}")
        
        # 测试2: 相同用户再次请求（应该获得不同变体）
        print("\n2. 测试相同用户再次请求")
        result2 = await service.get_or_create_variant(
            db, "nova", "penguin in garden", "user1"
        )
        print(f"结果2: {result2}")
        print(f"变体是否不同: {result1['variant_id'] != result2['variant_id']}")
        
        # 测试3: 不同用户请求相同内容（可能获得缓存）
        print("\n3. 测试不同用户请求相同内容")
        result3 = await service.get_or_create_variant(
            db, "nova", "penguin in garden", "user2"
        )
        print(f"结果3: {result3}")
        
        # 测试4: Valentina风格生成
        print("\n4. 测试Valentina风格生成")
        valentina_result = await service.get_or_create_variant(
            db, "valentina", "penguin in garden", "user1"
        )
        print(f"Valentina结果: {valentina_result}")
        
        # 测试5: 自拍功能
        print("\n5. 测试自拍功能")
        selfie_result = await service.create_selfie(
            db, "nova", "paris", "happy", "user1"
        )
        print(f"自拍结果: {selfie_result}")
        
        # 测试6: 相同用户再次自拍（应该选择不同地标）
        print("\n6. 测试相同用户再次自拍")
        selfie_result2 = await service.create_selfie(
            db, "nova", "paris", "happy", "user1"
        )
        print(f"自拍结果2: {selfie_result2}")
        print(f"地标是否不同: {selfie_result['landmark_key'] != selfie_result2['landmark_key']}")
        
        # 测试7: 不同城市自拍
        print("\n7. 测试不同城市自拍")
        tokyo_selfie = await service.create_selfie(
            db, "nova", "tokyo", "excited", "user1"
        )
        print(f"东京自拍结果: {tokyo_selfie}")
        
        print("OK 图像生成功能测试完成")
        
    except Exception as e:
        print(f"ERROR 图像生成功能测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_database_operations():
    """测试数据库操作"""
    print("\n=== 测试数据库操作 ===")
    
    db = next(get_db())
    
    try:
        # 测试1: Soul创建和获取
        print("\n1. 测试Soul创建和获取")
        nova_soul = SoulDAL.get_by_id(db, "nova")
        valentina_soul = SoulDAL.get_by_id(db, "valentina")
        print(f"Nova Soul: {nova_soul.display_name if nova_soul else 'Not found'}")
        print(f"Valentina Soul: {valentina_soul.display_name if valentina_soul else 'Not found'}")
        
        # 测试2: 风格配置获取
        print("\n2. 测试风格配置获取")
        nova_style = SoulStyleProfileDAL.get_by_soul_id(db, "nova")
        valentina_style = SoulStyleProfileDAL.get_by_soul_id(db, "valentina")
        print(f"Nova风格: {nova_style.base_model_ref if nova_style else 'Not found'}")
        print(f"Valentina风格: {valentina_style.base_model_ref if valentina_style else 'Not found'}")
        
        if nova_style:
            print(f"  Nova LoRA数量: {len(nova_style.lora_ids_json)}")
            print(f"  Nova负面词数量: {len(nova_style.negatives_json)}")
        
        if valentina_style:
            print(f"  Valentina LoRA数量: {len(valentina_style.lora_ids_json)}")
            print(f"  Valentina负面词数量: {len(valentina_style.negatives_json)}")
        
        print("OK 数据库操作测试完成")
        
    except Exception as e:
        print(f"ERROR 数据库操作测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("开始完整核心功能测试...")
    print("=" * 50)
    
    # 测试数据库操作
    await test_database_operations()
    
    # 测试提示词缓存
    await test_prompt_cache()
    
    # 测试提示词构建器
    await test_prompt_builder()
    
    # 测试地标选择
    await test_place_chooser()
    
    # 测试图像生成
    await test_image_generation()
    
    print("\n" + "=" * 50)
    print("所有测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())


