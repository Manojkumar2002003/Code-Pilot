from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_requirement_returns_201_and_persisted_payload():
    project = client.post('/api/projects', json={'name': 'Requirement API Project', 'description': 'Project for requirements'}).json()
    response = client.post(
        f"/api/projects/{project['id']}/requirements",
        json={
            'title': 'User authentication',
            'description': 'Users must be able to sign in securely.',
            'type': 'functional',
            'priority': 'high',
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body['project_id'] == project['id']
    assert body['title'] == 'User authentication'
    assert body['description'] == 'Users must be able to sign in securely.'
    assert body['type'] == 'functional'
    assert body['priority'] == 'high'
    assert body['status'] == 'draft'
    assert body['id']


def test_list_requirements_for_project_and_project_isolation():
    project_a = client.post('/api/projects', json={'name': 'Project A', 'description': 'Alpha'}).json()
    project_b = client.post('/api/projects', json={'name': 'Project B', 'description': 'Beta'}).json()

    client.post(f"/api/projects/{project_a['id']}/requirements", json={'title': 'Alpha requirement', 'description': 'Alpha body', 'type': 'functional', 'priority': 'medium'})
    client.post(f"/api/projects/{project_b['id']}/requirements", json={'title': 'Beta requirement', 'description': 'Beta body', 'type': 'functional', 'priority': 'low'})

    response = client.get(f"/api/projects/{project_a['id']}/requirements")
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]['title'] == 'Alpha requirement'

    missing = client.get(f"/api/projects/{project_a['id']}/requirements/{client.post(f'/api/projects/{project_b['id']}/requirements', json={'title': 'Other', 'description': 'Other', 'type': 'functional', 'priority': 'high'}).json()['id']}")
    assert missing.status_code == 404


def test_get_patch_and_delete_requirement_in_project_context():
    project = client.post('/api/projects', json={'name': 'Requirement Context Project', 'description': 'Context'}).json()
    created = client.post(
        f"/api/projects/{project['id']}/requirements",
        json={'title': 'Original title', 'description': 'Original description', 'type': 'functional', 'priority': 'medium'},
    ).json()

    retrieve = client.get(f"/api/projects/{project['id']}/requirements/{created['id']}")
    assert retrieve.status_code == 200
    assert retrieve.json()['title'] == 'Original title'

    patch = client.patch(
        f"/api/projects/{project['id']}/requirements/{created['id']}",
        json={'status': 'approved', 'priority': 'critical'},
    )
    assert patch.status_code == 200, patch.text
    patched = patch.json()
    assert patched['status'] == 'approved'
    assert patched['priority'] == 'critical'
    assert patched['title'] == 'Original title'

    delete_response = client.delete(f"/api/projects/{project['id']}/requirements/{created['id']}")
    assert delete_response.status_code == 204

    missing = client.get(f"/api/projects/{project['id']}/requirements/{created['id']}")
    assert missing.status_code == 404


def test_requirement_api_rejects_missing_project_invalid_payloads_and_cross_project_access():
    missing_project = client.post('/api/projects', json={'name': 'Missing Project check', 'description': 'Used to check missing cases'}).json()

    create_missing_project = client.post('/api/projects/does-not-exist/requirements', json={'title': 'Bad', 'description': 'Bad', 'type': 'functional', 'priority': 'medium'})
    assert create_missing_project.status_code == 404

    invalid = client.post(f"/api/projects/{missing_project['id']}/requirements", json={'title': '', 'description': 'Body', 'type': 'functional', 'priority': 'high'})
    assert invalid.status_code == 422

    invalid_type = client.post(f"/api/projects/{missing_project['id']}/requirements", json={'title': 'Bad type', 'description': 'Body', 'type': 'unknown', 'priority': 'high'})
    assert invalid_type.status_code == 422

    project_a = client.post('/api/projects', json={'name': 'A', 'description': 'A'}).json()
    project_b = client.post('/api/projects', json={'name': 'B', 'description': 'B'}).json()
    req = client.post(f"/api/projects/{project_a['id']}/requirements", json={'title': 'Owned', 'description': 'Body', 'type': 'functional', 'priority': 'medium'}).json()

    wrong_project_get = client.get(f"/api/projects/{project_b['id']}/requirements/{req['id']}")
    assert wrong_project_get.status_code == 404

    wrong_project_delete = client.delete(f"/api/projects/{project_b['id']}/requirements/{req['id']}")
    assert wrong_project_delete.status_code == 404
