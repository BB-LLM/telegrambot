"""
User Agent - Simulate real users for dynamic conversations
Aligned with pocket-souls-agents/evaluation
"""

import asyncio
import json
import random
from typing import List, Dict, Optional
from dataclasses import dataclass
import openai
from openai import AsyncOpenAI


@dataclass
class ConversationTurn:
    """Conversation turn data structure"""
    round_number: int
    user_input: str
    bot_response: str
    timestamp: str


@dataclass
class ConversationSession:
    """Complete conversation session data structure"""
    session_id: str
    topic: str
    starter: str
    user_persona: str
    turns: List[ConversationTurn]
    total_rounds: int


class UserAgent:
    """Simulate user agent for dynamic conversations with TelegramBot"""

    def __init__(self, openai_api_key: str, config: Optional[Dict] = None):
        # 支持 DeepSeek API（兼容 OpenAI 格式）
        from config.evaluation_config import DYNAMIC_CONVERSATION_CONFIG
        self.config = config or DYNAMIC_CONVERSATION_CONFIG
        
        base_url = self.config.get("base_url")
        if base_url:
            # 使用 DeepSeek API
            self.client = AsyncOpenAI(api_key=openai_api_key, base_url=base_url)
        else:
            # 默认 OpenAI
            self.client = AsyncOpenAI(api_key=openai_api_key)
        
        self.conversation_history = []

    def _build_user_prompt(self, persona: Dict, conversation_history: List[Dict],
                          bot_response: str, round_number: int) -> str:
        """Build persona-based User Agent prompt"""

        history_text = ""
        if conversation_history:
            for turn in conversation_history[-3:]:
                history_text += f"User: {turn['user']}\nTelegramBot: {turn['bot']}\n"

        name = persona["name"]
        age = persona["age"]
        style = persona["style"]
        sample_phrases = persona["sample_phrases"]

        response_types = [
            "react_and_share",
            "just_react",
            "ask_follow_up",
            "share_experience",
            "simple_response"
        ]

        if round_number <= 2:
            response_type = random.choice(["react_and_share", "just_react", "share_experience"])
        elif round_number >= 4:
            response_type = random.choice(["just_react", "simple_response", "share_experience"])
        else:
            response_type = random.choice(response_types)

        prompt = f"""You are {name}, a {age}-year-old from Singapore.

PERSONALITY: {style}
TYPICAL PHRASES: {', '.join(sample_phrases)}

CONVERSATION HISTORY:
{history_text}

TelegramBot just said: "{bot_response}"

RESPONSE TYPE FOR THIS ROUND: {response_type}

INSTRUCTIONS:
- This is round {round_number} of 5 (NOT the end of conversation)
- Response type: {response_type}
  * react_and_share: React to TelegramBot + share something brief
  * just_react: Just respond to what TelegramBot said
  * ask_follow_up: Ask a follow-up question
  * share_experience: Share a brief personal experience
  * simple_response: Give a short, natural reaction

CRITICAL RULES:
- Keep responses SHORT (1 sentence, max 2)
- Don't always ask questions - real people don't do that
- Don't treat round 5 as "ending" - it's just another turn
- Be natural and spontaneous
- Use your personality phrases naturally

Respond as {name} would (SHORT and natural):"""

        return prompt
    
    async def generate_user_response(self, persona: Dict, conversation_history: List[Dict],
                                   bot_response: str, round_number: int,
                                   config: Dict) -> str:
        """Generate persona-based user response"""

        try:
            prompt = self._build_user_prompt(persona, conversation_history,
                                           bot_response, round_number)

            response = await self.client.chat.completions.create(
                model=config["user_agent_model"],
                messages=[
                    {"role": "system", "content": "You are roleplaying as a specific person. Stay in character and respond authentically."},
                    {"role": "user", "content": prompt}
                ],
                temperature=config["temperature"],
                max_tokens=config["max_tokens"],
                timeout=config["timeout"]
            )

            user_response = response.choices[0].message.content.strip()

            # 清理回复
            user_response = user_response.strip('"\'')
            if user_response.startswith("用户:") or user_response.startswith(f"{persona['name']}:"):
                user_response = user_response.split(":", 1)[-1].strip()

            return user_response

        except Exception as e:
            print(f"User Agent failed to generate response: {e}")
            sample_phrases = persona.get("sample_phrases", ["That's interesting", "I see", "Cool"])
            return random.choice(sample_phrases)
