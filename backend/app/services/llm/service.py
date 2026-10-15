"""High-level LLM service facade consumed by API routes and future agents.

Owns the ``LLMProviderRegistry``, ``ModelRegistry``, and ``LLMRouter``.
Coordinates adapter registration, default parameter resolution, health checks,
and intelligent provider failover.
"""

from __future__ import annotations

from typing import Any

from app.core.llm_config import LLMSettings
from app.schemas.llm import (
    LLMError,
    LLMErrorCode,
    LLMProviderID,
    LLMRequest,
    LLMResponse,
    LLMStatusResponse,
    ModelCapabilities,
    ModelMetadata,
    ProviderHealthState,
    ProviderStatusResponse,
)
from app.services.llm.adapters.gemini import GeminiAdapter
from app.services.llm.adapters.groq import GroqAdapter
from app.services.llm.adapters.nvidia_nim import NvidiaNimAdapter
from app.services.llm.adapters.ollama_cloud import OllamaCloudAdapter
from app.services.llm.adapters.openrouter import OpenRouterAdapter
from app.services.llm.model_registry import ModelRegistry, get_model_registry
from app.services.llm.registry import LLMProviderRegistry
from app.services.llm.router import CircuitBreaker, LLMRouter


def build_default_registry(settings: LLMSettings) -> LLMProviderRegistry:
    """Instantiate and register all five cloud provider adapters."""
    registry = LLMProviderRegistry()
    registry.register(GeminiAdapter(settings.gemini))
    registry.register(OpenRouterAdapter(settings.openrouter))
    registry.register(NvidiaNimAdapter(settings.nvidia_nim))
    registry.register(GroqAdapter(settings.groq))
    registry.register(OllamaCloudAdapter(settings.ollama_cloud))
    return registry


class LLMService:
    """Facade that future AI agents call for cloud LLM generation."""

    def __init__(
        self,
        settings: LLMSettings,
        registry: LLMProviderRegistry | None = None,
        model_registry: ModelRegistry | None = None,
        router: LLMRouter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry or build_default_registry(settings)
        self._model_registry = model_registry or get_model_registry()
        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            default_cooldown_seconds=settings.circuit_breaker_cooldown_seconds
        )
        self._router = router or LLMRouter(
            settings=self._settings,
            registry=self._registry,
            model_registry=self._model_registry,
            circuit_breaker=self._circuit_breaker,
        )

    @property
    def registry(self) -> LLMProviderRegistry:
        """Direct access to provider adapter registry."""
        return self._registry

    @property
    def model_registry(self) -> ModelRegistry:
        """Direct access to model metadata catalog."""
        return self._model_registry

    @property
    def router(self) -> LLMRouter:
        """Direct access to the failover router."""
        return self._router

    @property
    def settings(self) -> LLMSettings:
        return self._settings

    # ------------------------------------------------------------------
    # Generation & Routing
    # ------------------------------------------------------------------

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Execute a generation request with intelligent failover.

        - If request specifies a provider that is unconfigured or unregistered,
          and failover is disabled, raises clear LLMError.
        - Otherwise, routes to the highest-priority eligible provider and
          fails over on rate-limit, quota, or transient error.
        """
        # Apply default generation parameters
        effective_request = self._apply_defaults(request)

        # If a single provider is explicitly targeted and failover is disabled,
        # validate that provider directly for explicit errors.
        metadata = effective_request.metadata or {}
        disallow_failover = metadata.get("disallow_failover", False) or not self._settings.failover_enabled

        if effective_request.provider is not None:
            provider_id = effective_request.provider
            if not self._registry.has(provider_id):
                raise LLMError(
                    code=LLMErrorCode.UNSUPPORTED_PROVIDER,
                    message=f"No adapter registered for provider '{provider_id.value}'.",
                    provider=provider_id,
                )
            adapter = self._registry.get(provider_id)
            if not adapter.is_configured():
                raise LLMError(
                    code=LLMErrorCode.PROVIDER_NOT_CONFIGURED,
                    message=f"Provider '{provider_id.value}' is not fully configured.",
                    provider=provider_id,
                )
            if disallow_failover:
                # Direct delegation when failover is specifically disabled
                return await adapter.generate(effective_request)

        # Route through the intelligent failover coordinator
        return await self._router.route_and_generate(effective_request)

    # ------------------------------------------------------------------
    # Capabilities & Models
    # ------------------------------------------------------------------

    async def get_capabilities(
        self,
        provider: LLMProviderID | None = None,
        model: str | None = None,
    ) -> ModelCapabilities:
        """Return capabilities for a provider/model pair."""
        provider_id = provider or self._settings.default_provider
        if not self._registry.has(provider_id):
            raise LLMError(
                code=LLMErrorCode.UNSUPPORTED_PROVIDER,
                message=f"No adapter registered for provider '{provider_id.value}'.",
                provider=provider_id,
            )
        adapter = self._registry.get(provider_id)
        return await adapter.get_capabilities(model)

    def list_models(self, provider: LLMProviderID | None = None) -> list[ModelMetadata]:
        """List registered models from the model registry."""
        return self._model_registry.list_models(provider)

    # ------------------------------------------------------------------
    # Health & Status
    # ------------------------------------------------------------------

    async def check_health(
        self,
        provider: LLMProviderID | None = None,
    ) -> dict[str, str]:
        """Run low-cost health check pings on configured provider(s)."""
        targets = [provider] if provider is not None else list(LLMProviderID)
        results: dict[str, str] = {}

        for pid in targets:
            if not self._registry.has(pid):
                results[pid.value] = ProviderHealthState.NOT_CONFIGURED.value
                continue
            adapter = self._registry.get(pid)
            if not adapter.is_configured():
                results[pid.value] = ProviderHealthState.NOT_CONFIGURED.value
                continue
            state = await adapter.check_health()
            results[pid.value] = state.value

        return results

    def get_status(self) -> LLMStatusResponse:
        """Build status overview of all configured providers and models."""
        providers: list[ProviderStatusResponse] = []

        for pid in LLMProviderID:
            cfg = self._settings.get_provider_config(pid)
            is_configured = self._settings.is_provider_configured(pid)

            # Get known models from registry
            registered_models = [m.model_id for m in self._model_registry.list_models(pid)]
            if cfg.default_model and cfg.default_model not in registered_models:
                registered_models.insert(0, cfg.default_model)

            # Capabilities for default model
            default_meta = self._model_registry.get_model(pid, cfg.default_model)
            capabilities = default_meta.capabilities

            # Health status from circuit breaker or configuration
            if not cfg.enabled:
                health_state = ProviderHealthState.DISABLED
            elif not is_configured:
                health_state = ProviderHealthState.NOT_CONFIGURED
            else:
                health_state = self._circuit_breaker.get_health_state(pid)
                if health_state == ProviderHealthState.AVAILABLE:
                    health_state = ProviderHealthState.CONFIGURED

            last_error = self._circuit_breaker.get_last_error(pid)

            providers.append(
                ProviderStatusResponse(
                    provider=pid,
                    enabled=cfg.enabled,
                    configured=is_configured,
                    health_status=health_state,
                    default_model=cfg.default_model,
                    available_models=registered_models,
                    capabilities=capabilities,
                    last_error=last_error,
                )
            )

        default_cfg = self._settings.get_provider_config(self._settings.default_provider)

        return LLMStatusResponse(
            default_provider=self._settings.default_provider,
            default_model=default_cfg.default_model,
            failover_enabled=self._settings.failover_enabled,
            provider_priority=self._settings.provider_priority,
            providers=providers,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _apply_defaults(self, request: LLMRequest) -> LLMRequest:
        """Fill in defaults when omitted from request."""
        overrides: dict[str, Any] = {}

        if request.provider is None:
            overrides["provider"] = self._settings.default_provider
        target_provider = overrides.get("provider", request.provider)

        if request.model is None and target_provider is not None:
            overrides["model"] = self._settings.get_default_model(target_provider)

        if request.temperature is None:
            overrides["temperature"] = self._settings.default_temperature
        if request.max_output_tokens is None:
            overrides["max_output_tokens"] = self._settings.default_max_output_tokens
        if request.timeout_seconds is None:
            overrides["timeout_seconds"] = self._settings.default_timeout_seconds

        if overrides:
            return request.model_copy(update=overrides)
        return request


__all__ = [
    "LLMService",
    "build_default_registry",
]
