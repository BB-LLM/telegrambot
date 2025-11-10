"""LLM service module - uses glm-4-flash to generate diary"""
import json
from datetime import datetime
from typing import List, Optional
from openai import OpenAI
from loguru import logger
from config import settings
from models import MessageModel, MemoriesModel


class LLMService:
    """LLM service - calls glm-4-flash to generate diary content"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        self.model = settings.llm_model
    
    def generate_diary(
        self,
        messages: List[MessageModel],
        memories: Optional[MemoriesModel] = None
    ) -> dict:
        """
        Generate diary based on daily conversations (messages) and optionally memories
        
        Requirements (according to requirement document A10):
        - Title: fixed "Today's Reflection"
        - Body: 3-6 lines in English
        - Tags: 2 lowercase English words
        - Do not fabricate facts that clearly don't exist
        - If memories not provided, only use messages to generate diary
        """
        
        # Build prompt
        system_prompt = """You are Nova, a positive and warm AI assistant. Your task is to generate a "Today's Reflection" diary based on the user's daily memories and conversations.

Requirements:
1. Title must be fixed as "Today's Reflection"
2. Body output 3-6 lines in English, each line a complete English sentence, clear, warm, and positive
3. Output 2 lowercase English tags, summarizing the main themes of the day
4. Must be based on the provided messages and memories content, do not fabricate facts that clearly don't exist
5. If information is insufficient, you can supplement with gentle general advice or encouraging words

Output format (strict JSON):
{
    "title": "Today's Reflection",
    "body_lines": ["First line", "Second line", "Third line", ...],
    "tags": ["tag1", "tag2"]
}"""

        # Build user input
        messages_text = "\n".join([
            f"[{msg.time or 'N/A'}] {msg.role}: {msg.content}"
            for msg in messages
        ])
        
        # Build prompt with or without memories
        if memories:
            user_prompt = f"""Based on the following daily conversations and memories, generate today's reflection diary:

【Daily Conversation Records】
{messages_text}

【Memory Information】
[memorable events]: {memories.facts}

[player profile]: {memories.profile}

[style notes]: {memories.style}

[tiny commitments]: {memories.commitments}

Please generate a diary in the required JSON format."""
        else:
            # Only use messages, no memories
            user_prompt = f"""Based on the following daily conversations, generate today's reflection diary:

【Daily Conversation Records】
{messages_text}

Please generate a diary in the required JSON format."""
        
        content = None
        try:
            # Call LLM
            logger.info(f"[LLMService] Calling LLM API (model={self.model}) to generate diary")
            logger.debug(f"[LLMService] Messages count: {len(messages)}, Has memories: {memories is not None}")
            
            llm_start = datetime.now()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"},  # Force JSON output
                timeout=60.0  # Add timeout to prevent hanging
            )
            llm_elapsed = (datetime.now() - llm_start).total_seconds()
            logger.info(f"[LLMService] LLM API call completed in {llm_elapsed:.2f}s")
            
            # Parse response
            content = response.choices[0].message.content
            logger.debug(f"[LLMService] LLM response content length: {len(content)} characters")
            diary_data = json.loads(content)
            logger.debug(f"[LLMService] Parsed diary data: title={diary_data.get('title')}, body_lines={len(diary_data.get('body_lines', []))}, tags={diary_data.get('tags')}")
            
            # Validate and normalize
            title = diary_data.get("title", "Today's Reflection")
            body_lines = diary_data.get("body_lines", [])
            tags = diary_data.get("tags", [])
            
            # Ensure body is within 3-6 lines
            if len(body_lines) < 3:
                # If less than 3 lines, duplicate the last line to fill
                while len(body_lines) < 3:
                    body_lines.append(body_lines[-1] if body_lines else "Today was fulfilling and productive.")
            elif len(body_lines) > 6:
                # If more than 6 lines, take only first 6
                body_lines = body_lines[:6]
            
            # Ensure tags count is 2
            if len(tags) < 2:
                # If less than 2, add default tags
                default_tags = ["daily", "reflection", "growth", "focus", "health", "balance"]
                for tag in default_tags:
                    if tag not in tags:
                        tags.append(tag)
                        if len(tags) >= 2:
                            break
            elif len(tags) > 2:
                tags = tags[:2]
            
            # Ensure tags are lowercase English
            tags = [tag.lower().strip() for tag in tags]
            
            return {
                "title": title,
                "body_lines": body_lines,
                "tags": tags
            }
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return default content
            logger.error(f"[LLMService] JSON decode error: {str(e)}")
            logger.debug(f"[LLMService] Response content that failed to parse: {content[:500] if content else 'N/A'}")
            logger.warning(f"[LLMService] Returning default diary content due to JSON parse error")
            return {
                "title": "Today's Reflection",
                "body_lines": [
                    "Completed today's goals successfully.",
                    "Maintaining focus and self-discipline.",
                    "Will continue to advance related work tomorrow."
                ],
                "tags": ["focus", "daily"]
            }
        except Exception as e:
            # Return default content on error
            logger.exception(f"[LLMService] Error calling LLM API: {str(e)}")
            logger.warning(f"[LLMService] Returning default diary content due to error")
            return {
                "title": "Today's Reflection",
                "body_lines": [
                    "Completed today's goals successfully.",
                    "Maintaining focus and self-discipline.",
                    "Will continue to advance related work tomorrow."
                ],
                "tags": ["focus", "daily"]
            }


# Global LLM service instance
llm_service = LLMService()
