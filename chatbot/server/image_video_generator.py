"""
图像和视频生成模块 - 调用 imageGen API 生成图像和视频
"""
import asyncio
import aiohttp
import requests
from typing import Optional, Dict, Tuple
from loguru import logger
from prompt_builder import get_prompt_builder


class ImageVideoGenerator:
    """图像和视频生成器 - 调用 imageGen API"""
    
    def __init__(self, imagegen_api_url: str = "http://36.138.179.204:8000"):
        """
        初始化生成器
        
        Args:
            imagegen_api_url: imageGen API 的基础 URL
        """
        self.imagegen_api_url = imagegen_api_url
        self.prompt_builder = get_prompt_builder()
    
    def generate_image(
        self,
        soul_id: str,
        cue: str,
        user_id: str,
        max_retries: int = 2
    ) -> Optional[Dict]:
        """
        生成图像（带重试机制）

        Args:
            soul_id: Soul ID
            cue: 提示词
            user_id: 用户 ID
            max_retries: 最大重试次数（默认2次）

        Returns:
            API 响应字典，包含 image_url 等信息
        """
        url = f"{self.imagegen_api_url}/image"
        params = {
            "soul_id": soul_id,
            "cue": cue,
            "user_id": user_id
        }

        for attempt in range(max_retries):
            try:
                logger.info(f"Calling imageGen API (attempt {attempt + 1}/{max_retries}): {url} with params: {params}")
                response = requests.get(url, params=params, timeout=120)

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Image generation successful: {result}")
                    return result
                else:
                    error_msg = response.text
                    logger.error(f"Image generation failed (attempt {attempt + 1}/{max_retries}): {response.status_code} - {error_msg}")

                    # 如果是数据库事务错误（500），且不是最后一次尝试，则重试
                    if response.status_code == 500 and "transaction" in error_msg.lower() and attempt < max_retries - 1:
                        logger.info(f"Database transaction error detected, retrying...")
                        continue

                    return None
            except Exception as e:
                logger.error(f"Error generating image (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying...")
                    continue
                return None

        return None
    
    def generate_video(
        self,
        soul_id: str,
        cue: str,
        user_id: str,
        max_retries: int = 2
    ) -> Optional[Dict]:
        """
        生成视频（带重试机制）

        Args:
            soul_id: Soul ID
            cue: 提示词
            user_id: 用户 ID
            max_retries: 最大重试次数（默认2次）

        Returns:
            API 响应字典，包含 mp4_url 等信息
        """
        url = f"{self.imagegen_api_url}/wan-video/"
        params = {
            "soul_id": soul_id,
            "cue": cue,
            "user_id": user_id
        }

        for attempt in range(max_retries):
            try:
                logger.info(f"Calling imageGen API (attempt {attempt + 1}/{max_retries}): {url} with params: {params}")
                # 增加超时时间
                response = requests.get(url, params=params, timeout=1500)

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Video generation successful: {result}")
                    return result
                else:
                    error_msg = response.text
                    logger.error(f"Video generation failed (attempt {attempt + 1}/{max_retries}): {response.status_code} - {error_msg}")

                    # 如果是数据库事务错误（500），且不是最后一次尝试，则重试
                    if response.status_code == 500 and "transaction" in error_msg.lower() and attempt < max_retries - 1:
                        logger.info(f"Database transaction error detected, retrying...")
                        continue

                    return None
            except Exception as e:
                logger.error(f"Error generating video (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying...")
                    continue
                return None

        return None
    
    def generate_selfie_image(
        self,
        soul_id: str,
        city_key: str,
        mood: str,
        user_id: str
    ) -> Optional[Dict]:
        """
        生成自拍图像
        
        Args:
            soul_id: Soul ID
            city_key: 城市键（paris, tokyo, newyork, london, rome）
            mood: 心情（happy, sad, excited, calm, romantic, adventurous）
            user_id: 用户 ID
        
        Returns:
            API 响应字典，包含 image_url 等信息
        """
        try:
            url = f"{self.imagegen_api_url}/image/selfie"
            payload = {
                "soul_id": soul_id,
                "city_key": city_key,
                "mood": mood,
                "user_id": user_id
            }
            
            logger.info(f"Calling imageGen API: {url} with payload: {payload}")
            response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Selfie image generation successful: {result}")
                return result
            else:
                logger.error(f"Selfie image generation failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error generating selfie image: {e}")
            return None
    
    def generate_selfie_video(
        self,
        soul_id: str,
        city_key: str,
        mood: str,
        user_id: str
    ) -> Optional[Dict]:
        """
        生成自拍视频

        Args:
            soul_id: Soul ID
            city_key: 城市键（paris, tokyo, newyork, london, rome）
            mood: 心情（happy, sad, excited, calm, romantic, adventurous）
            user_id: 用户 ID

        Returns:
            API 响应字典，包含 mp4_url 等信息
        """
        try:
            url = f"{self.imagegen_api_url}/wan-video/selfie"
            payload = {
                "soul_id": soul_id,
                "city_key": city_key,
                "mood": mood,
                "user_id": user_id
            }

            logger.info(f"Calling imageGen API: {url} with payload: {payload}")
            # 增加超时时间
            response = requests.post(url, json=payload, timeout=1500)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Selfie video generation successful: {result}")
                return result
            else:
                logger.error(f"Selfie video generation failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error generating selfie video: {e}")
            return None
    
    def build_cue_from_context(
        self,
        user_input: str,
        chat_history: list,
        soul_keywords: list = None
    ) -> str:
        """
        从聊天上下文构建 cue
        
        Args:
            user_input: 用户输入
            chat_history: 聊天历史
            soul_keywords: Soul 的风格关键词
        
        Returns:
            构建好的 cue 字符串
        """
        return self.prompt_builder.build_standard_cue(
            user_input,
            chat_history,
            soul_keywords
        )


# 全局生成器实例
_generator = None


def get_image_video_generator(imagegen_api_url: str = "http://36.138.179.204:8000") -> ImageVideoGenerator:
    """
    获取全局图像视频生成器实例
    
    Args:
        imagegen_api_url: imageGen API 的基础 URL
    
    Returns:
        ImageVideoGenerator 实例
    """
    global _generator
    if _generator is None:
        _generator = ImageVideoGenerator(imagegen_api_url)
    return _generator

