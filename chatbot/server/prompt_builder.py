"""
Prompt 构建模块 - 从聊天上下文生成图像/视频的 cue
"""
import re
from typing import List, Dict, Tuple, Optional
from loguru import logger


class PromptBuilder:
    """Prompt 构建器 - 从聊天上下文提取关键词并构建 cue"""
    
    # 停用词列表
    STOPWORDS = {
        "的", "了", "和", "是", "在", "我", "你", "他", "她", "它",
        "这", "那", "一", "个", "不", "有", "没", "很", "也", "都",
        "要", "会", "可以", "能", "想", "给", "把", "被", "让", "叫",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "must"
    }
    
    def __init__(self):
        """初始化 Prompt 构建器"""
        pass
    
    def extract_keywords_from_context(
        self,
        chat_history: List[Dict],
        num_messages: int = 5,
        max_keywords: int = 10
    ) -> List[str]:
        """
        从聊天历史中提取关键词
        
        Args:
            chat_history: 聊天历史列表
            num_messages: 提取最近 N 条消息
            max_keywords: 最多提取的关键词数量
        
        Returns:
            关键词列表
        """
        if not chat_history:
            return []
        
        # 取最近 N 条消息
        recent_msgs = chat_history[-num_messages:]
        
        # 提取用户消息
        user_messages = [
            msg.get("content", "")
            for msg in recent_msgs
            if msg.get("role") == "user"
        ]
        
        if not user_messages:
            return []
        
        # 合并所有用户消息
        combined_text = " ".join(user_messages)
        
        # 分词和清理
        keywords = self._extract_keywords(combined_text, max_keywords)
        
        return keywords
    
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
        # 构建 cue
        cue_parts = []

        # 添加用户当前输入的关键词（最重要）
        user_input_keywords = self._extract_keywords(user_input, max_keywords=8)
        if user_input_keywords:
            cue_parts.extend(user_input_keywords)

        # 添加聊天历史中的关键词（作为补充上下文）
        history_keywords = self.extract_keywords_from_context(chat_history, num_messages=5, max_keywords=5)
        if history_keywords:
            # 避免重复
            for kw in history_keywords:
                if kw not in cue_parts:
                    cue_parts.append(kw)

        # 添加质量提示词
        cue_parts.append("high quality")
        cue_parts.append("detailed")

        cue = ", ".join(cue_parts)

        logger.info(f"Built standard cue (without Soul keywords): {cue}")
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
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        从文本中提取关键词
        
        Args:
            text: 输入文本
            max_keywords: 最多提取的关键词数量
        
        Returns:
            关键词列表
        """
        # 转换为小写
        text = text.lower()
        
        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # 分词
        words = text.split()
        
        # 过滤停用词和短词
        keywords = [
            word for word in words
            if word not in self.STOPWORDS and len(word) > 1
        ]
        
        # 去重并保持顺序
        seen = set()
        unique_keywords = []
        for word in keywords:
            if word not in seen:
                seen.add(word)
                unique_keywords.append(word)
        
        return unique_keywords[:max_keywords]


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

