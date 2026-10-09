from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.requirement import Requirement
from app.schemas.requirement import RequirementCreate, RequirementUpdate


class RequirementRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, project_id: str, requirement_data: RequirementCreate) -> Requirement:
        requirement = Requirement(
            project_id=project_id,
            title=requirement_data.title,
            description=requirement_data.description,
            type=requirement_data.type.value,
            priority=requirement_data.priority.value,
            status='draft',
        )
        self.session.add(requirement)
        self.session.commit()
        self.session.refresh(requirement)
        return requirement

    def get_by_id(self, requirement_id: str) -> Requirement | None:
        return self.session.get(Requirement, requirement_id)

    def list_by_project(self, project_id: str) -> Sequence[Requirement]:
        return self.session.execute(
            select(Requirement)
            .where(Requirement.project_id == project_id)
            .order_by(Requirement.created_at.desc(), Requirement.id.desc())
        ).scalars().all()

    def update(self, requirement: Requirement, update_data: RequirementUpdate) -> Requirement:
        if update_data.title is not None:
            requirement.title = update_data.title
        if update_data.description is not None:
            requirement.description = update_data.description
        if update_data.type is not None:
            requirement.type = update_data.type.value
        if update_data.priority is not None:
            requirement.priority = update_data.priority.value
        if update_data.status is not None:
            requirement.status = update_data.status.value

        self.session.add(requirement)
        self.session.commit()
        self.session.refresh(requirement)
        return requirement

    def delete(self, requirement: Requirement) -> bool:
        if requirement is None:
            raise ValueError('Requirement cannot be None.')

        existing = self.session.get(Requirement, requirement.id)
        if existing is None:
            raise ValueError(f'Requirement with id {requirement.id} was not found.')

        self.session.delete(existing)
        self.session.commit()
        return True


__all__ = ['RequirementRepository']
