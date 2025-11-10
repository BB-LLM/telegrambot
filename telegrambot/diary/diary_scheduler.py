"""Diary scheduler - manages daily diary generation"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
from loguru import logger

from diary.diary_service import diary_service

_scheduler: Optional[BackgroundScheduler] = None


def start_diary_scheduler(chat_histories: Dict[str, List[Dict]], hour: int = 21, minute: int = 0):
    """
    启动日记定时任务调度器
    
    Args:
        chat_histories: 用户聊天历史字典 {user_id: [messages...]}
        hour: 触发小时（默认21）
        minute: 触发分钟（默认0，即21:00）
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        
        # 添加定时任务：每天21:00执行
        _scheduler.add_job(
            func=lambda: asyncio.run(scheduled_diary_generation(chat_histories)),
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_diary_generation',
            replace_existing=True,
            max_instances=1  # 防止重复执行
        )
        
        _scheduler.start()
        logger.info(f"Diary scheduler started: daily at {hour:02d}:{minute:02d}")
    else:
        logger.warning("Diary scheduler already running")


async def scheduled_diary_generation(chat_histories: Dict[str, List[Dict]]):
    """
    定时任务：遍历chat_histories中的所有用户，为每个用户生成日记
    
    Args:
        chat_histories: 用户聊天历史字典
    """
    today = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"Starting scheduled diary generation for {today}")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    # 遍历chat_histories中的所有用户
    for user_id, chat_history in chat_histories.items():
        if not chat_history:
            logger.debug(f"Skipping user {user_id}: no chat history")
            skip_count += 1
            continue
        
        # 1. 筛选该用户当天的消息
        today_messages = diary_service.filter_today_messages(chat_history, today)
        
        # 2. 如果该用户当天有消息，生成日记
        if today_messages:
            logger.info(f"Generating diary for user {user_id} with {len(today_messages)} messages")
            diary_data = await diary_service.generate_diary(
                user_id=user_id,
                date=today,
                messages=today_messages,
                timezone="Asia/Shanghai"  # 可以从用户配置中获取时区
            )
            
            if diary_data:
                success_count += 1
                logger.info(f"Diary generated successfully for user {user_id}")
            else:
                fail_count += 1
                logger.error(f"Failed to generate diary for user {user_id}")
        else:
            logger.debug(f"User {user_id} has no messages today, skipping")
            skip_count += 1
    
    logger.info(
        f"Diary generation completed for {today}: "
        f"{success_count} success, {fail_count} failed, {skip_count} skipped"
    )

