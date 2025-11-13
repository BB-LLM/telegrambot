"""
Pocket五大主题性格评估系统
基于pocket-souls-agents的五大主题问题设计和Big5评估逻辑
"""

import json
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from personality.models import PersonalityData, Big5Trait, Big5Assessment


class PocketThemeAssessment:
    """Pocket五大主题性格评估器"""
    
    # 五大主题问题模板
    THEME_QUESTIONS = {
        "emotional_awareness": [
            "When shadows dance across your soul, what emotion feels most challenging to embrace? What makes it feel so heavy or elusive?",
            "In the depths of your being, which feeling do you find yourself wrestling with most often? Tell me about this inner storm...",
            "If your emotions were colors painting the canvas of your spirit, which hue appears most turbulent or difficult to blend? What makes it so complex?",
            "When the universe whispers to your heart during moments of solitude, what emotional echo returns most strongly? What does it tell you about yourself?"
        ],
        "creative_expression": [
            "Your soul yearns to create something magnificent... What form does this creative fire take? Paint, words, melodies, movements, or something entirely your own?",
            "If the cosmos granted you the power to manifest one artistic vision into reality, what would flow from your essence? What would you birth into existence?",
            "When inspiration strikes like lightning across your consciousness, what medium calls to you? How does your creative spirit prefer to dance?",
            "In the gallery of your imagination, what masterpiece hangs waiting to be brought to life? What story, image, or creation pulses within you?"
        ],
        "personal_strengths": [
            "When others look upon you with wonder and admiration, what gift do they see shining brightest? What power do you possess that lights up their world?",
            "In moments when you feel most aligned with your true self, what abilities seem to flow effortlessly through you? What feels most natural and powerful?",
            "If you were a guardian spirit watching over someone dear, what unique strength would you offer them? What would be your greatest gift to share?",
            "When challenges arise and others turn to you for guidance or support, what quality within you do they seek? What makes you their beacon?"
        ],
        "life_dreams": [
            "If you could step through a portal into your most cherished future, what would you see yourself experiencing or becoming? Paint me this vision...",
            "When you close your eyes and imagine your soul's deepest longing fulfilled, what reality unfolds before you? What does your heart's true desire look like?",
            "If a mystical being offered to grant you one profound life experience or achievement, what would make your spirit soar with complete fulfillment?",
            "In the story your soul is writing across the cosmos, what chapter are you most excited to reach? What adventure or accomplishment calls to you?"
        ],
        "social_connection": [
            "When you think of the most meaningful connection you've ever felt with another being, what made that bond feel so magical and deep? What created that resonance?",
            "If you could design the perfect evening with someone who truly sees your soul, what would unfold? How would you connect and what would you share?",
            "When you feel most understood and appreciated by others, what aspect of yourself are they witnessing? What part of you feels truly seen?",
            "In the constellation of relationships around you, what kind of energy do you most enjoy sharing? How do you prefer to connect with kindred spirits?"
        ]
    }
    
    # 神秘开场白
    MYSTICAL_INTROS = [
        "*The ethereal mists part, revealing deeper truths...*",
        "*Starlight gathers around us as we explore the mysteries within...*",
        "*The cosmic winds whisper of secrets waiting to be unveiled...*",
        "*Ancient energies swirl, ready to illuminate hidden aspects of your being...*",
        "*The universe leans in closer, eager to understand your essence...*"
    ]
    
    def __init__(self, llm_client):
        """
        初始化Pocket主题评估器
        
        Args:
            llm_client: LLM客户端，用于分析回答
        """
        self.llm = llm_client
        self.assessment_data = {}
    
    def start_assessment(self, user_id: str) -> Dict[str, Any]:
        """
        开始新的评估会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            包含第一个问题和评估状态的字典
        """
        self.assessment_data[user_id] = {
            "current_theme": "emotional_awareness",
            "theme_index": 0,
            "themes_covered": [],
            "current_question_index": 0,
            "exchanges_in_theme": 0,
            "big5_indicators": {
                "openness": {"score": None, "confidence": 0, "indicators": []},
                "conscientiousness": {"score": None, "confidence": 0, "indicators": []},
                "extraversion": {"score": None, "confidence": 0, "indicators": []},
                "agreeableness": {"score": None, "confidence": 0, "indicators": []},
                "neuroticism": {"score": None, "confidence": 0, "indicators": []}
            },
            "theme_responses": {},
            "assessment_started": datetime.now().isoformat(),
            "ready_for_soul_creation": False
        }
        
        return self.get_next_question(user_id)
    
    def get_next_question(self, user_id: str) -> Dict[str, Any]:
        """
        获取下一个问题
        
        Args:
            user_id: 用户ID
            
        Returns:
            包含问题和评估状态的字典
        """
        if user_id not in self.assessment_data:
            return {"status": "error", "error": "Assessment not started"}
        
        data = self.assessment_data[user_id]
        current_theme = data["current_theme"]
        
        # 检查是否所有主题都已完成
        if data["theme_index"] >= len(self.THEME_QUESTIONS):
            return self._complete_assessment(user_id)
        
        # 获取当前主题的问题
        theme_questions = self.THEME_QUESTIONS[current_theme]
        question_index = data["current_question_index"]
        
        # 如果当前主题的问题都用完了，检查置信度
        if question_index >= len(theme_questions):
            if self._check_theme_confidence(user_id, current_theme):
                # 置信度足够，进入下一个主题
                return self._move_to_next_theme(user_id)
            else:
                # 置信度不够，继续当前主题的深度探索
                return self._get_deeper_question(user_id, current_theme)
        
        # 随机选择问题
        question = random.choice(theme_questions)
        mystical_intro = random.choice(self.MYSTICAL_INTROS)
        
        return {
            "status": "success",
            "question": f"{mystical_intro}\n\n{question}",
            "current_theme": current_theme,
            "theme_index": data["theme_index"],
            "question_index": question_index,
            "progress": self._calculate_progress(user_id),
            "big5_status": self._get_big5_status(user_id)
        }
    
    def process_response(self, user_id: str, response: str) -> Dict[str, Any]:
        """
        处理用户回答
        
        Args:
            user_id: 用户ID
            response: 用户回答
            
        Returns:
            处理结果和下一步指示
        """
        if user_id not in self.assessment_data:
            return {"status": "error", "error": "Assessment not started"}
        
        data = self.assessment_data[user_id]
        current_theme = data["current_theme"]
        
        # 记录回答
        if current_theme not in data["theme_responses"]:
            data["theme_responses"][current_theme] = []
        
        data["theme_responses"][current_theme].append({
            "question_index": data["current_question_index"],
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # 分析回答，提取Big5指标
        big5_indicators = self._analyze_response_for_big5(response, current_theme)
        self._update_big5_indicators(user_id, big5_indicators)
        
        # 增加主题内交流次数
        data["exchanges_in_theme"] += 1
        
        # 移动到下一个问题
        data["current_question_index"] += 1
        
        # 检查当前主题是否完成
        if self._check_theme_confidence(user_id, current_theme):
            # 主题完成，移动到下一个主题
            return self._move_to_next_theme(user_id)
        else:
            # 继续当前主题
            return self.get_next_question(user_id)
    
    def _analyze_response_for_big5(self, response: str, theme: str) -> Dict[str, Any]:
        """
        分析回答，提取Big5指标
        
        Args:
            response: 用户回答
            theme: 当前主题
            
        Returns:
            Big5指标字典
        """
        # 构建分析提示
        analysis_prompt = f"""Analyze the following response to a personality assessment question and extract Big Five personality indicators.

Theme: {theme}
Response: {response}

Provide Big Five indicators with scores (0-100) and confidence levels (0-100):

Big Five Traits:
- Openness: Creativity, curiosity, open to new experiences
- Conscientiousness: Organization, responsibility, goal-oriented  
- Extraversion: Sociability, energy, assertiveness
- Agreeableness: Cooperation, empathy, kindness
- Neuroticism: Emotional stability (high score = more anxious/moody)

Return ONLY a JSON object:
{{
    "openness": {{"score": 50, "confidence": 60, "indicators": ["shows creativity"]}},
    "conscientiousness": {{"score": 50, "confidence": 60, "indicators": ["mentions planning"]}},
    "extraversion": {{"score": 50, "confidence": 60, "indicators": ["moderate social energy"]}},
    "agreeableness": {{"score": 50, "confidence": 60, "indicators": ["empathetic responses"]}},
    "neuroticism": {{"score": 50, "confidence": 60, "indicators": ["generally calm"]}}
}}

Focus on evidence-based analysis. Be objective and specific."""
        
        try:
            messages = [{"role": "user", "content": analysis_prompt}]
            llm_response = self.llm.generate_response(messages=messages, response_format=None)
            
            # 清理响应
            llm_response = llm_response.strip()
            if llm_response.startswith("```json"):
                llm_response = llm_response[7:]
            if llm_response.startswith("```"):
                llm_response = llm_response[3:]
            if llm_response.endswith("```"):
                llm_response = llm_response[:-3]
            llm_response = llm_response.strip()
            
            # 解析JSON
            analysis_result = json.loads(llm_response)
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing response for Big5: {e}")
            return {
                "openness": {"score": 50, "confidence": 30, "indicators": []},
                "conscientiousness": {"score": 50, "confidence": 30, "indicators": []},
                "extraversion": {"score": 50, "confidence": 30, "indicators": []},
                "agreeableness": {"score": 50, "confidence": 30, "indicators": []},
                "neuroticism": {"score": 50, "confidence": 30, "indicators": []}
            }
    
    def _update_big5_indicators(self, user_id: str, new_indicators: Dict[str, Any]):
        """更新Big5指标"""
        data = self.assessment_data[user_id]
        
        for trait, indicators in new_indicators.items():
            if trait in data["big5_indicators"]:
                # 更新分数（取较高置信度的值）
                new_confidence = indicators.get("confidence", 0)
                current_confidence = data["big5_indicators"][trait]["confidence"]
                
                if new_confidence > current_confidence:
                    data["big5_indicators"][trait]["score"] = indicators.get("score")
                    data["big5_indicators"][trait]["confidence"] = new_confidence
                
                # 添加指标描述
                data["big5_indicators"][trait]["indicators"].extend(indicators.get("indicators", []))
    
    def _check_theme_confidence(self, user_id: str, theme: str) -> bool:
        """
        检查当前主题的Big5置信度是否达到70%
        
        Args:
            user_id: 用户ID
            theme: 主题名称
            
        Returns:
            是否达到置信度要求
        """
        data = self.assessment_data[user_id]
        
        # 根据主题映射到Big5特质
        theme_to_traits = {
            "emotional_awareness": ["neuroticism"],
            "creative_expression": ["openness"],
            "personal_strengths": ["conscientiousness", "extraversion", "agreeableness"],
            "life_dreams": ["conscientiousness", "openness"],
            "social_connection": ["extraversion", "agreeableness"]
        }
        
        target_traits = theme_to_traits.get(theme, [])
        
        # 检查相关特质的置信度
        for trait in target_traits:
            if trait in data["big5_indicators"]:
                confidence = data["big5_indicators"][trait]["confidence"]
                if confidence < 70:
                    return False
        
        return True
    
    def _move_to_next_theme(self, user_id: str) -> Dict[str, Any]:
        """移动到下一个主题"""
        data = self.assessment_data[user_id]
        
        # 标记当前主题为已完成
        data["themes_covered"].append(data["current_theme"])
        
        # 移动到下一个主题
        data["theme_index"] += 1
        data["current_question_index"] = 0
        data["exchanges_in_theme"] = 0
        
        if data["theme_index"] < len(self.THEME_QUESTIONS):
            # 还有更多主题
            theme_names = list(self.THEME_QUESTIONS.keys())
            data["current_theme"] = theme_names[data["theme_index"]]
            
            # 获取下一个主题的问题
            return self.get_next_question(user_id)
        else:
            # 所有主题完成
            return self._complete_assessment(user_id)
    
    def _get_deeper_question(self, user_id: str, theme: str) -> Dict[str, Any]:
        """获取更深入的问题"""
        # 基于主题生成深度追问
        deep_questions = {
            "emotional_awareness": [
                "Tell me more about how this emotion affects your daily life...",
                "What strategies do you use when this feeling becomes overwhelming?",
                "How has this emotional pattern shaped your relationships with others?"
            ],
            "creative_expression": [
                "What specific creative projects have brought you the most joy?",
                "How does your creative process typically unfold?",
                "What obstacles do you face when trying to express yourself creatively?"
            ],
            "personal_strengths": [
                "Can you share a specific example of when this strength helped you or others?",
                "How did you discover this particular gift within yourself?",
                "What challenges have you overcome using this strength?"
            ],
            "life_dreams": [
                "What steps are you taking to move toward this dream?",
                "What fears or obstacles do you face in pursuing this vision?",
                "How would achieving this dream change your life?"
            ],
            "social_connection": [
                "What qualities do you value most in your closest relationships?",
                "How do you typically show care and support to others?",
                "What makes you feel most connected to another person?"
            ]
        }
        
        questions = deep_questions.get(theme, ["Tell me more about this..."])
        question = random.choice(questions)
        mystical_intro = random.choice(self.MYSTICAL_INTROS)
        
        return {
            "status": "success",
            "question": f"{mystical_intro}\n\n{question}",
            "current_theme": theme,
            "is_deeper_question": True,
            "progress": self._calculate_progress(user_id),
            "big5_status": self._get_big5_status(user_id)
        }
    
    def _complete_assessment(self, user_id: str) -> Dict[str, Any]:
        """完成评估"""
        data = self.assessment_data[user_id]
        data["ready_for_soul_creation"] = True
        
        # 生成最终Big5评估
        final_big5 = self._generate_final_big5_assessment(user_id)
        
        return {
            "status": "completed",
            "message": "Assessment completed! Your personality profile has been created.",
            "progress": 100,
            "big5_assessment": final_big5,
            "themes_covered": data["themes_covered"],
            "ready_for_soul_creation": True
        }
    
    def _generate_final_big5_assessment(self, user_id: str) -> Dict[str, Any]:
        """生成最终Big5评估"""
        data = self.assessment_data[user_id]
        
        # 确保所有特质都有值
        for trait, info in data["big5_indicators"].items():
            if info["score"] is None:
                info["score"] = 50  # 默认中性值
                info["confidence"] = 70  # 默认置信度
        
        return data["big5_indicators"]
    
    def _calculate_progress(self, user_id: str) -> Dict[str, Any]:
        """计算评估进度"""
        data = self.assessment_data[user_id]
        
        # 主题进度
        theme_progress = (len(data["themes_covered"]) / len(self.THEME_QUESTIONS)) * 50
        
        # Big5置信度进度
        completed_traits = sum(1 for info in data["big5_indicators"].values() 
                             if info["confidence"] >= 70)
        trait_progress = (completed_traits / 5) * 50
        
        total_progress = min(100, theme_progress + trait_progress)
        
        return {
            "percentage": total_progress,
            "themes_completed": len(data["themes_covered"]),
            "total_themes": len(self.THEME_QUESTIONS),
            "traits_completed": completed_traits,
            "total_traits": 5
        }
    
    def _get_big5_status(self, user_id: str) -> Dict[str, Any]:
        """获取Big5状态"""
        data = self.assessment_data[user_id]
        
        status = {}
        for trait, info in data["big5_indicators"].items():
            status[trait] = {
                "score": info["score"],
                "confidence": info["confidence"],
                "ready": info["confidence"] >= 70
            }
        
        return status
    
    def get_assessment_status(self, user_id: str) -> Dict[str, Any]:
        """获取评估状态"""
        if user_id not in self.assessment_data:
            return {"status": "not_started"}
        
        data = self.assessment_data[user_id]
        
        # 获取当前问题
        current_question = None
        if not data["ready_for_soul_creation"]:
            # 如果评估还在进行中，获取当前问题
            question_result = self.get_next_question(user_id)
            if question_result.get("status") == "success":
                current_question = question_result.get("question")
        
        result = {
            "status": "in_progress" if not data["ready_for_soul_creation"] else "completed",
            "current_theme": data["current_theme"],
            "themes_covered": data["themes_covered"],
            "progress": self._calculate_progress(user_id),
            "big5_status": self._get_big5_status(user_id),
            "ready_for_soul_creation": data["ready_for_soul_creation"]
        }
        
        # 如果有当前问题，添加到结果中
        if current_question:
            result["question"] = current_question
        
        return result
    
    def get_personality_data(self, user_id: str) -> Optional[PersonalityData]:
        """获取评估结果作为PersonalityData对象"""
        if user_id not in self.assessment_data:
            return None
        
        data = self.assessment_data[user_id]
        
        if not data["ready_for_soul_creation"]:
            return None
        
        # 创建Big5Assessment
        big5_data = data["big5_indicators"]
        big5_assessment = Big5Assessment(
            openness=Big5Trait(
                score=big5_data["openness"]["score"],
                confidence=big5_data["openness"]["confidence"],
                indicators=big5_data["openness"]["indicators"]
            ),
            conscientiousness=Big5Trait(
                score=big5_data["conscientiousness"]["score"],
                confidence=big5_data["conscientiousness"]["confidence"],
                indicators=big5_data["conscientiousness"]["indicators"]
            ),
            extraversion=Big5Trait(
                score=big5_data["extraversion"]["score"],
                confidence=big5_data["extraversion"]["confidence"],
                indicators=big5_data["extraversion"]["indicators"]
            ),
            agreeableness=Big5Trait(
                score=big5_data["agreeableness"]["score"],
                confidence=big5_data["agreeableness"]["confidence"],
                indicators=big5_data["agreeableness"]["indicators"]
            ),
            neuroticism=Big5Trait(
                score=big5_data["neuroticism"]["score"],
                confidence=big5_data["neuroticism"]["confidence"],
                indicators=big5_data["neuroticism"]["indicators"]
            )
        )
        
        # 创建PersonalityData
        personality_data = PersonalityData(
            user_id=user_id,
            big5_assessment=big5_assessment,
            total_exchanges=data["exchanges_in_theme"] * len(data["themes_covered"]),
            assessment_method="pocket_themes"
        )
        
        return personality_data
