"""
Wan 文本到视频生成服务 - 使用阿里云 DashScope API
"""
import os
import asyncio
import time
from typing import Optional, Dict, Any
from pathlib import Path
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope
import requests
from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout, RequestException
import imageio

from ..config import config
from ..core.ids import generate_ulid
from ..core.lww import now_ms
from ..data.dal import (
    SoulStyleProfileDAL, VariantDAL, UserSeenDAL,
    PromptKeyDAL, WorkLockDAL, LandmarkLogDAL
)
from ..data.models import VariantBase, LandmarkLogBase
from .prompt_cache import PromptCache, PromptBuilder
from .place_chooser import PlaceChooser


# 配置 DashScope API
dashscope.base_http_api_url = config.WAN_API_BASE_URL


class WanVideoGenerationService:
    """Wan 文本到视频生成服务"""
    
    def __init__(self):
        """初始化服务"""
        self.prompt_cache = PromptCache()
        self.prompt_builder = PromptBuilder()
        self.place_chooser = PlaceChooser()
        
        # 获取 API Key
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")
        
        # 输出目录
        self.output_dir = Path(config.WAN_OUTPUT_DIR)
        if not self.output_dir.is_absolute():
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.output_dir = Path(project_root) / self.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置参数
        self.model = config.WAN_MODEL
        self.size = config.WAN_SIZE
        self.duration = config.WAN_DURATION
        self.prompt_extend = config.WAN_PROMPT_EXTEND
        self.watermark = config.WAN_WATERMARK
    
    async def generate_video_from_text(
        self,
        positive_prompt: str,
        negative_prompt: str = "",
        output_filename: Optional[str] = None,
        seed: Optional[int] = None,
        generate_gif: bool = True
    ) -> Dict[str, Any]:
        """
        从文本生成视频
        
        Args:
            positive_prompt: 正面提示词
            negative_prompt: 负面提示词
            output_filename: 输出文件名（不含扩展名），如果为None则自动生成
            seed: 随机种子
            generate_gif: 是否同时生成GIF，默认True
            
        Returns:
            生成结果信息
        """
        start_time = time.time()
        
        # 生成输出文件名
        if output_filename is None:
            output_filename = f"wan_video_{generate_ulid()}"
        
        # 调用异步API
        print(f"正在调用 Wan API 生成视频...")
        print(f"提示词: {positive_prompt}")
        
        rsp = VideoSynthesis.async_call(
            api_key=self.api_key,
            model=self.model,
            prompt=positive_prompt,
            size=self.size,
            duration=self.duration,
            negative_prompt=negative_prompt if negative_prompt else "",
            prompt_extend=self.prompt_extend,
            watermark=self.watermark,
            seed=seed
        )
        
        if rsp.status_code != HTTPStatus.OK:
            raise RuntimeError(
                f'Wan API调用失败: status_code={rsp.status_code}, '
                f'code={rsp.code}, message={rsp.message}'
            )
        
        task_id = rsp.output.task_id
        print(f"任务ID: {task_id}")
        
        # 等待任务完成（使用手动轮询，添加重试机制和错误处理）
        print("等待视频生成完成...")
        max_retries = 5  # 增加重试次数
        retry_count = 0
        max_wait_time = 600  # 最大等待时间（秒）
        start_wait_time = time.time()
        last_status = None
        
        while True:
            try:
                # 检查是否超时
                elapsed_time = time.time() - start_wait_time
                if elapsed_time > max_wait_time:
                    raise RuntimeError(f"视频生成超时（超过 {max_wait_time} 秒），任务ID: {task_id}")
                
                # 使用 fetch 查询任务状态（传入 api_key）
                try:
                    status_rsp = VideoSynthesis.fetch(rsp, api_key=self.api_key)
                except Exception as fetch_error:
                    # fetch 调用本身失败，可能是网络问题
                    if retry_count < max_retries:
                        retry_count += 1
                        wait_time = min(10 * retry_count, 30)
                        print(f"查询任务状态时发生错误: {type(fetch_error).__name__}: {str(fetch_error)}")
                        print(f"{wait_time}秒后重试 {retry_count}/{max_retries}...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise RuntimeError(f"查询任务状态失败，已重试 {max_retries} 次: {type(fetch_error).__name__}: {str(fetch_error)}")
                
                if status_rsp.status_code != HTTPStatus.OK:
                    if retry_count < max_retries:
                        retry_count += 1
                        print(f"查询任务状态失败，重试 {retry_count}/{max_retries}...")
                        await asyncio.sleep(5)  # 等待5秒后重试
                        continue
                    else:
                        raise RuntimeError(
                            f'查询任务状态失败: status_code={status_rsp.status_code}, '
                            f'code={status_rsp.code}, message={status_rsp.message}'
                        )
                
                task_status = status_rsp.output.task_status
                last_status = task_status
                print(f"任务状态: {task_status} (已等待 {elapsed_time:.1f} 秒)")
                
                if task_status == "SUCCEEDED":
                    rsp = status_rsp
                    print(f"视频生成成功！总耗时: {elapsed_time:.1f} 秒")
                    break
                elif task_status == "FAILED":
                    error_msg = "未知错误"
                    if hasattr(status_rsp.output, 'message') and status_rsp.output.message:
                        error_msg = status_rsp.output.message
                    elif hasattr(status_rsp, 'message') and status_rsp.message:
                        error_msg = status_rsp.message
                    raise RuntimeError(f"视频生成失败: {error_msg}")
                elif task_status in ["PENDING", "RUNNING"]:
                    # 任务还在进行中，等待后继续查询
                    retry_count = 0  # 重置重试计数（任务正常进行中）
                    await asyncio.sleep(10)  # 等待10秒后再次查询
                else:
                    # 未知状态，等待后重试
                    print(f"警告: 未知任务状态 '{task_status}'")
                    await asyncio.sleep(5)
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise RuntimeError(f"任务状态异常: {task_status}，已重试 {max_retries} 次")
                    
            except (ConnectionResetError, ConnectionError, RequestsConnectionError, Timeout, RequestException) as e:
                elapsed_time = time.time() - start_wait_time
                if retry_count < max_retries:
                    retry_count += 1
                    wait_time = min(10 * retry_count, 30)  # 递增等待时间，最多30秒
                    print(f"网络连接错误 ({elapsed_time:.1f}秒)，{wait_time}秒后重试 {retry_count}/{max_retries}...")
                    print(f"错误详情: {type(e).__name__}: {str(e)}")
                    await asyncio.sleep(wait_time)
                    # 继续使用现有的 rsp 对象，确保 task_id 存在
                    if not hasattr(rsp, 'output') or not hasattr(rsp.output, 'task_id'):
                        # 如果 rsp 对象损坏，需要重新构建
                        class TaskOutput:
                            def __init__(self, task_id):
                                self.task_id = task_id
                        class TaskResponse:
                            def __init__(self, task_id):
                                self.output = TaskOutput(task_id)
                        rsp = TaskResponse(task_id)
                else:
                    raise RuntimeError(f"网络连接失败，已重试 {max_retries} 次 (总耗时 {elapsed_time:.1f}秒): {type(e).__name__}: {str(e)}")
            except Exception as e:
                # 其他未知错误
                elapsed_time = time.time() - start_wait_time
                print(f"未知错误 ({elapsed_time:.1f}秒): {type(e).__name__}: {str(e)}")
                if retry_count < max_retries:
                    retry_count += 1
                    wait_time = min(10 * retry_count, 30)
                    print(f"{wait_time}秒后重试 {retry_count}/{max_retries}...")
                    await asyncio.sleep(wait_time)
                else:
                    raise RuntimeError(f"视频生成过程中发生错误 (总耗时 {elapsed_time:.1f}秒): {type(e).__name__}: {str(e)}")
        
        if rsp.status_code != HTTPStatus.OK:
            raise RuntimeError(
                f'视频生成失败: status_code={rsp.status_code}, '
                f'code={rsp.code}, message={rsp.message}'
            )
        
        video_url = rsp.output.video_url
        print(f"视频URL: {video_url}")
        
        # 下载视频
        mp4_path = await self._download_video(video_url, output_filename)
        
        video_generation_time = time.time() - start_time
        
        result = {
            "mp4_path": str(mp4_path),
            "mp4_url": f"/static/videos/{mp4_path.name}",
            "video_filename": mp4_path.name,
            "video_size_mb": round(mp4_path.stat().st_size / 1024 / 1024, 2),
            "video_generation_seconds": round(video_generation_time, 2),
            "task_id": task_id
        }
        
        # 转换为GIF
        if generate_gif:
            print("正在将MP4转换为GIF...")
            gif_start_time = time.time()
            
            gif_path = await self._convert_mp4_to_gif(str(mp4_path))
            
            gif_conversion_time = time.time() - gif_start_time
            
            result.update({
                "gif_path": str(gif_path),
                "gif_url": f"/static/videos/{gif_path.name}",
                "gif_filename": gif_path.name,
                "gif_size_mb": round(gif_path.stat().st_size / 1024 / 1024, 2),
                "gif_conversion_seconds": round(gif_conversion_time, 2)
            })
            
            print(f"GIF已生成: {gif_path}")
        
        total_time = time.time() - start_time
        result["total_seconds"] = round(total_time, 2)
        
        return result
    
    async def _download_video(self, video_url: str, output_filename: str) -> Path:
        """
        下载视频文件
        
        Args:
            video_url: 视频URL
            output_filename: 输出文件名（不含扩展名）
            
        Returns:
            视频文件路径
        """
        mp4_path = self.output_dir / f"{output_filename}.mp4"
        
        # 下载视频
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        
        with open(mp4_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"视频已下载: {mp4_path}")
        return mp4_path
    
    async def _convert_mp4_to_gif(self, mp4_path: str, gif_path: Optional[str] = None) -> Path:
        """
        将MP4转换为GIF
        
        Args:
            mp4_path: MP4文件路径
            gif_path: 输出GIF路径，如果为None则自动生成
            
        Returns:
            GIF文件路径
        """
        if gif_path is None:
            gif_path = str(Path(mp4_path).with_suffix('.gif'))
        
        gif_path_obj = Path(gif_path)
        
        try:
            # 读取MP4视频
            reader = imageio.get_reader(mp4_path)
            
            # 获取视频信息
            fps_actual = reader.get_meta_data().get('fps', 8)
            
            # 读取所有帧
            frames_list = []
            for frame in reader:
                frames_list.append(frame)
            reader.close()
            
            # 保存为GIF
            imageio.mimsave(
                str(gif_path_obj),
                frames_list,
                fps=min(fps_actual, 10),  # GIF帧率限制在10fps以内
                loop=0  # 0表示无限循环
            )
            
            return gif_path_obj
            
        except Exception as e:
            raise RuntimeError(f"GIF转换失败: {e}")
    
    async def get_or_create_variant(
        self,
        db,
        soul_id: str,
        cue: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        获取或创建视频变体（唯一变体逻辑）
        
        Args:
            db: 数据库会话
            soul_id: Soul ID
            cue: 提示词
            user_id: 用户ID
            
        Returns:
            变体信息
        """
        import random
        from ..core.locks import with_lock
        
        # 生成锁键（基于 soul_id + cue 确保同一提示词串行）
        lock_key = f"wan:{soul_id}|{cue}"
        
        async with with_lock(lock_key):
            # 1. 查找相似的提示词键
            similar_pk = self.prompt_cache.find_similar_prompt_key(db, soul_id, cue)
            
            if similar_pk:
                # 2. 获取现有变体（视频变体）
                existing_variants = VariantDAL.list_by_pk_id(db, similar_pk.pk_id)
                
                # 过滤视频变体（通过 meta_json 中的 type 字段）
                video_variants = [
                    v for v in existing_variants
                    if v.meta_json and v.meta_json.get('type') == 'wan_video'
                ]
                
                if video_variants:
                    # 3. 获取用户已看过的变体
                    user_seen_variants = UserSeenDAL.get_seen_variants(db, user_id)
                    
                    # 4. 过滤未看过的变体
                    unseen_variants = [
                        v for v in video_variants
                        if v.variant_id not in user_seen_variants
                    ]
                    
                    if unseen_variants:
                        # 5. 选择最佳变体（最新的）
                        best_variant = max(unseen_variants, key=lambda v: v.updated_at_ts)
                        
                        # 立即标记为已看
                        UserSeenDAL.mark_seen(db, user_id, best_variant.variant_id)
                        
                        return {
                            "mp4_url": best_variant.asset_url,
                            "gif_url": best_variant.meta_json.get('gif_url', ''),
                            "variant_id": best_variant.variant_id,
                            "pk_id": best_variant.pk_id,
                            "cache_hit": True
                        }
            
            # 6. 需要生成新变体
            return await self._generate_new_variant(db, soul_id, cue, user_id, similar_pk)
    
    async def _generate_new_variant(
        self,
        db,
        soul_id: str,
        cue: str,
        user_id: str,
        similar_pk: Optional[Any] = None
    ) -> Dict[str, Any]:
        """生成新视频变体"""
        import random
        
        # 1. 获取Soul风格配置
        style_profile = SoulStyleProfileDAL.get_by_soul_id(db, soul_id)
        if not style_profile:
            raise ValueError(f"Soul '{soul_id}' style profile not found")
        
        # 2. 构建提示词
        positive_prompt, negative_prompt = self.prompt_builder.build_prompt(soul_id, cue, db)
        
        # 3. 生成变体ID和随机种子
        variant_id = generate_ulid()
        seed = random.randint(1000, 999999)
        
        # 4. 生成视频
        video_result = await self.generate_video_from_text(
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            output_filename=f"wan_{variant_id}",
            seed=seed,
            generate_gif=True
        )
        
        # 5. 构建存储路径和URL
        mp4_filename = video_result["video_filename"]
        gif_filename = video_result.get("gif_filename", "")
        
        storage_key = f"soul/{soul_id}/wan/key/{similar_pk.pk_id if similar_pk else 'new'}/variant/{variant_id}.mp4"
        mp4_url = f"/static/videos/{mp4_filename}"
        gif_url = f"/static/videos/{gif_filename}" if gif_filename else ""
        
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
            asset_url=mp4_url,
            storage_key=storage_key,
            seed=seed,
            meta_json={
                "type": "wan_video",
                "local_filepath": video_result["mp4_path"],
                "gif_url": gif_url,
                "gif_path": video_result.get("gif_path", ""),
                "video_size_mb": video_result["video_size_mb"],
                "gif_size_mb": video_result.get("gif_size_mb", 0),
                "generation_time": video_result["total_seconds"]
            },
            updated_at_ts=now_ms()
        )
        
        VariantDAL.create(db, variant_data)
        
        # 8. 标记为已看
        UserSeenDAL.mark_seen(db, user_id, variant_id)
        
        return {
            "mp4_url": mp4_url,
            "gif_url": gif_url,
            "variant_id": variant_id,
            "pk_id": pk_id,
            "cache_hit": False
        }
    
    async def create_selfie(
        self,
        db,
        soul_id: str,
        city_key: str,
        mood: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        创建Soul自拍视频
        
        Args:
            db: 数据库会话
            soul_id: Soul ID
            city_key: 城市键
            mood: 情绪
            user_id: 用户ID
            
        Returns:
            自拍视频信息
        """
        import random
        from ..core.locks import with_lock
        from ..data.dal import LandmarkLogDAL
        from ..core.lww import now_ms
        
        # 1. 选择地标
        landmark_key = self.place_chooser.choose_landmark(db, soul_id, city_key)
        
        # 2. 构建自拍提示词
        positive_prompt, negative_prompt = self.prompt_builder.build_selfie_prompt(
            soul_id, city_key, landmark_key, mood, db
        )
        
        # 3. 生成变体ID和随机种子
        variant_id = generate_ulid()
        seed = random.randint(1000, 999999)
        
        # 4. 生成视频
        video_result = await self.generate_video_from_text(
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            output_filename=f"wan_selfie_{variant_id}",
            seed=seed,
            generate_gif=True
        )
        
        # 5. 构建存储路径和URL
        mp4_filename = video_result["video_filename"]
        gif_filename = video_result.get("gif_filename", "")
        
        storage_key = f"soul/{soul_id}/wan/selfie/{city_key}/{landmark_key}/{variant_id}.mp4"
        mp4_url = f"/static/videos/{mp4_filename}"
        gif_url = f"/static/videos/{gif_filename}" if gif_filename else ""
        
        # 6. 创建提示词键（自拍使用特殊的cue）
        selfie_cue = f"{soul_id} selfie at {landmark_key} in {city_key}, {mood} mood"
        pk_data = self.prompt_cache.create_prompt_key(
            db, soul_id, selfie_cue, {"canonical_prompt": positive_prompt, "type": "selfie"}
        )
        pk_id = pk_data.pk_id
        
        # 7. 创建变体记录
        variant_data = VariantBase(
            variant_id=variant_id,
            pk_id=pk_id,
            soul_id=soul_id,
            asset_url=mp4_url,
            storage_key=storage_key,
            seed=seed,
            meta_json={
                "type": "wan_video_selfie",
                "city_key": city_key,
                "landmark_key": landmark_key,
                "mood": mood,
                "local_filepath": video_result["mp4_path"],
                "gif_url": gif_url,
                "gif_path": video_result.get("gif_path", ""),
                "video_size_mb": video_result["video_size_mb"],
                "gif_size_mb": video_result.get("gif_size_mb", 0),
                "generation_time": video_result["total_seconds"]
            },
            updated_at_ts=now_ms()
        )
        
        VariantDAL.create(db, variant_data)
        
        # 8. 记录地标使用日志
        log_data = LandmarkLogBase(
            soul_id=soul_id,
            city_key=city_key,
            landmark_key=landmark_key,
            user_id=user_id or "",
            used_at_ts=now_ms()
        )
        LandmarkLogDAL.log_usage(db, log_data)
        
        # 9. 标记为已看
        UserSeenDAL.mark_seen(db, user_id, variant_id)
        
        return {
            "mp4_url": mp4_url,
            "gif_url": gif_url,
            "variant_id": variant_id,
            "pk_id": pk_id,
            "landmark_key": landmark_key
        }


# 全局服务实例
_wan_video_service: Optional[WanVideoGenerationService] = None


def get_wan_video_service() -> WanVideoGenerationService:
    """获取Wan视频生成服务实例（单例）"""
    global _wan_video_service
    if _wan_video_service is None:
        _wan_video_service = WanVideoGenerationService()
    return _wan_video_service

