from __future__ import annotations

import re
from pprint import pformat

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


def _sanitize_error_message(message: str, uri: str) -> str:
    sanitized = message
    if uri:
        sanitized = sanitized.replace(uri, "[REDACTED_MONGODB_URI]")
    sanitized = re.sub(
        r"mongodb(?:\+srv)?://[^\s\"'<>]+",
        "[REDACTED_MONGODB_URI]",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"['\"]?\b(?:password|passwd|pwd|username|user|secret|token|api[_-]?key|private[_-]?key|connection[_-]?string)['\"]?\s*[:=]\s*['\"]?[^\s,;'\"}]+",
        "credential=[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(r"-----BEGIN [^-]+-----.*?-----END [^-]+-----", "[REDACTED_PRIVATE_KEY]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"\bBearer\s+[^\s,;]+", "Bearer [REDACTED]", sanitized, flags=re.IGNORECASE)
    # PyMongo server-selection errors can include server addresses separately
    # from the URI; avoid returning infrastructure hostnames or IPs.
    sanitized = re.sub(
        r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\b",
        "[REDACTED_HOST]",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b", "[REDACTED_HOST]", sanitized)
    sanitized = " ".join(sanitized.split())
    return sanitized[:500] or "MongoDB operation failed"


def _diagnostic_exception(error: Exception) -> Exception:
    """Return the deepest chained exception without losing the wrapper as last_error."""
    current = error
    seen = {id(current)}
    while True:
        cause = current.__cause__ or current.__context__
        if cause is None or id(cause) in seen:
            return current
        current = cause
        seen.add(id(current))


def _sanitize_details(value: object, uri: str) -> object:
    if isinstance(value, dict):
        safe: dict[object, object] = {}
        for key, item in value.items():
            key_text = str(key)
            if re.search(r"password|passwd|pwd|username|user|secret|token|api[_-]?key|private[_-]?key|connection[_-]?string", key_text, re.IGNORECASE):
                safe[key] = "[REDACTED]"
            else:
                safe[key] = _sanitize_details(item, uri)
        return safe
    if isinstance(value, (list, tuple)):
        return [_sanitize_details(item, uri) for item in value]
    if isinstance(value, str):
        return _sanitize_error_message(value, uri)
    return value


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
        self.failure_diagnostic: dict[str, str] | None = None

    @property
    def missing_configuration(self) -> list[str]:
        return [] if self.uri_state == "present" else ["MONGODB_URI"]

    @property
    def failure_reason(self) -> str | None:
        error = self.last_error
        if error is None:
            return None
        error = _diagnostic_exception(error)
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

    def _record_failure(self, error: Exception) -> None:
        self.last_error = error
        diagnostic_error = _diagnostic_exception(error)
        diagnostic = {
            "error_type": type(diagnostic_error).__name__,
            "message": _sanitize_error_message(str(diagnostic_error), self.uri),
        }
        code = getattr(diagnostic_error, "code", None)
        details = getattr(diagnostic_error, "details", None)
        code_name = getattr(diagnostic_error, "code_name", None) or (
            details.get("codeName") if isinstance(details, dict) else None
        )
        if code is not None:
            diagnostic["error_code"] = str(code)
        if code_name:
            diagnostic["error_code_name"] = _sanitize_error_message(str(code_name), self.uri)
        if details:
            diagnostic["error_details"] = _sanitize_error_message(pformat(_sanitize_details(details, self.uri)), self.uri)
        self.failure_diagnostic = diagnostic

    def connect(self) -> bool:
        if self.uri_state in {"absent", "empty"}:
            # Do not try the local fallback URI when deployment configuration
            # is missing; that turns a configuration problem into a misleading
            # server-selection timeout.
            self._record_failure(ConfigurationError("MONGODB_URI is not configured"))
            self.client = None
            return False

        client: MongoClient | None = None
        try:
            client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=self.server_selection_timeout_ms,
            )
            client.admin.command("ping")
        except Exception as error:
            self._record_failure(error)
            if client is not None:
                client.close()
            self.client = None
            return False

        self.client = client
        self.last_error = None
        self.failure_diagnostic = None
        return True

    def ping(self) -> bool:
        if self.client is None:
            return self.connect()

        try:
            self.client.admin.command("ping")
        except Exception as error:
            self._record_failure(error)
            return False

        self.last_error = None
        self.failure_diagnostic = None
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
