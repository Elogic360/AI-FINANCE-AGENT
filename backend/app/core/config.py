from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "FinPilot AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://finpilot:finpilot@localhost:5433/finpilot"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    JWT_SECRET_KEY: str = "change-me-in-production-use-35-plus-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Providers
    PAWA_API_KEY: Optional[str] = None
    PAWA_API_URL: str = "https://api.pawa.ai"
    GEMINI_API_KEY: Optional[str] = None

    # File Storage (Cloudflare R2)
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: str = "finpilot-documents"
    R2_PUBLIC_URL: Optional[str] = None

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Financial
    DEFAULT_CURRENCY: str = "TZS"
    DEFAULT_COUNTRY: str = "TZ"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
