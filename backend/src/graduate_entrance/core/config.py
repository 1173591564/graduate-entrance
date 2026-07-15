from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )

    app_name: str = "Graduate Entrance API"
    environment: Literal["local", "test", "staging", "production"] = "local"
    database_url: str = (
        "postgresql+asyncpg://graduate_entrance:local-development-only"
        "@localhost:5432/graduate_entrance"
    )
    api_token: SecretStr = Field(
        default=SecretStr("local-development-only"),
        min_length=16,
    )
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    syllabus_raw_dir: Path = Path("../seed/syllabus/raw")


@lru_cache
def get_settings() -> Settings:
    return Settings()
