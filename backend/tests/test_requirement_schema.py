from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import Project, Requirement
from app.schemas.requirement import (
    RequirementCreate,
    RequirementPriority,
    RequirementResponse,
    RequirementStatus,
    RequirementType,
    RequirementUpdate,
)


def test_valid_create_schema_accepts_supported_values():
    payload = {
        'title': '    Manage user profile settings    ',
        'description': 'Users can update their profile information and preferences.',
        'type': 'functional',
        'priority': 'medium',
    }
    requirement = RequirementCreate.model_validate(payload)
    assert requirement.title == 'Manage user profile settings'
    assert requirement.description == 'Users can update their profile information and preferences.'
    assert requirement.type == RequirementType.FUNCTIONAL
    assert requirement.priority == RequirementPriority.MEDIUM


def test_requirement_create_rejects_overlong_title_and_blank_description_values():
    with pytest.raises(ValidationError):
        RequirementCreate.model_validate({
            'title': 'x' * 201,
            'description': 'Body',
            'type': 'functional',
            'priority': 'medium',
        })

    with pytest.raises(ValidationError):
        RequirementCreate.model_validate({
            'title': 'Valid title',
            'description': '',
            'type': 'functional',
            'priority': 'medium',
        })


def test_requirement_status_priority_and_type_enums_are_validated():
    assert RequirementType('functional') == RequirementType.FUNCTIONAL
    assert RequirementType('non_functional') == RequirementType.NON_FUNCTIONAL
    assert RequirementPriority('low') == RequirementPriority.LOW
    assert RequirementStatus('approved') == RequirementStatus.APPROVED

    with pytest.raises(ValueError):
        RequirementType('security')

    with pytest.raises(ValueError):
        RequirementPriority('urgent')

    with pytest.raises(ValueError):
        RequirementStatus('in_progress')


def test_requirement_update_accepts_partial_payloads_and_rejects_immutable_fields():
    updated = RequirementUpdate.model_validate({'description': 'Updated description', 'status': 'rejected'})
    assert updated.description == 'Updated description'
    assert updated.status == RequirementStatus.REJECTED

    with pytest.raises(ValidationError):
        RequirementUpdate.model_validate({'id': 'req-123'})

    with pytest.raises(ValidationError):
        RequirementUpdate.model_validate({'project_id': 'project-321'})

    with pytest.raises(ValidationError):
        RequirementUpdate.model_validate({})


def test_requirement_response_serializes_sqlalchemy_instance():
    project = Project(id='project-123', name='Requirement Schema Project')
    requirement = Requirement(
        project_id=project.id,
        title='Role-based access control',
        description='Only authorized users can edit project settings.',
        type='non_functional',
        priority='critical',
        status='draft',
    )

    response = RequirementResponse.model_validate(requirement)
    assert response.title == 'Role-based access control'
    assert response.project_id == requirement.project_id
    assert response.type == RequirementType.NON_FUNCTIONAL
    assert response.priority == RequirementPriority.CRITICAL
    assert response.status == RequirementStatus.DRAFT
    assert isinstance(response.created_at, datetime)
    assert isinstance(response.updated_at, datetime)


