from __future__ import annotations

import hashlib
import re
from pprint import pformat
from urllib.parse import quote, unquote, urlsplit

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
        try:
            parts = urlsplit(uri)
            for value in (parts.username, parts.password):
                if value:
                    decoded = unquote(value)
                    for credential in {value, decoded}:
                        if credential:
                            sanitized = sanitized.replace(credential, "[REDACTED]")
        except (ValueError, UnicodeError):
            pass
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


def mongodb_uri_diagnostics(uri: str, configured: bool, had_outer_whitespace: bool = False) -> dict[str, str]:
    """Describe a MongoDB URI without returning its password or full contents."""
    if not configured:
        return {
            "uri_exists": "false",
            "uri_scheme": "none",
            "uri_hostname": "none",
            "uri_database": "none",
            "uri_username": "none",
            "uri_password_present": "false",
            "uri_password_length": "0",
            "uri_suspicious_unencoded": "false",
            "uri_had_outer_whitespace": str(had_outer_whitespace).lower(),
            "uri_fingerprint": "unconfigured",
        }

    try:
        validate_mongodb_uri(uri)
        parts = urlsplit(uri)
        username = unquote(parts.username or "")
        password = unquote(parts.password or "")
        authority = parts.netloc.rsplit("@", 1)[-1]
        host_entries = authority.split(",")
        hostnames: list[str] = []
        host_fingerprint_parts: list[str] = []
        for entry in host_entries:
            if entry.startswith("[") and "]" in entry:
                closing = entry.index("]")
                host = entry[1:closing]
                port_suffix = entry[closing + 1 :]
                port = port_suffix[1:] if port_suffix.startswith(":") else ""
            else:
                host, separator, port = entry.rpartition(":")
                if not separator:
                    host, port = entry, ""
            hostnames.append(host or "none")
            host_fingerprint_parts.append(f"{host.lower()}:{port}" if port else host.lower())
        hostname = ",".join(hostnames) or "none"
        scheme = parts.scheme.lower() or "none"
        database_name = quote(unquote(parts.path.lstrip("/")), safe="-_.~") or "none"
        # Reserved delimiters in raw userinfo should be percent encoded. Do not
        # inspect or emit the password itself, only whether it contains one.
        userinfo = parts.netloc.rsplit("@", 1)[0] if "@" in parts.netloc else ""
        scheme_separator = uri.find("://")
        raw_uri_userinfo = ""
        if scheme_separator >= 0 and "@" in uri[scheme_separator + 3 :]:
            raw_uri_userinfo = uri[scheme_separator + 3 :].rsplit("@", 1)[0]
        suspicious = bool(
            any(char.isspace() for char in uri)
            or re.search(r"%(?![0-9A-Fa-f]{2})", uri)
            or any(char in userinfo for char in "/?#[]")
            or any(char in raw_uri_userinfo for char in "/?#[]")
            or parts.netloc.count("@") > 1
            or (parts.password is not None and any(char in parts.password for char in ":@"))
        )
        fingerprint_source = "|".join((scheme, ",".join(host_fingerprint_parts), parts.path))
        fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[:16]
        return {
            "uri_exists": "true",
            "uri_scheme": scheme,
            "uri_hostname": hostname,
            "uri_database": database_name,
            "uri_username": quote(username, safe="-_.~") if username else "none",
            "uri_password_present": str(parts.password is not None).lower(),
            "uri_password_length": str(len(password)),
            "uri_suspicious_unencoded": str(suspicious).lower(),
            "uri_had_outer_whitespace": str(had_outer_whitespace).lower(),
            "uri_fingerprint": fingerprint,
        }
    except (ConfigurationError, ValueError, UnicodeError):
        # Never expose parser fragments from a malformed URI; they may be pieces
        # of an unescaped credential that the URI parser misread as a host/path.
        fingerprint = hashlib.sha256(b"invalid-mongodb-uri").hexdigest()[:16]
        return {
            "uri_exists": "true",
            "uri_scheme": "invalid",
            "uri_hostname": "invalid",
            "uri_database": "invalid",
            "uri_username": "none",
            "uri_password_present": "unknown",
            "uri_password_length": "unknown",
            "uri_suspicious_unencoded": "true",
            "uri_had_outer_whitespace": str(had_outer_whitespace).lower(),
            "uri_fingerprint": fingerprint,
        }


def validate_mongodb_uri(uri: str, configured: bool = True, uri_state: str | None = None) -> None:
    """Validate URI structure without including configuration values in errors."""
    state = uri_state or ("present" if configured else "absent")
    if state == "absent":
        raise ConfigurationError("MONGODB_URI is not configured")
    if state == "empty" or not uri:
        raise ConfigurationError("MONGODB_URI is empty")
    if uri != uri.strip():
        raise ConfigurationError("MONGODB_URI has surrounding whitespace; remove it")
    if any(char.isspace() for char in uri):
        raise ConfigurationError("MONGODB_URI contains unescaped whitespace")
    if re.search(r"%(?![0-9A-Fa-f]{2})", uri):
        raise ConfigurationError("MONGODB_URI contains invalid percent encoding")

    try:
        parts = urlsplit(uri)
        scheme = parts.scheme.lower()
        if scheme not in {"mongodb", "mongodb+srv"}:
            raise ConfigurationError("MONGODB_URI must use mongodb:// or mongodb+srv://")
        if not parts.netloc or not parts.hostname:
            raise ConfigurationError("MONGODB_URI must include a hostname")
        if "@" in parts.path or "@" in parts.query or "@" in parts.fragment:
            raise ConfigurationError("MongoDB credentials contain reserved characters; URL-encode them")
        if parts.fragment:
            raise ConfigurationError("MONGODB_URI must not contain a fragment")
        if parts.netloc.count("@") > 1:
            raise ConfigurationError("MongoDB credentials contain reserved characters; URL-encode them")
        if "@" in parts.netloc:
            username, separator, password = parts.netloc.rsplit("@", 1)[0].partition(":")
            if not separator or not username:
                raise ConfigurationError("MongoDB URI credentials must include a username and password")
            if not password:
                raise ConfigurationError("MongoDB URI password is missing")
            if ":" in password:
                raise ConfigurationError("MongoDB password contains reserved characters; URL-encode it")
            try:
                unquote(username, errors="strict")
                unquote(password, errors="strict")
            except (UnicodeError, ValueError):
                raise ConfigurationError("MongoDB URI credentials have invalid encoding") from None

        # Standard Mongo URIs permit comma-separated hosts; SRV URIs require one DNS host.
        hosts = parts.netloc.rsplit("@", 1)[-1].split(",")
        if scheme == "mongodb+srv" and len(hosts) != 1:
            raise ConfigurationError("mongodb+srv URIs must specify exactly one hostname")
        for host in hosts:
            parsed_host = urlsplit(f"//{host}")
            if not parsed_host.hostname:
                raise ConfigurationError("MONGODB_URI must include a valid hostname")
            _ = parsed_host.port
            if scheme == "mongodb+srv" and parsed_host.port is not None:
                raise ConfigurationError("mongodb+srv URIs cannot specify a port")
    except ConfigurationError:
        raise
    except (ValueError, UnicodeError):
        raise ConfigurationError("MONGODB_URI is malformed") from None


class MongoDatabase:
    def __init__(
        self,
        uri: str,
        database_name: str,
        server_selection_timeout_ms: int,
        uri_configured: bool = True,
        uri_state: str | None = None,
        uri_had_outer_whitespace: bool = False,
    ) -> None:
        self.uri = uri
        self.database_name = database_name
        self.server_selection_timeout_ms = server_selection_timeout_ms
        self.uri_state = uri_state or ("present" if uri_configured else "absent")
        self.uri_configured = self.uri_state == "present"
        self.uri_diagnostic = mongodb_uri_diagnostics(
            uri,
            configured=self.uri_configured,
            had_outer_whitespace=uri_had_outer_whitespace,
        )
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
        if isinstance(error, OperationFailure) and (
            error.code == 13 or getattr(error, "code_name", None) in {"Unauthorized", "AuthorizationFailure"}
        ):
            return "authorization_failed"
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
        try:
            validate_mongodb_uri(self.uri, configured=self.uri_configured, uri_state=self.uri_state)
        except ConfigurationError as error:
            self._record_failure(error)
            self.client = None
            return False

        client: MongoClient | None = None
        try:
            client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=self.server_selection_timeout_ms,
            )
            client[self.database_name].command("ping")
            # A read-only metadata check confirms this user can access the configured DB.
            client[self.database_name].list_collection_names()
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
            self.client[self.database_name].command("ping")
            self.client[self.database_name].list_collection_names()
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
