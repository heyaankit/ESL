import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
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
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Excel Import
    excel_file_path: str = "English_Learning_Data_Clean.xlsx"
    excel_data_dir: str = "data"

    # SMTP / Email (for OTP delivery)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_use_tls: bool = True

    # OTP Rate Limiting
    otp_rate_limit_per_minute: int = 5

    # OpenAI (AI service for chat, quiz generation, answer evaluation)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_max_retries: int = 3
    openai_timeout_seconds: int = 30

    # Google Cloud (TTS / STT)
    google_cloud_credentials_json: Optional[str] = None
    google_tts_language_code: str = "en-US"
    google_stt_language_code: str = "en-US"

    # Firebase / FCM (Push Notifications)
    firebase_service_account_json: Optional[str] = None
    admin_push_key: Optional[str] = None

    # Social Login
    google_client_id: Optional[str] = None

    # File Uploads
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10

    # Notifications
    notification_scheduler_interval_minutes: int = 60

    # Audio
    audio_file_expiry_hours: int = 24

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def smtp_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return all([self.smtp_host, self.smtp_user, self.smtp_password, self.smtp_from_email])

    @property
    def openai_configured(self) -> bool:
        """Check if OpenAI is configured."""
        return self.openai_api_key is not None

    @property
    def google_cloud_configured(self) -> bool:
        """Check if Google Cloud credentials are set."""
        return self.google_cloud_credentials_json is not None

    @property
    def firebase_configured(self) -> bool:
        """Check if Firebase is configured."""
        return self.firebase_service_account_json is not None

    @property
    def database_url_with_params(self) -> str:
        """Database URL with connection params for SQLite."""
        url = self.database_url
        # Fallback: if DATABASE_URL was overridden by a parent .env with a non-SQLAlchemy URL,
        # use the default SQLite URL instead
        if not url or not url.startswith(("sqlite", "postgresql", "mysql")):
            url = "sqlite:///esl.db"
        if url.startswith("sqlite"):
            if "?" in url:
                return url
            return f"{url}?check_same_thread=false"
        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
