"""
Prompt 构建模块 - 从聊天上下文生成图像/视频的 cue
"""
import re
from typing import List, Dict, Tuple, Optional
from loguru import logger


class PromptBuilder:
    """Prompt 构建器 - 从聊天上下文构建 cue"""

    def __init__(self):
        """初始化 Prompt 构建器"""
        pass

    def build_standard_cue(
        self,
        user_input: str,
        chat_history: List[Dict],
        soul_keywords: List[str] = None
    ) -> str:
        """
        构建标准风格的 cue（基于聊天内容）

        注意：不包含 Soul 关键词，因为用户生成的图像不是 Soul 的自画像，
        而是用户想象中的场景。Soul 关键词只用于自拍生成。

        Args:
            user_input: 用户最后的输入
            chat_history: 聊天历史
            soul_keywords: Soul 的风格关键词（此方法中不使用）

        Returns:
            构建好的 cue 字符串
        """
        # 构建 cue - 直接使用用户输入和历史上下文，不做关键词提取
        cue_parts = []

        # 1. 添加用户当前输入（最重要）
        if user_input and user_input.strip():
            cue_parts.append(user_input.strip())

        # 2. 添加最近3轮对话的用户消息作为上下文
        if chat_history:
            # 获取所有用户消息
            user_messages = [
                msg.get("content", "").strip()
                for msg in chat_history
                if msg.get("role") == "user" and msg.get("content", "").strip()
            ]

            # 取最近3条历史消息（不包括当前输入）
            # 假设 chat_history 不包含当前输入，所以直接取最后3条
            if user_messages:
                recent_context = user_messages[-3:]  # 最近3条
                for context in recent_context:
                    if context and context not in cue_parts:
                        cue_parts.append(context)

        # 3. 拼接成完整的 cue
        cue = ". ".join(cue_parts)

        logger.info(f"Built standard cue: {cue}")
        return cue
    
    def build_selfie_cue(
        self,
        city_key: str,
        mood: str,
        soul_keywords: List[str] = None
    ) -> str:
        """
        构建自拍风格的 cue
        
        Args:
            city_key: 城市键（如 paris, tokyo）
            mood: 心情（如 happy, sad）
            soul_keywords: Soul 的风格关键词
        
        Returns:
            构建好的 cue 字符串
        """
        cue_parts = []
        
        # 添加 Soul 风格关键词
        if soul_keywords:
            cue_parts.extend(soul_keywords[:3])
        
        # 添加城市和心情
        cue_parts.append(f"selfie at {city_key}")
        cue_parts.append(mood)
        
        # 添加质量提示词
        cue_parts.append("professional photography")
        cue_parts.append("high quality")
        
        cue = ", ".join(cue_parts)
        
        logger.info(f"Built selfie cue: {cue}")
        return cue
    
    def detect_selfie_command(self, user_input: str) -> Optional[Tuple[str, str]]:
        """
        检测用户输入中的自拍命令
        
        支持的格式：
        - /selfie paris happy
        - /selfie-video tokyo excited
        - 给我生成一个在巴黎的自拍，我很开心
        
        Args:
            user_input: 用户输入
        
        Returns:
            (city_key, mood) 元组，如果不是自拍命令则返回 None
        """
        # 检查命令格式：/selfie city mood
        match = re.match(r'^/selfie(?:-video)?\s+(\w+)\s+(\w+)', user_input.strip())
        if match:
            city_key = match.group(1).lower()
            mood = match.group(2).lower()
            return (city_key, mood)
        
        # 检查自然语言格式：在 XXX 的自拍，我很 YYY
        # 支持的城市
        cities = {
            "巴黎": "paris", "paris": "paris",
            "东京": "tokyo", "tokyo": "tokyo",
            "纽约": "newyork", "new york": "newyork",
            "伦敦": "london", "london": "london",
            "罗马": "rome", "rome": "rome"
        }
        
        # 支持的心情
        moods = {
            "开心": "happy", "happy": "happy", "高兴": "happy",
            "伤心": "sad", "sad": "sad", "难过": "sad",
            "兴奋": "excited", "excited": "excited",
            "平静": "calm", "calm": "calm",
            "浪漫": "romantic", "romantic": "romantic",
            "冒险": "adventurous", "adventurous": "adventurous"
        }
        
        # 尝试匹配城市和心情
        for city_name, city_key in cities.items():
            if city_name in user_input:
                for mood_name, mood_key in moods.items():
                    if mood_name in user_input:
                        return (city_key, mood_key)
        
        return None
    



# 全局 Prompt 构建器实例
_prompt_builder = None


def get_prompt_builder() -> PromptBuilder:
    """
    获取全局 Prompt 构建器实例
    
    Returns:
        PromptBuilder 实例
    """
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = PromptBuilder()
    return _prompt_builder

