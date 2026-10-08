from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_project_returns_201_and_persisted_payload():
    payload = {'name': 'API Project', 'description': 'Created via API'}
    response = client.post('/api/projects', json=payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body['name'] == 'API Project'
    assert body['description'] == 'Created via API'
    assert body['status'] == 'active'
    assert body['id']
    assert body['created_at']
    assert body['updated_at']


def test_create_project_validation_rejects_invalid_names():
    response = client.post('/api/projects', json={'name': '', 'description': 'Bad request'})
    assert response.status_code == 422

    response = client.post('/api/projects', json={'name': '   ', 'description': 'Bad request'})
    assert response.status_code == 422


def test_list_projects_returns_project_collection():
    response = client.get('/api/projects')
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, list)
    assert len(body) >= 1


def test_get_project_and_patch_project():
    created = client.post('/api/projects', json={'name': 'Patch Project', 'description': 'Before'}).json()
    project_id = created['id']

    response = client.get(f'/api/projects/{project_id}')
    assert response.status_code == 200, response.text
    assert response.json()['name'] == 'Patch Project'

    patch = client.patch(f'/api/projects/{project_id}', json={'name': 'Updated Project', 'status': 'archived'})
    assert patch.status_code == 200, patch.text
    patched = patch.json()
    assert patched['name'] == 'Updated Project'
    assert patched['status'] == 'archived'
    assert patched['description'] == 'Before'


def test_delete_project_returns_204_and_missing_project_returns_404():
    created = client.post('/api/projects', json={'name': 'Delete Project', 'description': 'To remove'}).json()
    delete_response = client.delete(f"/api/projects/{created['id']}")
    assert delete_response.status_code == 204

    missing = client.get(f"/api/projects/{created['id']}")
    assert missing.status_code == 404
