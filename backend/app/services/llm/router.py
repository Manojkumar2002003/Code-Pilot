"""Intelligent cloud LLM provider router and failover coordinator.

Coordinates:
- Configurable provider priority ordering
- Provider eligibility and capability matching (structured JSON, context limits)
- Error classification for failover eligibility
- Circuit breaker state tracking and provider cooldowns
- Bounded retries and total request deadlines
- Failover telemetry recording
"""

from __future__ import annotations

import asyncio
import random
import time

from app.core.llm_config import LLMSettings
from app.schemas.llm import (
    CapabilitySupport,
    FailoverAttemptMetadata,
    FailoverMetadata,
    LLMError,
    LLMErrorCode,
    LLMProviderID,
    LLMRequest,
    LLMResponse,
    ProviderHealthState,
)
from app.services.llm.model_registry import ModelRegistry, get_model_registry
from app.services.llm.registry import LLMProviderRegistry


class CircuitBreaker:
    """In-memory circuit breaker tracking provider health and cooldowns."""

    def __init__(self, default_cooldown_seconds: float = 60.0) -> None:
        self._default_cooldown = default_cooldown_seconds
        # Maps provider_id -> (cooldown_until_timestamp, ProviderHealthState, last_error_message)
        self._states: dict[LLMProviderID, tuple[float, ProviderHealthState, str | None]] = {}

    def record_failure(
        self,
        provider: LLMProviderID,
        error_code: LLMErrorCode,
        error_message: str,
        cooldown_seconds: float | None = None,
    ) -> None:
        """Mark provider with an error state and enter cooldown."""
        cooldown = cooldown_seconds if cooldown_seconds is not None else self._default_cooldown
        until = time.time() + max(1.0, cooldown)

        health_state = ProviderHealthState.TEMPORARILY_UNAVAILABLE
        if error_code == LLMErrorCode.RATE_LIMIT_EXCEEDED:
            health_state = ProviderHealthState.RATE_LIMITED
        elif error_code == LLMErrorCode.QUOTA_EXHAUSTED:
            health_state = ProviderHealthState.QUOTA_EXHAUSTED
        elif error_code == LLMErrorCode.INVALID_CREDENTIALS:
            health_state = ProviderHealthState.AUTHENTICATION_FAILURE
        elif error_code == LLMErrorCode.UNSUPPORTED_MODEL:
            health_state = ProviderHealthState.MODEL_UNAVAILABLE

        self._states[provider] = (until, health_state, error_message)

    def is_available(self, provider: LLMProviderID) -> bool:
        """Return True if the provider is not currently in cooldown."""
        if provider not in self._states:
            return True
        until, _, _ = self._states[provider]
        return time.time() >= until

    def get_health_state(self, provider: LLMProviderID) -> ProviderHealthState:
        """Return current health state of the provider."""
        if provider not in self._states:
            return ProviderHealthState.AVAILABLE
        until, state, _ = self._states[provider]
        if time.time() >= until:
            return ProviderHealthState.AVAILABLE
        return state

    def get_last_error(self, provider: LLMProviderID) -> str | None:
        """Return the last error message recorded for the provider."""
        if provider in self._states:
            return self._states[provider][2]
        return None

    def reset(self, provider: LLMProviderID | None = None) -> None:
        """Clear circuit breaker state for a provider or all providers."""
        if provider is not None:
            self._states.pop(provider, None)
        else:
            self._states.clear()


class LLMRouter:
    """Intelligent failover router executing requests across cloud LLM providers."""

    def __init__(
        self,
        settings: LLMSettings,
        registry: LLMProviderRegistry,
        model_registry: ModelRegistry | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._model_registry = model_registry or get_model_registry()
        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            default_cooldown_seconds=settings.circuit_breaker_cooldown_seconds
        )

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker

    async def route_and_generate(self, request: LLMRequest) -> LLMResponse:
        """Route generation request to the highest priority eligible provider.

        If a failover-eligible error occurs and failover is allowed, gracefully
        transitions to the next eligible provider within configured retry/deadline bounds.
        """
        deadline = time.time() + (request.timeout_seconds or self._settings.total_request_deadline_seconds)
        max_attempts = self._settings.max_failover_attempts
        metadata = request.metadata or {}

        # Check if failover is disabled for this request or globally
        disallow_failover = (
            metadata.get("disallow_failover", False) is True
            or not self._settings.failover_enabled
        )

        # Plan sequence of candidate (provider, model) pairs
        candidates = self._select_candidates(request, disallow_failover=disallow_failover)

        if not candidates:
            raise LLMError(
                code=LLMErrorCode.UNSUPPORTED_PROVIDER,
                message="No eligible or configured LLM providers available satisfying request requirements.",
            )

        initial_provider, initial_model = candidates[0]
        attempts_history: list[FailoverAttemptMetadata] = []
        overall_start_time = time.perf_counter()

        last_error: Exception | None = None
        failover_reason: str | None = None

        for attempt_index, (provider_id, model_id) in enumerate(candidates, start=1):
            if attempt_index > max_attempts:
                break

            # Enforce total request deadline
            if time.time() >= deadline:
                raise LLMError(
                    code=LLMErrorCode.REQUEST_TIMEOUT,
                    message=f"Total request deadline of {self._settings.total_request_deadline_seconds}s exceeded during failover.",
                    provider=provider_id,
                    model=model_id,
                )

            # Build provider-specific concrete request
            provider_req = request.model_copy(
                update={"provider": provider_id, "model": model_id}
            )

            attempt_start = time.perf_counter()
            try:
                adapter = self._registry.get(provider_id)
                response = await adapter.generate(provider_req)
                attempt_duration = time.perf_counter() - attempt_start

                # Record successful attempt
                attempts_history.append(
                    FailoverAttemptMetadata(
                        provider=provider_id,
                        model=model_id,
                        attempt_number=attempt_index,
                        duration_seconds=round(attempt_duration, 3),
                        eligible_for_failover=False,
                    )
                )

                # Reset circuit breaker on success
                self._circuit_breaker.reset(provider_id)

                total_duration = time.perf_counter() - overall_start_time
                failover_occurred = (provider_id != initial_provider or model_id != initial_model)

                # Inject failover telemetry
                failover_telemetry = FailoverMetadata(
                    initial_provider=initial_provider,
                    initial_model=initial_model,
                    final_provider=provider_id,
                    final_model=model_id,
                    total_attempts=attempt_index,
                    failover_occurred=failover_occurred,
                    failover_reason=failover_reason if failover_occurred else None,
                    total_duration_seconds=round(total_duration, 3),
                    attempts=attempts_history,
                )

                resp_meta = dict(response.metadata or {})
                resp_meta["failover"] = failover_telemetry.model_dump()
                return response.model_copy(update={"metadata": resp_meta})

            except LLMError as exc:
                attempt_duration = time.perf_counter() - attempt_start
                last_error = exc
                is_eligible = self._is_error_eligible_for_failover(exc)

                attempts_history.append(
                    FailoverAttemptMetadata(
                        provider=provider_id,
                        model=model_id,
                        attempt_number=attempt_index,
                        duration_seconds=round(attempt_duration, 3),
                        error_code=exc.code.value,
                        error_message=str(exc),
                        eligible_for_failover=is_eligible,
                    )
                )

                # Record in circuit breaker
                retry_after = getattr(exc, "retry_after", None)
                self._circuit_breaker.record_failure(
                    provider=provider_id,
                    error_code=exc.code,
                    error_message=str(exc),
                    cooldown_seconds=retry_after,
                )

                # If failover is not eligible or prohibited, fail immediately
                if disallow_failover or not is_eligible:
                    raise exc

                failover_reason = f"Provider {provider_id.value} failed with {exc.code.value}: {exc}"

                # Brief jittered backoff before trying alternate provider
                jitter = random.uniform(0.05, 0.2)
                await asyncio.sleep(jitter)

            except Exception as exc:
                attempt_duration = time.perf_counter() - attempt_start
                last_error = exc
                attempts_history.append(
                    FailoverAttemptMetadata(
                        provider=provider_id,
                        model=model_id,
                        attempt_number=attempt_index,
                        duration_seconds=round(attempt_duration, 3),
                        error_code="UNEXPECTED_ERROR",
                        error_message=str(exc),
                        eligible_for_failover=False,
                    )
                )
                if disallow_failover:
                    raise

        if last_error is not None:
            if isinstance(last_error, LLMError):
                raise last_error
            raise LLMError(
                code=LLMErrorCode.INTERNAL_ERROR,
                message=f"All failover attempts exhausted. Last failure: {last_error}",
            )

        raise LLMError(
            code=LLMErrorCode.INTERNAL_ERROR,
            message="No generation candidates could be processed.",
        )

    def _select_candidates(
        self,
        request: LLMRequest,
        disallow_failover: bool = False,
    ) -> list[tuple[LLMProviderID, str]]:
        """Determine an ordered list of (provider, model) candidates to attempt."""
        metadata = request.metadata or {}
        allowed_providers = metadata.get("allowed_providers")

        # Start with priority list from settings
        priority_order = list(self._settings.provider_priority)

        # If request explicitly specifies a provider, prioritize it
        if request.provider is not None:
            if request.provider in priority_order:
                priority_order.remove(request.provider)
            priority_order.insert(0, request.provider)

        # If failover is disallowed, only keep the first provider
        if disallow_failover and priority_order:
            priority_order = [priority_order[0]]

        candidates: list[tuple[LLMProviderID, str]] = []

        for provider in priority_order:
            # Check allowed_providers restriction
            if allowed_providers is not None and provider.value not in allowed_providers and provider not in allowed_providers:
                continue

            # Must be registered and configured
            if not self._registry.has(provider):
                continue
            adapter = self._registry.get(provider)
            if not adapter.is_configured():
                continue

            # Resolve model for provider
            if provider == request.provider and request.model:
                model_id = request.model
            else:
                model_id = self._settings.get_default_model(provider)

            # Check circuit breaker availability
            if not self._circuit_breaker.is_available(provider):
                # Only bypass circuit breaker if it was explicitly requested as sole provider
                if request.provider != provider or not disallow_failover:
                    continue

            # Check structured output capability if requested
            if request.structured_output is not None:
                support = self._model_registry.supports_capability(
                    provider, model_id, "structured_json_output"
                )
                if support == CapabilitySupport.UNSUPPORTED:
                    continue

            # Check context window size if prompt length is estimated
            estimated_tokens = metadata.get("estimated_tokens")
            if estimated_tokens is not None and isinstance(estimated_tokens, int):
                if not self._model_registry.fits_context(provider, model_id, estimated_tokens):
                    continue

            candidates.append((provider, model_id))

        return candidates

    def _is_error_eligible_for_failover(self, error: LLMError) -> bool:
        """Classify whether an error should trigger automatic failover."""
        # Rate limits, quota limits, timeouts, network errors, outages, and model unavailable trigger failover
        eligible_codes = {
            LLMErrorCode.RATE_LIMIT_EXCEEDED,
            LLMErrorCode.QUOTA_EXHAUSTED,
            LLMErrorCode.REQUEST_TIMEOUT,
            LLMErrorCode.NETWORK_ERROR,
            LLMErrorCode.PROVIDER_OUTAGE,
            LLMErrorCode.UNSUPPORTED_MODEL,
        }
        return error.code in eligible_codes


__all__ = [
    "CircuitBreaker",
    "LLMRouter",
]
