from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

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
    client = FakeClient(PyMongoError("database unavailable"))
    monkeypatch.setattr("app.database.MongoClient", lambda *args, **kwargs: client)

    with TestClient(create_app()) as test_client:
        response = test_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"]["status"] == "unavailable"
