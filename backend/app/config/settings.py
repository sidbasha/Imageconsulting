from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="IC_", extra="ignore")

    env: str = "development"  # development | testing | staging | production
    database_url: str = "postgresql+psycopg://ic:ic@localhost:5432/ic_dev"
    # Optional direct (non-pooled) URL for Alembic. Hosted Postgres behind a pooler (e.g. Neon's
    # -pooler host) needs migrations on a direct connection. Empty: migrations use database_url.
    migration_database_url: str = ""
    jwt_secret: str = "change-me-in-every-environment-0000000000"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    storage_backend: str = "local"  # local | s3 (see app/integrations/storage.py)
    storage_dir: str = "./var/uploads"  # local backend
    s3_bucket: str = ""  # s3 backend
    # Standard AWS names (what `neon env pull` writes), read from the environment or .env.
    s3_access_key_id: str = Field("", validation_alias=AliasChoices("IC_S3_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID"))
    s3_secret_access_key: str = Field("", validation_alias=AliasChoices("IC_S3_SECRET_ACCESS_KEY", "AWS_SECRET_ACCESS_KEY"))
    s3_endpoint_url: str = Field("", validation_alias=AliasChoices("IC_S3_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3"))
    s3_region: str = Field("", validation_alias=AliasChoices("IC_S3_REGION", "AWS_REGION"))
    model_dir: str = "./var/models"  # on-device vision models, see ai_analysis/engine.py
    # Browser origins allowed to call the API, comma-separated. Empty: the apps are native, no browser client.
    cors_origins: str = ""
    # Demo hosting only: the app's own public health URL, e.g. https://ic-api.onrender.com/health.
    # When set, the app pings it every keep_alive_minutes so a free host does not put it to sleep.
    keep_alive_url: str = ""
    keep_alive_minutes: float = 10
    default_language: str = "en"
    supported_languages: tuple[str, ...] = ("en", "ar")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.env in ("staging", "production") and settings.jwt_secret.startswith("change-me"):
        raise RuntimeError("IC_JWT_SECRET must be set outside development")
    return settings
