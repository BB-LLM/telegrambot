"""
Test Simple Emotional Theme Detection
测试简单情感主题检测
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from emotional.detector import detect_themes_and_tone, build_emotional_prompt


def test_facing_fears():
    """Test facing fears theme detection"""
    print("\n" + "="*60)
    print("Test 1: Facing Fears (Anxious/Worried)")
    print("="*60)
    
    result = detect_themes_and_tone(
        memory_text="User has been stressed about work deadlines",
        current_message="I'm really worried about tomorrow's presentation"
    )
    
    print(f"Input: 'I'm really worried about tomorrow's presentation'")
    print(f"Themes: {result['themes']}")
    print(f"Tone: {result['emotional_tone']}")
    
    assert "facing fears" in result['themes']
    assert result['emotional_tone'] == "protective"
    print("[PASS] Test passed!")


def test_creative_spark():
    """Test creative spark theme detection"""
    print("\n" + "="*60)
    print("Test 2: Creative Spark")
    print("="*60)
    
    result = detect_themes_and_tone(
        memory_text="User loves art and design",
        current_message="I just finished painting a new landscape"
    )
    
    print(f"Input: 'I just finished painting a new landscape'")
    print(f"Themes: {result['themes']}")
    print(f"Tone: {result['emotional_tone']}")
    
    assert "creative spark" in result['themes']
    print("[PASS] Test passed!")


def test_tender_heart():
    """Test tender heart theme detection"""
    print("\n" + "="*60)
    print("Test 3: Tender Heart (Sad/Lonely)")
    print("="*60)
    
    result = detect_themes_and_tone(
        memory_text="",
        current_message="I miss my friends and feel lonely today"
    )
    
    print(f"Input: 'I miss my friends and feel lonely today'")
    print(f"Themes: {result['themes']}")
    print(f"Tone: {result['emotional_tone']}")
    
    assert "tender heart" in result['themes']
    assert result['emotional_tone'] == "gentle"
    print("[PASS] Test passed!")


def test_joy_blooming():
    """Test joy blooming theme detection"""
    print("\n" + "="*60)
    print("Test 4: Joy Blooming (Happy/Excited)")
    print("="*60)
    
    result = detect_themes_and_tone(
        memory_text="",
        current_message="I'm so excited! This is amazing!"
    )
    
    print(f"Input: 'I'm so excited! This is amazing!'")
    print(f"Themes: {result['themes']}")
    print(f"Tone: {result['emotional_tone']}")
    
    assert "joy blooming" in result['themes']
    assert result['emotional_tone'] == "celebratory"
    print("[PASS] Test passed!")


def test_multiple_themes():
    """Test multiple theme detection"""
    print("\n" + "="*60)
    print("Test 5: Multiple Themes")
    print("="*60)
    
    result = detect_themes_and_tone(
        memory_text="User is an artist who often feels anxious",
        current_message="I'm worried if my new painting is good enough"
    )
    
    print(f"Input: 'I'm worried if my new painting is good enough'")
    print(f"Themes: {result['themes']}")
    print(f"Tone: {result['emotional_tone']}")
    
    assert "facing fears" in result['themes']
    assert "creative spark" in result['themes']
    assert result['emotional_tone'] == "protective"  # First detected tone wins
    print("[PASS] Test passed!")


def test_no_keywords():
    """Test default behavior when no keywords match"""
    print("\n" + "="*60)
    print("Test 6: No Keywords (Default Behavior)")
    print("="*60)
    
    result = detect_themes_and_tone(
        memory_text="",
        current_message="What's the weather like?"
    )
    
    print(f"Input: 'What's the weather like?'")
    print(f"Themes: {result['themes']}")
    print(f"Tone: {result['emotional_tone']}")
    
    assert result['themes'] == ["quiet reflection"]
    assert result['emotional_tone'] == "hopeful"
    print("[PASS] Test passed!")


def test_prompt_building():
    """Test emotional prompt building"""
    print("\n" + "="*60)
    print("Test 7: Prompt Building")
    print("="*60)
    
    result = detect_themes_and_tone(
        memory_text="",
        current_message="I'm anxious about the exam"
    )
    
    prompt = build_emotional_prompt(
        themes=result['themes'],
        emotional_tone=result['emotional_tone']
    )
    
    print(f"Themes: {result['themes']}")
    print(f"Tone: {result['emotional_tone']}")
    print(f"\nGenerated Prompt:")
    print(prompt[:300] + "...")
    
    assert "EMOTIONAL AWARENESS" in prompt
    assert "facing fears" in prompt
    assert "PROTECTIVE" in prompt
    print("[PASS] Test passed!")


def test_overwhelmed():
    """Test feeling overwhelmed theme"""
    print("\n" + "="*60)
    print("Test 8: Feeling Overwhelmed")
    print("="*60)
    
    result = detect_themes_and_tone(
        memory_text="",
        current_message="I'm so tired and overwhelmed with everything"
    )
    
    print(f"Input: 'I'm so tired and overwhelmed with everything'")
    print(f"Themes: {result['themes']}")
    print(f"Tone: {result['emotional_tone']}")
    
    assert "feeling overwhelmed" in result['themes']
    assert result['emotional_tone'] == "caring"
    print("[PASS] Test passed!")


def test_growth_journey():
    """Test growth journey theme"""
    print("\n" + "="*60)
    print("Test 9: Growth Journey")
    print("="*60)
    
    result = detect_themes_and_tone(
        memory_text="",
        current_message="I'm learning to code and making progress every day"
    )
    
    print(f"Input: 'I'm learning to code and making progress every day'")
    print(f"Themes: {result['themes']}")
    print(f"Tone: {result['emotional_tone']}")
    
    assert "growth journey" in result['themes']
    print("[PASS] Test passed!")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Simple Emotional Theme Detection - Test Suite")
    print("="*60)
    
    try:
        test_facing_fears()
        test_creative_spark()
        test_tender_heart()
        test_joy_blooming()
        test_multiple_themes()
        test_no_keywords()
        test_prompt_building()
        test_overwhelmed()
        test_growth_journey()
        
        print("\n" + "="*60)
        print("[SUCCESS] All Tests Passed!")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n[FAIL] Test Failed: {e}")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

