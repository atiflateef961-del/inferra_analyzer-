from fastapi.testclient import TestClient

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
