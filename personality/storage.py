"""
Personality Data Storage
使用记忆系统存储personality数据
"""

import json
from typing import Optional
from loguru import logger

from personality.models import PersonalityData


class PersonalityStorage:
    """性格数据存储"""
    
    def __init__(self, memory_instance):
        """
        初始化存储
        
        Args:
            memory_instance: Memory实例，用于存储数据
        """
        self.memory = memory_instance
    
    def save(self, personality_data: PersonalityData):
        """
        保存personality数据到记忆系统
        
        Args:
            personality_data: 要保存的性格数据
        """
        try:
            # 转换为JSON字符串
            data_dict = personality_data.to_dict()
            data_json = json.dumps(data_dict, ensure_ascii=False)
            
            # 构建metadata
            metadata = {
                "type": "personality_profile",
                "user_id": personality_data.user_id,
                "total_exchanges": personality_data.total_exchanges,
                "last_assessment": personality_data.last_assessment
            }
            
            # 删除旧的personality profile（如果存在）
            self._delete_old_profile(personality_data.user_id)
            
            # 添加新的profile到记忆系统
            self.memory.add(
                messages=[{
                    "role": "system",
                    "content": f"personality_profile:{data_json}"
                }],
                user_id=personality_data.user_id,
                metadata=metadata,
                infer=False  # 不进行推理，直接存储
            )
            
            logger.info(f"Saved personality profile for user {personality_data.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to save personality data: {e}")
    
    def load(self, user_id: str) -> Optional[PersonalityData]:
        """
        从记忆系统加载personality数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            PersonalityData对象，如果不存在则返回None
        """
        try:
            # 从记忆系统搜索personality profile
            result = self.memory.get_all(
                user_id=user_id,
                filters={"type": "personality_profile"},
                limit=1
            )
            
            if result and "results" in result and len(result["results"]) > 0:
                # 获取最新的profile
                profile_entry = result["results"][0]
                profile_content = profile_entry.get("memory", "")
                
                # 解析JSON
                if profile_content.startswith("personality_profile:"):
                    json_str = profile_content[len("personality_profile:"):]
                    data_dict = json.loads(json_str)
                    
                    # 重建PersonalityData对象
                    personality_data = PersonalityData.from_dict(data_dict)
                    logger.info(f"Loaded personality profile for user {user_id}")
                    return personality_data
            
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse personality data JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load personality data: {e}")
            return None
    
    def _delete_old_profile(self, user_id: str):
        """删除旧的personality profile"""
        try:
            # 查找旧profile
            result = self.memory.get_all(
                user_id=user_id,
                filters={"type": "personality_profile"},
                limit=10
            )
            
            if result and "results" in result:
                for entry in result["results"]:
                    memory_id = entry.get("id")
                    if memory_id:
                        self.memory.delete(memory_id)
                        logger.debug(f"Deleted old personality profile: {memory_id}")
        except Exception as e:
            logger.warning(f"Failed to delete old profile: {e}")

