from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True, extra="forbid")

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Task title cannot be empty.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None


class TaskCreate(TaskBase):
    requirement_ids: list[str] | None = Field(default=None)


class TaskUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True, extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    requirement_ids: list[str] | None = Field(default=None)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Task title cannot be empty.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None

    @model_validator(mode="after")
    def ensure_not_empty(self) -> TaskUpdate:
        if all(field is None for field in (self.title, self.description, self.status, self.priority, self.requirement_ids)):
            raise ValueError("At least one task field must be provided for update.")
        return self


class RequirementAssociationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    requirement_id: str = Field(..., min_length=1)


class TaskResponse(TaskBase):
    id: str
    project_id: str
    requirement_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


__all__ = [
    "TaskPriority",
    "TaskStatus",
    "TaskBase",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "RequirementAssociationRequest",
]

