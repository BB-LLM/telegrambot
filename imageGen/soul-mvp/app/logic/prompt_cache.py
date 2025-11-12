"""
提示词缓存和相似性匹配
"""
import hashlib
import re
import json
from typing import List, Optional, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from ..data.dal import PromptKeyDAL, SoulStyleProfileDAL
from ..data.models import PromptKeyBase
from ..core.lww import now_ms
from ..core.ids import generate_pk_id


class PromptCache:
    """提示词缓存管理器"""
    
    def __init__(self):
        # 初始化文本嵌入模型
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 停用词列表
        self.stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
            "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could", "should"
        }
    
    def normalize_cue(self, cue: str, soul_id: str, db: Session) -> str:
        """
        标准化提示词
        
        Args:
            cue: 原始提示词
            soul_id: Soul ID
            db: 数据库会话
            
        Returns:
            标准化后的提示词
        """
        # 小写、去除标点、压缩空格
        normalized = cue.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # 去除停用词
        tokens = [word for word in normalized.split() if word not in self.stopwords]
        
        # 排序关键token
        tokens.sort()
        
        # 从数据库获取Soul风格标签
        style_tags = self._get_soul_style_tags(db, soul_id)
        if style_tags:
            tokens.extend(style_tags)
        
        return " ".join(tokens)
    
    def _get_soul_style_tags(self, db: Session, soul_id: str) -> List[str]:
        """
        从数据库获取Soul风格标签
        
        Args:
            db: 数据库会话
            soul_id: Soul ID
            
        Returns:
            风格标签列表
        """
        try:
            style_profile = SoulStyleProfileDAL.get_by_soul_id(db, soul_id)
            if not style_profile:
                return []
            
            # 从LoRA IDs中提取风格标签
            style_tags = []
            
            # 添加LoRA相关的风格标签
            for lora_id in style_profile.lora_ids_json:
                # 从LoRA ID中提取风格信息，例如 "anime_style@v1" -> "anime style"
                style_name = lora_id.split('@')[0].replace('_', ' ')
                style_tags.append(style_name)
            
            # 添加调色板相关的风格标签
            if style_profile.palette_json:
                palette = style_profile.palette_json
                if 'primary' in palette:
                    style_tags.append('pastel colors' if 'pastel' in palette.get('primary', '').lower() else 'elegant colors')
            
            # 添加运动模块相关的风格标签
            if style_profile.motion_module:
                if 'animate' in style_profile.motion_module.lower():
                    style_tags.append('animated style')
                else:
                    style_tags.append('static style')
            
            return style_tags
            
        except Exception as e:
            # 如果获取失败，返回空列表
            print(f"Warning: Failed to get style tags for {soul_id}: {e}")
            return []
    
    def generate_cache_key(self, cue: str, soul_id: str, db: Session) -> tuple[str, str]:
        """
        生成缓存键
        
        Args:
            cue: 提示词
            soul_id: Soul ID
            
        Returns:
            (key_norm, key_hash, pk_id)
        """
        key_norm = self.normalize_cue(cue, soul_id, db)
        key_hash = hashlib.sha1(key_norm.encode()).hexdigest()[:16]
        pk_id = generate_pk_id(soul_id, key_hash)
        
        return key_norm, key_hash, pk_id
    
    def find_similar_prompt_key(
        self, 
        db: Session, 
        soul_id: str, 
        cue: str, 
        threshold: float = 0.85
    ) -> Optional[PromptKeyBase]:
        """
        查找相似的提示词键
        
        Args:
            db: 数据库会话
            soul_id: Soul ID
            cue: 提示词
            threshold: 相似度阈值
            
        Returns:
            相似的PromptKey或None
        """
        # 1. 先尝试精确匹配
        key_norm, key_hash, pk_id = self.generate_cache_key(cue, soul_id, db)
        exact_match = PromptKeyDAL.find_similar(db, soul_id, key_hash)
        if exact_match:
            return exact_match
        
        # 2. 使用嵌入向量进行相似性匹配
        cue_embedding = self.embedder.encode(key_norm)
        
        # 获取该Soul的所有提示词键
        all_pks = PromptKeyDAL.list_by_soul(db, soul_id)
        
        best_match = None
        best_similarity = 0.0
        
        for pk in all_pks:
            if pk.key_embed is not None:
                # 将bytes转换回numpy数组
                stored_embedding = np.frombuffer(pk.key_embed, dtype=np.float32)
                
                # 计算余弦相似度
                similarity = self._cosine_similarity(cue_embedding, stored_embedding)
                
                if similarity >= threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = pk
        
        return best_match
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def create_prompt_key(
        self, 
        db: Session, 
        soul_id: str, 
        cue: str, 
        meta_json: Optional[Dict[str, Any]] = None
    ) -> PromptKeyBase:
        """
        创建新的提示词键
        
        Args:
            db: 数据库会话
            soul_id: Soul ID
            cue: 提示词
            meta_json: 元数据
            
        Returns:
            创建的PromptKey
        """
        key_norm, key_hash, pk_id = self.generate_cache_key(cue, soul_id, db)
        
        # 生成嵌入向量
        embedding = self.embedder.encode(key_norm)
        
        # 创建PromptKey
        pk_data = PromptKeyBase(
            pk_id=pk_id,
            soul_id=soul_id,
            key_norm=key_norm,
            key_hash=key_hash,
            key_embed=embedding.tobytes(),
            meta_json=meta_json or {},
            updated_at_ts=now_ms()
        )
        
        PromptKeyDAL.create(db, pk_data)
        return pk_data


class PromptBuilder:
    """提示词构建器"""
    
    def __init__(self):
        pass  # 不再硬编码风格配置
    
    def build_prompt(self, soul_id: str, cue: str, db: Session, extra_tags: Optional[List[str]] = None) -> tuple[str, str]:
        """
        构建最终提示词
        
        Args:
            soul_id: Soul ID
            cue: 原始提示词
            extra_tags: 额外标签（如地标、情绪等）
            
        Returns:
            (positive_prompt, negative_prompt)
        """
        # 从数据库获取Soul风格配置
        style_profile = SoulStyleProfileDAL.get_by_soul_id(db, soul_id)
        if not style_profile:
            raise ValueError(f"Soul '{soul_id}' style profile not found")
        
        # 构建正面提示词
        positive_parts = [cue]
        
        # 从LoRA IDs构建风格标签
        style_tags = []
        for lora_id in style_profile.lora_ids_json:
            style_name = lora_id.split('@')[0].replace('_', ' ')
            style_tags.append(style_name)
        
        # 添加调色板风格
        if style_profile.palette_json:
            palette = style_profile.palette_json
            if 'primary' in palette:
                color_style = 'pastel colors' if 'pastel' in palette.get('primary', '').lower() else 'elegant colors'
                style_tags.append(color_style)
        
        # 添加运动模块风格
        if style_profile.motion_module:
            if 'animate' in style_profile.motion_module.lower():
                style_tags.append('animated style')
            else:
                style_tags.append('static style')
        
        positive_parts.extend(style_tags)
        
        # 添加额外标签
        if extra_tags:
            positive_parts.extend(extra_tags)
        
        positive_prompt = ", ".join(positive_parts)
        
        # 构建负面提示词
        negative_prompt = ", ".join(style_profile.negatives_json)
        
        return positive_prompt, negative_prompt
    
    def build_selfie_prompt(
        self, 
        soul_id: str, 
        city_key: str, 
        landmark_key: str, 
        mood: str,
        db: Session
    ) -> tuple[str, str]:
        """
        构建自拍提示词
        
        Args:
            soul_id: Soul ID
            city_key: 城市键
            landmark_key: 地标键
            mood: 情绪
            
        Returns:
            (positive_prompt, negative_prompt)
        """
        # 构建自拍特定的提示词
        selfie_cue = f"{soul_id} selfie at {landmark_key} in {city_key}, {mood} mood"
        
        # 添加自拍相关标签
        selfie_tags = [
            "selfie pose",
            "smiling",
            "beautiful background",
            "perfect lighting",
            "high quality"
        ]
        
        return self.build_prompt(soul_id, selfie_cue, db, selfie_tags)
