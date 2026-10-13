from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.repositories.task import TaskRepository
from app.schemas.requirement import RequirementResponse
from app.schemas.task import (
    RequirementAssociationRequest,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.task import TaskService

router = APIRouter(prefix='/projects/{project_id}/tasks', tags=['tasks'])


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    return TaskService(
        TaskRepository(db),
        ProjectRepository(db),
        RequirementRepository(db),
    )



@router.post('', response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary='Create a task')
def create_task(
    project_id: str,
    task_data: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    task = service.create_task(project_id, task_data)
    return TaskResponse.model_validate(task)


@router.get('', response_model=list[TaskResponse], summary='List tasks for a project')
def list_tasks(
    project_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[TaskResponse]:
    tasks = service.list_tasks(project_id)
    return [TaskResponse.model_validate(task) for task in tasks]


@router.get('/{task_id}', response_model=TaskResponse, summary='Get a task in a project context')
def get_task(
    project_id: str,
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    task = service.get_task(project_id, task_id)
    return TaskResponse.model_validate(task)


@router.patch('/{task_id}', response_model=TaskResponse, summary='Update a task')
def update_task(
    project_id: str,
    task_id: str,
    task_data: TaskUpdate,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    task = service.update_task(project_id, task_id, task_data)
    return TaskResponse.model_validate(task)


@router.delete('/{task_id}', status_code=status.HTTP_204_NO_CONTENT, summary='Delete a task')
def delete_task(
    project_id: str,
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> Response:
    service.delete_task(project_id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/{task_id}/requirements', response_model=list[RequirementResponse], summary='List requirements associated with a task')
def list_task_requirements(
    project_id: str,
    task_id: str,
    service: TaskService = Depends(get_task_service),
) -> list[RequirementResponse]:
    requirements = service.list_requirements_for_task(project_id, task_id)
    return [RequirementResponse.model_validate(req) for req in requirements]


@router.post('/{task_id}/requirements', response_model=RequirementResponse, status_code=status.HTTP_201_CREATED, summary='Link a requirement to a task')
def link_requirement_to_task(
    project_id: str,
    task_id: str,
    link_data: RequirementAssociationRequest,
    service: TaskService = Depends(get_task_service),
) -> RequirementResponse:
    requirement = service.link_requirement(project_id, task_id, link_data.requirement_id)
    return RequirementResponse.model_validate(requirement)


@router.post('/{task_id}/requirements/{requirement_id}', response_model=RequirementResponse, status_code=status.HTTP_201_CREATED, summary='Link a requirement to a task by path')
def link_requirement_to_task_by_path(
    project_id: str,
    task_id: str,
    requirement_id: str,
    service: TaskService = Depends(get_task_service),
) -> RequirementResponse:
    requirement = service.link_requirement(project_id, task_id, requirement_id)
    return RequirementResponse.model_validate(requirement)


@router.delete('/{task_id}/requirements/{requirement_id}', status_code=status.HTTP_204_NO_CONTENT, summary='Unlink a requirement from a task')
def unlink_requirement_from_task(
    project_id: str,
    task_id: str,
    requirement_id: str,
    service: TaskService = Depends(get_task_service),
) -> Response:
    service.unlink_requirement(project_id, task_id, requirement_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ['router']

