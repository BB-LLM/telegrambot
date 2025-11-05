"""
LLM Judge - Use large language models to score conversation quality
Aligned with pocket-souls-agents/evaluation
"""

import json
import asyncio
from typing import Dict, List, Optional, Tuple
import openai
from dataclasses import dataclass
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.evaluation_config import EVALUATION_DIMENSIONS, LLM_JUDGE_CONFIG, TELEGRAMBOT_CHARACTER_TRAITS


@dataclass
class EvaluationResult:
    """Evaluation result data structure"""
    scores: Dict[str, int]  
    explanations: Dict[str, str]  
    overall_score: float 
    suggestions: List[str] 
    examples: Dict[str, str] 


class LLMJudge:
    """LLM Judge class"""

    def __init__(self, api_key: str):
        self.config = LLM_JUDGE_CONFIG
        base_url = self.config.get("base_url")
        # 如果配置了 base_url（如 DeepSeek），则走自定义地址
        if base_url:
            self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = openai.AsyncOpenAI(api_key=api_key)

    async def evaluate_single_response(
        self,
        user_input: str,
        bot_response: str,
        context: Optional[List[Dict]] = None
    ) -> EvaluationResult:
        """
        Evaluate single response

        Args:
            user_input: User input
            bot_response: Bot response
            context: Conversation context (optional)

        Returns:
            EvaluationResult: Evaluation result
        """

        prompt = self._build_evaluation_prompt(user_input, bot_response, context)

        try:
            response = await self.client.chat.completions.create(
                model=self.config["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config["temperature"],
                max_tokens=self.config["max_tokens"]
            )

            result_text = response.choices[0].message.content
            return self._parse_evaluation_result(result_text)

        except Exception as e:
            print(f"LLM evaluation API call failed: {e}")
            raise Exception(f"LLM evaluation API failed: {e}")
    
    async def evaluate_conversation(
        self, 
        conversation: List[Dict[str, str]]
    ) -> EvaluationResult:
        """
        Evaluate entire conversation

        Args:
            conversation: Conversation history, format: [{"role": "user/assistant", "content": "..."}]

        Returns:
            EvaluationResult: Evaluation result
        """

        prompt = self._build_conversation_evaluation_prompt(conversation)

        try:
            response = await self.client.chat.completions.create(
                model=self.config["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config["temperature"],
                max_tokens=self.config["max_tokens"]
            )

            result_text = response.choices[0].message.content
            return self._parse_evaluation_result(result_text)

        except Exception as e:
            print(f"Conversation evaluation API call failed: {e}")
            raise Exception(f"LLM conversation evaluation API failed: {e}")
    
    def _build_evaluation_prompt(
        self, 
        user_input: str, 
        bot_response: str, 
        context: Optional[List[Dict]] = None
    ) -> str:
        """Build single response evaluation prompt"""

        context_str = ""
        if context:
            context_str = "\nConversation Context:\n"
            for turn in context[-3:]: 
                context_str += f"{turn['role']}: {turn['content']}\n"

        dimensions_str = ""
        for dim_key, dim_config in EVALUATION_DIMENSIONS.items():
            dimensions_str += f"\n{dim_config.name} (Weight: {dim_config.weight}):\n"
            dimensions_str += f"- Evaluation Criteria: {dim_config.description}\n"
            for score, desc in dim_config.criteria.items():
                dimensions_str += f"  {score} 分: {desc}\n"

        traits_str = f"""
TelegramBot Character Reference:
- Core Personality: Warm and caring companion, mysterious yet elegant presence, patient listener, wise and gentle guide
- Typical Actions: *glows softly*, *warm presence surrounds you*, *starlight flickers in eyes*
- Speech Patterns: Gentle and soft tone, elegant and poetic words, caring expressions, moderate mystique
- Emotional Range: Warmth, care, calm, wisdom, encouragement, comfort, understanding, protection
"""

        max_score = max(list(EVALUATION_DIMENSIONS.values())[0].criteria.keys())
        score_range = f"1-{max_score}"

        prompt = f"""
You are a professional AI conversation quality evaluation expert. Please comprehensively evaluate TelegramBot's response below using a {max_score}-point scale.

IMPORTANT: Use the full {score_range} range. Be discriminating and strict in your evaluation. A score of {max_score} should be reserved for truly exceptional responses.

{traits_str}

{context_str}

Current Conversation:
User: {user_input}
TelegramBot: {bot_response}

Evaluation Dimensions:{dimensions_str}

Please output the evaluation results in the following JSON format:
{{
    "scores": {{
        "logic": score({score_range}),
        "fluency": score({score_range}),
        "engagement": score({score_range}),
        "character_consistency": score({score_range}),
        "action_description": score({score_range}),
        "emotional_expression": score({score_range}),
        "game_immersion": score({score_range})
    }},
    "explanations": {{
        "logic": "Logic consistency score explanation",
        "fluency": "Language fluency score explanation",
        "engagement": "Engagement score explanation",
        "character_consistency": "Character consistency score explanation",
        "action_description": "Action description quality score explanation",
        "emotional_expression": "Emotional expression score explanation",
        "game_immersion": "Game immersion score explanation"
    }},
    "suggestions": [
        "Specific improvement suggestion 1",
        "Specific improvement suggestion 2",
        "Specific improvement suggestion 3"
    ],
    "examples": {{
        "good_aspects": "Examples of excellent aspects in the response",
        "improvement_areas": "Examples of areas that need improvement"
    }}
}}

Please ensure objective and fair scoring using the full {score_range} range, detailed and specific explanations, and practical suggestions.
"""
        return prompt
    
    def _build_conversation_evaluation_prompt(self, conversation: List[Dict[str, str]]) -> str:
        """Build conversation evaluation prompt"""

        conversation_str = ""
        for turn in conversation:
            role = "User" if turn["role"] == "user" else "TelegramBot"
            conversation_str += f"{role}: {turn['content']}\n"

        dimensions_str = ""
        for dim_key, dim_config in EVALUATION_DIMENSIONS.items():
            dimensions_str += f"- {dim_config.name}: {dim_config.description}\n"

        prompt = f"""
You are a professional AI conversation quality evaluation expert. Please evaluate the following complete conversation.

TelegramBot Character Setting: A warm and caring companion with mysterious and elegant qualities.

Complete Conversation:
{conversation_str}

Evaluation Dimensions:
{dimensions_str}

Please evaluate from the perspective of the overall conversation, focusing on:
1. Conversation coherence and consistency
2. TelegramBot character stability and charm
3. Conversation engagement and immersion
4. Naturalness and depth of emotional expression

Please output evaluation results in the following JSON format:
{{
    "scores": {{
        "logic": score(1-10),
        "fluency": score(1-10),
        "engagement": score(1-10),
        "character_consistency": score(1-10),
        "action_description": score(1-10),
        "emotional_expression": score(1-10),
        "game_immersion": score(1-10)
    }},
    "explanations": {{
        "logic": "explanation text",
        "fluency": "explanation text",
        "engagement": "explanation text",
        "character_consistency": "explanation text",
        "action_description": "explanation text",
        "emotional_expression": "explanation text",
        "game_immersion": "explanation text"
    }},
    "suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"],
    "examples": {{
        "good_aspects": "examples of excellent aspects",
        "improvement_areas": "examples of areas that need improvement"
    }}
}}

IMPORTANT: Use exact dimension names: logic, fluency, engagement, character_consistency, action_description, emotional_expression, game_immersion
"""
        return prompt
    
    def _parse_evaluation_result(self, result_text: str) -> EvaluationResult:
        """Parse LLM returned evaluation result"""
        try:
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end]
            elif "{" in result_text:
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                result_text = result_text[json_start:json_end]

            data = json.loads(result_text)
            
            # 处理嵌套结构（如 {"evaluation": {...}}）
            if "evaluation" in data:
                data = data["evaluation"]
            
            # 处理不同的字段名称
            scores_dict = {}
            explanations_dict = {}
            
            if "scores" in data:
                scores_dict = data["scores"]
            elif "dimension_scores" in data:
                scores_dict = data["dimension_scores"]
            elif "dimensions" in data:
                # 处理 {"dimensions": {"logic_consistency": {"score": 9, "explanation": "..."}}}
                for dim_name, dim_data in data["dimensions"].items():
                    if isinstance(dim_data, dict):
                        if "score" in dim_data:
                            # 转换为标准维度名称（去掉下划线和格式化）
                            std_name = self._normalize_dimension_name(dim_name)
                            scores_dict[std_name] = dim_data["score"]
                            explanations_dict[std_name] = dim_data.get("explanation", "")
                    else:
                        std_name = self._normalize_dimension_name(dim_name)
                        scores_dict[std_name] = dim_data
            
            # 标准化维度名称（从 "logic_consistency" 转为 "logic"）
            normalized_scores = {}
            for dim_name, score in scores_dict.items():
                normalized_name = self._normalize_dimension_name(dim_name)
                normalized_scores[normalized_name] = int(score) if isinstance(score, (int, float)) else score
            
            # 如果没有获取到分数，尝试从 overall_score 和维度名称推断
            if not normalized_scores and "overall_score" in data:
                # 如果只有总分，使用默认值
                overall = data.get("overall_score", 8.0)
                if isinstance(overall, (int, float)) and overall > 10:
                    # 如果总分是100分制，转换为10分制
                    overall = overall / 10.0
                normalized_scores = {dim: round(overall) for dim in EVALUATION_DIMENSIONS.keys()}
            
            # 处理 explanations
            if "explanations" in data:
                explanations_dict = data["explanations"]
            elif not explanations_dict:
                explanations_dict = {dim: f"Score: {score}" for dim, score in normalized_scores.items()}

            # 计算加权总分
            overall_score = 0
            for dim_key, score in normalized_scores.items():
                if dim_key in EVALUATION_DIMENSIONS:
                    weight = EVALUATION_DIMENSIONS[dim_key].weight
                    overall_score += float(score) * weight

            return EvaluationResult(
                scores=normalized_scores,
                explanations=explanations_dict,
                overall_score=round(overall_score, 2),
                suggestions=data.get("suggestions", []),
                examples=data.get("examples", {})
            )

        except Exception as e:
            print(f"Failed to parse evaluation result: {e}")
            print(f"Original result: {result_text[:500]}...")
            raise Exception(f"LLM evaluation result parsing failed: {e}")
    
    def _normalize_dimension_name(self, dim_name: str) -> str:
        """标准化维度名称，将各种变体转换为标准名称"""
        dim_name_lower = dim_name.lower()
        
        # 映射关系
        name_mapping = {
            "logic": "logic",
            "logic_consistency": "logic",
            "logicconsistency": "logic",
            "fluency": "fluency",
            "language_fluency": "fluency",
            "languagefluency": "fluency",
            "engagement": "engagement",
            "user_engagement": "engagement",
            "character_consistency": "character_consistency",
            "characterconsistency": "character_consistency",
            "action_description": "action_description",
            "action_description_quality": "action_description",
            "actiondescription": "action_description",
            "emotional_expression": "emotional_expression",
            "emotionalexpression": "emotional_expression",
            "game_immersion": "game_immersion",
            "gameimmersion": "game_immersion",
        }
        
        # 尝试精确匹配
        if dim_name_lower in name_mapping:
            return name_mapping[dim_name_lower]
        
        # 尝试部分匹配
        for key, value in name_mapping.items():
            if key in dim_name_lower or dim_name_lower in key:
                return value
        
        # 如果都不匹配，返回原始名称的小写（去掉特殊字符）
        return dim_name_lower.replace("_", "").replace(" ", "")
    
    def _create_fallback_result(self) -> EvaluationResult:
        """Create fallback evaluation result when LLM evaluation fails"""
        max_score = max(list(EVALUATION_DIMENSIONS.values())[0].criteria.keys())
        min_score = min(list(EVALUATION_DIMENSIONS.values())[0].criteria.keys())
        midpoint_score = (max_score + min_score) // 2 

        print(f"LLM evaluation failed, using fallback score: {midpoint_score} (range: {min_score}-{max_score})")

        return EvaluationResult(
            scores={dim: midpoint_score for dim in EVALUATION_DIMENSIONS.keys()},
            explanations={dim: "Evaluation failed, using default score" for dim in EVALUATION_DIMENSIONS.keys()},
            overall_score=float(midpoint_score),
            suggestions=["LLM evaluation failed, please check network connection and API configuration"],
            examples={"error": "Error occurred during evaluation process"}
        )

