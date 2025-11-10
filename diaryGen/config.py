"""Configuration management module"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    # API authentication
    
    # Database
    database_url: str = "sqlite:///./diary.db"
    
    # LLM configuration
    openai_api_key: str = "0031af15104f4a49bb70e1e6bf1e4d72.nybmwLU1gf7U41fh"
    openai_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    llm_model: str = "glm-4-flash"
    
    # Service ports
    api_port: int = 8083
    demo_port: int = 8084
    
    # Default configuration
    default_timezone: str = "Asia/Shanghai"
    default_publish_start: str = "21:00"
    default_publish_end: str = "22:00"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

