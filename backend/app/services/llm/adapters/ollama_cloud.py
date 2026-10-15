"""Ollama Cloud hosted LLM provider adapter.

Official API documentation: https://docs.ollama.com/
Cloud models catalog: https://ollama.com/search?c=cloud

IMPORTANT: This adapter exclusively communicates with hosted Ollama Cloud inference services.
Local Ollama instances, localhost endpoints, and locally downloaded models are strictly prohibited.
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.llm_config import OllamaCloudConfig
from app.schemas.llm import (
    LLMError,
    LLMErrorCode,
    LLMProviderID,
    LLMRequest,
    LLMResponse,
    MessageRole,
    ModelCapabilities,
    ProviderHealthState,
    TokenUsage,
)
from app.services.llm.adapters.base import classify_http_error, extract_openai_usage
from app.services.llm.model_registry import get_model_registry
from app.services.llm.provider import BaseLLMProvider


class OllamaCloudAdapter(BaseLLMProvider):
    """Adapter for hosted Ollama Cloud inference service."""

    def __init__(
        self,
        config: OllamaCloudConfig,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._http_client = http_client
        self._validate_cloud_endpoint(config.base_url)

    @property
    def provider_id(self) -> LLMProviderID:
        return LLMProviderID.OLLAMA_CLOUD

    def _validate_cloud_endpoint(self, url: str) -> None:
        """Enforce that Ollama Cloud is a remote cloud endpoint, never localhost."""
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or hostname.startswith("192.168.") or hostname.startswith("10."):
            raise LLMError(
                code=LLMErrorCode.INVALID_REQUEST,
                message="Local Ollama endpoints are not supported. CodePilot requires hosted Ollama Cloud inference.",
                provider=self.provider_id,
            )

    def is_configured(self) -> bool:
        if not self._config.enabled or not self._config.api_key:
            return False
        if len(self._config.api_key.strip()) == 0:
            return False
        try:
            self._validate_cloud_endpoint(self._config.base_url)
            return True
        except LLMError:
            return False

    async def get_capabilities(self, model: str | None = None) -> ModelCapabilities:
        target_model = model or self._config.default_model
        model_meta = get_model_registry().get_model(self.provider_id, target_model)
        return model_meta.capabilities

    async def check_health(self) -> ProviderHealthState:
        """Low-cost health check querying the Ollama Cloud tags endpoint."""
        if not self.is_configured():
            return ProviderHealthState.NOT_CONFIGURED

        try:
            self._validate_cloud_endpoint(self._config.base_url)
        except LLMError:
            return ProviderHealthState.TEMPORARILY_UNAVAILABLE

        base = self._config.base_url.rstrip("/")
        url = f"{base}/api/tags"
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
        """Execute a generation request against the Ollama Cloud service."""
        if not self.is_configured():
            raise LLMError(
                code=LLMErrorCode.PROVIDER_NOT_CONFIGURED,
                message="Ollama Cloud API key is not configured or endpoint is invalid.",
                provider=self.provider_id,
            )

        self._validate_cloud_endpoint(self._config.base_url)

        model = request.model or self._config.default_model
        base = self._config.base_url.rstrip("/")
        is_openai_compat = base.endswith("/v1")
        url = f"{base}/chat/completions" if is_openai_compat else f"{base}/api/chat"

        headers = {
            "Authorization": f"Bearer {self._config.api_key.strip()}",
            "Content-Type": "application/json",
        }

        payload = (
            self._build_openai_payload(request, model)
            if is_openai_compat
            else self._build_native_payload(request, model)
        )
        timeout = request.timeout_seconds or 60.0

        start_time = time.perf_counter()
        client = self._http_client or httpx.AsyncClient(timeout=timeout)
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMError(
                code=LLMErrorCode.REQUEST_TIMEOUT,
                message=f"Request to Ollama Cloud timed out after {timeout}s: {exc}",
                provider=self.provider_id,
                model=model,
            ) from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise LLMError(
                code=LLMErrorCode.NETWORK_ERROR,
                message=f"Network error communicating with Ollama Cloud: {exc}",
                provider=self.provider_id,
                model=model,
            ) from exc
        except Exception as exc:
            raise LLMError(
                code=LLMErrorCode.INTERNAL_ERROR,
                message=f"Unexpected error communicating with Ollama Cloud: {exc}",
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
                message="Failed to parse JSON response from Ollama Cloud.",
                provider=self.provider_id,
                model=model,
            ) from exc

        return (
            self._parse_openai_response(data, model, duration, request.metadata)
            if is_openai_compat
            else self._parse_native_response(data, model, duration, request.metadata)
        )

    def _build_native_payload(self, request: LLMRequest, model: str) -> dict[str, Any]:
        """Build native Ollama /api/chat payload."""
        messages: list[dict[str, str]] = []

        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})

        for msg in request.messages:
            role_str = "user" if msg.role == MessageRole.USER else ("assistant" if msg.role == MessageRole.ASSISTANT else "system")
            messages.append({"role": role_str, "content": msg.content})

        options: dict[str, Any] = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            options["num_predict"] = request.max_output_tokens

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options

        if request.structured_output is not None:
            payload["format"] = "json"

        return payload

    def _build_openai_payload(self, request: LLMRequest, model: str) -> dict[str, Any]:
        """Build OpenAI-compatible payload for /v1/chat/completions."""
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

    def _parse_native_response(
        self,
        data: dict[str, Any],
        model: str,
        duration: float,
        request_metadata: dict[str, Any] | None,
    ) -> LLMResponse:
        """Parse native Ollama /api/chat response."""
        msg = data.get("message", {})
        content = msg.get("content", "")
        finish_reason = data.get("done_reason") or ("stop" if data.get("done") else None)

        prompt_tokens = data.get("prompt_eval_count")
        completion_tokens = data.get("eval_count")
        total_tokens = None
        if prompt_tokens is not None or completion_tokens is not None:
            total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

        token_usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        metadata: dict[str, Any] = {"provider": self.provider_id.value}
        if request_metadata:
            metadata.update(request_metadata)
        if "total_duration" in data:
            metadata["ollama_total_duration_ns"] = data["total_duration"]

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

    def _parse_openai_response(
        self,
        data: dict[str, Any],
        model: str,
        duration: float,
        request_metadata: dict[str, Any] | None,
    ) -> LLMResponse:
        """Parse /v1/chat/completions response."""
        choices = data.get("choices", [])
        if not choices:
            raise LLMError(
                code=LLMErrorCode.INVALID_RESPONSE,
                message="Ollama Cloud returned response with no choices.",
                provider=self.provider_id,
                model=model,
            )

        choice = choices[0]
        msg = choice.get("message", {})
        content = msg.get("content", "")
        finish_reason = choice.get("finish_reason")
        token_usage = extract_openai_usage(data.get("usage"))

        metadata: dict[str, Any] = {"provider": self.provider_id.value}
        if request_metadata:
            metadata.update(request_metadata)

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


__all__ = ["OllamaCloudAdapter"]
