from fastapi.testclient import TestClient
from pymongo.errors import ConfigurationError, OperationFailure, PyMongoError, ServerSelectionTimeoutError

from app.config import Settings
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

    empty = MongoDatabase("", "ai_inference", 1000, uri_state="empty")
    empty.last_error = ConfigurationError("empty URI")
    assert empty.failure_reason == "missing_configuration"
    assert empty.missing_configuration == ["MONGODB_URI"]


def test_settings_reads_mongodb_uri_from_process_environment(monkeypatch):
    uri = "mongodb://fake-user:fake-password@example.test/ai_inference"
    monkeypatch.setenv("MONGODB_URI", uri)

    settings = Settings()

    assert settings.mongodb_uri_state == "present"
    assert settings.mongodb_uri_configured is True
    assert settings.mongodb_uri == uri


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
    assert response.json()["database"]["configuration_state"] == "present"


def test_health_reports_absent_mongodb_configuration(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)
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
        "configuration_state": "absent",
        "missing": ["MONGODB_URI"],
    }
    assert client.admin.commands == []


def test_health_reports_empty_mongodb_configuration(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", " \t ")
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
        "configuration_state": "empty",
        "missing": ["MONGODB_URI"],
    }
    assert client.admin.commands == []


def test_nonempty_uri_timeout_is_not_misclassified_as_missing(monkeypatch, caplog):
    uri = "mongodb://fake-user:fake-password@example.test/ai_inference"
    monkeypatch.setenv("MONGODB_URI", uri)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "")
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "")
    client = FakeClient(ServerSelectionTimeoutError("server selection timed out"))
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    with TestClient(create_app()) as test_client:
        response = test_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["database"]["reason"] == "timeout"
    assert response.json()["database"]["configuration_state"] == "present"
    assert "missing" not in response.json()["database"]
    assert uri not in response.text
    assert "reason=timeout configuration_state=present" in caplog.text
    assert uri not in caplog.text


def test_nonempty_uri_authentication_failure_is_classified_and_sanitized(monkeypatch, caplog):
    uri = "mongodb://fake-user:fake-password@example.test/ai_inference"
    monkeypatch.setenv("MONGODB_URI", uri)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "")
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "")
    client = FakeClient(OperationFailure(f"authentication failed for {uri}", code=18))
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    with TestClient(create_app()) as test_client:
        response = test_client.get("/api/health")

    database = response.json()["database"]
    assert database["reason"] == "authentication_failed"
    assert database["configuration_state"] == "present"
    assert "fake-user" not in response.text
    assert "fake-password" not in response.text
    assert "fake-user" not in caplog.text
    assert "fake-password" not in caplog.text


def test_health_diagnostics_do_not_expose_mongodb_uri_or_password(monkeypatch, caplog):
    uri = "mongodb://fake-user:fake-password@example.test/ai_inference"
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
    for secret in (uri, "fake-user", "fake-password"):
        assert secret not in caplog.text
        assert secret not in response.text
