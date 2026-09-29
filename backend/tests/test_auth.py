from fastapi.testclient import TestClient

from app.auth import FirebaseAuthService
from app.main import _safe_error_message, create_app


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
    for values in (("", "email", "key"), ("project", "", "key"), ("project", "email", "")):
        service = FirebaseAuthService(*values)
        assert service.configured is False
        assert service.initialize() is False


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


def test_initialization_error_diagnostics_redact_credentials():
    uri = "mongodb+srv://user:password@cluster.example/db?retryWrites=true"
    private_key = "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----"
    message = _safe_error_message(Exception(f"failed for {uri} and {private_key}"), (uri, private_key))

    assert "password" not in message
    assert "secret" not in message
    assert "mongodb+srv://" not in message


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


def test_health_reports_configured_but_uninitialized_firebase(monkeypatch):
    monkeypatch.setattr(
        "app.main.FirebaseAuthService",
        lambda **kwargs: FirebaseAuthService("project", "service@example.com", "private-key"),
    )
    monkeypatch.setattr("app.auth.firebase_admin.get_app", lambda: (_ for _ in ()).throw(ValueError("missing")))
    monkeypatch.setattr("app.auth.credentials.Certificate", lambda data: object())
    monkeypatch.setattr(
        "app.auth.firebase_admin.initialize_app",
        lambda credential, options: (_ for _ in ()).throw(ValueError("private-key invalid")),
    )

    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.json()["auth"]["status"] == "unavailable"
    assert "private-key" not in response.text
