from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_architecture_returns_201_and_persisted_payload():
    project = client.post(
        '/api/projects',
        json={'name': 'Architecture API Project', 'description': 'Project for arch API testing'},
    ).json()

    response = client.post(
        f"/api/projects/{project['id']}/architecture",
        json={
            'name': 'Hexagonal Service Architecture',
            'description': 'Ports and adapters model for service isolation.',
            'content': {
                'pattern': 'hexagonal',
                'components': ['domain', 'ports', 'adapters'],
                'connections': [{'from': 'ports', 'to': 'domain'}],
            },
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body['project_id'] == project['id']
    assert body['name'] == 'Hexagonal Service Architecture'
    assert body['description'] == 'Ports and adapters model for service isolation.'
    assert body['content'] == {
        'pattern': 'hexagonal',
        'components': ['domain', 'ports', 'adapters'],
        'connections': [{'from': 'ports', 'to': 'domain'}],
    }
    assert body['id']
    assert body['created_at']
    assert body['updated_at']


def test_get_patch_and_delete_architecture_lifecycle():
    project = client.post(
        '/api/projects',
        json={'name': 'Lifecycle Architecture Project', 'description': 'Lifecycle testing'},
    ).json()

    # Initially, getting architecture returns 404 (no architecture yet)
    initial_get = client.get(f"/api/projects/{project['id']}/architecture")
    assert initial_get.status_code == 404
    assert initial_get.json()['error']['code'] == 'ARCHITECTURE_NOT_FOUND'

    # Create architecture
    client.post(
        f"/api/projects/{project['id']}/architecture",
        json={
            'name': 'Original Architecture',
            'description': 'Original description.',
            'content': {'v': 1},
        },
    )

    # Retrieve architecture
    retrieve = client.get(f"/api/projects/{project['id']}/architecture")
    assert retrieve.status_code == 200, retrieve.text
    retrieved_body = retrieve.json()
    assert retrieved_body['name'] == 'Original Architecture'
    assert retrieved_body['description'] == 'Original description.'
    assert retrieved_body['content'] == {'v': 1}

    # Partially update architecture
    patch = client.patch(
        f"/api/projects/{project['id']}/architecture",
        json={
            'name': 'Updated Architecture Name',
            'content': {'v': 2, 'cached': True},
        },
    )
    assert patch.status_code == 200, patch.text
    patched_body = patch.json()
    assert patched_body['name'] == 'Updated Architecture Name'
    assert patched_body['description'] == 'Original description.'
    assert patched_body['content'] == {'v': 2, 'cached': True}

    # Delete architecture
    delete_response = client.delete(f"/api/projects/{project['id']}/architecture")
    assert delete_response.status_code == 204

    # Subsequent GET returns 404
    after_delete_get = client.get(f"/api/projects/{project['id']}/architecture")
    assert after_delete_get.status_code == 404

    # Parent project still exists and was not deleted
    project_check = client.get(f"/api/projects/{project['id']}")
    assert project_check.status_code == 200


def test_reject_duplicate_architecture_creation_returns_409():
    project = client.post(
        '/api/projects',
        json={'name': 'Conflict Project', 'description': 'Testing 409 conflict'},
    ).json()

    first = client.post(
        f"/api/projects/{project['id']}/architecture",
        json={'name': 'First Architecture'},
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/projects/{project['id']}/architecture",
        json={'name': 'Second Architecture'},
    )
    assert second.status_code == 409, second.text
    assert second.json()['error']['code'] == 'ARCHITECTURE_ALREADY_EXISTS'


def test_architecture_api_project_isolation():
    project_a = client.post('/api/projects', json={'name': 'Isolation A'}).json()
    project_b = client.post('/api/projects', json={'name': 'Isolation B'}).json()

    client.post(
        f"/api/projects/{project_a['id']}/architecture",
        json={'name': 'Architecture Alpha', 'content': {'owner': 'Team A'}},
    )
    client.post(
        f"/api/projects/{project_b['id']}/architecture",
        json={'name': 'Architecture Beta', 'content': {'owner': 'Team B'}},
    )

    res_a = client.get(f"/api/projects/{project_a['id']}/architecture")
    res_b = client.get(f"/api/projects/{project_b['id']}/architecture")

    assert res_a.status_code == 200
    assert res_b.status_code == 200
    assert res_a.json()['name'] == 'Architecture Alpha'
    assert res_a.json()['content'] == {'owner': 'Team A'}
    assert res_b.json()['name'] == 'Architecture Beta'
    assert res_b.json()['content'] == {'owner': 'Team B'}


def test_architecture_api_error_handling():
    # Nonexistent project
    create_missing_proj = client.post(
        '/api/projects/nonexistent-project-uuid/architecture',
        json={'name': 'Orphan'},
    )
    assert create_missing_proj.status_code == 404
    assert create_missing_proj.json()['error']['code'] == 'PROJECT_NOT_FOUND'

    get_missing_proj = client.get('/api/projects/nonexistent-project-uuid/architecture')
    assert get_missing_proj.status_code == 404
    assert get_missing_proj.json()['error']['code'] == 'PROJECT_NOT_FOUND'

    patch_missing_proj = client.patch(
        '/api/projects/nonexistent-project-uuid/architecture',
        json={'name': 'Updated'},
    )
    assert patch_missing_proj.status_code == 404
    assert patch_missing_proj.json()['error']['code'] == 'PROJECT_NOT_FOUND'

    delete_missing_proj = client.delete('/api/projects/nonexistent-project-uuid/architecture')
    assert delete_missing_proj.status_code == 404
    assert delete_missing_proj.json()['error']['code'] == 'PROJECT_NOT_FOUND'

    # Project exists, but no architecture
    existing_proj = client.post('/api/projects', json={'name': 'Empty Project'}).json()

    patch_missing_arch = client.patch(
        f"/api/projects/{existing_proj['id']}/architecture",
        json={'name': 'Updated'},
    )
    assert patch_missing_arch.status_code == 404
    assert patch_missing_arch.json()['error']['code'] == 'ARCHITECTURE_NOT_FOUND'

    delete_missing_arch = client.delete(f"/api/projects/{existing_proj['id']}/architecture")
    assert delete_missing_arch.status_code == 404
    assert delete_missing_arch.json()['error']['code'] == 'ARCHITECTURE_NOT_FOUND'

    # Validation errors (422)
    empty_name = client.post(
        f"/api/projects/{existing_proj['id']}/architecture",
        json={'name': '   '},
    )
    assert empty_name.status_code == 422

    missing_name = client.post(
        f"/api/projects/{existing_proj['id']}/architecture",
        json={'description': 'Only description'},
    )
    assert missing_name.status_code == 422

    server_managed_field = client.post(
        f"/api/projects/{existing_proj['id']}/architecture",
        json={'name': 'Valid', 'id': 'forbidden-id'},
    )
    assert server_managed_field.status_code == 422

    empty_patch = client.patch(
        f"/api/projects/{existing_proj['id']}/architecture",
        json={},
    )
    assert empty_patch.status_code == 422


def test_openapi_schema_contains_architecture_endpoints():
    response = client.get('/openapi.json')
    assert response.status_code == 200
    schema = response.json()
    paths = schema['paths']

    assert '/api/projects/{project_id}/architecture' in paths
    arch_methods = paths['/api/projects/{project_id}/architecture']
    assert 'post' in arch_methods
    assert 'get' in arch_methods
    assert 'patch' in arch_methods
    assert 'delete' in arch_methods
