"""
Create three new Soul characters: Li Zhe, Lin Na, Wang Jing
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.data.dal import get_db, SoulDAL, SoulStyleProfileDAL
from app.data.models import SoulBase, SoulStyleProfileBase
from app.core.lww import now_ms


def create_lizhe_soul(db):
    """Create Li Zhe Soul - INTJ, 30-year-old Data Analyst"""
    print("\n=== Creating Li Zhe Soul ===")
    
    # Soul basic info
    lizhe_soul = SoulBase(
        soul_id="lizhe",
        display_name="Li Zhe",
        updated_at_ts=now_ms()
    )
    SoulDAL.create(db, lizhe_soul)
    print("✓ Soul basic info created")
    
    # Soul style profile
    lizhe_style = SoulStyleProfileBase(
        soul_id="lizhe",
        base_model_ref="realistic_vision_v5",
        lora_ids_json=[
            "professional_style@v1",
            "minimalist_fashion@v1",
            "business_casual@v1",
            "modern_sophisticated@v1"
        ],
        palette_json={
            "primary": "#4A4A4A",      # Dark gray (suit)
            "secondary": "#FFFFFF",     # White (shirt)
            "accent": "#000000",        # Black (pants, shoes)
            "metal": "#C0C0C0"          # Silver (watch, glasses)
        },
        negatives_json=[
            "cartoon",
            "anime",
            "childish",
            "bright colors",
            "casual",
            "sportswear",
            "decorative",
            "excessive accessories",
            "colorful",
            "playful",
            "messy",
            "disorganized"
        ],
        motion_module="static_diff_v1",
        extra_json={
            "strength": 0.85,
            "age": 30,
            "gender": "male",
            "personality": "INTJ",
            "profession": "data_analyst",
            "style_keywords": ["professional", "minimalist", "sophisticated", "functional", "elegant"],
            "clothing_style": {
                "suit": "dark gray fitted suit jacket",
                "shirt": "white cotton shirt",
                "pants": "black fitted trousers",
                "shoes": "polished leather dress shoes",
                "accessories": ["silver smartwatch", "black frame glasses"]
            },
            "hair_style": "neat short hair",
            "overall_theme": "minimalist professional, clean and neat, functional, understated elegance"
        },
        updated_at_ts=now_ms()
    )
    SoulStyleProfileDAL.upsert(db, lizhe_style)
    print("✓ Soul style profile created")
    print("  Style: Minimalist Professional, Business Elite")


def create_linna_soul(db):
    """Create Lin Na Soul - ESFP, 25-year-old Freelance Party Planner"""
    print("\n=== Creating Lin Na Soul ===")
    
    # Soul basic info
    linna_soul = SoulBase(
        soul_id="linna",
        display_name="Lin Na",
        updated_at_ts=now_ms()
    )
    SoulDAL.create(db, linna_soul)
    print("✓ Soul basic info created")
    
    # Soul style profile
    linna_style = SoulStyleProfileBase(
        soul_id="linna",
        base_model_ref="dreamshaper_8",
        lora_ids_json=[
            "fashion_style@v1",
            "vibrant_colors@v1",
            "casual_chic@v1",
            "bohemian_style@v1",
            "party_style@v1"
        ],
        palette_json={
            "primary": "#FFD700",      # Bright yellow (top)
            "secondary": "#4169E1",     # Blue (denim shorts)
            "accent": "#FF69B4",        # Pink (decorations)
            "vibrant": "#FF4500"        # Orange-red (energy)
        },
        negatives_json=[
            "dark",
            "gloomy",
            "formal",
            "business",
            "minimalist",
            "monochrome",
            "serious",
            "professional",
            "boring",
            "plain"
        ],
        motion_module="animate_diff_v1",
        extra_json={
            "strength": 0.8,
            "age": 25,
            "gender": "female",
            "personality": "ESFP",
            "profession": "party_planner",
            "style_keywords": ["fashionable", "vibrant", "colorful", "energetic", "playful", "casual"],
            "clothing_style": {
                "top": "bright yellow off-shoulder knit top",
                "bottom": "high-waisted denim shorts",
                "shoes": "colorful sneakers",
                "hat": "wide-brimmed straw hat with handmade flower decorations",
                "accessories": ["multi-layer colorful beaded necklace", "large earrings", "friendship bracelet"]
            },
            "hair_style": "messy braids",
            "makeup": "bright makeup",
            "overall_theme": "fashionable and individual, full of vitality, colorful, casual and passionate"
        },
        updated_at_ts=now_ms()
    )
    SoulStyleProfileDAL.upsert(db, linna_style)
    print("✓ Soul style profile created")
    print("  Style: Fashionable Individual, Energetic")


def create_wangjing_soul(db):
    """Create Wang Jing Soul - INFJ, 28-year-old Psychologist"""
    print("\n=== Creating Wang Jing Soul ===")
    
    # Soul basic info
    wangjing_soul = SoulBase(
        soul_id="wangjing",
        display_name="Wang Jing",
        updated_at_ts=now_ms()
    )
    SoulDAL.create(db, wangjing_soul)
    print("✓ Soul basic info created")
    
    # Soul style profile
    wangjing_style = SoulStyleProfileBase(
        soul_id="wangjing",
        base_model_ref="realistic_vision_v5",
        lora_ids_json=[
            "comfortable_style@v1",
            "soft_elegant@v1",
            "natural_beauty@v1",
            "gentle_feminine@v1",
            "minimalist_comfort@v1"
        ],
        palette_json={
            "primary": "#87CEEB",       # Light blue (dress)
            "secondary": "#F5F5DC",     # Beige (cardigan)
            "accent": "#C0C0C0",        # Silver (necklace)
            "soft": "#E6E6FA"           # Lavender (soft)
        },
        negatives_json=[
            "bright",
            "flashy",
            "loud",
            "excessive",
            "overdecorated",
            "formal",
            "stiff",
            "harsh",
            "aggressive",
            "bold patterns"
        ],
        motion_module="static_diff_v1",
        extra_json={
            "strength": 0.82,
            "age": 28,
            "gender": "female",
            "personality": "INFJ",
            "profession": "psychologist",
            "style_keywords": ["comfortable", "gentle", "soft", "meaningful", "calm", "peaceful"],
            "clothing_style": {
                "dress": "light blue linen long dress with cloud pattern embroidery",
                "cardigan": "beige knit cardigan",
                "shoes": "soft-soled flat shoes",
                "accessories": ["silver pendant necklace (engraved with 'Serenity')", "thin frame glasses"]
            },
            "hair_style": "low ponytail",
            "makeup": "natural and elegant",
            "overall_theme": "comfortable and meaningful, soft and understated, inner peace, humanistic care, serene charm"
        },
        updated_at_ts=now_ms()
    )
    SoulStyleProfileDAL.upsert(db, wangjing_style)
    print("✓ Soul style profile created")
    print("  Style: Comfortable and Meaningful, Soft and Serene")


def create_all_souls():
    """Create all three Souls"""
    print("=" * 50)
    print("Starting to create Soul characters...")
    print("=" * 50)
    
    db = next(get_db())
    
    try:
        # Create Li Zhe
        create_lizhe_soul(db)
        
        # Create Lin Na
        create_linna_soul(db)
        
        # Create Wang Jing
        create_wangjing_soul(db)
        
        print("\n" + "=" * 50)
        print("All Souls created successfully!")
        print("=" * 50)
        print("\nCreated Souls list:")
        print("1. Li Zhe (lizhe) - INTJ, 30-year-old Data Analyst")
        print("2. Lin Na (linna) - ESFP, 25-year-old Freelance Party Planner")
        print("3. Wang Jing (wangjing) - INFJ, 28-year-old Psychologist")
        
    except Exception as e:
        print(f"\n✗ Creation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    create_all_souls()