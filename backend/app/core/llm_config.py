"""LLM provider configuration for CodePilot.

Loads provider-specific settings from environment variables and validates
that the selected default provider has sufficient configuration.

All API keys are loaded via environment variables — never hardcoded.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.llm import LLMProviderID


# ---------------------------------------------------------------------------
# Per-provider configuration blocks
# ---------------------------------------------------------------------------

class GeminiConfig(BaseModel):
    """Configuration for the Google Gemini provider."""

    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(default=None, description="Gemini API key.")
    default_model: str = Field(
        default="gemini-2.0-flash",
        description="Default Gemini model identifier.",
    )
    enabled: bool = True


class OpenRouterConfig(BaseModel):
    """Configuration for the OpenRouter provider."""

    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(default=None, description="OpenRouter API key.")
    base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL.",
    )
    default_model: str = Field(
        default="openai/gpt-4o",
        description="Default OpenRouter model identifier.",
    )
    enabled: bool = True


class NvidiaNimConfig(BaseModel):
    """Configuration for the NVIDIA NIM provider."""

    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(default=None, description="NVIDIA NIM API key.")
    base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="NVIDIA NIM base URL / endpoint.",
    )
    default_model: str = Field(
        default="meta/llama-3.1-8b-instruct",
        description="Default NVIDIA NIM model identifier.",
    )
    enabled: bool = True


class GroqConfig(BaseModel):
    """Configuration for the Groq provider."""

    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(default=None, description="Groq API key.")
    base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Groq API base URL.",
    )
    default_model: str = Field(
        default="llama-3.1-8b-instant",
        description="Default Groq model identifier.",
    )
    enabled: bool = True


class OllamaCloudConfig(BaseModel):
    """Configuration for the Ollama Cloud provider.

    This is a *hosted* cloud inference service — **not** local Ollama.
    Do not configure a localhost endpoint.
    """

    model_config = ConfigDict(extra="forbid")

    api_key: str | None = Field(default=None, description="Ollama Cloud API key.")
    base_url: str = Field(
        default="https://api.ollama.com",
        description="Ollama Cloud API endpoint (must NOT be localhost).",
    )
    default_model: str = Field(
        default="llama3.1",
        description="Default Ollama Cloud model identifier.",
    )
    enabled: bool = True


# ---------------------------------------------------------------------------
# Aggregate LLM settings
# ---------------------------------------------------------------------------

class LLMSettings(BaseModel):
    """Top-level, provider-independent LLM settings.

    These are populated from environment variables by the ``Settings``
    class in ``app.core.config``.  Individual provider configs are
    constructed from flattened env vars with a ``LLM_<PROVIDER>_``
    prefix.
    """

    model_config = ConfigDict(extra="forbid")

    default_provider: LLMProviderID = Field(
        default=LLMProviderID.GEMINI,
        description="Provider used when none is explicitly specified.",
    )
    default_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Default request timeout in seconds.",
    )
    default_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default sampling temperature.",
    )
    default_max_output_tokens: int = Field(
        default=4096,
        gt=0,
        description="Default max output tokens.",
    )

    # Intelligent routing & failover settings
    failover_enabled: bool = Field(
        default=True,
        description="Whether to automatically failover to an alternative provider upon rate limit, quota exhaustion, or outage.",
    )
    provider_priority: list[LLMProviderID] = Field(
        default_factory=lambda: [
            LLMProviderID.GEMINI,
            LLMProviderID.OPENROUTER,
            LLMProviderID.GROQ,
            LLMProviderID.NVIDIA_NIM,
            LLMProviderID.OLLAMA_CLOUD,
        ],
        description="Ordered list of preferred cloud LLM providers.",
    )
    max_failover_attempts: int = Field(
        default=3,
        gt=0,
        description="Maximum provider attempts per logical generation request.",
    )
    total_request_deadline_seconds: float = Field(
        default=120.0,
        gt=0,
        description="Total wall-clock deadline for a request across all failover attempts.",
    )
    circuit_breaker_cooldown_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Cooldown period in seconds for temporarily unavailable or rate-limited providers.",
    )

    # Per-provider configurations
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    openrouter: OpenRouterConfig = Field(default_factory=OpenRouterConfig)
    nvidia_nim: NvidiaNimConfig = Field(default_factory=NvidiaNimConfig)
    groq: GroqConfig = Field(default_factory=GroqConfig)
    ollama_cloud: OllamaCloudConfig = Field(default_factory=OllamaCloudConfig)

    def get_provider_config(
        self, provider: LLMProviderID
    ) -> GeminiConfig | OpenRouterConfig | NvidiaNimConfig | GroqConfig | OllamaCloudConfig:
        """Return the configuration block for *provider*."""
        mapping = {
            LLMProviderID.GEMINI: self.gemini,
            LLMProviderID.OPENROUTER: self.openrouter,
            LLMProviderID.NVIDIA_NIM: self.nvidia_nim,
            LLMProviderID.GROQ: self.groq,
            LLMProviderID.OLLAMA_CLOUD: self.ollama_cloud,
        }
        return mapping[provider]

    def is_provider_configured(self, provider: LLMProviderID) -> bool:
        """Return ``True`` when *provider* has sufficient config to initialize."""
        cfg = self.get_provider_config(provider)
        if not cfg.enabled:
            return False
        # All cloud providers require an API key.
        return cfg.api_key is not None and len(cfg.api_key.strip()) > 0

    def get_default_model(self, provider: LLMProviderID) -> str:
        """Return the configured default model for *provider*."""
        return self.get_provider_config(provider).default_model


__all__ = [
    "GeminiConfig",
    "OpenRouterConfig",
    "NvidiaNimConfig",
    "GroqConfig",
    "OllamaCloudConfig",
    "LLMSettings",
]
