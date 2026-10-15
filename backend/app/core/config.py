from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.llm_config import (
    GeminiConfig,
    GroqConfig,
    LLMSettings,
    NvidiaNimConfig,
    OllamaCloudConfig,
    OpenRouterConfig,
)
from app.schemas.llm import LLMProviderID

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

    # --- LLM configuration (all optional, loaded from env vars) -----------
    llm_default_provider: str = "gemini"
    llm_default_timeout_seconds: float = 60.0
    llm_default_temperature: float = 0.7
    llm_default_max_output_tokens: int = 4096

    # Gemini
    llm_gemini_api_key: str | None = None
    llm_gemini_default_model: str = "gemini-2.0-flash"
    llm_gemini_enabled: bool = True

    # OpenRouter
    llm_openrouter_api_key: str | None = None
    llm_openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_openrouter_default_model: str = "openai/gpt-4o"
    llm_openrouter_enabled: bool = True

    # NVIDIA NIM
    llm_nvidia_nim_api_key: str | None = None
    llm_nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    llm_nvidia_nim_default_model: str = "meta/llama-3.1-8b-instruct"
    llm_nvidia_nim_enabled: bool = True

    # Groq
    llm_groq_api_key: str | None = None
    llm_groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_groq_default_model: str = "llama-3.1-8b-instant"
    llm_groq_enabled: bool = True

    # Ollama Cloud (hosted cloud service — NOT local Ollama)
    llm_ollama_cloud_api_key: str | None = None
    llm_ollama_cloud_base_url: str = "https://api.ollama.com"
    llm_ollama_cloud_default_model: str = "llama3.1"
    llm_ollama_cloud_enabled: bool = True

    # Failover & Routing configuration
    llm_failover_enabled: bool = True
    llm_provider_priority: str = "gemini,openrouter,groq,nvidia_nim,ollama_cloud"
    llm_max_failover_attempts: int = 3
    llm_total_request_deadline_seconds: float = 120.0
    llm_circuit_breaker_cooldown_seconds: float = 60.0

    @property
    def service_name(self) -> str:
        return self.app_name.lower().replace(" ", "-")

    def build_llm_settings(self) -> LLMSettings:
        """Build the aggregate ``LLMSettings`` from flat env-var fields."""
        priority_list: list[LLMProviderID] = []
        for p in self.llm_provider_priority.split(","):
            p_clean = p.strip().lower()
            if p_clean:
                try:
                    priority_list.append(LLMProviderID(p_clean))
                except ValueError:
                    pass
        if not priority_list:
            priority_list = [
                LLMProviderID.GEMINI,
                LLMProviderID.OPENROUTER,
                LLMProviderID.GROQ,
                LLMProviderID.NVIDIA_NIM,
                LLMProviderID.OLLAMA_CLOUD,
            ]

        return LLMSettings(
            default_provider=LLMProviderID(self.llm_default_provider),
            default_timeout_seconds=self.llm_default_timeout_seconds,
            default_temperature=self.llm_default_temperature,
            default_max_output_tokens=self.llm_default_max_output_tokens,
            failover_enabled=self.llm_failover_enabled,
            provider_priority=priority_list,
            max_failover_attempts=self.llm_max_failover_attempts,
            total_request_deadline_seconds=self.llm_total_request_deadline_seconds,
            circuit_breaker_cooldown_seconds=self.llm_circuit_breaker_cooldown_seconds,
            gemini=GeminiConfig(
                api_key=self.llm_gemini_api_key,
                default_model=self.llm_gemini_default_model,
                enabled=self.llm_gemini_enabled,
            ),
            openrouter=OpenRouterConfig(
                api_key=self.llm_openrouter_api_key,
                base_url=self.llm_openrouter_base_url,
                default_model=self.llm_openrouter_default_model,
                enabled=self.llm_openrouter_enabled,
            ),
            nvidia_nim=NvidiaNimConfig(
                api_key=self.llm_nvidia_nim_api_key,
                base_url=self.llm_nvidia_nim_base_url,
                default_model=self.llm_nvidia_nim_default_model,
                enabled=self.llm_nvidia_nim_enabled,
            ),
            groq=GroqConfig(
                api_key=self.llm_groq_api_key,
                base_url=self.llm_groq_base_url,
                default_model=self.llm_groq_default_model,
                enabled=self.llm_groq_enabled,
            ),
            ollama_cloud=OllamaCloudConfig(
                api_key=self.llm_ollama_cloud_api_key,
                base_url=self.llm_ollama_cloud_base_url,
                default_model=self.llm_ollama_cloud_default_model,
                enabled=self.llm_ollama_cloud_enabled,
            ),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_llm_settings() -> LLMSettings:
    """Return a cached ``LLMSettings`` instance built from the environment."""
    return get_settings().build_llm_settings()


__all__ = [
    "BASE_DIR",
    "Settings",
    "get_settings",
    "get_llm_settings",
]
