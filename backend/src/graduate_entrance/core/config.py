from datetime import date
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
    vocab_seed_path: Path = Path("../seed/vocab/kaoyan_words.json")
    recitation_seed_path: Path = Path("../seed/recitation/politics.json")
    problem_images_dir: Path = Path("./data/problem-images")
    chat_images_dir: Path = Path("./data/chat-images")
    papers_dir: Path = Path("./data/papers")
    ai_base_url: str = ""
    ai_api_key: SecretStr = SecretStr("")
    ai_model: str = ""
    ai_timeout_seconds: float = 120.0
    ai_reasoning_effort: str = ""
    ai_planning_reasoning_effort: str = ""
    exam_date: date = date(2026, 12, 26)
    automation_enabled: bool = True
    automation_timezone: str = "Asia/Shanghai"


@lru_cache
def get_settings() -> Settings:
    return Settings()
