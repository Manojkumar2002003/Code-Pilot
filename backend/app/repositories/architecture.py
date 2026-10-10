from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.architecture import Architecture
from app.schemas.architecture import ArchitectureCreate, ArchitectureUpdate


class ArchitectureRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, project_id: str, architecture_data: ArchitectureCreate) -> Architecture:
        architecture = Architecture(
            project_id=project_id,
            name=architecture_data.name,
            description=architecture_data.description,
            content=architecture_data.content,
        )
        self.session.add(architecture)
        self.session.commit()
        self.session.refresh(architecture)
        return architecture

    def get_by_id(self, architecture_id: str) -> Architecture | None:
        return self.session.get(Architecture, architecture_id)

    def get_by_project_id(self, project_id: str) -> Architecture | None:
        return self.session.execute(
            select(Architecture).where(Architecture.project_id == project_id)
        ).scalars().first()

    def update(self, architecture: Architecture, update_data: ArchitectureUpdate) -> Architecture:
        if update_data.name is not None:
            architecture.name = update_data.name
        if update_data.description is not None:
            architecture.description = update_data.description
        if update_data.content is not None:
            architecture.content = update_data.content

        self.session.add(architecture)
        self.session.commit()
        self.session.refresh(architecture)
        return architecture

    def delete(self, architecture: Architecture) -> bool:
        if architecture is None:
            raise ValueError("Architecture cannot be None.")

        existing = self.session.get(Architecture, architecture.id)
        if existing is None:
            raise ValueError(f"Architecture with id {architecture.id} was not found.")

        self.session.delete(existing)
        self.session.commit()
        return True


__all__ = ["ArchitectureRepository"]
