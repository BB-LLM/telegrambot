"""
Data models for personality assessment
人格评估的数据模型
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Big5Trait:
    """Big Five单个特质的数据结构"""
    score: Optional[float] = None  # 0-100分
    confidence: float = 0.0  # 置信度 0-100%
    indicators: List[str] = field(default_factory=list)  # 指标列表
    last_updated: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


@dataclass
class Big5Assessment:
    """Big Five完整评估"""
    openness: Big5Trait = field(default_factory=Big5Trait)
    conscientiousness: Big5Trait = field(default_factory=Big5Trait)
    extraversion: Big5Trait = field(default_factory=Big5Trait)
    agreeableness: Big5Trait = field(default_factory=Big5Trait)
    neuroticism: Big5Trait = field(default_factory=Big5Trait)
    
    def to_dict(self):
        return {
            "openness": self.openness.to_dict(),
            "conscientiousness": self.conscientiousness.to_dict(),
            "extraversion": self.extraversion.to_dict(),
            "agreeableness": self.agreeableness.to_dict(),
            "neuroticism": self.neuroticism.to_dict()
        }
    
    def is_complete(self, min_confidence: float = 60.0) -> bool:
        """检查是否所有特质都已评估"""
        traits = [self.openness, self.conscientiousness, self.extraversion, 
                  self.agreeableness, self.neuroticism]
        return all(
            trait.score is not None and trait.confidence >= min_confidence 
            for trait in traits
        )
    
    def get_completion_status(self) -> Dict[str, bool]:
        """获取各个特质的完成状态"""
        return {
            "openness": self.openness.score is not None and self.openness.confidence >= 60,
            "conscientiousness": self.conscientiousness.score is not None and self.conscientiousness.confidence >= 60,
            "extraversion": self.extraversion.score is not None and self.extraversion.confidence >= 60,
            "agreeableness": self.agreeableness.score is not None and self.agreeableness.confidence >= 60,
            "neuroticism": self.neuroticism.score is not None and self.neuroticism.confidence >= 60
        }


@dataclass
class PersonalityDimensions:
    """性格维度 (1-10分制)"""
    warmth_level: float = 5.0  # 温暖度
    energy_level: float = 5.0  # 能量水平
    openness: float = 5.0  # 开放性
    emotional_depth: float = 5.0  # 情感深度
    playfulness: float = 5.0  # 玩心
    supportiveness: float = 5.0  # 支持性
    curiosity: float = 5.0  # 好奇心
    wisdom: float = 5.0  # 智慧
    
    def to_dict(self):
        return asdict(self)


@dataclass
class InteractionPreferences:
    """互动偏好"""
    conversation_pace: str = "moderate"  # slow, moderate, fast
    formality: str = "casual"  # formal, casual, intimate
    humor_style: str = "gentle"  # dry, witty, gentle, playful, minimal
    emotional_expression: str = "balanced"  # reserved, balanced, expressive
    
    def to_dict(self):
        return asdict(self)


@dataclass
class BehavioralTraits:
    """行为特质"""
    response_length: str = "moderate"  # brief, moderate, detailed
    question_frequency: str = "occasional"  # rare, occasional, frequent
    empathy_style: str = "active_listening"  # active_listening, advice_giving, emotional_mirroring
    conflict_approach: str = "gentle"  # direct, gentle, avoidant
    
    def to_dict(self):
        return asdict(self)


@dataclass
class PersonalityData:
    """用户的完整性格数据"""
    user_id: str
    big5_assessment: Big5Assessment = field(default_factory=Big5Assessment)
    personality_dimensions: PersonalityDimensions = field(default_factory=PersonalityDimensions)
    interaction_preferences: InteractionPreferences = field(default_factory=InteractionPreferences)
    behavioral_traits: BehavioralTraits = field(default_factory=BehavioralTraits)
    
    # 元数据
    total_exchanges: int = 0  # 总对话轮数
    last_assessment: Optional[str] = None  # 最后评估时间
    primary_traits: List[str] = field(default_factory=list)  # 主要特质
    interests: List[str] = field(default_factory=list)  # 兴趣爱好
    emotional_state: str = "balanced"  # melancholic, upbeat, balanced
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "big5_assessment": self.big5_assessment.to_dict(),
            "personality_dimensions": self.personality_dimensions.to_dict(),
            "interaction_preferences": self.interaction_preferences.to_dict(),
            "behavioral_traits": self.behavioral_traits.to_dict(),
            "total_exchanges": self.total_exchanges,
            "last_assessment": self.last_assessment,
            "primary_traits": self.primary_traits,
            "interests": self.interests,
            "emotional_state": self.emotional_state
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """从字典创建PersonalityData对象"""
        big5_data = data.get("big5_assessment", {})
        big5 = Big5Assessment(
            openness=Big5Trait(**big5_data.get("openness", {})),
            conscientiousness=Big5Trait(**big5_data.get("conscientiousness", {})),
            extraversion=Big5Trait(**big5_data.get("extraversion", {})),
            agreeableness=Big5Trait(**big5_data.get("agreeableness", {})),
            neuroticism=Big5Trait(**big5_data.get("neuroticism", {}))
        )
        
        return cls(
            user_id=data.get("user_id", ""),
            big5_assessment=big5,
            personality_dimensions=PersonalityDimensions(**data.get("personality_dimensions", {})),
            interaction_preferences=InteractionPreferences(**data.get("interaction_preferences", {})),
            behavioral_traits=BehavioralTraits(**data.get("behavioral_traits", {})),
            total_exchanges=data.get("total_exchanges", 0),
            last_assessment=data.get("last_assessment"),
            primary_traits=data.get("primary_traits", []),
            interests=data.get("interests", []),
            emotional_state=data.get("emotional_state", "balanced")
        )

