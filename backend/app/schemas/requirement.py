from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RequirementType(str, Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"


class RequirementPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequirementStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class RequirementBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True, extra="forbid")

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    type: RequirementType = RequirementType.FUNCTIONAL
    priority: RequirementPriority = RequirementPriority.MEDIUM

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Requirement title cannot be empty.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Requirement description cannot be empty.")
        return cleaned


class RequirementCreate(RequirementBase):
    pass


class RequirementUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True, extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    type: RequirementType | None = None
    priority: RequirementPriority | None = None
    status: RequirementStatus | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Requirement title cannot be empty.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Requirement description cannot be empty.")
        return cleaned

    @model_validator(mode="after")
    def ensure_not_empty(self) -> "RequirementUpdate":
        if all(field is None for field in (self.title, self.description, self.type, self.priority, self.status)):
            raise ValueError("At least one requirement field must be provided for update.")
        return self


class RequirementResponse(RequirementBase):
    id: str
    project_id: str
    status: RequirementStatus
    created_at: datetime
    updated_at: datetime


__all__ = [
    "RequirementType",
    "RequirementPriority",
    "RequirementStatus",
    "RequirementBase",
    "RequirementCreate",
    "RequirementUpdate",
    "RequirementResponse",
]
