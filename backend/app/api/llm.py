"""LLM API router.

Exposes endpoints for:
- Reporting configured LLM provider and model status without exposing secrets.
- Listing registered models and verified capability metadata.
- Executing low-cost provider health checks without consuming quota.
- Executing generation requests with intelligent cloud failover.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.config import get_llm_settings
from app.core.llm_config import LLMSettings
from app.schemas.llm import (
    LLMProviderID,
    LLMRequest,
    LLMResponse,
    LLMStatusResponse,
    ModelMetadata,
)
from app.services.llm.service import LLMService

router = APIRouter(prefix="/llm", tags=["llm"])


def get_llm_service(settings: LLMSettings = Depends(get_llm_settings)) -> LLMService:
    """FastAPI dependency that provides a configured ``LLMService``.

    In tests, override this dependency with a fake service.
    """
    return LLMService(settings=settings)


@router.get("/status", response_model=LLMStatusResponse)
def get_llm_status(service: LLMService = Depends(get_llm_service)) -> LLMStatusResponse:
    """Return the configuration status of all LLM providers.

    Reports:
    - Default provider and model.
    - Failover enablement and provider priority.
    - Per-provider enablement, configuration readiness, health state, and models.

    Never returns API keys, secrets, or credential-bearing URLs.
    """
    return service.get_status()


@router.get("/models", response_model=list[ModelMetadata])
def list_models(
    provider: LLMProviderID | None = Query(default=None, description="Optional provider filter"),
    service: LLMService = Depends(get_llm_service),
) -> list[ModelMetadata]:
    """List registered models from the centralized Model Registry."""
    return service.list_models(provider=provider)


@router.post("/health/check")
async def check_llm_health(
    provider: LLMProviderID | None = Query(default=None, description="Optional provider to check"),
    service: LLMService = Depends(get_llm_service),
) -> dict[str, str]:
    """Execute low-cost health checks on configured provider(s).

    Does NOT generate completions or consume significant token quota.
    """
    return await service.check_health(provider=provider)


@router.post("/generate", response_model=LLMResponse)
async def generate_completion(
    request: LLMRequest,
    service: LLMService = Depends(get_llm_service),
) -> LLMResponse:
    """Execute an LLM generation request with intelligent provider failover."""
    return await service.generate(request)


__all__ = ["router", "get_llm_service"]
