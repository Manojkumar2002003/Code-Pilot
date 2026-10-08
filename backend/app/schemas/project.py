from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True, extra='forbid')

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Project name cannot be empty.')
        return cleaned

    @field_validator('description', mode='before')
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError('Project description must be a string.')

        cleaned = value.strip()
        return cleaned or None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True, extra='forbid')

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    status: ProjectStatus | None = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError('Project name cannot be empty.')
        return cleaned

    @field_validator('description', mode='before')
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError('Project description must be a string.')

        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode='after')
    def ensure_not_empty(self) -> 'ProjectUpdate':
        if self.name is None and self.description is None and self.status is None:
            raise ValueError('At least one project field must be provided for update.')
        return self


class ProjectResponse(ProjectBase):
    id: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


__all__ = ['ProjectStatus', 'ProjectBase', 'ProjectCreate', 'ProjectUpdate', 'ProjectResponse']
