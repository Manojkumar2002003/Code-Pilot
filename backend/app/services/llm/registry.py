"""Thread-safe registry for cloud LLM provider adapters.

New adapters are registered by provider identifier and retrieved at
runtime by ``LLMService``.  Tests can substitute fake adapters via
dependency injection without modifying business logic.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from app.schemas.llm import LLMError, LLMErrorCode, LLMProviderID

if TYPE_CHECKING:
    from app.services.llm.provider import BaseLLMProvider


class LLMProviderRegistry:
    """Registry mapping ``LLMProviderID`` → ``BaseLLMProvider`` instances.

    The registry is thread-safe and can be replaced wholesale for testing.
    """

    def __init__(self) -> None:
        self._providers: dict[LLMProviderID, BaseLLMProvider] = {}
        self._lock = threading.Lock()

    def register(self, provider: BaseLLMProvider) -> None:
        """Register an adapter, keyed by its ``provider_id``."""
        with self._lock:
            self._providers[provider.provider_id] = provider

    def unregister(self, provider_id: LLMProviderID) -> None:
        """Remove a previously registered adapter."""
        with self._lock:
            self._providers.pop(provider_id, None)

    def get(self, provider_id: LLMProviderID) -> BaseLLMProvider:
        """Retrieve a registered adapter or raise ``LLMError``.

        Raises:
            LLMError: With ``UNSUPPORTED_PROVIDER`` code when no adapter
                is registered for *provider_id*.
        """
        with self._lock:
            provider = self._providers.get(provider_id)
        if provider is None:
            raise LLMError(
                code=LLMErrorCode.UNSUPPORTED_PROVIDER,
                message=f"No adapter registered for provider '{provider_id.value}'.",
                provider=provider_id,
            )
        return provider

    def list_providers(self) -> list[LLMProviderID]:
        """Return a sorted list of currently registered provider IDs."""
        with self._lock:
            return sorted(self._providers.keys(), key=lambda p: p.value)

    def has(self, provider_id: LLMProviderID) -> bool:
        """Return ``True`` when *provider_id* is registered."""
        with self._lock:
            return provider_id in self._providers

    def clear(self) -> None:
        """Remove all registered adapters (useful in tests)."""
        with self._lock:
            self._providers.clear()


__all__ = ["LLMProviderRegistry"]
