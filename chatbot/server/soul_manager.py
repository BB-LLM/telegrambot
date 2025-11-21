"""
Soul 数据管理模块 - 从 imageGen 获取 Soul 信息
"""
import requests
from typing import Dict, List, Optional
from loguru import logger


class SoulManager:
    """Soul 管理器 - 获取和缓存 Soul 信息"""
    
    def __init__(self, imagegen_api_url: str = "http://36.138.179.204:8000"):
        """
        初始化 Soul 管理器
        
        Args:
            imagegen_api_url: imageGen API 地址
        """
        self.imagegen_api_url = imagegen_api_url
        self._souls_cache = None
        self._cache_timestamp = None
    
    def get_all_souls(self, use_cache: bool = True) -> Dict[str, Dict]:
        """
        获取所有 Soul 信息
        
        Args:
            use_cache: 是否使用缓存
        
        Returns:
            {
                "nova": {
                    "soul_id": "nova",
                    "display_name": "Nova",
                    "style_keywords": [...],
                    "personality": "...",
                    "age": "...",
                    "profession": "...",
                    "description": "..."
                },
                ...
            }
        """
        if use_cache and self._souls_cache is not None:
            return self._souls_cache
        
        try:
            # 尝试从 imageGen 的 API 获取 Soul 列表
            # 如果 imageGen 没有提供 API，则使用硬编码的配置
            souls = self._fetch_souls_from_imagegen()
            if souls:
                self._souls_cache = souls
                return souls
        except Exception as e:
            logger.warning(f"Failed to fetch souls from imageGen: {e}")
        
        # 如果获取失败，使用硬编码的配置
        return self._get_default_souls()
    
    def get_soul_by_id(self, soul_id: str) -> Optional[Dict]:
        """
        根据 Soul ID 获取 Soul 信息
        
        Args:
            soul_id: Soul ID
        
        Returns:
            Soul 信息字典，如果不存在则返回 None
        """
        souls = self.get_all_souls()
        return souls.get(soul_id)
    
    def get_soul_display_info(self, soul_id: str) -> str:
        """
        获取 Soul 的显示信息（用于 UI 展示）
        显示 Soul 的完整描述和风格关键词

        Args:
            soul_id: Soul ID

        Returns:
            格式化的 Soul 信息字符串
        """
        soul = self.get_soul_by_id(soul_id)
        if not soul:
            return f"Soul '{soul_id}' not found"

        # 显示完整的 Soul 信息
        info = ""

        # 显示描述
        if soul.get('description'):
            info += f"{soul['description']}\n\n"

        # 显示风格关键词
        if soul.get('style_keywords'):
            keywords = '\n'.join(soul['style_keywords'])
            info += keywords

        return info
    
    def _fetch_souls_from_imagegen(self) -> Optional[Dict]:
        """
        从 imageGen 的 API 获取 Soul 信息
        
        Returns:
            Soul 信息字典，如果获取失败则返回 None
        """
        try:
            # 尝试调用 imageGen 的 /souls 端点（如果存在）
            response = requests.get(
                f"{self.imagegen_api_url}/souls",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Failed to fetch from /souls endpoint: {e}")
        
        return None
    
    def _get_default_souls(self) -> Dict[str, Dict]:
        """
        获取默认的 Soul 配置（硬编码）
        
        Returns:
            Soul 信息字典
        """
        return {
            "nova": {
                "soul_id": "nova",
                "display_name": "Nova",
                "personality": "Guardian Angel",
                "age": "mid-20s (ageless spirit)",
                "profession": "Guardian",
                "description": "Anime style, pastel colors, kawaii cute",
                "style_keywords": ["anime", "pastel", "cute", "ethereal"]
            },
            "valentina": {
                "soul_id": "valentina",
                "display_name": "Valentina",
                "personality": "Sophisticated",
                "age": "Unknown",
                "profession": "Unknown",
                "description": "Realistic style, elegant colors, sophisticated",
                "style_keywords": ["realistic", "elegant", "sophisticated"]
            },
            "lizhe": {
                "soul_id": "lizhe",
                "display_name": "Li Zhe",
                "personality": "INTJ",
                "age": "30",
                "profession": "Data Analyst",
                "description": "Professional style, minimalist, business elite",
                "style_keywords": ["professional", "minimalist", "business", "sophisticated"]
            },
            "linna": {
                "soul_id": "linna",
                "display_name": "Lin Na",
                "personality": "ESFP",
                "age": "25",
                "profession": "Party Planner",
                "description": "Fashionable style, vibrant colors, energetic",
                "style_keywords": ["fashionable", "vibrant", "colorful", "energetic"]
            },
            "wangjing": {
                "soul_id": "wangjing",
                "display_name": "Wang Jing",
                "personality": "INFJ",
                "age": "28",
                "profession": "Psychologist",
                "description": "Comfortable style, soft colors, serene",
                "style_keywords": ["comfortable", "soft", "serene", "peaceful"]
            }
        }


# 全局 Soul 管理器实例
_soul_manager = None


def get_soul_manager(imagegen_api_url: str = "http://36.138.179.204:8000") -> SoulManager:
    """
    获取全局 Soul 管理器实例
    
    Args:
        imagegen_api_url: imageGen API 地址
    
    Returns:
        SoulManager 实例
    """
    global _soul_manager
    if _soul_manager is None:
        _soul_manager = SoulManager(imagegen_api_url)
    return _soul_manager

