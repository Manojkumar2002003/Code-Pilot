"""Groq cloud LLM provider adapter.

Official API documentation: https://console.groq.com/docs
Supported models: https://console.groq.com/docs/models
Rate limits: https://console.groq.com/docs/rate-limits
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.llm_config import GroqConfig
from app.schemas.llm import (
    LLMError,
    LLMErrorCode,
    LLMProviderID,
    LLMRequest,
    LLMResponse,
    MessageRole,
    ModelCapabilities,
    ProviderHealthState,
)
from app.services.llm.adapters.base import classify_http_error, extract_openai_usage
from app.services.llm.model_registry import get_model_registry
from app.services.llm.provider import BaseLLMProvider


class GroqAdapter(BaseLLMProvider):
    """Adapter for Groq LPU cloud inference API."""

    def __init__(
        self,
        config: GroqConfig,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._http_client = http_client

    @property
    def provider_id(self) -> LLMProviderID:
        return LLMProviderID.GROQ

    def is_configured(self) -> bool:
        return (
            self._config.enabled
            and self._config.api_key is not None
            and len(self._config.api_key.strip()) > 0
        )

    async def get_capabilities(self, model: str | None = None) -> ModelCapabilities:
        target_model = model or self._config.default_model
        model_meta = get_model_registry().get_model(self.provider_id, target_model)
        return model_meta.capabilities

    async def check_health(self) -> ProviderHealthState:
        """Low-cost health check querying the Groq models endpoint."""
        if not self.is_configured():
            return ProviderHealthState.NOT_CONFIGURED

        base = self._config.base_url.rstrip("/")
        url = f"{base}/models"
        headers = {
            "Authorization": f"Bearer {self._config.api_key.strip()}",
            "Content-Type": "application/json",
        }

        client = self._http_client or httpx.AsyncClient(timeout=10.0)
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return ProviderHealthState.AVAILABLE
            elif response.status_code in (401, 403):
                return ProviderHealthState.AUTHENTICATION_FAILURE
            elif response.status_code == 429:
                return ProviderHealthState.RATE_LIMITED
            return ProviderHealthState.TEMPORARILY_UNAVAILABLE
        except Exception:
            return ProviderHealthState.TEMPORARILY_UNAVAILABLE
        finally:
            if self._http_client is None:
                await client.aclose()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Execute a generation request against the Groq API."""
        if not self.is_configured():
            raise LLMError(
                code=LLMErrorCode.PROVIDER_NOT_CONFIGURED,
                message="Groq API key is not configured.",
                provider=self.provider_id,
            )

        model = request.model or self._config.default_model
        base = self._config.base_url.rstrip("/")
        url = f"{base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._config.api_key.strip()}",
            "Content-Type": "application/json",
        }

        payload = self._build_payload(request, model)
        timeout = request.timeout_seconds or 60.0

        start_time = time.perf_counter()
        client = self._http_client or httpx.AsyncClient(timeout=timeout)
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMError(
                code=LLMErrorCode.REQUEST_TIMEOUT,
                message=f"Request to Groq timed out after {timeout}s: {exc}",
                provider=self.provider_id,
                model=model,
            ) from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise LLMError(
                code=LLMErrorCode.NETWORK_ERROR,
                message=f"Network error communicating with Groq: {exc}",
                provider=self.provider_id,
                model=model,
            ) from exc
        except Exception as exc:
            raise LLMError(
                code=LLMErrorCode.INTERNAL_ERROR,
                message=f"Unexpected error communicating with Groq: {exc}",
                provider=self.provider_id,
                model=model,
            ) from exc
        finally:
            if self._http_client is None:
                await client.aclose()

        duration = time.perf_counter() - start_time

        if response.status_code != 200:
            raise classify_http_error(
                status_code=response.status_code,
                response_text=response.text,
                headers=response.headers,
                provider=self.provider_id,
                model=model,
            )

        try:
            data = response.json()
        except Exception as exc:
            raise LLMError(
                code=LLMErrorCode.INVALID_RESPONSE,
                message="Failed to parse JSON response from Groq.",
                provider=self.provider_id,
                model=model,
            ) from exc

        return self._parse_response(data, model, duration, request.metadata)

    def _build_payload(self, request: LLMRequest, model: str) -> dict[str, Any]:
        """Convert standard LLMRequest to Groq OpenAI-compatible payload."""
        messages: list[dict[str, str]] = []

        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})

        for msg in request.messages:
            role_str = "user" if msg.role == MessageRole.USER else ("assistant" if msg.role == MessageRole.ASSISTANT else "system")
            messages.append({"role": role_str, "content": msg.content})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens

        if request.structured_output is not None:
            payload["response_format"] = {"type": "json_object"}

        return payload

    def _parse_response(
        self,
        data: dict[str, Any],
        model: str,
        duration: float,
        request_metadata: dict[str, Any] | None,
    ) -> LLMResponse:
        """Parse Groq response into normalized LLMResponse."""
        choices = data.get("choices", [])
        if not choices:
            raise LLMError(
                code=LLMErrorCode.INVALID_RESPONSE,
                message="Groq returned response with no choices.",
                provider=self.provider_id,
                model=model,
                details={"data": data},
            )

        choice = choices[0]
        msg = choice.get("message", {})
        content = msg.get("content", "")
        finish_reason = choice.get("finish_reason")
        token_usage = extract_openai_usage(data.get("usage"))

        metadata: dict[str, Any] = {"provider": self.provider_id.value}
        if request_metadata:
            metadata.update(request_metadata)
        if "id" in data:
            metadata["groq_id"] = data["id"]

        return LLMResponse(
            content=content,
            provider=self.provider_id,
            model=model,
            token_usage=token_usage,
            duration_seconds=round(duration, 3),
            finish_reason=finish_reason,
            structured_output=None,
            metadata=metadata,
        )


__all__ = ["GroqAdapter"]
