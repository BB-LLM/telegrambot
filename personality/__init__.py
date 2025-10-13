"""
Personality Analysis Module
基于Big Five人格理论的用户性格分析模块

灵感来源: pocket-souls-agents
功能: 通过对话分析用户性格，动态调整AI回复风格
"""

from personality.tracker import PersonalityTracker
from personality.profile import PersonalityProfile
from personality.adjuster import PersonalityPromptAdjuster

__all__ = ['PersonalityTracker', 'PersonalityProfile', 'PersonalityPromptAdjuster']

