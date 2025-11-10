"""Data model definitions"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import UniqueConstraint


class DiaryDaily(SQLModel, table=True):
    """Daily diary table - meets A10 requirement with unique constraint"""
    __tablename__ = "diary_daily"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="unique_user_date"),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, description="User ID")
    date: str = Field(description="Date in yyyy-mm-dd format")
    title: str = Field(description="Title")
    body: str = Field(description="Body text (multiline, separated by \\n)")
    tags: List[str] = Field(sa_column=Column(JSON), description="Tag list")
    created_at: datetime = Field(default_factory=datetime.now, description="Created timestamp")


class MessageModel(SQLModel):
    """Message model (aligned with telegrambot)"""
    role: str = Field(description="Role: user or assistant")
    content: str = Field(description="Message content")
    time: Optional[str] = Field(default=None, description="Timestamp")


class MemoriesModel(SQLModel):
    """Memories model (aligned with telegrambot)"""
    facts: str = Field(description="memorable events")
    profile: str = Field(description="player profile")
    style: str = Field(description="style notes")
    commitments: str = Field(description="tiny commitments")


class DiaryGenerateRequest(SQLModel):
    """Diary generation request (format consistent with telegrambot)"""
    user_id: str = Field(description="User ID")
    date: str = Field(description="Date in yyyy-mm-dd format")
    timezone: Optional[str] = Field(default="Asia/Shanghai", description="Timezone")
    messages: List[MessageModel] = Field(description="Daily messages list")
    memories: Optional[MemoriesModel] = Field(default=None, description="Memory information (optional, mainly use messages)")


class DiaryResponse(SQLModel):
    """Diary response format (for frontend display and telegrambot)"""
    user_id: str
    date: str
    title: str
    body_lines: List[str] = Field(description="Body lines list (3-6 lines)")
    tags: List[str] = Field(description="Tag list (2 tags)")
    ui: dict = Field(
        default={
            "inline_keyboard": [
                [{"text": "♥ Save", "callback": "save"}],
                [{"text": "↩ Reply", "callback": "reply"}]
            ]
        },
        description="UI button configuration"
    )

