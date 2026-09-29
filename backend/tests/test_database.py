from fastapi.testclient import TestClient
from pymongo.errors import ConfigurationError, OperationFailure, PyMongoError, ServerSelectionTimeoutError

from app.database import MongoDatabase
from app.main import create_app


class FakeAdmin:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.commands: list[str] = []

    def command(self, name: str) -> dict[str, int]:
        self.commands.append(name)
        if self.error is not None:
            raise self.error
        return {"ok": 1}


class FakeClient:
    def __init__(self, error: Exception | None = None) -> None:
        self.admin = FakeAdmin(error)
        self.closed = False
        self.databases: dict[str, object] = {}

    def close(self) -> None:
        self.closed = True

    def __getitem__(self, name: str) -> object:
        database = self.databases.setdefault(name, object())
        return database


def test_mongodb_connects_and_closes(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    database = MongoDatabase("mongodb://example", "ai_inference", 1000)

    assert database.connect() is True
    assert database.ping() is True
    assert database.database is client.databases["ai_inference"]

    database.close()

    assert client.closed is True
    assert database.client is None


def test_mongodb_connection_failure_is_graceful(monkeypatch):
    client = FakeClient(PyMongoError("database unavailable"))
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    database = MongoDatabase("mongodb://example", "ai_inference", 1000)

    assert database.connect() is False
    assert database.client is None
    assert database.last_error is not None
    assert client.closed is True
    assert database.ping() is False
    assert database.failure_reason == "connection_failed"


def test_mongodb_failure_reasons_are_classified():
    timeout = MongoDatabase("mongodb://example", "ai_inference", 1000)
    timeout.last_error = ServerSelectionTimeoutError("timed out")
    assert timeout.failure_reason == "timeout"

    authentication = MongoDatabase("mongodb://example", "ai_inference", 1000)
    authentication.last_error = OperationFailure("authentication failed", code=18)
    assert authentication.failure_reason == "authentication_failed"

    invalid = MongoDatabase("not-a-uri", "ai_inference", 1000)
    invalid.last_error = ConfigurationError("invalid URI")
    assert invalid.failure_reason == "invalid_configuration"

    missing = MongoDatabase("mongodb://127.0.0.1:27017", "ai_inference", 1000, uri_configured=False)
    missing.last_error = PyMongoError("could not reach default local instance")
    assert missing.failure_reason == "missing_configuration"
    assert missing.missing_configuration == ["MONGODB_URI"]


def test_mongodb_ping_reconnects_after_startup_failure(monkeypatch):
    unavailable_client = FakeClient(PyMongoError("database unavailable"))
    available_client = FakeClient()
    clients = iter((unavailable_client, available_client))
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: next(clients))

    database = MongoDatabase("mongodb://example", "ai_inference", 1000)

    assert database.connect() is False
    assert database.ping() is True
    assert database.client is available_client


def test_health_reports_database_status_when_connected(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://example")
    client = FakeClient()
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    with TestClient(create_app()) as test_client:
        response = test_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["database"] == {
        "status": "ok",
        "name": "ai_inference",
    }


def test_health_reports_unavailable_database_without_failing_startup(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://example")
    client = FakeClient(PyMongoError("database unavailable"))
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    with TestClient(create_app()) as test_client:
        response = test_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"]["status"] == "unavailable"
    assert response.json()["database"]["reason"] == "connection_failed"


def test_health_reports_missing_mongodb_configuration(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "")
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "")
    client = FakeClient(ServerSelectionTimeoutError("local fallback unavailable"))
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    with TestClient(create_app()) as test_client:
        response = test_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["database"] == {
        "status": "unavailable",
        "name": "ai_inference",
        "reason": "missing_configuration",
        "missing": ["MONGODB_URI"],
    }


def test_health_diagnostics_do_not_expose_mongodb_uri_or_password(monkeypatch, caplog):
    uri = "mongodb+srv://diagnostic-user:diagnostic-password@cluster.example/database"
    monkeypatch.setenv("MONGODB_URI", uri)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "")
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "")
    client = FakeClient(PyMongoError(f"connection failed for {uri}"))
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    with TestClient(create_app()) as test_client:
        response = test_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["database"]["reason"] == "connection_failed"
    assert "diagnostic-user" not in response.text
    assert "diagnostic-password" not in response.text
    assert uri not in caplog.text
