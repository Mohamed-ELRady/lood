from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LOOD_", extra="ignore")

    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])
    job_ttl_seconds: int = Field(default=3600, ge=300, le=86400)
    max_active_jobs: int = Field(default=2, ge=1, le=10)
    max_file_size_mb: int = Field(default=1024, ge=10, le=10240)
    download_timeout_seconds: int = Field(default=1800, ge=60, le=7200)
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
