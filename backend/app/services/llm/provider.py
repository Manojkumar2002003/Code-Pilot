"""Abstract base class for cloud LLM provider adapters.

Every cloud provider (Gemini, OpenRouter, NVIDIA NIM, Groq, Ollama Cloud)
will subclass ``BaseLLMProvider`` and implement the abstract methods.

S3.1 establishes the contract only — concrete adapters belong to S3.2.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.llm import (
    LLMProviderID,
    LLMRequest,
    LLMResponse,
    ModelCapabilities,
    ProviderHealthState,
)


class BaseLLMProvider(ABC):
    """Provider adapter interface.

    Adapters MUST:
    - Translate ``LLMRequest`` into the provider-native format.
    - Return a normalised ``LLMResponse``.
    - Raise ``LLMError`` (or a subclass) for any failure.
    - Keep authentication, endpoint construction, and response parsing
      entirely within the adapter.
    """

    @property
    @abstractmethod
    def provider_id(self) -> LLMProviderID:
        """Return the canonical provider identifier."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Send a generation request to the provider and return a normalised response.

        This method is ``async`` so it can be used directly inside
        FastAPI path operations without blocking the event loop.

        Raises:
            LLMError: For any provider-related failure, with a
                normalised error code, safe message, and retryability flag.
        """

    @abstractmethod
    async def get_capabilities(self, model: str | None = None) -> ModelCapabilities:
        """Return declared capabilities for *model* (or the default model).

        Unknown capabilities MUST be represented as
        ``CapabilitySupport.UNKNOWN`` rather than guessed.
        """

    @abstractmethod
    def is_configured(self) -> bool:
        """Return ``True`` when the adapter has sufficient configuration
        to attempt a generation request (e.g. API key present).

        This does NOT imply connectivity or quota availability.
        """

    async def check_health(self) -> ProviderHealthState:
        """Check provider connectivity and health using a low-cost metadata or tags endpoint.

        Does NOT generate completions or consume significant token quota.
        """
        if not self.is_configured():
            return ProviderHealthState.NOT_CONFIGURED
        return ProviderHealthState.CONFIGURED


__all__ = ["BaseLLMProvider"]
