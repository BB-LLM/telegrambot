"""
Personality Profile Generation
基于Big Five评估结果生成完整的性格档案
"""

from typing import List, Dict, Any
from personality.models import PersonalityData, PersonalityDimensions, InteractionPreferences, BehavioralTraits


class PersonalityProfile:
    """性格档案生成器"""
    
    @staticmethod
    def generate_from_big5(personality_data: PersonalityData) -> PersonalityData:
        """
        基于Big Five评估结果生成完整的性格档案
        
        Args:
            personality_data: 包含Big Five评估结果的性格数据
            
        Returns:
            更新后的PersonalityData对象，包含完整的性格档案
        """
        big5 = personality_data.big5_assessment
        dims = personality_data.personality_dimensions
        prefs = personality_data.interaction_preferences
        behaviors = personality_data.behavioral_traits
        
        # 基于Big Five分数生成性格维度
        PersonalityProfile._generate_dimensions(big5, dims)
        
        # 生成交互偏好
        PersonalityProfile._generate_preferences(big5, prefs)
        
        # 生成行为特征
        PersonalityProfile._generate_behaviors(big5, behaviors, personality_data)
        
        # 生成主要性格特征标签
        PersonalityProfile._generate_primary_traits(big5, personality_data)
        
        return personality_data
    
    @staticmethod
    def _generate_dimensions(big5, dims: PersonalityDimensions):
        """生成性格维度 (1-10分制)"""
        # 外向性 -> 能量水平
        if big5.extraversion.score is not None:
            dims.energy_level = big5.extraversion.score / 10.0  # 0-100 转换为 0-10
        
        # 神经质 -> 情感深度 (反向映射，神经质高表示情感敏感)
        if big5.neuroticism.score is not None:
            dims.emotional_depth = big5.neuroticism.score / 10.0
        
        # 开放性 -> 好奇心和开放性
        if big5.openness.score is not None:
            dims.openness = big5.openness.score / 10.0
            dims.curiosity = big5.openness.score / 10.0
        
        # 宜人性 -> 温暖度和支持性
        if big5.agreeableness.score is not None:
            dims.warmth_level = big5.agreeableness.score / 10.0
            dims.supportiveness = big5.agreeableness.score / 10.0
        
        # 外向性和开放性 -> 玩心
        if big5.extraversion.score is not None and big5.openness.score is not None:
            dims.playfulness = (big5.extraversion.score + big5.openness.score) / 20.0
        elif big5.extraversion.score is not None:
            dims.playfulness = big5.extraversion.score / 10.0
        
        # 开放性和尽责性 -> 智慧 (平衡创造力和条理性)
        if big5.openness.score is not None and big5.conscientiousness.score is not None:
            dims.wisdom = (big5.openness.score + big5.conscientiousness.score) / 20.0
        elif big5.conscientiousness.score is not None:
            dims.wisdom = big5.conscientiousness.score / 10.0
    
    @staticmethod
    def _generate_preferences(big5, prefs: InteractionPreferences):
        """生成交互偏好"""
        # 基于外向性设置对话节奏和幽默风格
        if big5.extraversion.score is not None:
            if big5.extraversion.score > 70:
                prefs.conversation_pace = "fast"
                prefs.humor_style = "playful"
            elif big5.extraversion.score < 40:
                prefs.conversation_pace = "slow"
                prefs.humor_style = "gentle"
            else:
                prefs.conversation_pace = "moderate"
                prefs.humor_style = "gentle"
        
        # 基于神经质设置情感表达
        if big5.neuroticism.score is not None:
            if big5.neuroticism.score > 70:
                prefs.emotional_expression = "expressive"
            elif big5.neuroticism.score < 40:
                prefs.emotional_expression = "reserved"
            else:
                prefs.emotional_expression = "balanced"
        
        # 基于开放性和宜人性设置正式程度
        if big5.agreeableness.score is not None:
            if big5.agreeableness.score > 70:
                prefs.formality = "intimate"
            elif big5.agreeableness.score < 40:
                prefs.formality = "formal"
            else:
                prefs.formality = "casual"
    
    @staticmethod
    def _generate_behaviors(big5, behaviors: BehavioralTraits, personality_data: PersonalityData):
        """生成行为特征"""
        # 基于尽责性设置回复长度
        if big5.conscientiousness.score is not None:
            score = big5.conscientiousness.score
            if score > 70:
                behaviors.response_length = "moderate"
                if "organized" not in personality_data.primary_traits:
                    personality_data.primary_traits.append("organized")
            elif score < 40:
                behaviors.response_length = "brief"
            else:
                behaviors.response_length = "brief"
        
        # 基于宜人性设置共情风格
        if big5.agreeableness.score is not None:
            if big5.agreeableness.score > 70:
                behaviors.empathy_style = "emotional_mirroring"
            elif big5.agreeableness.score < 40:
                behaviors.empathy_style = "advice_giving"
            else:
                behaviors.empathy_style = "active_listening"
        
        # 基于开放性设置提问频率
        if big5.openness.score is not None:
            if big5.openness.score > 70:
                behaviors.question_frequency = "frequent"
            elif big5.openness.score < 40:
                behaviors.question_frequency = "rare"
            else:
                behaviors.question_frequency = "occasional"
        
        # 基于宜人性和神经质设置冲突处理方式
        if big5.agreeableness.score is not None:
            if big5.agreeableness.score < 40:
                behaviors.conflict_approach = "direct"
            elif big5.neuroticism.score is not None and big5.neuroticism.score > 70:
                behaviors.conflict_approach = "avoidant"
            else:
                behaviors.conflict_approach = "gentle"
    
    @staticmethod
    def _generate_primary_traits(big5, personality_data: PersonalityData):
        """生成主要性格特征标签"""
        traits = []
        
        # 根据Big Five分数添加特征标签
        if big5.extraversion.score is not None:
            if big5.extraversion.score > 70:
                traits.extend(["outgoing", "energetic", "social"])
            elif big5.extraversion.score < 40:
                traits.extend(["introverted", "reflective", "reserved"])
        
        if big5.openness.score is not None:
            if big5.openness.score > 70:
                traits.extend(["creative", "curious", "imaginative"])
            elif big5.openness.score < 40:
                traits.extend(["practical", "traditional", "grounded"])
        
        if big5.conscientiousness.score is not None:
            if big5.conscientiousness.score > 70:
                traits.extend(["organized", "disciplined", "reliable"])
            elif big5.conscientiousness.score < 40:
                traits.extend(["flexible", "spontaneous", "adaptable"])
        
        if big5.agreeableness.score is not None:
            if big5.agreeableness.score > 70:
                traits.extend(["caring", "cooperative", "trusting"])
            elif big5.agreeableness.score < 40:
                traits.extend(["assertive", "independent", "direct"])
        
        if big5.neuroticism.score is not None:
            if big5.neuroticism.score > 70:
                traits.extend(["sensitive", "empathetic", "thoughtful"])
            elif big5.neuroticism.score < 40:
                traits.extend(["calm", "resilient", "stable"])
        
        # 更新主要特征（去重）
        existing_traits = set(personality_data.primary_traits)
        new_traits = [t for t in traits if t not in existing_traits]
        personality_data.primary_traits.extend(new_traits[:5])  # 限制数量
