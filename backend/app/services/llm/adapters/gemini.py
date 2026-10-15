"""Google Gemini cloud LLM provider adapter.

Official API documentation: https://ai.google.dev/gemini-api/docs
REST API reference: https://ai.google.dev/api
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.llm_config import GeminiConfig
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
from app.services.llm.adapters.base import classify_http_error
from app.services.llm.model_registry import get_model_registry
from app.services.llm.provider import BaseLLMProvider


class GeminiAdapter(BaseLLMProvider):
    """Adapter for Google Gemini API."""

    def __init__(
        self,
        config: GeminiConfig,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._http_client = http_client
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def provider_id(self) -> LLMProviderID:
        return LLMProviderID.GEMINI

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
        """Low-cost health check querying the Gemini models list endpoint."""
        if not self.is_configured():
            return ProviderHealthState.NOT_CONFIGURED

        url = f"{self._base_url}/models"
        headers = {
            "x-goog-api-key": self._config.api_key.strip(),
            "Content-Type": "application/json",
        }
        params = {"pageSize": "1"}

        client = self._http_client or httpx.AsyncClient(timeout=10.0)
        try:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                return ProviderHealthState.AVAILABLE
            elif response.status_code in (401, 403):
                return ProviderHealthState.AUTHENTICATION_FAILURE
            elif response.status_code == 429:
                return ProviderHealthState.RATE_LIMITED
            return ProviderHealthState.TEMPORARILY_UNAVAILABLE
        except (httpx.TimeoutException, httpx.NetworkError):
            return ProviderHealthState.TEMPORARILY_UNAVAILABLE
        except Exception:
            return ProviderHealthState.TEMPORARILY_UNAVAILABLE
        finally:
            if self._http_client is None:
                await client.aclose()

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Execute a generation request against the Gemini API."""
        if not self.is_configured():
            raise LLMError(
                code=LLMErrorCode.PROVIDER_NOT_CONFIGURED,
                message="Gemini API key is not configured.",
                provider=self.provider_id,
            )

        model = request.model or self._config.default_model
        url = f"{self._base_url}/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": self._config.api_key.strip(),
            "Content-Type": "application/json",
        }

        # Build request payload
        payload = self._build_payload(request)
        timeout = request.timeout_seconds or 60.0

        start_time = time.perf_counter()
        client = self._http_client or httpx.AsyncClient(timeout=timeout)
        try:
            response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMError(
                code=LLMErrorCode.REQUEST_TIMEOUT,
                message=f"Request to Gemini API timed out after {timeout}s: {exc}",
                provider=self.provider_id,
                model=model,
            ) from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise LLMError(
                code=LLMErrorCode.NETWORK_ERROR,
                message=f"Network error communicating with Gemini API: {exc}",
                provider=self.provider_id,
                model=model,
            ) from exc
        except Exception as exc:
            raise LLMError(
                code=LLMErrorCode.INTERNAL_ERROR,
                message=f"Unexpected error communicating with Gemini API: {exc}",
                provider=self.provider_id,
                model=model,
            ) from exc
        finally:
            if self._http_client is None:
                await client.aclose()

        duration = time.perf_counter() - start_time

        # Check for HTTP errors
        if response.status_code != 200:
            raise classify_http_error(
                status_code=response.status_code,
                response_text=response.text,
                headers=response.headers,
                provider=self.provider_id,
                model=model,
            )

        # Parse response
        try:
            data = response.json()
        except Exception as exc:
            raise LLMError(
                code=LLMErrorCode.INVALID_RESPONSE,
                message="Failed to parse JSON response from Gemini API.",
                provider=self.provider_id,
                model=model,
            ) from exc

        return self._parse_response(data, model, duration, request.metadata)

    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        """Convert standard LLMRequest to Gemini REST format."""
        contents: list[dict[str, Any]] = []

        # Convert messages
        for msg in request.messages:
            # Gemini maps assistant role to 'model'
            role = "model" if msg.role == MessageRole.ASSISTANT else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}],
            })

        payload: dict[str, Any] = {"contents": contents}

        # Handle system instruction
        if request.system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": request.system_instruction}]
            }

        # Handle generation config
        gen_config: dict[str, Any] = {}
        if request.temperature is not None:
            gen_config["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            gen_config["maxOutputTokens"] = request.max_output_tokens

        # Structured output mode
        if request.structured_output is not None:
            gen_config["responseMimeType"] = "application/json"

        if gen_config:
            payload["generationConfig"] = gen_config

        return payload

    def _parse_response(
        self,
        data: dict[str, Any],
        model: str,
        duration: float,
        request_metadata: dict[str, Any] | None,
    ) -> LLMResponse:
        """Parse Gemini response into normalized LLMResponse."""
        candidates = data.get("candidates", [])
        if not candidates:
            # Check prompt feedback for blocking reasons
            feedback = data.get("promptFeedback", {})
            block_reason = feedback.get("blockReason")
            msg = f"No candidates returned by Gemini. Block reason: {block_reason}" if block_reason else "No candidates returned by Gemini."
            raise LLMError(
                code=LLMErrorCode.INVALID_RESPONSE,
                message=msg,
                provider=self.provider_id,
                model=model,
                details={"promptFeedback": feedback},
            )

        first_candidate = candidates[0]
        content_obj = first_candidate.get("content", {})
        parts = content_obj.get("parts", [])
        content_text = "".join(part.get("text", "") for part in parts if "text" in part)
        finish_reason = first_candidate.get("finishReason")

        # Parse usage metadata
        usage_meta = data.get("usageMetadata", {})
        token_usage: TokenUsage | None = None
        if usage_meta:
            token_usage = TokenUsage(
                prompt_tokens=usage_meta.get("promptTokenCount"),
                completion_tokens=usage_meta.get("candidatesTokenCount"),
                total_tokens=usage_meta.get("totalTokenCount"),
            )

        metadata: dict[str, Any] = {"provider": self.provider_id.value}
        if request_metadata:
            metadata.update(request_metadata)
        if "modelVersion" in data:
            metadata["modelVersion"] = data["modelVersion"]

        return LLMResponse(
            content=content_text,
            provider=self.provider_id,
            model=model,
            token_usage=token_usage,
            duration_seconds=round(duration, 3),
            finish_reason=finish_reason,
            structured_output=None,
            metadata=metadata,
        )


__all__ = ["GeminiAdapter"]
