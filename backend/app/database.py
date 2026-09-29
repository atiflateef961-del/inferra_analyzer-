from __future__ import annotations

from pymongo import MongoClient
from pymongo.errors import (
    ConfigurationError,
    ExecutionTimeout,
    NetworkTimeout,
    OperationFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
    WaitQueueTimeoutError,
    WTimeoutError,
)


class MongoDatabase:
    def __init__(
        self,
        uri: str,
        database_name: str,
        server_selection_timeout_ms: int,
        uri_configured: bool = True,
        uri_state: str | None = None,
    ) -> None:
        self.uri = uri
        self.database_name = database_name
        self.server_selection_timeout_ms = server_selection_timeout_ms
        self.uri_state = uri_state or ("present" if uri_configured else "absent")
        self.uri_configured = self.uri_state == "present"
        self.client: MongoClient | None = None
        self.last_error: Exception | None = None

    @property
    def missing_configuration(self) -> list[str]:
        return [] if self.uri_state == "present" else ["MONGODB_URI"]

    @property
    def failure_reason(self) -> str | None:
        error = self.last_error
        if error is None:
            return None
        if self.uri_state in {"absent", "empty"}:
            return "missing_configuration"
        if isinstance(error, (ServerSelectionTimeoutError, NetworkTimeout, ExecutionTimeout, WaitQueueTimeoutError, WTimeoutError)):
            return "timeout"
        if isinstance(error, ConfigurationError):
            return "invalid_configuration"
        if isinstance(error, OperationFailure) and (
            error.code == 18 or getattr(error, "code_name", None) == "AuthenticationFailed"
        ):
            return "authentication_failed"
        if isinstance(error, PyMongoError):
            return "connection_failed"
        if isinstance(error, (TypeError, ValueError)):
            return "invalid_configuration"
        return "initialization_failed"

    def connect(self) -> bool:
        client: MongoClient | None = None
        try:
            client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=self.server_selection_timeout_ms,
            )
            client.admin.command("ping")
        except Exception as error:
            self.last_error = error
            if client is not None:
                client.close()
            self.client = None
            return False

        self.client = client
        self.last_error = None
        return True

    def ping(self) -> bool:
        if self.client is None:
            return self.connect()

        try:
            self.client.admin.command("ping")
        except Exception as error:
            self.last_error = error
            return False

        self.last_error = None
        return True

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None

    @property
    def database(self):
        if self.client is None:
            raise RuntimeError("MongoDB is not connected")
        return self.client[self.database_name]
