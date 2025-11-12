"""
地标多样性选择系统
"""
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from ..data.dal import LandmarkLogDAL
from ..data.models import LandmarkLogBase
from ..core.lww import now_ms


class PlaceChooser:
    """地标选择器"""
    
    def __init__(self):
        # 城市地标配置
        self.city_landmarks = {
            "paris": [
                "eiffel_tower",
                "louvre",
                "montmartre", 
                "pont_alexandre_iii",
                "notre_dame",
                "arc_de_triomphe",
                "champs_elysees",
                "sacre_coeur"
            ],
            "tokyo": [
                "tokyo_tower",
                "skytree",
                "sensoji_temple",
                "shibuya_crossing",
                "harajuku",
                "ginza",
                "imperial_palace",
                "meiji_shrine"
            ],
            "newyork": [
                "statue_of_liberty",
                "empire_state_building",
                "times_square",
                "central_park",
                "brooklyn_bridge",
                "wall_street",
                "high_line",
                "broadway"
            ],
            "london": [
                "big_ben",
                "london_eye",
                "tower_bridge",
                "buckingham_palace",
                "westminster_abbey",
                "hyde_park",
                "covent_garden",
                "camden_market"
            ],
            "rome": [
                "colosseum",
                "vatican",
                "trevi_fountain",
                "pantheon",
                "spanish_steps",
                "roman_forum",
                "sistine_chapel",
                "piazza_navona"
            ]
        }
        
        # 地标描述映射
        self.landmark_descriptions = {
            "eiffel_tower": "Eiffel Tower with iron lattice structure",
            "louvre": "Louvre Museum with glass pyramid",
            "montmartre": "Montmartre hill with Sacré-Cœur",
            "pont_alexandre_iii": "Pont Alexandre III bridge",
            "notre_dame": "Notre-Dame Cathedral",
            "arc_de_triomphe": "Arc de Triomphe monument",
            "champs_elysees": "Champs-Élysées avenue",
            "sacre_coeur": "Sacré-Cœur Basilica",
            "tokyo_tower": "Tokyo Tower red and white structure",
            "skytree": "Tokyo Skytree tower",
            "sensoji_temple": "Sensō-ji Buddhist temple",
            "shibuya_crossing": "Shibuya crossing intersection",
            "harajuku": "Harajuku fashion district",
            "ginza": "Ginza shopping district",
            "imperial_palace": "Imperial Palace gardens",
            "meiji_shrine": "Meiji Shrine forest",
            "statue_of_liberty": "Statue of Liberty monument",
            "empire_state_building": "Empire State Building skyscraper",
            "times_square": "Times Square neon lights",
            "central_park": "Central Park green space",
            "brooklyn_bridge": "Brooklyn Bridge suspension",
            "wall_street": "Wall Street financial district",
            "high_line": "High Line elevated park",
            "broadway": "Broadway theater district",
            "big_ben": "Big Ben clock tower",
            "london_eye": "London Eye ferris wheel",
            "tower_bridge": "Tower Bridge bascule",
            "buckingham_palace": "Buckingham Palace royal residence",
            "westminster_abbey": "Westminster Abbey church",
            "hyde_park": "Hyde Park green space",
            "covent_garden": "Covent Garden market",
            "camden_market": "Camden Market alternative",
            "colosseum": "Colosseum ancient amphitheater",
            "vatican": "Vatican City state",
            "trevi_fountain": "Trevi Fountain baroque",
            "pantheon": "Pantheon ancient temple",
            "spanish_steps": "Spanish Steps staircase",
            "roman_forum": "Roman Forum ruins",
            "sistine_chapel": "Sistine Chapel ceiling",
            "piazza_navona": "Piazza Navona square"
        }
    
    def choose_landmark(
        self, 
        db: Session, 
        soul_id: str, 
        city_key: str, 
        user_id: Optional[str] = None
    ) -> str:
        """
        选择地标
        
        Args:
            db: 数据库会话
            soul_id: Soul ID
            city_key: 城市键
            user_id: 用户ID（可选）
            
        Returns:
            选择的地标键
        """
        if city_key not in self.city_landmarks:
            raise ValueError(f"Unsupported city: {city_key}")
        
        available_landmarks = self.city_landmarks[city_key]
        
        # 获取已使用的地标
        used_landmarks = LandmarkLogDAL.get_used_landmarks(db, soul_id, city_key, user_id)
        
        # 找到未使用的地标
        unused_landmarks = [lm for lm in available_landmarks if lm not in used_landmarks]
        
        if unused_landmarks:
            # 有未使用的地标，选择第一个
            selected_landmark = unused_landmarks[0]
        else:
            # 所有地标都已使用，选择最少使用的
            selected_landmark = self._choose_least_used_landmark(db, soul_id, city_key, available_landmarks)
        
        # 记录地标使用
        self._log_landmark_usage(db, soul_id, city_key, selected_landmark, user_id)
        
        return selected_landmark
    
    def _choose_least_used_landmark(
        self, 
        db: Session, 
        soul_id: str, 
        city_key: str, 
        available_landmarks: List[str]
    ) -> str:
        """选择最少使用的地标"""
        # 获取所有地标的使用次数
        landmark_usage = {}
        
        for landmark in available_landmarks:
            used_count = len(LandmarkLogDAL.get_used_landmarks(db, soul_id, city_key))
            landmark_usage[landmark] = used_count
        
        # 选择使用次数最少的地标
        min_usage = min(landmark_usage.values())
        least_used = [lm for lm, count in landmark_usage.items() if count == min_usage]
        
        # 如果有多个最少使用的地标，选择第一个
        return least_used[0]
    
    def _log_landmark_usage(
        self, 
        db: Session, 
        soul_id: str, 
        city_key: str, 
        landmark_key: str, 
        user_id: Optional[str] = None
    ):
        """记录地标使用"""
        log_data = LandmarkLogBase(
            soul_id=soul_id,
            city_key=city_key,
            landmark_key=landmark_key,
            user_id=user_id or "",
            used_at_ts=now_ms()
        )
        
        LandmarkLogDAL.log_usage(db, log_data)
    
    def get_landmark_description(self, landmark_key: str) -> str:
        """获取地标描述"""
        return self.landmark_descriptions.get(landmark_key, landmark_key)
    
    def get_city_landmarks(self, city_key: str) -> List[str]:
        """获取城市的所有地标"""
        return self.city_landmarks.get(city_key, [])
    
    def is_city_supported(self, city_key: str) -> bool:
        """检查城市是否支持"""
        return city_key in self.city_landmarks
