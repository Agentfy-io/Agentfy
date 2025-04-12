# -*- coding: utf-8 -*-
"""
@file: config.py
@desc: Agentfy config settings
@auth: Callmeiks
"""
from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings
from typing import List, Optional
from dotenv import load_dotenv

# load environment variables
load_dotenv()

class Settings(BaseSettings):
    """application config settings"""

    # database settings
    db_host: str = Field("localhost", env="DB_HOST")
    db_port: int = Field(9000, env="DB_PORT")
    db_username: str = Field("postgres", env="DB_USERNAME")
    db_password: str = Field("", env="DB_PASSWORD")
    db_database: str = Field("social_media_agent", env="DB_NAME")
    db_pool_size: int = Field(10, env="DB_POOL_SIZE")
    db_connection_timeout: int = Field(30, env="DB_CONN_TIMEOUT")

    # External Service API Keys
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    tikhub_api_key: Optional[str] = Field(None, env="TIKHUB_API_KEY")
    lemonfox_api_key: Optional[str] = Field(None, env="LEMONFOX_API_KEY")
    elevenlabs_api_key: Optional[str] = Field(None, env="ELEVENLABS_API_KEY")

    # social media API keys
    x_api_key: Optional[str] = Field(None, env="X_API_KEY")
    x_api_secret: Optional[str] = Field(None, env="X_API_SECRET")
    x_access_token: Optional[str] = Field(None, env="X_ACCESS_TOKEN")
    x_access_token_secret: Optional[str] = Field(None, env="X_ACCESS_TOKEN_SECRET")
    youtube_api_key: Optional[str] = Field(None, env="YOUTUBE_API_KEY")
    youtube_client_id: Optional[str] = Field(None, env="YOUTUBE_CLIENT_ID")
    youtube_client_secret: Optional[str] = Field(None, env="YOUTUBE_CLIENT_SECRET")

    # TikHub data source
    tikhub_base_url: str = "https://api.tikhub.io"

    # Task Queue Settings, if using Celery (uncomment if needed)
    """
    broker_url: str = Field("redis://localhost:6379/0", env="QUEUE_BROKER_URL")
    result_backend: str = Field("redis://localhost:6379/0", env="QUEUE_RESULT_BACKEND")
    task_default_queue: str = Field("default", env="QUEUE_DEFAULT")
    task_serializer: str = Field("json", env="QUEUE_TASK_SERIALIZER")
    result_serializer: str = Field("json", env="QUEUE_RESULT_SERIALIZER")
    accept_content: List[str] = ["json"]
    """

    log_level: str = Field("INFO", env="LOG_LEVEL")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")

    class Config:
        env_file = ".env"
        case_sensitive = False  # Change to False to handle case differences
        populate_by_name = True  # Allow populating by field name and alias


# Create a global settings object
settings = Settings()