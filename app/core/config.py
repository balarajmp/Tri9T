import os
from typing import Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    APP_NAME: str = "Tri9T API"
    APP_ENV: Literal["development", "production", "testing"] = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    LOG_LEVEL: str = "INFO"

    # SQLite Settings
    SQLITE_DB_URL: str = "sqlite+aiosqlite:///./sql_app.db"

    # MongoDB Settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "tri9t_db"

    # LLM Settings
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    @field_validator("SQLITE_DB_URL")
    @classmethod
    def validate_sqlite_db_url(cls, v: str) -> str:
        if not v.startswith("sqlite+aiosqlite:///"):
            # If standard sqlite:/// is provided, convert to aiosqlite for async support
            if v.startswith("sqlite:///"):
                return v.replace("sqlite:///", "sqlite+aiosqlite:///")
            raise ValueError("SQLITE_DB_URL must use the aiosqlite protocol for async operations (sqlite+aiosqlite:///)")
        return v


# Instantiate settings
settings = Settings()
