from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_task_returns_201_and_persisted_payload():
    project = client.post(
        '/api/projects',
        json={'name': 'Task API Project', 'description': 'Project for task API testing'},
    ).json()

    response = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={
            'title': 'Implement authentication',
            'description': 'Add secure user authentication to the application.',
            'priority': 'high',
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body['project_id'] == project['id']
    assert body['title'] == 'Implement authentication'
    assert body['description'] == 'Add secure user authentication to the application.'
    assert body['priority'] == 'high'
    assert body['status'] == 'todo'
    assert body['id']
    assert body['created_at']
    assert body['updated_at']


def test_create_task_accepts_initial_status_and_applies_defaults():
    project = client.post(
        '/api/projects',
        json={'name': 'Task Defaults Project', 'description': 'Testing defaults'},
    ).json()

    # Minimal payload: only title provided
    response = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={'title': 'Minimal Task'},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body['title'] == 'Minimal Task'
    assert body['description'] is None
    assert body['priority'] == 'medium'
    assert body['status'] == 'todo'

    # Payload with explicit initial status
    response_in_prog = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={'title': 'In Progress Task', 'status': 'in_progress'},
    )
    assert response_in_prog.status_code == 201, response_in_prog.text
    assert response_in_prog.json()['status'] == 'in_progress'


def test_list_tasks_for_project_and_project_isolation():
    project_a = client.post('/api/projects', json={'name': 'Project A', 'description': 'Alpha'}).json()
    project_b = client.post('/api/projects', json={'name': 'Project B', 'description': 'Beta'}).json()

    # Initially empty list
    empty_list_res = client.get(f"/api/projects/{project_a['id']}/tasks")
    assert empty_list_res.status_code == 200
    assert empty_list_res.json() == []

    # Create tasks in separate projects
    task_a = client.post(
        f"/api/projects/{project_a['id']}/tasks",
        json={'title': 'Task Alpha 1', 'priority': 'low'},
    ).json()
    task_b = client.post(
        f"/api/projects/{project_b['id']}/tasks",
        json={'title': 'Task Beta 1', 'priority': 'critical'},
    ).json()

    res_a = client.get(f"/api/projects/{project_a['id']}/tasks")
    res_b = client.get(f"/api/projects/{project_b['id']}/tasks")

    assert res_a.status_code == 200
    assert res_b.status_code == 200

    items_a = res_a.json()
    items_b = res_b.json()

    assert len(items_a) == 1
    assert items_a[0]['id'] == task_a['id']
    assert items_a[0]['title'] == 'Task Alpha 1'

    assert len(items_b) == 1
    assert items_b[0]['id'] == task_b['id']
    assert items_b[0]['title'] == 'Task Beta 1'


def test_get_patch_and_delete_task_lifecycle():
    project = client.post(
        '/api/projects',
        json={'name': 'Lifecycle Task Project', 'description': 'Testing full task lifecycle'},
    ).json()

    created = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={
            'title': 'Original Task Title',
            'description': 'Original description.',
            'priority': 'medium',
            'status': 'todo',
        },
    ).json()

    # Retrieve task
    retrieve = client.get(f"/api/projects/{project['id']}/tasks/{created['id']}")
    assert retrieve.status_code == 200, retrieve.text
    assert retrieve.json()['title'] == 'Original Task Title'
    assert retrieve.json()['description'] == 'Original description.'

    # Partial update: modify status and priority, omitted title and description must be preserved
    patch = client.patch(
        f"/api/projects/{project['id']}/tasks/{created['id']}",
        json={'status': 'completed', 'priority': 'high'},
    )
    assert patch.status_code == 200, patch.text
    patched = patch.json()
    assert patched['status'] == 'completed'
    assert patched['priority'] == 'high'
    assert patched['title'] == 'Original Task Title'
    assert patched['description'] == 'Original description.'

    # Partial update: modify title only
    patch2 = client.patch(
        f"/api/projects/{project['id']}/tasks/{created['id']}",
        json={'title': 'Updated Title'},
    )
    assert patch2.status_code == 200, patch2.text
    patched2 = patch2.json()
    assert patched2['title'] == 'Updated Title'
    assert patched2['status'] == 'completed'

    # Delete task
    delete_response = client.delete(f"/api/projects/{project['id']}/tasks/{created['id']}")
    assert delete_response.status_code == 204
    assert delete_response.text == ''

    # Subsequent GET returns 404
    after_delete = client.get(f"/api/projects/{project['id']}/tasks/{created['id']}")
    assert after_delete.status_code == 404

    # Parent project is preserved
    project_check = client.get(f"/api/projects/{project['id']}")
    assert project_check.status_code == 200


def test_task_api_validation_rejections():
    project = client.post(
        '/api/projects',
        json={'name': 'Validation Task Project', 'description': 'Validation'},
    ).json()

    # Blank title
    empty_title = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={'title': ''},
    )
    assert empty_title.status_code == 422
    assert empty_title.json()['error']['code'] == 'VALIDATION_ERROR'

    whitespace_title = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={'title': '    '},
    )
    assert whitespace_title.status_code == 422

    # Overlong title (>255)
    overlong_title = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={'title': 'x' * 256},
    )
    assert overlong_title.status_code == 422

    # Unsupported priority
    bad_priority = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={'title': 'Valid Title', 'priority': 'extreme'},
    )
    assert bad_priority.status_code == 422

    # Unsupported status
    bad_status = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={'title': 'Valid Title', 'status': 'agent_running'},
    )
    assert bad_status.status_code == 422

    # Server-managed fields on create
    server_managed_id = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={'title': 'Valid Title', 'id': 'custom-id'},
    )
    assert server_managed_id.status_code == 422

    server_managed_proj_id = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={'title': 'Valid Title', 'project_id': 'custom-proj'},
    )
    assert server_managed_proj_id.status_code == 422

    # Empty update payload
    task = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={'title': 'To be patched'},
    ).json()

    empty_patch = client.patch(
        f"/api/projects/{project['id']}/tasks/{task['id']}",
        json={},
    )
    assert empty_patch.status_code == 422

    # Immutable fields on update
    patch_id = client.patch(
        f"/api/projects/{project['id']}/tasks/{task['id']}",
        json={'id': 'new-id'},
    )
    assert patch_id.status_code == 422

    patch_proj = client.patch(
        f"/api/projects/{project['id']}/tasks/{task['id']}",
        json={'project_id': 'other-proj'},
    )
    assert patch_proj.status_code == 422


def test_task_api_project_isolation_and_error_handling():
    project_a = client.post('/api/projects', json={'name': 'Project A'}).json()
    project_b = client.post('/api/projects', json={'name': 'Project B'}).json()

    task_a = client.post(
        f"/api/projects/{project_a['id']}/tasks",
        json={'title': 'Task of Project A'},
    ).json()

    # Create task for nonexistent project
    create_missing_proj = client.post(
        '/api/projects/nonexistent-proj-id/tasks',
        json={'title': 'Orphan Task'},
    )
    assert create_missing_proj.status_code == 404
    assert create_missing_proj.json()['error']['code'] == 'PROJECT_NOT_FOUND'

    # List tasks for nonexistent project
    list_missing_proj = client.get('/api/projects/nonexistent-proj-id/tasks')
    assert list_missing_proj.status_code == 404
    assert list_missing_proj.json()['error']['code'] == 'PROJECT_NOT_FOUND'

    # Get nonexistent task
    get_missing_task = client.get(f"/api/projects/{project_a['id']}/tasks/nonexistent-task-id")
    assert get_missing_task.status_code == 404
    assert get_missing_task.json()['error']['code'] == 'TASK_NOT_FOUND'

    # Cross-project retrieval
    cross_get = client.get(f"/api/projects/{project_b['id']}/tasks/{task_a['id']}")
    assert cross_get.status_code == 404
    assert cross_get.json()['error']['code'] == 'TASK_PROJECT_MISMATCH'

    # Cross-project update
    cross_patch = client.patch(
        f"/api/projects/{project_b['id']}/tasks/{task_a['id']}",
        json={'title': 'Illegally modified'},
    )
    assert cross_patch.status_code == 404
    assert cross_patch.json()['error']['code'] == 'TASK_PROJECT_MISMATCH'

    # Cross-project delete
    cross_delete = client.delete(f"/api/projects/{project_b['id']}/tasks/{task_a['id']}")
    assert cross_delete.status_code == 404
    assert cross_delete.json()['error']['code'] == 'TASK_PROJECT_MISMATCH'

    # Task is still intact in project A
    check_task = client.get(f"/api/projects/{project_a['id']}/tasks/{task_a['id']}")
    assert check_task.status_code == 200
    assert check_task.json()['title'] == 'Task of Project A'


def test_openapi_schema_contains_task_endpoints():
    response = client.get('/openapi.json')
    assert response.status_code == 200
    schema = response.json()
    paths = schema['paths']

    list_create_path = '/api/projects/{project_id}/tasks'
    item_path = '/api/projects/{project_id}/tasks/{task_id}'

    assert list_create_path in paths
    assert item_path in paths

    assert 'post' in paths[list_create_path]
    assert 'get' in paths[list_create_path]
    assert 'get' in paths[item_path]
    assert 'patch' in paths[item_path]
    assert 'delete' in paths[item_path]

    # Verify tags
    assert 'tasks' in paths[list_create_path]['post']['tags']
    assert 'tasks' in paths[item_path]['patch']['tags']
