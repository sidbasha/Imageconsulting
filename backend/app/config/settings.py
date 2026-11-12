from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="IC_", extra="ignore")

    env: str = "development"  # development | testing | staging | production
    database_url: str = "postgresql+psycopg://ic:ic@localhost:5432/ic_dev"
    jwt_secret: str = "change-me-in-every-environment-0000000000"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    storage_dir: str = "./var/uploads"  # local private storage; S3-compatible backend planned
    model_dir: str = "./var/models"  # on-device vision models, see ai_analysis/engine.py
    default_language: str = "en"
    supported_languages: tuple[str, ...] = ("en", "ar")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.env in ("staging", "production") and settings.jwt_secret.startswith("change-me"):
        raise RuntimeError("IC_JWT_SECRET must be set outside development")
    return settings
