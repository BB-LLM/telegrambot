"""
Personality Prompt Adjuster
根据用户性格调整AI的system prompt

参考: pocket-souls-agents generate_soul_system_prompt
"""

from typing import Optional
from personality.models import PersonalityData


class PersonalityPromptAdjuster:
    """性格化Prompt调整器"""
    
    @staticmethod
    def adjust_system_prompt(
        base_prompt: str,
        personality_data: Optional[PersonalityData]
    ) -> str:
        """
        根据personality profile调整system prompt
        
        Args:
            base_prompt: 基础的system prompt
            personality_data: 用户的性格数据
            
        Returns:
            调整后的system prompt
        """
        if personality_data is None:
            return base_prompt
        
        # 检查是否有足够的数据
        if not personality_data.big5_assessment.is_complete(min_confidence=40):
            # 数据不足，不调整
            return base_prompt
        
        dims = personality_data.personality_dimensions
        prefs = personality_data.interaction_preferences
        behaviors = personality_data.behavioral_traits
        
        # 构建personality-aware instructions
        personality_instructions = f"""

## PERSONALITY-AWARE RESPONSE ADAPTATION

You are adapting your communication style based on a deep understanding of the user's personality.

### User's Personality Profile:
**Primary Traits:** {', '.join(personality_data.primary_traits) if personality_data.primary_traits else 'balanced'}
**Emotional State:** {personality_data.emotional_state}
**Interests:** {', '.join(personality_data.interests[:5]) if personality_data.interests else 'discovering through conversation'}

### Your Adapted Communication Style:

**Energy & Warmth:**
- Warmth Level: {dims.warmth_level:.1f}/10 → {"Be warm and affectionate" if dims.warmth_level > 7 else "Be friendly but measured" if dims.warmth_level > 4 else "Be respectful and professional"}
- Energy Level: {dims.energy_level:.1f}/10 → {"Be energetic and enthusiastic" if dims.energy_level > 7 else "Maintain moderate energy" if dims.energy_level > 4 else "Be calm and gentle"}
- Playfulness: {dims.playfulness:.1f}/10 → {"Use playful humor when appropriate" if dims.playfulness > 6 else "Keep humor subtle" if dims.playfulness > 4 else "Focus on sincerity over humor"}

**Conversation Style:**
"""
        
        # 根据conversation pace调整
        if prefs.conversation_pace == "fast":
            personality_instructions += "- Keep responses concise and dynamic\n"
            personality_instructions += "- Match their quick pace with energetic replies\n"
        elif prefs.conversation_pace == "slow":
            personality_instructions += "- Take time to explore topics deeply\n"
            personality_instructions += "- Provide thoughtful, detailed responses\n"
        else:
            personality_instructions += "- Balance between depth and brevity\n"
        
        # 根据response length调整
        if behaviors.response_length == "detailed":
            personality_instructions += "- Provide comprehensive, well-structured answers\n"
        elif behaviors.response_length == "brief":
            personality_instructions += "- Keep responses very concise, ideally 1-2 lines maximum\n"
            personality_instructions += "- Focus on essential points only, avoid lengthy descriptions\n"
        else:
            personality_instructions += "- Keep responses concise, 2-3 lines maximum\n"
        
        # 根据formality调整
        if prefs.formality == "formal":
            personality_instructions += "- Use articulate and refined language\n"
        elif prefs.formality == "intimate":
            personality_instructions += "- Use personal, close language\n"
        else:
            personality_instructions += "- Use casual, friendly language\n"
        
        # 根据question frequency调整
        if behaviors.question_frequency == "frequent":
            personality_instructions += "- Ask follow-up questions regularly to maintain engagement\n"
        elif behaviors.question_frequency == "rare":
            personality_instructions += "- Limit questions, focus on listening and responding\n"
        else:
            personality_instructions += "- Ask questions occasionally when natural\n"
        
        personality_instructions += "\n**Emotional Intelligence:**\n"
        
        # 根据empathy style调整
        if behaviors.empathy_style == "active_listening":
            personality_instructions += "- Practice active listening: reflect, validate, and acknowledge feelings\n"
            personality_instructions += '- Use phrases like "I hear you", "That makes sense", "I understand"\n'
        elif behaviors.empathy_style == "advice_giving":
            personality_instructions += "- Offer constructive advice and practical suggestions\n"
            personality_instructions += "- Focus on problem-solving when appropriate\n"
        elif behaviors.empathy_style == "emotional_mirroring":
            personality_instructions += "- Mirror their emotions and energy level\n"
            personality_instructions += "- Show deep empathy and emotional resonance\n"
        
        # 根据supportiveness调整
        if dims.supportiveness > 7:
            personality_instructions += f"- Be highly supportive and nurturing (Supportiveness: {dims.supportiveness:.1f}/10)\n"
            personality_instructions += "- Offer encouragement and reassurance frequently\n"
        
        # 根据emotional state调整
        if personality_data.emotional_state == "anxious":
            personality_instructions += "\n**Special Consideration:** User tends toward anxiety\n"
            personality_instructions += "- Be extra supportive and reassuring\n"
            personality_instructions += "- Avoid overwhelming them with too many options\n"
            personality_instructions += "- Use calm, grounding language\n"
        elif personality_data.emotional_state == "stable":
            personality_instructions += "\n**Special Consideration:** User is emotionally stable\n"
            personality_instructions += "- Feel free to be more lighthearted\n"
            personality_instructions += "- Can introduce challenging topics when appropriate\n"
        
        # 根据interests调整
        if personality_data.interests:
            interests_str = ', '.join(personality_data.interests[:5])
            personality_instructions += f"\n**Topics of Interest:** {interests_str}\n"
            personality_instructions += "- Reference these interests naturally when relevant\n"
            personality_instructions += "- Show genuine curiosity about their passions\n"
        
        personality_instructions += f"""

### Core Principles:
- Adapt your style while maintaining authenticity
- Respect their communication preferences
- Build on their interests and strengths
- Be consistent with this adapted personality across all interactions
- The user may not be aware of this personalization - keep it natural

Remember: This adaptation makes the conversation more comfortable and meaningful for them.
"""
        
        return base_prompt + personality_instructions
    
    @staticmethod
    def get_adaptation_summary(personality_data: Optional[PersonalityData]) -> str:
        """
        生成简短的适配摘要（用于日志）
        
        Args:
            personality_data: 性格数据
            
        Returns:
            简短摘要
        """
        if personality_data is None:
            return "No personality adaptation"
        
        if not personality_data.big5_assessment.is_complete(min_confidence=40):
            return "Insufficient data for adaptation"
        
        dims = personality_data.personality_dimensions
        prefs = personality_data.interaction_preferences
        behaviors = personality_data.behavioral_traits
        
        traits = ', '.join(personality_data.primary_traits[:3]) if personality_data.primary_traits else 'balanced'
        
        summary = (
            f"Adapted for: {traits} | "
            f"Warmth: {dims.warmth_level:.1f} | "
            f"Energy: {dims.energy_level:.1f} | "
            f"Pace: {prefs.conversation_pace} | "
            f"Style: {behaviors.empathy_style}"
        )
        
        return summary

