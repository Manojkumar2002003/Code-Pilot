from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "CodePilot API"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api"
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "sqlite:///./data/codepilot.db"

    @property
    def service_name(self) -> str:
        return self.app_name.lower().replace(" ", "-")


@lru_cache
def get_settings() -> Settings:
    return Settings()
