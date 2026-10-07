from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint_returns_status_message():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "CodePilot backend is running"}


def test_health_endpoint_returns_service_status():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "codepilot-api"}


def test_dependency_health_endpoint_returns_dependency_status():
    response = client.get('/api/health/dependencies')
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] in {'healthy', 'degraded'}
    assert payload['environment'] == 'development'
    assert payload['service'] == 'codepilot-api'
    assert payload['dependencies']['backend']['status'] == 'healthy'
    assert payload['dependencies']['database']['status'] in {'healthy', 'unhealthy'}
    assert payload['dependencies']['database']['type'] == 'sqlite'


def test_dependency_health_endpoint_reports_unhealthy_database(monkeypatch):
    import app.services.health_service as health_service

    monkeypatch.setattr(health_service, 'check_database_connection', lambda: False)

    payload = health_service.get_dependency_health().model_dump()

    assert payload['status'] == 'degraded'
    assert payload['dependencies']['database']['status'] == 'unhealthy'


def test_not_found_returns_standard_error_payload():
    response = client.get('/definitely-not-real')
    assert response.status_code == 404
    payload = response.json()
    assert payload['error']['code'] == 'HTTP_ERROR'
    assert 'not found' in payload['error']['message'].lower()


def test_validation_errors_return_standard_error_payload():
    def debug_value(item_id: int):
        return {'item_id': item_id}

    app.add_api_route('/debug-validation/{item_id}', debug_value, methods=['GET'])

    response = client.get('/debug-validation/not-a-number')
    assert response.status_code == 422
    payload = response.json()
    assert payload['error']['code'] == 'VALIDATION_ERROR'
    assert 'validation failed' in payload['error']['message'].lower()


def test_unhandled_exception_returns_safe_server_error():
    def raise_error():
        raise RuntimeError('explode')

    app.add_api_route('/debug-error', raise_error, methods=['GET'])

    response = client.get('/debug-error')
    assert response.status_code == 500
    payload = response.json()
    assert payload['error']['code'] == 'INTERNAL_SERVER_ERROR'
    assert payload['error']['message'] == 'An unexpected server error occurred.'
