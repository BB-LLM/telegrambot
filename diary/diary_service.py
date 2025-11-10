"""Diary service - core business logic"""
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session, select
from loguru import logger
from models import DiaryDaily, DiaryGenerateRequest, DiaryResponse
from llm_service import llm_service
from database import engine


class DiaryService:
    """Diary service class"""
    
    @staticmethod
    def generate_diary(request: DiaryGenerateRequest) -> DiaryResponse:
        """
        Generate or get diary (idempotency guaranteed)
        Meets requirement document A10: ensures uniqueness via user_id+date
        """
        start_time = datetime.now()
        logger.info(f"[DiaryService] generate_diary called for user_id={request.user_id}, date={request.date}")
        
        try:
            with Session(engine) as session:
                # Check if already exists
                logger.debug(f"[DiaryService] Checking if diary already exists for user_id={request.user_id}, date={request.date}")
                statement = select(DiaryDaily).where(
                    DiaryDaily.user_id == request.user_id,
                    DiaryDaily.date == request.date
                )
                existing = session.exec(statement).first()
                
                if existing:
                    # If exists, return directly
                    logger.info(f"[DiaryService] Diary already exists for user_id={request.user_id}, date={request.date}, returning existing")
                    body_lines = existing.body.split("\n") if existing.body else []
                    return DiaryResponse(
                        user_id=existing.user_id,
                        date=existing.date,
                        title=existing.title,
                        body_lines=body_lines,
                        tags=existing.tags,
                        ui={
                            "inline_keyboard": [
                                [{"text": "♥ Save", "callback": "save"}],
                                [{"text": "↩ Reply", "callback": "reply"}]
                            ]
                        }
                    )
                
                # Generate new diary
                logger.info(f"[DiaryService] Generating new diary for user_id={request.user_id}, date={request.date}")
                logger.debug(f"[DiaryService] Calling LLM service with {len(request.messages)} messages")
                
                llm_start = datetime.now()
                diary_content = llm_service.generate_diary(
                    messages=request.messages,
                    memories=request.memories
                )
                llm_elapsed = (datetime.now() - llm_start).total_seconds()
                logger.info(f"[DiaryService] LLM service completed in {llm_elapsed:.2f}s")
                logger.debug(f"[DiaryService] Generated diary: title={diary_content.get('title')}, body_lines={len(diary_content.get('body_lines', []))}, tags={diary_content.get('tags')}")
                
                # Save to database
                logger.debug(f"[DiaryService] Saving diary to database")
                diary_entry = DiaryDaily(
                    user_id=request.user_id,
                    date=request.date,
                    title=diary_content["title"],
                    body="\n".join(diary_content["body_lines"]),
                    tags=diary_content["tags"],
                    created_at=datetime.now()
                )
                
                session.add(diary_entry)
                session.commit()
                session.refresh(diary_entry)
                
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"[DiaryService] Diary saved successfully for user_id={request.user_id}, date={request.date}, total_elapsed={elapsed:.2f}s")
                
                return DiaryResponse(
                    user_id=diary_entry.user_id,
                    date=diary_entry.date,
                    title=diary_entry.title,
                    body_lines=diary_content["body_lines"],
                    tags=diary_entry.tags,
                    ui={
                        "inline_keyboard": [
                            [{"text": "♥ Save", "callback": "save"}],
                            [{"text": "↩ Reply", "callback": "reply"}]
                        ]
                    }
                )
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.exception(
                f"[DiaryService] Error in generate_diary for user_id={request.user_id}, date={request.date}, "
                f"elapsed={elapsed:.2f}s, error={str(e)}"
            )
            raise
    
    @staticmethod
    def get_today_diary(user_id: str) -> Optional[DiaryResponse]:
        """
        Get today's diary, if not available return yesterday's diary
        Meets requirement document L7/L20: if today's diary not published, show yesterday's
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        with Session(engine) as session:
            # First look for today's diary
            statement = select(DiaryDaily).where(
                DiaryDaily.user_id == user_id,
                DiaryDaily.date == today
            )
            diary = session.exec(statement).first()
            
            if diary:
                body_lines = diary.body.split("\n") if diary.body else []
                return DiaryResponse(
                    user_id=diary.user_id,
                    date=diary.date,
                    title=diary.title,
                    body_lines=body_lines,
                    tags=diary.tags,
                    ui={
                        "inline_keyboard": [
                            [{"text": "♥ Save", "callback": "save"}],
                            [{"text": "↩ Reply", "callback": "reply"}]
                        ]
                    }
                )
            
            # If today not available, look for yesterday's diary
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            statement = select(DiaryDaily).where(
                DiaryDaily.user_id == user_id,
                DiaryDaily.date == yesterday
            )
            diary = session.exec(statement).first()
            
            if diary:
                body_lines = diary.body.split("\n") if diary.body else []
                return DiaryResponse(
                    user_id=diary.user_id,
                    date=diary.date,
                    title=diary.title,
                    body_lines=body_lines,
                    tags=diary.tags,
                    ui={
                        "inline_keyboard": [
                            [{"text": "♥ Save", "callback": "save"}],
                            [{"text": "↩ Reply", "callback": "reply"}]
                        ]
                    }
                )
            
            return None


diary_service = DiaryService()
