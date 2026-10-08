from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectStatus, ProjectUpdate


class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, project_data: ProjectCreate) -> Project:
        project = Project(
            name=project_data.name,
            description=project_data.description,
            status=ProjectStatus.ACTIVE.value,
        )
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def get_by_id(self, project_id: str) -> Project | None:
        return self.session.get(Project, project_id)

    def list(self) -> Sequence[Project]:
        return self.session.execute(
            select(Project).order_by(Project.created_at.desc())
        ).scalars().all()

    def update(self, project: Project, update_data: ProjectUpdate) -> Project:
        if update_data.name is not None:
            project.name = update_data.name
        if update_data.description is not None:
            project.description = update_data.description
        if update_data.status is not None:
            project.status = update_data.status.value

        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def delete(self, project: Project) -> bool:
        self.session.delete(project)
        self.session.commit()
        return True


__all__ = ['ProjectRepository']
