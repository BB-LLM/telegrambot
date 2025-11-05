"""
TelegramBot Interface Adapter
Connects to the real TelegramBot system for conversations
"""

import requests
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
import random


@dataclass
class TelegramBotConfig:
    """TelegramBot configuration"""
    api_url: str = "http://localhost:8082"
    model: str = "glm-4-flash"
    user_id: str = "evaluation_user"
    default_persona: str = """
Name: Nova  
Archetype: Guardian Angel / Apprentice Wayfinder  
Pronouns: they/them
Apparent age: mid‑20s (ageless spirit)
Origin: The Cloud Forest (star‑moss, mist, wind‑chimes)  
Visual Motifs: soft glow, leaf‑shaped pin with a tiny star, firefly motes when delighted  
"""


class TelegramBotInterface:
    """TelegramBot 接口类"""

    def __init__(self, config: Optional[TelegramBotConfig] = None):
        self.config = config or TelegramBotConfig()
        
    async def send_message(self, message: str, context: Optional[List[Dict]] = None) -> str:
        """
        Send a message and get the bot response
        
        Args:
            message: user message
            context: conversation context (optional)
            
        Returns:
            str: bot response
        """
        try:
            # 构建请求负载
            payload = {
                "user_id": self.config.user_id,
                "message": message,
                "model": self.config.model,
                "persona": self.config.default_persona,
                "frequency": 1,
                "summary_frequency": 10,
                "scene": "default",
                "assessment_mode": "normal"
            }
            
            # 发送请求
            response = requests.post(
                f"{self.config.api_url}/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                json_response = response.json()
                bot_reply = json_response.get("response", "No response from server.")
                return bot_reply
            else:
                print(f"TelegramBot API error: {response.status_code}")
                raise Exception(f"API returned error status code: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending message: {e}")
            raise Exception(f"TelegramBot API error: {str(e)}")
    
    async def get_response(self, user_input: str, max_retries: int = 3) -> str:
        """
        Get TelegramBot response with retry mechanism
        
        Args:
            user_input: user input
            max_retries: max retry attempts
            
        Returns:
            str: bot response
        """
        for attempt in range(max_retries + 1):
            try:
                response = await self.send_message(user_input)
                # 如果成功获得回复，直接返回
                return response
                
            except Exception as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                    print(f"Warning: TelegramBot API error, retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries + 1}): {str(e)[:100]}...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # 最后一次重试也失败了，抛出异常
                    print(f"Error: TelegramBot API failed after {max_retries} retries: {e}")
                    raise Exception(f"TelegramBot API failed after {max_retries} retries: {e}")

        # This line should theoretically never be reached
        raise Exception("TelegramBot API failed - unexpected code path")
