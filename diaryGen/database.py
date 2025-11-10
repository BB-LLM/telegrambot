"""Database connection and initialization"""
from sqlmodel import SQLModel, create_engine, Session
from config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False
)


def init_db():
    """Initialize database tables"""
    # Import models to ensure tables are registered
    from models import DiaryDaily
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session"""
    with Session(engine) as session:
        yield session

