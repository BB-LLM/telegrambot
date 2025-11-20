"""Diary service - handles diary generation logic"""
import httpx
import requests
from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger


class DiaryService:
    """Diary service for generating and retrieving diaries"""
    
    def __init__(self, diary_api_url: str = "http://34.148.51.133:8083"):
        """
        Initialize diary service
        
        Args:
            diary_api_url: Diary module API base URL
        """
        self.diary_api_url = diary_api_url
    
    async def generate_diary(
        self, 
        user_id: str, 
        date: str,  # yyyy-mm-dd
        messages: List[Dict],  # 该用户当天的消息列表
        timezone: str = "Asia/Shanghai"
    ) -> Optional[Dict]:
        """
        为该用户生成日记
        
        Args:
            user_id: 用户ID
            date: 日期 (yyyy-mm-dd)
            messages: 当天消息列表，格式 [{"role": "...", "content": "...", "time": "..."}, ...]
            timezone: 用户时区
            
        Returns:
            日记数据字典，如果失败返回None
        """
        # 构建请求体（符合DiaryGenerateRequest格式）
        request_body = {
            "user_id": user_id,
            "date": date,
            "timezone": timezone,
            "messages": [
                {
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "time": msg.get("time", "")
                }
                for msg in messages
            ]
            # 注意：根据需求文档，不需要memories字段
        }
        
        # 调用POST /diary/generate（带重试机制）
        # 直接使用同步requests，因为httpx AsyncClient在某些情况下会立即返回502
        # 使用asyncio.to_thread在线程池中运行，避免阻塞事件循环
        max_retries = 3
        base_retry_delay = 1.0  # 基础重试延迟（秒）
        
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"[DiaryService] Calling diary API (attempt {attempt + 1}/{max_retries}): "
                    f"POST {self.diary_api_url}/diary/generate"
                )
                logger.debug(f"[DiaryService] Request body: user_id={user_id}, date={date}, messages_count={len(messages)}")
                
                # 直接使用同步requests，在线程池中运行，避免阻塞
                import asyncio
                response = await asyncio.to_thread(
                    requests.post,
                    f"{self.diary_api_url}/diary/generate",
                    json=request_body,
                    timeout=90.0  # 增加超时时间到90秒，确保LLM调用有足够时间（LLM调用可能需要9-10秒）
                )
                logger.debug(f"[DiaryService] Response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    diary_data = result.get("diary")
                    logger.info(f"[DiaryService] Diary generated successfully for user {user_id} on {date}")
                    return diary_data
                else:
                    # 其他错误状态码
                    try:
                        error_text = response.text[:500] if response.text else "No response body"
                        logger.error(
                            f"[DiaryService] Diary API error for user {user_id}: "
                            f"status={response.status_code}, response={error_text}"
                        )
                    except Exception as e:
                        logger.error(
                            f"[DiaryService] Diary API error for user {user_id}: "
                            f"status={response.status_code}, failed to read response: {str(e)}"
                        )
                    if attempt < max_retries - 1:
                        retry_delay = base_retry_delay * (2 ** attempt)
                        logger.warning(
                            f"[DiaryService] Request failed (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {retry_delay}s..."
                        )
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        return None
                        
            except requests.exceptions.Timeout as e:
                # 超时错误
                if attempt < max_retries - 1:
                    retry_delay = base_retry_delay * (2 ** attempt)
                    logger.warning(
                        f"[DiaryService] Request timeout (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {retry_delay}s... Error: {str(e)}"
                    )
                    import asyncio
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"[DiaryService] Diary API request timeout for user {user_id} after {max_retries} attempts: {str(e)}")
                    return None
            except requests.exceptions.ConnectionError as e:
                # 连接错误
                if attempt < max_retries - 1:
                    retry_delay = base_retry_delay * (2 ** attempt)
                    logger.warning(
                        f"[DiaryService] Connection error (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {retry_delay}s... Error: {str(e)}"
                    )
                    import asyncio
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(
                        f"[DiaryService] Failed to connect to diary service at {self.diary_api_url} after {max_retries} attempts. "
                        f"Is the diary service running on port 8083? Error: {str(e)}"
                    )
                    return None
            except requests.exceptions.RequestException as e:
                # 其他请求错误
                if attempt < max_retries - 1:
                    retry_delay = base_retry_delay * (2 ** attempt)
                    logger.warning(
                        f"[DiaryService] Request error (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {retry_delay}s... Error: {str(e)}"
                    )
                    import asyncio
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"[DiaryService] Diary API request error for user {user_id} after {max_retries} attempts: {str(e)}")
                    return None
            except Exception as e:
                logger.exception(f"[DiaryService] Unexpected error generating diary for user {user_id} (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    retry_delay = base_retry_delay * (2 ** attempt)
                    import asyncio
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return None
        
        # 如果所有重试都失败，返回None
        logger.error(f"[DiaryService] Failed to generate diary for user {user_id} after {max_retries} attempts")
        return None
    
    async def get_user_diary(self, user_id: str) -> Optional[Dict]:
        """
        获取该用户的日记（今天或昨天）
        
        Args:
            user_id: 用户ID
        
        Returns:
            日记数据字典，如果未找到返回None
        """
        try:
            url = f"{self.diary_api_url}/diary/today?user_id={user_id}"
            logger.debug(f"[DiaryService] Calling diary API: {url}")
            
            # 直接使用同步requests，在线程池中运行，避免阻塞
            import asyncio
            response = await asyncio.to_thread(
                requests.get,
                url,
                timeout=30.0  # 增加超时时间到30秒
            )
            logger.debug(f"[DiaryService] Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                diary_data = result.get("diary")
                source_date = result.get("source_date", "")
                
                if diary_data:
                    # 检查是否是今天的日记
                    today = datetime.now().strftime("%Y-%m-%d")
                    is_today = source_date == today
                    
                    return {
                        "user_id": user_id,
                        "date": source_date,
                        "is_today": is_today,
                        "diary": diary_data
                    }
                else:
                    logger.warning(f"[DiaryService] Diary API returned 200 but no diary data for user {user_id}")
                    return None
            elif response.status_code == 404:
                logger.info(f"[DiaryService] No diary found for user {user_id}")
                return None
            else:
                # 记录详细错误信息
                try:
                    error_body = response.text
                    logger.error(f"[DiaryService] Diary API error {response.status_code}: {error_body[:200]}")
                except:
                    logger.error(f"[DiaryService] Diary API error: {response.status_code}")
                return None
                    
        except requests.exceptions.Timeout as e:
            logger.error(f"[DiaryService] Diary API request timeout: {str(e)}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"[DiaryService] Failed to connect to diary service at {self.diary_api_url}. "
                f"Is the diary service running on port 8083? Error: {str(e)}"
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[DiaryService] Diary API request error: {str(e)}")
            return None
        except Exception as e:
            logger.exception(f"[DiaryService] Error getting diary for user {user_id}: {str(e)}")
            return None
    
    def filter_today_messages(self, chat_history: List[Dict], date: str) -> List[Dict]:
        """
        从聊天历史中筛选当天的消息
        
        Args:
            chat_history: 完整聊天历史 [{"role": "...", "content": "...", "time": "2025-11-03 10:30:00"}, ...]
            date: 目标日期 (yyyy-mm-dd)
            
        Returns:
            当天的消息列表
        """
        today_messages = []
        for msg in chat_history:
            msg_time = msg.get("time", "")
            # 提取日期部分（格式："2025-11-03 10:30:00" -> "2025-11-03"）
            if msg_time and msg_time.startswith(date):
                today_messages.append(msg)
        
        return today_messages


# 全局实例
diary_service = DiaryService()

