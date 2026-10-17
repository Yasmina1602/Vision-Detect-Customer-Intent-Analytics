"""Ilova sozlamalari. Majburiy o'zgaruvchi bo'lmasa server ishga tushmaydi (17-bo'lim, #22)."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[4]  # monorepo ildizi


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(ROOT_DIR / ".env"), ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    APP_ENV: str = "development"
    EDITION: str = "full"                    # full | basic (faqat Oddiy tarif: storefront'siz, yengil)
    APP_SECRET_KEY: str = Field(min_length=32)
    PUBLIC_API_URL: str = "http://127.0.0.1:8000"
    DASHBOARD_URL: str = "http://localhost:3000"
    STOREFRONT_URL: str = "http://localhost:3001"
    MEDIA_DIR: str = ""                      # bo'sh bo'lsa apps/api/media

    DATABASE_URL: str
    REDIS_URL: str = ""

    GEMINI_API_KEY: str = ""
    GEMINI_MODELS: str = "gemini-2.0-flash"
    AI_TIMEOUT_SECONDS: int = 8
    AI_DAILY_BUDGET_USD: float = 50

    JWT_ACCESS_TTL_MIN: int = 15
    JWT_REFRESH_TTL_DAYS: int = 30
    CORS_DASHBOARD_ORIGINS: str = "http://localhost:3000"

    MAX_IMAGE_MB: int = 5
    RATE_LIMIT_SEARCH_PER_MIN_IP: int = 10
    RATE_LIMIT_SEARCH_PER_MIN_TENANT: int = 120
    DEFAULT_UNMET_THRESHOLD: float = 0.45
    ABANDON_AFTER_HOURS: int = 24
    ATTRIBUTION_DAYS: int = 7

    RUN_WORKER_IN_API: bool = True
    SENTRY_DSN: str = ""

    @field_validator("APP_ENV")
    @classmethod
    def _env(cls, v: str) -> str:
        if v not in {"development", "staging", "production"}:
            raise ValueError("APP_ENV development|staging|production bo'lishi kerak")
        return v

    @property
    def is_basic_edition(self) -> bool:
        return self.EDITION.lower() == "basic"

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def async_database_url(self) -> str:
        """mysql://... → mysql+aiomysql://... (SQLAlchemy async drayveri)."""
        url = self.DATABASE_URL
        if url.startswith("mysql://"):
            url = "mysql+aiomysql://" + url[len("mysql://"):]
        elif url.startswith("mysql+pymysql://"):
            url = "mysql+aiomysql://" + url[len("mysql+pymysql://"):]
        return url

    @property
    def sync_database_url(self) -> str:
        return self.async_database_url.replace("+aiomysql", "+pymysql")

    @property
    def media_path(self) -> Path:
        path = Path(self.MEDIA_DIR) if self.MEDIA_DIR else ROOT_DIR / "apps" / "api" / "media"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_DASHBOARD_ORIGINS.split(",") if o.strip()]

    @property
    def gemini_models(self) -> list[str]:
        return [m.strip() for m in self.GEMINI_MODELS.split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
