import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    app_env: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite:///esl.db"
    database_echo: bool = False

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Excel Import
    excel_file_path: str = "English_Learning_Data_Clean.xlsx"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def database_url_with_params(self) -> str:
        """Database URL with connection params for SQLite."""
        if self.database_url.startswith("sqlite"):
            if "?" in self.database_url:
                return self.database_url
            return f"{self.database_url}?check_same_thread=false"
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()