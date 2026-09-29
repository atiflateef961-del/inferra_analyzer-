from fastapi.testclient import TestClient
from pymongo.errors import ConfigurationError, OperationFailure, PyMongoError, ServerSelectionTimeoutError

from app.config import Settings
from app.database import MongoDatabase, mongodb_uri_diagnostics
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
    assert database.failure_diagnostic is None
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
    assert database.failure_diagnostic == {
        "error_type": "PyMongoError",
        "message": "database unavailable",
    }
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


def test_settings_trims_uri_and_records_outer_whitespace(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "  mongodb://user:secret@db.example/test  ")

    settings = Settings()

    assert settings.mongodb_uri == "mongodb://user:secret@db.example/test"
    assert settings.mongodb_uri_configured is True
    assert settings.mongodb_uri_had_outer_whitespace is True


def test_settings_local_fallback_is_not_marked_configured(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)

    settings = Settings()

    assert settings.mongodb_uri == "mongodb://127.0.0.1:27017"
    assert settings.mongodb_uri_state == "absent"
    assert settings.mongodb_uri_configured is False


def test_mongodb_uri_diagnostics_are_safe_and_fingerprint_ignores_password():
    uri = "mongodb+srv://infera2:s%40fe%3Apass@cluster.example.net/analytics"
    diagnostics = mongodb_uri_diagnostics(uri, configured=True)
    other_password = mongodb_uri_diagnostics(
        "mongodb+srv://infera2:different-secret@cluster.example.net/analytics",
        configured=True,
    )

    assert diagnostics == {
        "uri_exists": "true",
        "uri_scheme": "mongodb+srv",
        "uri_hostname": "cluster.example.net",
        "uri_database": "analytics",
        "uri_username": "infera2",
        "uri_password_present": "true",
        "uri_password_length": "9",
        "uri_suspicious_unencoded": "false",
        "uri_had_outer_whitespace": "false",
        "uri_fingerprint": diagnostics["uri_fingerprint"],
    }
    assert len(diagnostics["uri_fingerprint"]) == 16
    assert diagnostics["uri_fingerprint"] == other_password["uri_fingerprint"]
    assert "s%40fe%3Apass" not in str(diagnostics)


def test_mongodb_uri_diagnostics_flag_unencoded_characters_and_trimmed_whitespace():
    diagnostics = mongodb_uri_diagnostics(
        "mongodb://infera2:bad@pass@cluster.example.net/db name",
        configured=True,
        had_outer_whitespace=True,
    )

    assert diagnostics["uri_suspicious_unencoded"] == "true"
    assert diagnostics["uri_had_outer_whitespace"] == "true"
    assert "bad@pass" not in str(diagnostics)


def test_mongodb_client_receives_effective_uri_without_transformation(monkeypatch):
    uri = "mongodb+srv://infera2:encoded%40password@cluster.example.net/analytics"
    observed: list[str] = []
    client = FakeClient()

    def fake_mongo_client(effective_uri, **kwargs):
        observed.append(effective_uri)
        return client

    monkeypatch.setattr("app.database.MongoClient", fake_mongo_client)
    database = MongoDatabase(uri, "ai_inference", 1000)

    assert database.connect() is True
    assert observed == [uri]
    assert database.uri_diagnostic["uri_password_present"] == "true"
    assert uri not in str(database.uri_diagnostic)


def test_mongodb_ping_reconnects_after_startup_failure(monkeypatch):
    unavailable_client = FakeClient(PyMongoError("database unavailable"))
    available_client = FakeClient()
    clients = iter((unavailable_client, available_client))
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: next(clients))

    database = MongoDatabase("mongodb://example", "ai_inference", 1000)

    assert database.connect() is False
    assert database.ping() is True
    assert database.client is available_client
    assert database.failure_diagnostic is None


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
        "diagnostic": {
            "error_type": "ConfigurationError",
            "message": "MONGODB_URI is not configured",
        },
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
        "diagnostic": {
            "error_type": "ConfigurationError",
            "message": "MONGODB_URI is not configured",
        },
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
    assert response.json()["database"]["diagnostic"] == {
        "error_type": "ServerSelectionTimeoutError",
        "message": "server selection timed out",
    }
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
    assert database["diagnostic"] == {
        "error_type": "OperationFailure",
        "message": "authentication failed for [REDACTED_MONGODB_URI]",
        "error_code": "18",
    }
    assert "fake-user" not in response.text
    assert "fake-password" not in response.text
    assert "fake-user" not in caplog.text
    assert "fake-password" not in caplog.text


def test_mongodb_startup_logs_safe_operation_failure_diagnostics(monkeypatch, caplog):
    uri = "mongodb://fake-user:fake-password@example.test/ai_inference"
    monkeypatch.setenv("MONGODB_URI", uri)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "")
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "")
    error = OperationFailure(
        f"authentication failed for {uri}; password=other-secret",
        code=8000,
        details={"codeName": "AtlasError", "errmsg": "authentication failed", "password": "details-secret"},
    )
    client = FakeClient(error)
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    with TestClient(create_app()):
        pass

    assert "reason=connection_failed" in caplog.text
    assert "configuration_state=present" in caplog.text
    assert "missing=none" in caplog.text
    assert "error_type=OperationFailure" in caplog.text
    assert "error_code=8000" in caplog.text
    assert "error_code_name=AtlasError" in caplog.text
    assert "error_message=authentication failed for [REDACTED_MONGODB_URI]" in caplog.text
    for secret in (uri, "fake-user", "fake-password", "other-secret", "details-secret"):
        assert secret not in caplog.text


def test_mongodb_diagnostic_uses_underlying_chained_exception(monkeypatch, caplog):
    uri = "mongodb://fake-user:fake-password@example.test/ai_inference"
    monkeypatch.setenv("MONGODB_URI", uri)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "")
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "")
    cause = OperationFailure("authentication failed", code=18)
    wrapper = RuntimeError("MongoDB startup wrapper")
    wrapper.__cause__ = cause
    client = FakeClient(wrapper)
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    with TestClient(create_app()):
        pass

    assert "error_type=OperationFailure" in caplog.text
    assert "error_code=18" in caplog.text
    assert "error_message=authentication failed" in caplog.text


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


def test_mongodb_health_diagnostic_redacts_uri_credentials_and_hosts(monkeypatch):
    uri = "mongodb+srv://fake-user:fake-password@private-cluster.example.net/ai_inference"
    monkeypatch.setenv("MONGODB_URI", uri)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "")
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "")
    message = (
        f"connection to private-cluster.example.net:27017 failed; password=other-secret; "
        f"api_key=fake-api-key; private_key=fake-private-key; URI={uri}"
    )
    client = FakeClient(PyMongoError(message))
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    with TestClient(create_app()) as test_client:
        response = test_client.get("/api/health")

    diagnostic = response.json()["database"]["diagnostic"]
    assert diagnostic["error_type"] == "PyMongoError"
    assert "connection to [REDACTED_HOST]:27017 failed" in diagnostic["message"]
    assert "[REDACTED_MONGODB_URI]" in diagnostic["message"]
    for secret in (
        uri,
        "fake-user",
        "fake-password",
        "other-secret",
        "fake-api-key",
        "fake-private-key",
        "private-cluster.example.net",
    ):
        assert secret not in response.text
