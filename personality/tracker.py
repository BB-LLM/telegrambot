"""
Personality Tracker
追踪用户对话，评估Big Five人格特质

参考: pocket-souls-agents/pocket_souls_god/tools/personality.py
"""

import json
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from personality.models import PersonalityData, Big5Trait


class PersonalityTracker:
    """性格追踪器"""
    
    def __init__(self, llm_client):
        """
        初始化追踪器
        
        Args:
            llm_client: LLM客户端，用于分析对话
        """
        self.llm = llm_client
        
    def should_assess(self, total_exchanges: int, last_assessment_exchange: int = 0) -> bool:
        """
        判断是否需要进行性格评估
        
        评估策略（参考pocket）:
        - 第3轮对话：首次评估
        - 前10轮：每5轮评估一次
        - 10轮后：每10轮评估一次
        
        Args:
            total_exchanges: 总对话轮数
            last_assessment_exchange: 上次评估时的轮数
            
        Returns:
            是否应该评估
        """
        if total_exchanges < 3:
            return False
        
        if total_exchanges == 3:
            return True  # 首次评估
        
        exchanges_since_last = total_exchanges - last_assessment_exchange
        
        if total_exchanges <= 10:
            return exchanges_since_last >= 5  # 前10轮每5轮
        else:
            return exchanges_since_last >= 10  # 10轮后每10轮
    
    def analyze_conversation(
        self, 
        recent_messages: List[Dict[str, str]],
        existing_assessment: Optional[Dict] = None
    ) -> Dict:
        """
        使用LLM分析对话，提取Big Five指标
        
        Args:
            recent_messages: 最近的对话记录 [{"role": "user/assistant", "content": "..."}]
            existing_assessment: 现有的评估结果（用于增量更新）
            
        Returns:
            包含insights和big5_indicators的字典
        """
        # 准备对话文本
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in recent_messages[-10:]  # 最近5轮对话
        ])
        
        # 构建分析prompt
        analysis_prompt = f"""Analyze the following conversation to assess the USER's personality based on the Big Five model.

Conversation:
{conversation_text}

Analyze and provide:
1. Key personality insights about the USER
2. Big Five trait indicators with scores (0-100) and confidence levels (0-100)

Big Five Traits:
- Openness: Creativity, curiosity, open to new experiences
- Conscientiousness: Organization, responsibility, goal-oriented
- Extraversion: Sociability, energy, assertiveness
- Agreeableness: Cooperation, empathy, kindness
- Neuroticism: Emotional stability (high score = more anxious/moody)

Return ONLY a JSON object (no markdown):
{{
    "insights": ["insight 1", "insight 2", "insight 3"],
    "big5_indicators": {{
        "openness": {{"score": 75, "confidence": 80, "indicators": ["shows creativity", "curious questions"]}},
        "conscientiousness": {{"score": 60, "confidence": 70, "indicators": ["mentions planning"]}},
        "extraversion": {{"score": 55, "confidence": 75, "indicators": ["moderate social energy"]}},
        "agreeableness": {{"score": 80, "confidence": 85, "indicators": ["empathetic responses"]}},
        "neuroticism": {{"score": 45, "confidence": 70, "indicators": ["generally calm"]}}
    }},
    "primary_traits": ["creative", "empathetic"],
    "interests": ["art", "technology"],
    "emotional_state": "balanced"
}}

Focus on the USER's messages and behavior patterns. Be objective and evidence-based."""
        
        try:
            # 调用LLM分析
            messages = [{"role": "user", "content": analysis_prompt}]
            response = self.llm.generate_response(messages=messages, response_format=None)
            
            # 清理响应（移除可能的markdown标记）
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # 解析JSON
            analysis_result = json.loads(response)
            
            logger.info(f"Personality analysis completed: {len(analysis_result.get('insights', []))} insights extracted")
            return analysis_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response[:200]}")
            return self._get_default_analysis()
        except Exception as e:
            logger.error(f"Error in personality analysis: {e}")
            return self._get_default_analysis()
    
    def _get_default_analysis(self) -> Dict:
        """返回默认的分析结果"""
        return {
            "insights": ["Insufficient data for analysis"],
            "big5_indicators": {
                "openness": {"score": 50, "confidence": 30, "indicators": []},
                "conscientiousness": {"score": 50, "confidence": 30, "indicators": []},
                "extraversion": {"score": 50, "confidence": 30, "indicators": []},
                "agreeableness": {"score": 50, "confidence": 30, "indicators": []},
                "neuroticism": {"score": 50, "confidence": 30, "indicators": []}
            },
            "primary_traits": [],
            "interests": [],
            "emotional_state": "balanced"
        }
    
    def update_personality_data(
        self,
        personality_data: PersonalityData,
        analysis_result: Dict
    ) -> PersonalityData:
        """
        根据分析结果更新personality data
        
        Args:
            personality_data: 现有的性格数据
            analysis_result: LLM分析结果
            
        Returns:
            更新后的PersonalityData
        """
        # 更新Big Five scores
        big5_indicators = analysis_result.get("big5_indicators", {})
        
        for trait_name, trait_data in big5_indicators.items():
            if hasattr(personality_data.big5_assessment, trait_name):
                trait_obj = getattr(personality_data.big5_assessment, trait_name)
                
                # 更新score和confidence（取较高的confidence）
                new_score = trait_data.get("score")
                new_confidence = trait_data.get("confidence", 0)
                
                if new_confidence > trait_obj.confidence:
                    trait_obj.score = new_score
                    trait_obj.confidence = new_confidence
                    trait_obj.indicators.extend(trait_data.get("indicators", []))
                    trait_obj.last_updated = datetime.now().isoformat()
        
        # 更新primary traits和interests
        personality_data.primary_traits = list(set(
            personality_data.primary_traits + analysis_result.get("primary_traits", [])
        ))
        personality_data.interests = list(set(
            personality_data.interests + analysis_result.get("interests", [])
        ))
        
        # 更新emotional state
        if analysis_result.get("emotional_state"):
            personality_data.emotional_state = analysis_result["emotional_state"]
        
        # 更新元数据
        personality_data.last_assessment = datetime.now().isoformat()
        
        return personality_data
    
    def track_and_assess(
        self,
        user_id: str,
        chat_history: List[Dict[str, str]],
        existing_personality: Optional[PersonalityData] = None
    ) -> Optional[PersonalityData]:
        """
        完整的追踪和评估流程
        
        Args:
            user_id: 用户ID
            chat_history: 对话历史
            existing_personality: 现有的性格数据
            
        Returns:
            更新后的PersonalityData，如果不需要评估则返回None
        """
        total_exchanges = len(chat_history) // 2
        
        # 初始化或加载现有数据
        if existing_personality is None:
            personality_data = PersonalityData(user_id=user_id, total_exchanges=total_exchanges)
            last_assessment_exchange = 0
        else:
            personality_data = existing_personality
            personality_data.total_exchanges = total_exchanges
            # 计算上次评估时的轮数（简化处理）
            last_assessment_exchange = max(0, total_exchanges - 10)
        
        # 判断是否需要评估
        if not self.should_assess(total_exchanges, last_assessment_exchange):
            return None
        
        logger.info(f"Triggering personality assessment for user {user_id} at exchange {total_exchanges}")
        
        # 分析对话
        analysis_result = self.analyze_conversation(
            recent_messages=chat_history,
            existing_assessment=personality_data.big5_assessment.to_dict()
        )
        
        # 更新personality data
        updated_personality = self.update_personality_data(personality_data, analysis_result)
        
        return updated_personality

