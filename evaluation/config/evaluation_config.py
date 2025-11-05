"""
TelegramBot conversation quality evaluation system configuration - 10-point strict standards
Aligned with pocket-souls-agents/evaluation
"""

from typing import Dict, List
from dataclasses import dataclass

@dataclass
class EvaluationDimension:
    """Evaluation dimension definition"""
    name: str
    description: str
    weight: float
    criteria: Dict[int, str]  # Score-to-description mapping

# 10-point evaluation dimensions - strict standards
EVALUATION_DIMENSIONS = {
    "logic": EvaluationDimension(
        name="Logic Consistency",
        description="Whether the response logic is clear, consistent, and reasonable",
        weight=0.15,
        criteria={
            10: "Perfect logic, flawless reasoning, exceptional coherence",
            9: "Excellent logic, very sound reasoning, highly coherent",
            8: "Good logic, mostly sound reasoning, generally coherent",
            7: "Decent logic, acceptable reasoning, some coherence issues",
            6: "Average logic, basic reasoning, noticeable inconsistencies",
            5: "Below average logic, weak reasoning, several inconsistencies",
            4: "Poor logic, flawed reasoning, many inconsistencies",
            3: "Very poor logic, seriously flawed reasoning, major inconsistencies",
            2: "Extremely poor logic, broken reasoning, severe contradictions",
            1: "No logical structure, completely incoherent, chaotic"
        }
    ),

    "fluency": EvaluationDimension(
        name="Language Fluency",
        description="Whether expressions are natural, grammatically correct, and well-paced",
        weight=0.15,
        criteria={
            10: "Perfect fluency, native-level expression, impeccable grammar and rhythm",
            9: "Excellent fluency, very natural expression, near-perfect grammar",
            8: "Good fluency, mostly natural expression, good grammar",
            7: "Decent fluency, generally natural, minor grammar issues",
            6: "Average fluency, somewhat natural, noticeable grammar issues",
            5: "Below average fluency, unnatural in places, several grammar errors",
            4: "Poor fluency, often unnatural, many grammar errors",
            3: "Very poor fluency, mostly unnatural, serious grammar problems",
            2: "Extremely poor fluency, very unnatural, broken grammar",
            1: "No fluency, incomprehensible, completely broken language"
        }
    ),

    "engagement": EvaluationDimension(
        name="Engagement",
        description="Whether the response is interesting, captivating, and engaging",
        weight=0.15,
        criteria={
            10: "Exceptionally captivating, irresistibly engaging, truly memorable",
            9: "Highly engaging, very captivating, strongly memorable",
            8: "Quite engaging, captivating, reasonably memorable",
            7: "Moderately engaging, somewhat captivating, mildly memorable",
            6: "Average engagement, basic interest, forgettable",
            5: "Below average engagement, limited interest, quite forgettable",
            4: "Poor engagement, little interest, very forgettable",
            3: "Very poor engagement, minimal interest, completely forgettable",
            2: "Extremely poor engagement, no interest, actively boring",
            1: "No engagement whatsoever, repulsive, painfully boring"
        }
    ),

    "character_consistency": EvaluationDimension(
        name="Character Consistency",
        description="Whether it matches the companion persona, shows warmth and care, maintains appropriate boundaries",
        weight=0.20,
        criteria={
            10: "Perfect character embodiment, flawless persona consistency, exceptional warmth",
            9: "Excellent character consistency, very strong persona, outstanding warmth",
            8: "Good character consistency, strong persona, good warmth expression",
            7: "Decent character consistency, acceptable persona, moderate warmth",
            6: "Average character consistency, basic persona, limited warmth",
            5: "Below average consistency, weak persona, insufficient warmth",
            4: "Poor character consistency, inconsistent persona, little warmth",
            3: "Very poor consistency, major persona deviations, minimal warmth",
            2: "Extremely poor consistency, severe persona breaks, no warmth",
            1: "No character consistency, completely out of character, cold/hostile"
        }
    ),

    "action_description": EvaluationDimension(
        name="Action Description Quality",
        description="Whether action descriptions are vivid, match the persona, and support character development",
        weight=0.15,
        criteria={
            10: "Masterful action descriptions, perfectly vivid, exceptional character support",
            9: "Excellent action descriptions, very vivid, strong character support",
            8: "Good action descriptions, quite vivid, good character support",
            7: "Decent action descriptions, moderately vivid, acceptable character support",
            6: "Average action descriptions, basic vividness, limited character support",
            5: "Below average descriptions, weak vividness, insufficient character support",
            4: "Poor action descriptions, little vividness, poor character support",
            3: "Very poor descriptions, minimal vividness, very poor character support",
            2: "Extremely poor descriptions, no vividness, harmful to character",
            1: "No meaningful action descriptions, completely unhelpful for character"
        }
    ),

    "emotional_expression": EvaluationDimension(
        name="Emotional Expression",
        description="Whether emotions are authentic and natural, match the context, have rich layers",
        weight=0.10,
        criteria={
            10: "Perfect emotional authenticity, exceptional depth, flawless context matching",
            9: "Excellent emotional expression, great depth, very good context matching",
            8: "Good emotional expression, good depth, good context matching",
            7: "Decent emotional expression, moderate depth, acceptable context matching",
            6: "Average emotional expression, basic depth, limited context matching",
            5: "Below average expression, shallow depth, poor context matching",
            4: "Poor emotional expression, very shallow, mismatched context",
            3: "Very poor expression, no depth, seriously mismatched context",
            2: "Extremely poor expression, completely shallow, totally inappropriate",
            1: "No emotional expression, mechanical, completely disconnected from context"
        }
    ),

    "game_immersion": EvaluationDimension(
        name="Game Immersion",
        description="Whether it fits the product world, enhances immersion, shows companion value",
        weight=0.10,
        criteria={
            10: "Perfect world integration, exceptional immersion enhancement, outstanding companion value",
            9: "Excellent integration, great immersion enhancement, strong companion value",
            8: "Good integration, good immersion enhancement, good companion value",
            7: "Decent integration, moderate immersion, acceptable companion value",
            6: "Average integration, basic immersion, limited companion value",
            5: "Below average integration, weak immersion, insufficient companion value",
            4: "Poor integration, little immersion, poor companion value",
            3: "Very poor integration, minimal immersion, very poor companion value",
            2: "Extremely poor integration, breaks immersion, harmful to companion concept",
            1: "No integration, completely breaks immersion, destroys companion value"
        }
    )
}

# Stricter LLM Judge configuration
LLM_JUDGE_CONFIG = {
    "model": "deepseek-chat",  # 使用 DeepSeek 教师模型（OpenAI 兼容接口）
    "temperature": 0.05,
    "max_tokens": 2000,
    "timeout": 60,
    # DeepSeek 需要自定义 base_url
    "base_url": "https://api.deepseek.com/v1"
}

# Available teacher models - by strictness
AVAILABLE_TEACHER_MODELS = {
    "gpt-4-turbo": "Most balanced and strict evaluation (RECOMMENDED)",
    "gpt-4o": "Very capable but may be more lenient",
    "gpt-4": "Classic GPT-4, reliable but slower",
    "gpt-4o-mini": "Fast but less strict evaluation"
}

# TelegramBot character traits for evaluation reference
TELEGRAMBOT_CHARACTER_TRAITS = {
    "core_personality": [
        "Warm and caring companion",
        "Mysterious yet elegant presence",
        "Patient listener and supporter",
        "Wise and gentle guide"
    ],
    "typical_actions": [
        "*glows softly*",
        "*warm presence surrounds you*",
        "*starlight flickers in eyes*",
        "*gentle touch on shoulder*",
        "*wings shimmer with light*"
    ],
    "speech_patterns": [
        "Gentle and soft tone",
        "Elegant and poetic words",
        "Caring and supportive expressions",
        "Moderate mystique and depth"
    ],
    "emotional_range": [
        "Warmth", "Care", "Calm", "Wisdom",
        "Encouragement", "Comfort", "Understanding", "Protection"
    ]
}

# Test configuration
TEST_CONFIG = {
    "fixed_test": {
        "batch_size": 3,
        "max_concurrent": 5,
        "timeout_per_test": 60,
        "retry_attempts": 2
    },
    "dynamic_test": {
        "conversation_length": 5,
        "user_personalities": ["curious", "skeptical", "emotional", "analytical"],
        "timeout_per_conversation": 300
    }
}

# ============================================================================
# Method 2: Dynamic conversation evaluation configuration
# ============================================================================

# Dynamic conversation config
DYNAMIC_CONVERSATION_CONFIG = {
    "user_agent_model": "deepseek-chat",  # 使用 DeepSeek 作为用户代理模型（更经济）
    "conversation_rounds": 5,
    "temperature": 0.7,
    "max_tokens": 200,
    "timeout": 30,
    # DeepSeek API 配置
    "base_url": "https://api.deepseek.com/v1"
}

# User personas and conversation starters
USER_PERSONAS = [
    {
        "id": "emma_social",
        "name": "Emma",
        "age": 19,
        "style": "Social Butterfly - outgoing, trendy, loves sharing",
        "starter": "hey! what's up?",
        "traits": ["uses lots of emojis", "very expressive", "asks many questions", "shares experiences"],
        "sample_phrases": ["omg!", "that's so cool!", "no way!", "lol", "fr?", "same!"]
    },
    {
        "id": "lily_artistic",
        "name": "Lily",
        "age": 21,
        "style": "Creative Dreamer - artistic, thoughtful, poetic",
        "starter": "hi... I've been feeling uninspired lately",
        "traits": ["uses descriptive language", "reflects on emotions", "asks deep questions", "creative insights"],
        "sample_phrases": ["that's beautiful", "I feel like...", "it reminds me of...", "hmm interesting", "I love that"]
    },
    {
        "id": "sophie_academic",
        "name": "Sophie",
        "age": 22,
        "style": "Academic Achiever - logical, goal-oriented, precise",
        "starter": "hey, I want to work on personal development",
        "traits": ["clear communication", "analytical questions", "goal-focused", "structured thinking"],
        "sample_phrases": ["that makes sense", "how can I improve", "what's the best way", "I've been working on", "good point"]
    },
    {
        "id": "mia_anxious",
        "name": "Mia",
        "age": 18,
        "style": "Anxious Overthinker - sensitive, needs support, genuine",
        "starter": "I'm feeling really overwhelmed...",
        "traits": ["seeks reassurance", "expresses worries", "hesitant language", "appreciates support"],
        "sample_phrases": ["I'm worried that", "do you think", "I'm not sure", "that's kinda scary", "maybe"]
    },
    {
        "id": "zoe_energetic",
        "name": "Zoe",
        "age": 20,
        "style": "Energetic Optimist - positive, motivational, active",
        "starter": "hey! I need some motivation today",
        "traits": ["always positive", "energetic language", "motivates others", "very supportive"],
        "sample_phrases": ["let's go!", "you got this!", "that's amazing!", "awesome!", "yes!"]
    }
]

# Simple conversation starters
CONVERSATION_STARTERS = [
    {
        "id": "daily_chat",
        "topic": "Daily Chat",
        "persona": USER_PERSONAS[0],  
        "expected_flow": "Light and energetic social conversation"
    },
    {
        "id": "creative_support",
        "topic": "Creative Support",
        "persona": USER_PERSONAS[1],  
        "expected_flow": "Inspiring and artistic conversation"
    },
    {
        "id": "personal_growth",
        "topic": "Personal Growth",
        "persona": USER_PERSONAS[2],  
        "expected_flow": "Goal-oriented development conversation"
    },
    {
        "id": "emotional_support",
        "topic": "Emotional Support",
        "persona": USER_PERSONAS[3],  
        "expected_flow": "Comforting and supportive conversation"
    },
    {
        "id": "motivation",
        "topic": "Motivation",
        "persona": USER_PERSONAS[4],  
        "expected_flow": "Uplifting and energizing conversation"
    }
]

# Dynamic evaluation dimensions
DYNAMIC_EVALUATION_DIMENSIONS = {
    "conversation_flow": {
        "description": "Conversation fluency and naturalness",
        "weight": 0.2,
        "criteria": [
            "Whether the conversation flows naturally and smoothly",
            "Whether topic transitions are reasonable",
            "Whether there are abrupt disconnections"
        ]
    },
    "user_engagement": {
        "description": "User engagement and interest maintenance",
        "weight": 0.2,
        "criteria": [
            "Whether it can attract users to continue the conversation",
            "Whether users show interest",
            "Whether the conversation is engaging"
        ]
    },
    "character_consistency": {
        "description": "AI character consistency",
        "weight": 0.15,
        "criteria": [
            "Whether the AI's character is consistently maintained",
            "Whether language style is consistent",
            "Whether behavior patterns match the setting"
        ]
    },
    "emotional_intelligence": {
        "description": "Emotional intelligence and empathy",
        "weight": 0.15,
        "criteria": [
            "Whether it understands user emotions",
            "Whether responses are appropriate",
            "Whether it shows empathy"
        ]
    },
    "topic_handling": {
        "description": "Topic handling ability",
        "weight": 0.15,
        "criteria": [
            "Whether it can handle topics well",
            "Whether replies are relevant and valuable",
            "Whether it can advance conversation development"
        ]
    },
    "adaptability": {
        "description": "Adaptability and flexibility",
        "weight": 0.15,
        "criteria": [
            "Whether it adapts to user conversation style",
            "Whether it adjusts response strategies flexibly",
            "Whether it handles unexpected situations"
        ]
    }
}

