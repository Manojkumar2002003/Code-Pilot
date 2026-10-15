"""Provider-independent LLM contracts for CodePilot.

Defines the common request, response, capability, and error models
used by all cloud LLM provider adapters. No provider-specific logic
belongs in this module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Provider identifiers
# ---------------------------------------------------------------------------

class LLMProviderID(str, Enum):
    """Canonical identifiers for supported cloud LLM providers."""

    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    NVIDIA_NIM = "nvidia_nim"
    GROQ = "groq"
    OLLAMA_CLOUD = "ollama_cloud"


# ---------------------------------------------------------------------------
# Capability representation
# ---------------------------------------------------------------------------

class CapabilitySupport(str, Enum):
    """Tri-state for a model capability: supported, unsupported, or unknown."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class ModelCapabilities(BaseModel):
    """Declared capabilities for a specific provider/model combination.

    Values default to ``unknown`` — adapters or configuration must
    explicitly declare support or lack thereof.
    """

    model_config = ConfigDict(extra="forbid")

    text_generation: CapabilitySupport = CapabilitySupport.UNKNOWN
    structured_json_output: CapabilitySupport = CapabilitySupport.UNKNOWN
    tool_calling: CapabilitySupport = CapabilitySupport.UNKNOWN
    streaming: CapabilitySupport = CapabilitySupport.UNKNOWN
    context_window_tokens: int | None = Field(
        default=None,
        description="Maximum context-window size in tokens, if known.",
    )
    max_output_tokens: int | None = Field(
        default=None,
        description="Maximum output tokens supported, if known.",
    )


# ---------------------------------------------------------------------------
# Message types
# ---------------------------------------------------------------------------

class MessageRole(str, Enum):
    """Standard conversation message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ConversationMessage(BaseModel):
    """A single message in a conversation history."""

    model_config = ConfigDict(extra="forbid")

    role: MessageRole
    content: str


# ---------------------------------------------------------------------------
# Structured-output hints
# ---------------------------------------------------------------------------

class StructuredOutputRequirement(BaseModel):
    """Optional hint for requesting structured (JSON) output."""

    model_config = ConfigDict(extra="forbid")

    json_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema the response should conform to.",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of the expected structure.",
    )


# ---------------------------------------------------------------------------
# LLM Request contract
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Provider Health States
# ---------------------------------------------------------------------------

class ProviderHealthState(str, Enum):
    """Health and availability status of a cloud LLM provider."""

    NOT_CONFIGURED = "not_configured"
    CONFIGURED = "configured"
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXHAUSTED = "quota_exhausted"
    AUTHENTICATION_FAILURE = "authentication_failure"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    MODEL_UNAVAILABLE = "model_unavailable"
    DISABLED = "disabled"


# ---------------------------------------------------------------------------
# Model Registry Metadata
# ---------------------------------------------------------------------------

class ModelMetadata(BaseModel):
    """Metadata describing a supported provider/model in the Model Registry."""

    model_config = ConfigDict(extra="forbid")

    provider: LLMProviderID
    model_id: str
    display_name: str
    enabled: bool = True
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities)
    context_window_tokens: int | None = None
    max_output_tokens: int | None = None
    supported_parameters: list[str] = Field(default_factory=list)
    pricing_tier: str | None = None
    source_url: str | None = None
    last_verified_date: str | None = None


# ---------------------------------------------------------------------------
# Failover Telemetry
# ---------------------------------------------------------------------------

class FailoverAttemptMetadata(BaseModel):
    """Telemetry recorded for a single provider attempt during generation."""

    model_config = ConfigDict(extra="forbid")

    provider: LLMProviderID
    model: str
    attempt_number: int
    duration_seconds: float
    error_code: str | None = None
    error_message: str | None = None
    eligible_for_failover: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FailoverMetadata(BaseModel):
    """Summary of failover decisions and execution history for a request."""

    model_config = ConfigDict(extra="forbid")

    initial_provider: LLMProviderID
    initial_model: str
    final_provider: LLMProviderID
    final_model: str
    total_attempts: int
    failover_occurred: bool
    failover_reason: str | None = None
    total_duration_seconds: float
    attempts: list[FailoverAttemptMetadata] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# LLM Request contract
# ---------------------------------------------------------------------------

class LLMRequest(BaseModel):
    """Provider-independent request for an LLM generation.

    Not every provider supports every field. Adapters translate
    supported fields and raise ``UnsupportedCapabilityError`` for
    features that are required but unavailable.
    """

    model_config = ConfigDict(extra="forbid")

    provider: LLMProviderID | None = Field(
        default=None,
        description="Target provider identifier, or None to let the router choose.",
    )
    model: str | None = Field(
        default=None,
        description="Model identifier understood by the target provider, or None for default.",
    )

    # Prompt / conversation
    system_instruction: str | None = Field(
        default=None,
        description="Optional system-level instruction.",
    )
    messages: list[ConversationMessage] = Field(
        default_factory=list,
        description="Conversation messages (user, assistant turns).",
    )

    # Generation parameters
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (provider-dependent range).",
    )
    max_output_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Maximum tokens to generate.",
    )

    # Structured output
    structured_output: StructuredOutputRequirement | None = Field(
        default=None,
        description="Optional structured-output requirement.",
    )

    # Request behaviour
    timeout_seconds: float | None = Field(
        default=None,
        gt=0,
        description="Request timeout in seconds.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata passed through to the response.",
    )


# ---------------------------------------------------------------------------
# Token-usage information
# ---------------------------------------------------------------------------

class TokenUsage(BaseModel):
    """Token-usage statistics when available from the provider."""

    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


# ---------------------------------------------------------------------------
# LLM Response contract
# ---------------------------------------------------------------------------

class LLMResponse(BaseModel):
    """Normalized response from any cloud LLM provider."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(
        ...,
        description="Generated text content.",
    )
    provider: LLMProviderID
    model: str
    token_usage: TokenUsage | None = Field(
        default=None,
        description="Token-usage statistics, if provided.",
    )
    duration_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Wall-clock request duration in seconds.",
    )
    finish_reason: str | None = Field(
        default=None,
        description="Provider-reported completion finish reason.",
    )
    structured_output: dict[str, Any] | None = Field(
        default=None,
        description="Parsed structured output, if applicable.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Pass-through and provider-specific metadata.",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Normalized LLM errors
# ---------------------------------------------------------------------------

class LLMErrorCode(str, Enum):
    """Standardized error codes for cloud LLM provider failures."""

    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    UNSUPPORTED_PROVIDER = "UNSUPPORTED_PROVIDER"
    UNSUPPORTED_MODEL = "UNSUPPORTED_MODEL"
    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_PARAMETER = "UNSUPPORTED_PARAMETER"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    PROVIDER_OUTAGE = "PROVIDER_OUTAGE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Errors that may succeed on retry or trigger failover.
_RETRYABLE_CODES: frozenset[LLMErrorCode] = frozenset({
    LLMErrorCode.RATE_LIMIT_EXCEEDED,
    LLMErrorCode.QUOTA_EXHAUSTED,
    LLMErrorCode.REQUEST_TIMEOUT,
    LLMErrorCode.NETWORK_ERROR,
    LLMErrorCode.PROVIDER_OUTAGE,
})


class LLMError(Exception):
    """Normalized exception raised by provider adapters.

    Adapters MUST translate provider-specific errors into this type
    so that callers handle failures consistently.
    """

    def __init__(
        self,
        code: LLMErrorCode,
        message: str,
        *,
        provider: LLMProviderID | None = None,
        model: str | None = None,
        details: dict[str, Any] | None = None,
        retry_after: float | None = None,
    ) -> None:
        safe_message = _redact_secrets(message)
        super().__init__(safe_message)
        self.code = code
        self.provider = provider
        self.model = model
        self.details = details or {}
        self.retry_after = retry_after
        if retry_after is not None and "retry_after_seconds" not in self.details:
            self.details["retry_after_seconds"] = retry_after
        self._safe_message = safe_message

    @property
    def is_retryable(self) -> bool:
        """Return ``True`` when the error category is generally retryable."""
        return self.code in _RETRYABLE_CODES

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation that never contains secrets."""
        result: dict[str, Any] = {
            "code": self.code.value,
            "message": self._safe_message,
            "retryable": self.is_retryable,
        }
        if self.provider is not None:
            result["provider"] = self.provider.value
        if self.model is not None:
            result["model"] = self.model
        if self.retry_after is not None:
            result["retry_after_seconds"] = self.retry_after
        return result


class UnsupportedCapabilityError(LLMError):
    """Raised when a requested capability is not supported by the model."""

    def __init__(
        self,
        capability: str,
        *,
        provider: LLMProviderID | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(
            code=LLMErrorCode.UNSUPPORTED_CAPABILITY,
            message=f"Capability '{capability}' is not supported.",
            provider=provider,
            model=model,
            details={"capability": capability},
        )
        self.capability = capability


def _redact_secrets(text: str) -> str:
    """Best-effort redaction of secret-like substrings and credentials in error messages.

    Masks actual credential values, API keys, and bearer tokens with [REDACTED],
    while preserving safe diagnostic context.
    """
    redacted = text
    # 1. Mask key=value or key: value credential assignments
    redacted = re.sub(
        r"(?i)\b(api[_-]?key|token|secret|password|credential)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{4,})['\"]?",
        r"\1=[REDACTED]",
        redacted,
    )
    # 2. Mask sk-... style API tokens
    redacted = re.sub(r"(?i)\b(sk-[a-zA-Z0-9_\-]{6,})\b", "[REDACTED]", redacted)
    # 3. Mask Bearer authorization tokens
    redacted = re.sub(r"(?i)\bBearer\s+[a-zA-Z0-9_\-\.]{6,}\b", "Bearer [REDACTED]", redacted)
    return redacted


# ---------------------------------------------------------------------------
# API-facing status models
# ---------------------------------------------------------------------------

class ProviderStatusResponse(BaseModel):
    """Status of a single configured LLM provider (no secrets exposed)."""

    model_config = ConfigDict(extra="forbid")

    provider: LLMProviderID
    enabled: bool
    configured: bool = Field(
        description="Whether the provider has sufficient configuration to initialize.",
    )
    health_status: ProviderHealthState = ProviderHealthState.NOT_CONFIGURED
    default_model: str | None = None
    available_models: list[str] = Field(default_factory=list)
    capabilities: ModelCapabilities | None = None
    last_error: str | None = None
    last_checked_at: datetime | None = None


class LLMStatusResponse(BaseModel):
    """Overall LLM subsystem status exposed by the API."""

    model_config = ConfigDict(extra="forbid")

    default_provider: LLMProviderID | None = None
    default_model: str | None = None
    failover_enabled: bool = True
    provider_priority: list[LLMProviderID] = Field(default_factory=list)
    providers: list[ProviderStatusResponse] = Field(default_factory=list)


__all__ = [
    "LLMProviderID",
    "CapabilitySupport",
    "ModelCapabilities",
    "ProviderHealthState",
    "ModelMetadata",
    "FailoverAttemptMetadata",
    "FailoverMetadata",
    "MessageRole",
    "ConversationMessage",
    "StructuredOutputRequirement",
    "LLMRequest",
    "TokenUsage",
    "LLMResponse",
    "LLMErrorCode",
    "LLMError",
    "UnsupportedCapabilityError",
    "ProviderStatusResponse",
    "LLMStatusResponse",
]
