"""
测试AI模型集成
"""
import asyncio
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from app.logic.service_image import ImageGenerationService
from app.logic.ai_model_service import get_ai_service
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
    
    print("测试数据设置完成")


async def test_ai_model_service():
    """测试AI模型服务"""
    print("\n=== 测试AI模型服务 ===")
    
    try:
        # 获取AI服务实例
        ai_service = get_ai_service()
        print(f"AI服务初始化成功，使用设备: {ai_service.device}")
        
        # 测试图像生成
        print("\n1. 测试图像生成")
        result = await ai_service.generate_image(
            positive_prompt="a beautiful anime girl, cute, pastel colors",
            negative_prompt="blurry, low quality, realistic",
            soul_id="nova",
            variant_id="test_variant_001",
            seed=42,
            num_inference_steps=10,  # 减少步数以加快测试
            width=512,  # 减小尺寸以加快测试
            height=512
        )
        
        print(f"图像生成结果: {result}")
        print(f"文件路径: {result['filepath']}")
        print(f"文件大小: {result['file_size']} bytes")
        print(f"图像尺寸: {result['width']}x{result['height']}")
        
        print("OK AI模型服务测试完成")
        
    except Exception as e:
        print(f"ERROR AI模型服务测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_integrated_image_generation():
    """测试集成的图像生成功能"""
    print("\n=== 测试集成的图像生成功能 ===")
    
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
            db, "nova", "a cute penguin in garden", "user1"
        )
        print(f"结果1: {result1}")
        print(f"URL: {result1['url']}")
        
        # 测试2: 自拍功能
        print("\n2. 测试自拍功能")
        selfie_result = await service.create_selfie(
            db, "nova", "paris", "happy", "user1"
        )
        print(f"自拍结果: {selfie_result}")
        print(f"自拍URL: {selfie_result['url']}")
        
        print("OK 集成图像生成功能测试完成")
        
    except Exception as e:
        print(f"ERROR 集成图像生成功能测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_model_config():
    """测试模型配置"""
    print("\n=== 测试模型配置 ===")
    
    try:
        from app.logic.ai_model_service import ModelConfig
        
        config = ModelConfig()
        print(f"模型路径: {config.get_model_path()}")
        print(f"输出目录: {config.get_output_dir()}")
        print(f"默认参数: {config.get_default_params()}")
        
        # 检查模型文件是否存在
        model_path = config.get_model_path()
        if os.path.exists(model_path):
            print(f"OK 模型文件存在: {model_path}")
        else:
            print(f"WARNING 模型文件不存在: {model_path}")
        
        print("OK 模型配置测试完成")
        
    except Exception as e:
        print(f"ERROR 模型配置测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("开始AI模型集成测试...")
    print("=" * 50)
    
    # 测试模型配置
    await test_model_config()
    
    # 测试AI模型服务
    await test_ai_model_service()
    
    # 测试集成的图像生成功能
    await test_integrated_image_generation()
    
    print("\n" + "=" * 50)
    print("所有测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
