"""Shared utilities and base helpers for cloud LLM provider adapters."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.schemas.llm import LLMError, LLMErrorCode, LLMProviderID, TokenUsage


def parse_retry_after(headers: httpx.Headers) -> float | None:
    """Extract and parse Retry-After or X-RateLimit-Reset headers into seconds."""
    # 1. Standard Retry-After header (seconds or HTTP date)
    retry_after = headers.get("retry-after")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass

    # 2. X-RateLimit-Reset (epoch timestamp in seconds or milliseconds)
    reset_header = headers.get("x-ratelimit-reset")
    if reset_header:
        try:
            val = float(reset_header)
            # If in milliseconds
            if val > 1_000_000_000_000:
                val /= 1000.0
            # If it's a future epoch timestamp
            now = time.time()
            if val > now:
                return max(0.0, val - now)
            # If it was a relative duration
            return max(0.0, val)
        except ValueError:
            pass

    return None


def classify_http_error(
    status_code: int,
    response_text: str,
    headers: httpx.Headers,
    provider: LLMProviderID,
    model: str | None = None,
) -> LLMError:
    """Classify an HTTP error response into a normalized LLMError."""
    retry_after = parse_retry_after(headers)
    lower_text = response_text.lower()

    # Differentiate 401/403 Authentication vs Permissions
    if status_code in (401, 403):
        return LLMError(
            code=LLMErrorCode.INVALID_CREDENTIALS,
            message=f"Authentication failed for {provider.value} (HTTP {status_code}). Verify configured API key.",
            provider=provider,
            model=model,
            details={"status_code": status_code, "response": response_text[:200]},
            retry_after=retry_after,
        )

    # 402 is returned by OpenRouter and others for insufficient quota / credits
    if status_code == 402:
        return LLMError(
            code=LLMErrorCode.QUOTA_EXHAUSTED,
            message=f"Account quota or credits exhausted for {provider.value} (HTTP 402).",
            provider=provider,
            model=model,
            details={"status_code": status_code, "response": response_text[:200]},
            retry_after=retry_after,
        )

    # 404 Model Not Found
    if status_code == 404:
        return LLMError(
            code=LLMErrorCode.UNSUPPORTED_MODEL,
            message=f"Model '{model}' not found on {provider.value} (HTTP 404).",
            provider=provider,
            model=model,
            details={"status_code": status_code, "response": response_text[:200]},
            retry_after=retry_after,
        )

    # 429 Rate Limit vs Quota Exhausted
    if status_code == 429:
        is_quota = any(term in lower_text for term in ["quota", "credit", "insufficient_quota", "daily limit", "exceeded your current quota"])
        code = LLMErrorCode.QUOTA_EXHAUSTED if is_quota else LLMErrorCode.RATE_LIMIT_EXCEEDED
        msg = (
            f"Quota exhausted for {provider.value} on model '{model}'."
            if is_quota
            else f"Rate limit reached for {provider.value} on model '{model}'."
        )
        return LLMError(
            code=code,
            message=msg,
            provider=provider,
            model=model,
            details={"status_code": status_code, "response": response_text[:200]},
            retry_after=retry_after,
        )

    # 400 Bad Request / Unsupported Parameter
    if status_code == 400:
        return LLMError(
            code=LLMErrorCode.INVALID_REQUEST,
            message=f"Invalid request for {provider.value}: {response_text[:150]}",
            provider=provider,
            model=model,
            details={"status_code": status_code, "response": response_text[:200]},
        )

    # 504 Request Timeout
    if status_code == 504:
        return LLMError(
            code=LLMErrorCode.REQUEST_TIMEOUT,
            message=f"Request timed out upstream at {provider.value} (HTTP 504).",
            provider=provider,
            model=model,
            details={"status_code": status_code},
            retry_after=retry_after,
        )

    # 502 Bad Gateway
    if status_code == 502:
        return LLMError(
            code=LLMErrorCode.NETWORK_ERROR,
            message=f"Bad gateway communicating with {provider.value} (HTTP 502).",
            provider=provider,
            model=model,
            details={"status_code": status_code},
            retry_after=retry_after,
        )

    # 500/503 Outage
    if status_code in (500, 503):
        return LLMError(
            code=LLMErrorCode.PROVIDER_OUTAGE,
            message=f"Service unavailable or outage at {provider.value} (HTTP {status_code}).",
            provider=provider,
            model=model,
            details={"status_code": status_code},
            retry_after=retry_after,
        )

    # Generic catch-all
    return LLMError(
        code=LLMErrorCode.INTERNAL_ERROR,
        message=f"Unexpected HTTP {status_code} error from {provider.value}.",
        provider=provider,
        model=model,
        details={"status_code": status_code, "response": response_text[:200]},
        retry_after=retry_after,
    )


def extract_openai_usage(usage_dict: dict[str, Any] | None) -> TokenUsage | None:
    """Extract standard OpenAI-compatible usage dictionary into TokenUsage."""
    if not usage_dict or not isinstance(usage_dict, dict):
        return None
    return TokenUsage(
        prompt_tokens=usage_dict.get("prompt_tokens"),
        completion_tokens=usage_dict.get("completion_tokens"),
        total_tokens=usage_dict.get("total_tokens"),
    )


__all__ = [
    "parse_retry_after",
    "classify_http_error",
    "extract_openai_usage",
]
