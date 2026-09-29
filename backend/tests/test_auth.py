from fastapi.testclient import TestClient
import pytest

from app.auth import FirebaseAuthService
from app.main import create_app


class FakeFirebaseAuthService:
    def __init__(self, configured: bool = True) -> None:
        self.configured = configured

    def initialize(self) -> bool:
        return self.configured

    def verify_id_token(self, token: str) -> dict[str, str]:
        if token != "valid-token":
            raise ValueError("invalid token")
        return {
            "uid": "firebase-user-123",
            "email": "user@example.com",
            "name": "Example User",
            "picture": "https://example.com/user.png",
            "sensitive_claim": "must not be returned",
        }


class FakeMongoAdmin:
    def command(self, name: str) -> dict[str, int]:
        return {"ok": 1}


class FakeMongoClient:
    def __init__(self) -> None:
        self.admin = FakeMongoAdmin()

    def close(self) -> None:
        pass


@pytest.fixture(autouse=True)
def mock_mongodb(monkeypatch):
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: FakeMongoClient())


def test_firebase_credentials_convert_literal_newlines(monkeypatch):
    service = FirebaseAuthService("project", "service@example.com", "first\\nsecond")
    captured = {}

    class Certificate:
        def __init__(self, data):
            captured["data"] = data

    class App:
        pass

    monkeypatch.setattr("app.auth.firebase_admin.get_app", lambda: (_ for _ in ()).throw(ValueError("missing")))
    monkeypatch.setattr("app.auth.credentials.Certificate", Certificate)
    monkeypatch.setattr("app.auth.firebase_admin.initialize_app", lambda credential, options: App())

    assert service.initialize() is True
    assert captured["data"]["private_key"] == "first\nsecond"


def test_firebase_missing_credentials_are_unconfigured():
    missing_cases = (
        (("", "email", "key"), "FIREBASE_PROJECT_ID"),
        (("project", "", "key"), "FIREBASE_CLIENT_EMAIL"),
        (("project", "email", ""), "FIREBASE_PRIVATE_KEY"),
    )
    for values, missing_name in missing_cases:
        service = FirebaseAuthService(*values)
        assert service.configured is False
        assert service.initialize() is False
        assert service.missing_configuration == [missing_name]


def test_firebase_successful_initialization_is_healthy(monkeypatch):
    service = FirebaseAuthService("project-id", "service@example.com", "private-key")

    class FakeApp:
        pass

    monkeypatch.setattr("app.auth.firebase_admin.get_app", lambda: (_ for _ in ()).throw(ValueError("missing")))
    monkeypatch.setattr("app.auth.credentials.Certificate", lambda data: object())
    monkeypatch.setattr("app.auth.firebase_admin.initialize_app", lambda credential, options: FakeApp())

    assert service.initialize() is True
    assert service.configured is True
    assert service.failure_reason is None


def test_firebase_initialization_failure_is_retained(monkeypatch):
    service = FirebaseAuthService("project", "service@example.com", "private-key")
    monkeypatch.setattr("app.auth.firebase_admin.get_app", lambda: (_ for _ in ()).throw(ValueError("missing")))
    monkeypatch.setattr("app.auth.credentials.Certificate", lambda data: object())
    monkeypatch.setattr(
        "app.auth.firebase_admin.initialize_app",
        lambda credential, options: (_ for _ in ()).throw(ValueError("invalid credentials")),
    )

    assert service.initialize() is False
    assert str(service.last_error) == "invalid credentials"


def test_auth_endpoint_rejects_missing_token():
    with TestClient(create_app()) as client:
        response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_auth_endpoint_reports_unconfigured_service(monkeypatch):
    monkeypatch.setattr(
        "app.main.FirebaseAuthService",
        lambda **kwargs: FakeFirebaseAuthService(configured=False),
    )

    with TestClient(create_app()) as client:
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer any-token"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication service is not configured"


def test_auth_endpoint_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(
        "app.main.FirebaseAuthService",
        lambda **kwargs: FakeFirebaseAuthService(),
    )

    with TestClient(create_app()) as client:
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token"


def test_auth_endpoint_rejects_malformed_authorization(monkeypatch):
    monkeypatch.setattr(
        "app.main.FirebaseAuthService",
        lambda **kwargs: FakeFirebaseAuthService(),
    )

    with TestClient(create_app()) as client:
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Basic not-a-bearer-token"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_auth_endpoint_returns_safe_verified_claims(monkeypatch):
    monkeypatch.setattr(
        "app.main.FirebaseAuthService",
        lambda **kwargs: FakeFirebaseAuthService(),
    )

    with TestClient(create_app()) as client:
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer valid-token"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "uid": "firebase-user-123",
        "email": "user@example.com",
        "name": "Example User",
        "picture": "https://example.com/user.png",
    }


def test_health_reports_configured_but_uninitialized_firebase(monkeypatch, caplog):
    monkeypatch.setattr(
        "app.main.FirebaseAuthService",
        lambda **kwargs: FirebaseAuthService("project", "service@example.com", "private-key"),
    )
    monkeypatch.setattr("app.auth.firebase_admin.get_app", lambda: (_ for _ in ()).throw(ValueError("missing")))
    monkeypatch.setattr("app.auth.credentials.Certificate", lambda data: object())
    monkeypatch.setattr(
        "app.auth.firebase_admin.initialize_app",
        lambda credential, options: (_ for _ in ()).throw(ValueError("private-key-secret invalid")),
    )

    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.json()["auth"] == {
        "status": "unavailable",
        "reason": "invalid_configuration",
    }
    assert "private-key-secret" not in response.text
    assert "private-key-secret" not in caplog.text


def test_health_reports_initialized_firebase(monkeypatch):
    monkeypatch.setattr(
        "app.main.FirebaseAuthService",
        lambda **kwargs: FirebaseAuthService("project-id", "service@example.com", "private-key"),
    )

    class FakeApp:
        pass

    monkeypatch.setattr("app.auth.firebase_admin.get_app", lambda: (_ for _ in ()).throw(ValueError("missing")))
    monkeypatch.setattr("app.auth.credentials.Certificate", lambda data: object())
    monkeypatch.setattr("app.auth.firebase_admin.initialize_app", lambda credential, options: FakeApp())

    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["auth"] == {"status": "ok"}


def test_health_reports_missing_firebase_configuration_names_only(monkeypatch):
    monkeypatch.setattr(
        "app.main.FirebaseAuthService",
        lambda **kwargs: FirebaseAuthService("", "service@example.com", "private-key-secret"),
    )

    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.json()["auth"] == {
        "status": "unconfigured",
        "reason": "missing_configuration",
        "missing": ["FIREBASE_PROJECT_ID"],
    }
    assert "private-key-secret" not in response.text
    assert "service@example.com" not in response.text
