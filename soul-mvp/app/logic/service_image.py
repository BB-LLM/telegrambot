"""
核心图像生成服务
"""
import asyncio
import random
import os
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from ..data.dal import (
    SoulStyleProfileDAL, VariantDAL, UserSeenDAL, 
    PromptKeyDAL, WorkLockDAL
)
from ..data.models import VariantBase
from ..core.lww import now_ms
from ..core.ids import generate_ulid, generate_lock_key
from ..core.locks import with_lock

# 全局锁键 - 防止同时生成图片和视频
GLOBAL_GENERATION_LOCK_KEY = "global:generation"
from ..core.task_manager import TaskManager, TaskType, BackgroundTask
from .prompt_cache import PromptCache, PromptBuilder
from .place_chooser import PlaceChooser
from .ai_model_service import generate_soul_image, generate_soul_gif


class ImageGenerationService:
    """图像生成服务"""
    
    def __init__(self):
        from ..config import config
        self.prompt_cache = PromptCache()
        self.prompt_builder = PromptBuilder()
        self.place_chooser = PlaceChooser()
        self.task_manager = TaskManager(max_concurrent=config.MAX_CONCURRENT_TASKS)
    
    async def get_or_create_variant(
        self, 
        db: Session, 
        soul_id: str, 
        cue: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        获取或创建变体（灵魂风格任务）
        
        Args:
            db: 数据库会话
            soul_id: Soul ID
            cue: 提示词
            user_id: 用户ID
            
        Returns:
            变体信息
        """
        # 直接调用 _process_variant_request（内部已加锁）
        return await self._process_variant_request(db, soul_id, cue, user_id)
    
    async def _process_variant_request(
        self, 
        db: Session, 
        soul_id: str, 
        cue: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """处理变体请求"""
        # 生成锁键（基于 soul_id + cue 确保同一提示词串行）
        lock_key = f"{soul_id}|{cue}"
        
        # 首先获取全局锁，防止与视频生成同时进行
        async with with_lock(GLOBAL_GENERATION_LOCK_KEY):
            # 然后获取提示词锁，确保相同的提示词串行执行
            async with with_lock(lock_key):
                # 1. 查找相似的提示词键
                similar_pk = self.prompt_cache.find_similar_prompt_key(db, soul_id, cue)
                
                if similar_pk:
                    # 2. 获取现有变体
                    existing_variants = VariantDAL.list_by_pk_id(db, similar_pk.pk_id)
                    
                    # 3. 获取用户已看过的变体
                    user_seen_variants = UserSeenDAL.get_seen_variants(db, user_id)
                    
                    # 4. 过滤未看过的变体
                    unseen_variants = [
                        v for v in existing_variants 
                        if v.variant_id not in user_seen_variants
                    ]
                    
                    if unseen_variants:
                        # 5. 选择最佳变体（最新的）
                        best_variant = max(unseen_variants, key=lambda v: v.updated_at_ts)
                        
                        # 立即标记为已看，防止后续请求返回同一变体
                        UserSeenDAL.mark_seen(db, user_id, best_variant.variant_id)
                        
                        return {
                            "url": best_variant.asset_url,
                            "variant_id": best_variant.variant_id,
                            "pk_id": best_variant.pk_id,
                            "cache_hit": True
                        }
                
                # 7. 需要生成新变体
                result = await self._generate_new_variant(db, soul_id, cue, user_id, similar_pk)
                # 返回结果时仍在锁内，确保后续任务看不到
                return result
    
    async def _generate_new_variant(
        self, 
        db: Session, 
        soul_id: str, 
        cue: str, 
        user_id: str,
        similar_pk: Optional[Any] = None
    ) -> Dict[str, Any]:
        """生成新变体"""
        # 1. 获取Soul风格配置
        style_profile = SoulStyleProfileDAL.get_by_soul_id(db, soul_id)
        if not style_profile:
            raise ValueError(f"Soul '{soul_id}' style profile not found")
        
        # 2. 构建提示词
        positive_prompt, negative_prompt = self.prompt_builder.build_prompt(soul_id, cue, db)
        
        # 3. 生成变体ID和随机种子
        variant_id = generate_ulid()
        seed = random.randint(1000, 999999)
        
        # 4. 使用真实AI模型生成图像
        ai_result = await generate_soul_image(
            soul_id=soul_id,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            variant_id=variant_id,
            seed=seed
        )
        
        # 5. 生成本地文件路径（后续可改为GCS）
        local_filepath = ai_result["filepath"]
        filename = os.path.basename(local_filepath)
        storage_key = f"soul/{soul_id}/key/{similar_pk.pk_id if similar_pk else 'new'}/variant/{variant_id}.png"
        asset_url = f"/generated/{filename}"  # 生成图像URL
        
        # 6. 创建或更新提示词键
        if not similar_pk:
            pk_data = self.prompt_cache.create_prompt_key(
                db, soul_id, cue, {"canonical_prompt": positive_prompt}
            )
            pk_id = pk_data.pk_id
        else:
            pk_id = similar_pk.pk_id
        
        # 7. 创建变体记录
        variant_data = VariantBase(
            variant_id=variant_id,
            pk_id=pk_id,
            soul_id=soul_id,
            asset_url=asset_url,
            storage_key=storage_key,
            seed=seed,
            phash=ai_result["phash"],
            meta_json={
                "width": ai_result["width"],
                "height": ai_result["height"],
                "file_size": ai_result["file_size"],
                "generation_time_ms": ai_result.get("generation_time_ms", 0),
                "positive_prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "local_filepath": local_filepath
            },
            updated_at_ts=now_ms()
        )
        VariantDAL.create(db, variant_data)
        
        # 立即标记为已看，防止后续任务返回这一新生成的变体
        UserSeenDAL.mark_seen(db, user_id, variant_id)
        
        return {
            "url": asset_url,
            "variant_id": variant_id,
            "pk_id": pk_id,
            "cache_hit": False
        }
    
    async def create_selfie(
        self, 
        db: Session, 
        soul_id: str, 
        city_key: str, 
        mood: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        创建自拍（灵魂自拍任务）
        
        Args:
            db: 数据库会话
            soul_id: Soul ID
            city_key: 城市键
            mood: 情绪
            user_id: 用户ID
            
        Returns:
            自拍信息
        """
        # 1. 选择地标
        landmark_key = self.place_chooser.choose_landmark(db, soul_id, city_key, user_id)
        
        # 2. 构建自拍提示词
        positive_prompt, negative_prompt = self.prompt_builder.build_selfie_prompt(
            soul_id, city_key, landmark_key, mood, db
        )
        
        # 3. 生成自拍变体ID和随机种子
        variant_id = generate_ulid()
        seed = random.randint(1000, 999999)
        
        # 4. 使用真实AI模型生成自拍图像
        ai_result = await generate_soul_image(
            soul_id=soul_id,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            variant_id=variant_id,
            seed=seed
        )
        
        # 5. 生成缓存键
        selfie_cue = f"selfie_{city_key}_{landmark_key}_{mood}"
        pk_data = self.prompt_cache.create_prompt_key(
            db, soul_id, selfie_cue, {
                "selfie_type": True,
                "city": city_key,
                "landmark": landmark_key,
                "mood": mood,
                "canonical_prompt": positive_prompt
            }
        )
        
        # 6. 生成本地文件路径（后续可改为GCS）
        local_filepath = ai_result["filepath"]
        filename = os.path.basename(local_filepath)
        storage_key = f"soul/{soul_id}/selfie/{city_key}/{landmark_key}/{variant_id}.png"
        asset_url = f"/generated/{filename}"  # 生成图像URL
        
        # 7. 创建变体记录
        variant_data = VariantBase(
            variant_id=variant_id,
            pk_id=pk_data.pk_id,
            soul_id=soul_id,
            asset_url=asset_url,
            storage_key=storage_key,
            seed=seed,
            phash=ai_result["phash"],
            meta_json={
                "width": ai_result["width"],
                "height": ai_result["height"],
                "file_size": ai_result["file_size"],
                "generation_time_ms": ai_result.get("generation_time_ms", 0),
                "selfie_type": True,
                "city": city_key,
                "landmark": landmark_key,
                "mood": mood,
                "positive_prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "local_filepath": local_filepath
            },
            updated_at_ts=now_ms()
        )
        VariantDAL.create(db, variant_data)
        
        # 9. 不在这里标记为已看，等用户实际看到时再标记
        
        return {
            "url": asset_url,
            "variant_id": variant_id,
            "pk_id": pk_data.pk_id,
            "landmark_key": landmark_key
        }
    
    async def start_background_generation(
        self, 
        db: Session, 
        soul_id: str, 
        cue: str, 
        user_id: str
    ) -> str:
        """
        启动后台图像生成任务
        
        Args:
            db: 数据库会话
            soul_id: Soul ID
            cue: 提示词
            user_id: 用户ID
            
        Returns:
            任务ID
        """
        # 创建任务
        task_id = self.task_manager.create_task(
            TaskType.STYLE_GENERATION,
            {
                "soul_id": soul_id,
                "cue": cue,
                "user_id": user_id
            }
        )
        
        # 启动后台任务
        await self.task_manager.start_task(
            task_id,
            self._background_generate_variant,
            db
        )
        
        return task_id
    
    async def start_background_selfie(
        self, 
        db: Session, 
        soul_id: str, 
        city_key: str, 
        mood: str, 
        user_id: str
    ) -> str:
        """
        启动后台自拍生成任务
        
        Args:
            db: 数据库会话
            soul_id: Soul ID
            city_key: 城市键
            mood: 情绪
            user_id: 用户ID
            
        Returns:
            任务ID
        """
        # 创建任务
        task_id = self.task_manager.create_task(
            TaskType.SELFIE_GENERATION,
            {
                "soul_id": soul_id,
                "city_key": city_key,
                "mood": mood,
                "user_id": user_id
            }
        )
        
        # 启动后台任务
        await self.task_manager.start_task(
            task_id,
            self._background_generate_selfie,
            db
        )
        
        return task_id
    
    async def _background_generate_variant(
        self, 
        task: BackgroundTask, 
        db: Session
    ) -> Dict[str, Any]:
        """
        后台生成变体任务
        
        Args:
            task: 后台任务对象
            db: 数据库会话
            
        Returns:
            生成结果
        """
        params = task.params
        soul_id = params["soul_id"]
        cue = params["cue"]
        user_id = params["user_id"]
        
        # 生成锁键（基于 soul_id + cue 确保同一提示词串行）
        lock_key = f"{soul_id}|{cue}"
        
        # 使用进程内锁确保相同的提示词串行执行
        async with with_lock(lock_key):
            try:
                # 更新进度
                task.progress = 10
                await asyncio.sleep(0.1)  # 让出控制权
                
                # 检查取消
                if task.cancelled:
                    raise asyncio.CancelledError()
                
                # 1. 尝试从缓存中查找相似的PromptKey
                task.progress = 20
                similar_pk = self.prompt_cache.find_similar_prompt_key(db, soul_id, cue)
                
                await asyncio.sleep(0.1)
                if task.cancelled:
                    raise asyncio.CancelledError()
                
                if similar_pk:
                    # 2. 查找该PromptKey下用户未看过的变体
                    task.progress = 30
                    unseen_variants = VariantDAL.list_unseen_by_pk_id(db, similar_pk.pk_id, user_id)
                    
                    await asyncio.sleep(0.1)
                    if task.cancelled:
                        raise asyncio.CancelledError()
                    
                    if unseen_variants:
                        # 5. 选择最佳变体（最新的）
                        best_variant = max(unseen_variants, key=lambda v: v.updated_at_ts)
                        
                        # 立即标记为已看，防止后续任务返回同一变体
                        UserSeenDAL.mark_seen(db, user_id, best_variant.variant_id)
                        
                        task.progress = 100
                        return {
                            "url": best_variant.asset_url,
                            "variant_id": best_variant.variant_id,
                            "pk_id": best_variant.pk_id,
                            "cache_hit": True
                        }
                
                # 7. 需要生成新变体
                task.progress = 40
                await asyncio.sleep(0.1)
                if task.cancelled:
                    raise asyncio.CancelledError()
                
                result = await self._background_generate_new_variant(
                    task, db, soul_id, cue, user_id, similar_pk
                )
                
                task.progress = 100
                return result
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                task.error = str(e)
                raise
    
    async def _background_generate_selfie(
        self, 
        task: BackgroundTask, 
        db: Session
    ) -> Dict[str, Any]:
        """
        后台生成自拍任务
        
        Args:
            task: 后台任务对象
            db: 数据库会话
            
        Returns:
            生成结果
        """
        params = task.params
        soul_id = params["soul_id"]
        city_key = params["city_key"]
        mood = params["mood"]
        user_id = params["user_id"]
        
        try:
            # 更新进度
            task.progress = 10
            await asyncio.sleep(0.1)
            
            if task.cancelled:
                raise asyncio.CancelledError()
            
            # 1. 选择地标
            task.progress = 20
            landmark_key = self.place_chooser.choose_landmark(db, soul_id, city_key, user_id)
            
            await asyncio.sleep(0.1)
            if task.cancelled:
                raise asyncio.CancelledError()
            
            # 2. 构建自拍提示词
            task.progress = 30
            positive_prompt, negative_prompt = self.prompt_builder.build_selfie_prompt(
                soul_id, city_key, landmark_key, mood, db
            )
            
            await asyncio.sleep(0.1)
            if task.cancelled:
                raise asyncio.CancelledError()
            
            # 3. 生成自拍变体ID和随机种子
            task.progress = 40
            variant_id = generate_ulid()
            seed = random.randint(1000, 999999)
            
            await asyncio.sleep(0.1)
            if task.cancelled:
                raise asyncio.CancelledError()
            
            # 4. 使用真实AI模型生成自拍图像
            task.progress = 50
            ai_result = await generate_soul_image(
                soul_id=soul_id,
                positive_prompt=positive_prompt,
                negative_prompt=negative_prompt,
                variant_id=variant_id,
                seed=seed
            )
            
            await asyncio.sleep(0.1)
            if task.cancelled:
                raise asyncio.CancelledError()
            
            # 5. 生成缓存键
            task.progress = 70
            selfie_cue = f"selfie_{city_key}_{landmark_key}_{mood}"
            pk_data = self.prompt_cache.create_prompt_key(
                db, soul_id, selfie_cue, {
                    "selfie_type": True,
                    "city": city_key,
                    "landmark": landmark_key,
                    "mood": mood,
                    "canonical_prompt": positive_prompt
                }
            )
            
            await asyncio.sleep(0.1)
            if task.cancelled:
                raise asyncio.CancelledError()
            
            # 6. 生成本地文件路径（后续可改为GCS）
            task.progress = 80
            local_filepath = ai_result["filepath"]
            filename = os.path.basename(local_filepath)
            storage_key = f"soul/{soul_id}/selfie/{city_key}/{landmark_key}/{variant_id}.png"
            asset_url = f"/generated/{filename}"  # 生成图像URL
            
            # 7. 创建变体记录
            task.progress = 90
            variant_data = VariantBase(
                variant_id=variant_id,
                pk_id=pk_data.pk_id,
                soul_id=soul_id,
                asset_url=asset_url,
                storage_key=storage_key,
                seed=seed,
                phash=ai_result["phash"],
                meta_json={
                    "width": ai_result["width"],
                    "height": ai_result["height"],
                    "file_size": ai_result["file_size"],
                    "generation_time_ms": ai_result.get("generation_time_ms", 0),
                    "selfie_type": True,
                    "city": city_key,
                    "landmark": landmark_key,
                    "mood": mood,
                    "positive_prompt": positive_prompt,
                    "negative_prompt": negative_prompt,
                    "local_filepath": local_filepath
                },
                updated_at_ts=now_ms()
            )
            VariantDAL.create(db, variant_data)
            
            # 立即标记为已看，防止后续任务返回这一新生成的变体
            UserSeenDAL.mark_seen(db, user_id, variant_id)
            
            task.progress = 100
            return {
                "url": asset_url,
                "variant_id": variant_id,
                "pk_id": pk_data.pk_id,
                "landmark_key": landmark_key
            }
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            task.error = str(e)
            raise
    
    async def _background_generate_new_variant(
        self, 
        task: BackgroundTask,
        db: Session, 
        soul_id: str, 
        cue: str, 
        user_id: str,
        similar_pk: Optional[Any] = None
    ) -> Dict[str, Any]:
        """后台生成新变体"""
        try:
            # 1. 获取Soul风格配置
            task.progress = 50
            style_profile = SoulStyleProfileDAL.get_by_soul_id(db, soul_id)
            if not style_profile:
                raise ValueError(f"Soul '{soul_id}' style profile not found")
            
            await asyncio.sleep(0.1)
            if task.cancelled:
                raise asyncio.CancelledError()
            
            # 2. 构建提示词
            task.progress = 60
            positive_prompt, negative_prompt = self.prompt_builder.build_prompt(soul_id, cue, db)
            
            await asyncio.sleep(0.1)
            if task.cancelled:
                raise asyncio.CancelledError()
            
            # 3. 生成变体ID和随机种子
            task.progress = 70
            variant_id = generate_ulid()
            seed = random.randint(1000, 999999)
            
            await asyncio.sleep(0.1)
            if task.cancelled:
                raise asyncio.CancelledError()
            
            # 4. 使用真实AI模型生成图像
            task.progress = 80
            
            # 在调用AI模型之前再次检查取消状态
            if task.cancelled:
                raise asyncio.CancelledError()
            
            try:
                ai_result = await generate_soul_image(
                    soul_id=soul_id,
                    positive_prompt=positive_prompt,
                    negative_prompt=negative_prompt,
                    variant_id=variant_id,
                    seed=seed,
                    cancellation_token=task.cancel_event
                )
            except asyncio.CancelledError:
                # AI模型生成被取消
                print(f"AI模型生成被取消: {task.task_id}")
                raise
            
            await asyncio.sleep(0.1)
            if task.cancelled:
                raise asyncio.CancelledError()
            
            # 5. 生成本地文件路径（后续可改为GCS）
            task.progress = 85
            local_filepath = ai_result["filepath"]
            filename = os.path.basename(local_filepath)
            storage_key = f"soul/{soul_id}/key/{similar_pk.pk_id if similar_pk else 'new'}/variant/{variant_id}.png"
            asset_url = f"/generated/{filename}"  # 生成图像URL
            
            # 6. 创建或更新提示词键
            task.progress = 90
            if not similar_pk:
                pk_data = self.prompt_cache.create_prompt_key(
                    db, soul_id, cue, {"canonical_prompt": positive_prompt}
                )
                pk_id = pk_data.pk_id
            else:
                pk_id = similar_pk.pk_id
            
            # 7. 创建变体记录
            task.progress = 95
            variant_data = VariantBase(
                variant_id=variant_id,
                pk_id=pk_id,
                soul_id=soul_id,
                asset_url=asset_url,
                storage_key=storage_key,
                seed=seed,
                phash=ai_result["phash"],
                meta_json={
                    "width": ai_result["width"],
                    "height": ai_result["height"],
                    "file_size": ai_result["file_size"],
                    "generation_time_ms": ai_result.get("generation_time_ms", 0),
                    "positive_prompt": positive_prompt,
                    "negative_prompt": negative_prompt,
                    "local_filepath": local_filepath
                },
                updated_at_ts=now_ms()
            )
            VariantDAL.create(db, variant_data)
            
            # 立即标记为已看，防止后续任务返回这一新生成的变体
            UserSeenDAL.mark_seen(db, user_id, variant_id)
            
            return {
                "url": asset_url,
                "variant_id": variant_id,
                "pk_id": pk_id,
                "cache_hit": False
            }
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            task.error = str(e)
            raise
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.task_manager.get_task_status(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return await self.task_manager.cancel_task(task_id)
    
    def list_tasks(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出任务"""
        from ..core.task_manager import TaskStatus
        filter_status = None
        if status_filter:
            try:
                filter_status = TaskStatus(status_filter)
            except ValueError:
                pass
        
        return self.task_manager.list_tasks(filter_status)
