from __future__ import annotations

from collections.abc import Sequence

from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectStatus, ProjectUpdate


class ProjectNotFoundError(Exception):
    def __init__(self, project_id: str):
        super().__init__(f'Project with id {project_id} was not found.')
        self.project_id = project_id


class ProjectService:
    def __init__(self, repository: ProjectRepository):
        self.repository = repository

    def create_project(self, project_data: ProjectCreate) -> Project:
        return self.repository.create(project_data)

    def get_project(self, project_id: str) -> Project:
        project = self.repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)
        return project

    def list_projects(self) -> Sequence[Project]:
        return self.repository.list()

    def update_project(self, project_id: str, project_data: ProjectUpdate) -> Project:
        project = self.get_project(project_id)
        return self.repository.update(project, project_data)

    def delete_project(self, project_id: str) -> bool:
        project = self.get_project(project_id)
        return self.repository.delete(project)


__all__ = ['ProjectNotFoundError', 'ProjectService']
