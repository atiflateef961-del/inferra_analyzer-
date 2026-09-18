from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_ok():
    app = create_app()
    client = TestClient(app)

    response = client.get('/api/health')

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['service'] == 'Inferra AI Backend'
    assert data['environment'] == 'development'


def test_root_endpoint_returns_api_links():
    app = create_app()
    client = TestClient(app)

    response = client.get('/')

    assert response.status_code == 200
    assert response.json() == {
        'service': 'Inferra AI Backend',
        'status': 'ok',
        'docs': '/docs',
        'health': '/api/health',
    }


def test_create_app_uses_environment_configuration(monkeypatch):
    monkeypatch.setenv('APP_NAME', 'Custom Inferra API')
    monkeypatch.setenv('APP_ENV', 'staging')
    monkeypatch.setenv('DEBUG', 'true')

    app = create_app()

    assert app.title == 'Custom Inferra API'
    assert app.debug is True
