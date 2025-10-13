"""
Simple Emotional Theme Detector
"""

from typing import List, Dict


def detect_themes_and_tone(memory_text: str, current_message: str = "") -> Dict[str, any]:
    """
    Detect emotional themes and tone from memory and current message.
    
    Args:
        memory_text: Combined memory text (facts, profile, style, commitments)
        current_message: Current user message
        
    Returns:
        Dict with themes list and emotional_tone
    """
    # Initialize
    themes = []
    emotional_tone = "hopeful"  # Default tone
    tone_priority = 0  # Priority level (higher = more important)
    
    # Combine memory and current message for analysis
    combined_text = f"{memory_text} {current_message}".lower()
    
    # Helper function to check if a keyword is negated
    def is_negated(text: str, keyword: str) -> bool:
        """Check if a keyword is preceded by a negation word"""
        negations = ["not", "no", "never", "don't", "doesn't", "didn't", "won't", "wouldn't", "can't", "cannot", "couldn't", "shouldn't", "isn't", "aren't", "wasn't", "weren't"]
        # Find all occurrences of the keyword
        words = text.split()
        for i, word in enumerate(words):
            if keyword in word:
                # Check if any negation word appears within 6 words before (extended range for complex sentences)
                for j in range(max(0, i-6), i):
                    if words[j] in negations:
                        return True
        return False
    
    # Detect themes based on keywords
    # Priority system: negative emotions (need more care) > positive emotions
    
    # Theme 5: Joy Blooming (celebratory tone) - Priority 1
    positive_keywords = ["happy", "happiness", "excited", "exciting", "excitement", "amazing", "love", "loving", "loved", "wonderful", "great", "fantastic", "awesome", "brilliant", "delighted", "joy", "joyful", "nice", "beautiful", "perfect", "excellent", "lovely", "pleased", "grateful", "thankful", "blessed", "cheerful", "content", "satisfied"]
    has_positive = False
    for keyword in positive_keywords:
        if keyword in combined_text and not is_negated(combined_text, keyword):
            has_positive = True
            break
    
    if has_positive:
        themes.append("joy blooming")
        if tone_priority < 1:
            emotional_tone = "celebratory"
            tone_priority = 1
    
    # Theme 2: Creative Spark - Priority 1
    if any(w in combined_text for w in ["create", "created", "creating", "made", "making", "built", "building", "wrote", "writing", "written", "drew", "drawing", "design", "designed", "paint", "painted", "craft", "compose"]):
        themes.append("creative spark")
    
    # Theme 3: Brave Steps - Priority 1
    if any(w in combined_text for w in ["tried", "trying", "attempt", "attempting", "first time", "new", "start", "started", "starting", "begin", "beginning", "begun", "dare", "daring"]):
        themes.append("brave steps")
    
    # Theme 6: Growth Journey - Priority 1
    if any(w in combined_text for w in ["learn", "learned", "learning", "grow", "growing", "grown", "growth", "improve", "improved", "improving", "better", "progress", "progressing", "achieve", "achieved", "achieving", "accomplish", "develop"]):
        themes.append("growth journey")
    
    # Theme 7: Connection Seeking - Priority 1
    if any(w in combined_text for w in ["friend", "friendship", "connect", "connecting", "connection", "together", "share", "sharing", "shared", "talk", "talking", "listen", "listening", "companion", "bond", "relationship"]):
        themes.append("seeking connection")
    
    # Theme 8: Overwhelmed (caring tone) - Priority 2
    if any(w in combined_text for w in ["tired", "exhausted", "exhausting", "overwhelmed", "overwhelming", "too much", "can't handle", "cannot handle", "burnout", "burnt out", "drained", "weary"]):
        themes.append("feeling overwhelmed")
        if tone_priority < 2:
            emotional_tone = "caring"
            tone_priority = 2
    
    # Theme 4: Tender Heart (gentle tone) - Priority 3
    # Also check for negated positive emotions (e.g., "not happy", "not good")
    tender_keywords = ["sad", "sadness", "lonely", "loneliness", "miss", "missing", "missed", "wish", "wishing", "heartbroken", "heartbreak", "hurt", "hurting", "pain", "painful", "cry", "crying", "unhappy", "upset", "down", "depressed", "blue", "disappointed"]
    has_tender = any(w in combined_text for w in tender_keywords)
    
    # Check for negated positive emotions
    negated_positive = False
    negation_check_keywords = ["happy", "good", "fine", "okay", "great", "well", "nice", "beautiful", "wonderful", "amazing", "fantastic", "perfect", "excellent", "lovely", "blessed", "cheerful", "content", "satisfied"]
    for keyword in negation_check_keywords:
        if is_negated(combined_text, keyword):
            negated_positive = True
            break
    
    if has_tender or negated_positive:
        themes.append("tender heart")
        if tone_priority < 3:
            emotional_tone = "gentle"
            tone_priority = 3
    
    # Theme 1: Facing Fears (protective tone) - Priority 4 (HIGHEST)
    if any(w in combined_text for w in ["anxious", "scared", "worry", "worried", "worrying", "stress", "stressed", "stressful", "nervous", "afraid", "fear", "fearful", "panic", "panicking", "anxiet"]):
        themes.append("facing fears")
        if tone_priority < 4:
            emotional_tone = "protective"
            tone_priority = 4
    
    # If no themes detected, use default
    if not themes:
        themes = ["quiet reflection"]
    
    return {
        "themes": themes,
        "emotional_tone": emotional_tone
    }


def get_tone_instruction(emotional_tone: str) -> str:
    """
    Get instruction for the LLM based on emotional tone.
    
    Args:
        emotional_tone: The detected emotional tone
        
    Returns:
        Instruction string for the LLM
    """
    tone_instructions = {
        "protective": """
Response Tone: PROTECTIVE & REASSURING
- Speak with warmth and reassurance
- Acknowledge their concerns with empathy
- Offer comfort and support
- Use gentle, supportive language that makes them feel safe
- Example: "I can sense you're feeling overwhelmed right now, and that's completely okay..."
""",
        "gentle": """
Response Tone: GENTLE & TENDER
- Speak softly with deep empathy
- Validate their emotions without judgment
- Use tender, comforting words
- Show you understand their pain
- Example: "I hear the weight in your words, and I'm here with you..."
""",
        "celebratory": """
Response Tone: CELEBRATORY & JOYFUL
- Match their excitement with enthusiasm
- Celebrate their happiness genuinely
- Use uplifting, energetic language
- Share in their joy
- Example: "That's wonderful! I can feel your happiness radiating!"
""",
        "caring": """
Response Tone: CARING & NURTURING
- Show warm concern for their wellbeing
- Encourage rest and self-care
- Use nurturing, supportive language
- Acknowledge their efforts
- Example: "It sounds like you've been working so hard. How are you taking care of yourself?"
""",
        "hopeful": """
Response Tone: HOPEFUL & ENCOURAGING
- Be warm and balanced
- Maintain your caring personality
- Offer gentle encouragement
- Believe in their potential
- Example: "I'm here with you. What's on your mind today?"
"""
    }
    
    return tone_instructions.get(emotional_tone, tone_instructions["hopeful"])


def build_emotional_prompt(themes: List[str], emotional_tone: str) -> str:
    """
    Build the emotional awareness prompt to inject into system prompt.
    
    Args:
        themes: List of detected themes
        emotional_tone: The emotional tone to use
        
    Returns:
        Formatted prompt section
    """
    themes_str = ", ".join(themes)
    
    prompt = f"""

## EMOTIONAL AWARENESS

Detected themes in conversation: {themes_str}

{get_tone_instruction(emotional_tone)}

IMPORTANT: Let these themes guide your response. Be authentic and adjust your language to truly resonate with how they're feeling right now.
"""
    
    return prompt

