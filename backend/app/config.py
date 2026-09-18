from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

for _env_path in (PROJECT_ROOT / ".env", BASE_DIR / ".env"):
    if _env_path.exists():
        load_dotenv(_env_path)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None:
        return default

    try:
        parsed = int(value.strip())
    except ValueError:
        return default

    return parsed if parsed > 0 else default


def _resolve_data_path(value: str | None, default: Path) -> Path:
    if not value:
        return default.resolve()
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    if path.parts and path.parts[0] == "backend":
        return (PROJECT_ROOT / path).resolve()
    return (BASE_DIR / path).resolve()


def _default_cors_origins() -> list[str]:
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    network_address = (
        os.getenv("FRONTEND_NETWORK_ADDRESS")
        or os.getenv("LAN_IP")
        or os.getenv("NETWORK_HOST")
        or ""
    ).strip()
    if network_address:
        origins.append(f"http://{network_address}:3000")
    return origins


class Settings:
    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "Inferra AI Backend")
        self.app_environment = os.getenv("APP_ENV", "development").lower()
        self.debug = _as_bool(os.getenv("DEBUG"), default=False)
        self.api_prefix = os.getenv("API_PREFIX", "/api")
        self.version = os.getenv("APP_VERSION", "0.1.0")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip() or "openai/gpt-oss-120b"
        self.mongodb_uri = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017").strip()
        self.mongodb_database = os.getenv("MONGODB_DATABASE", "ai_inference").strip()
        self.mongodb_server_selection_timeout_ms = _as_int(
            os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS"),
            default=1000,
        )
        self.firebase_project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
        self.firebase_client_email = os.getenv("FIREBASE_CLIENT_EMAIL", "").strip()
        self.firebase_private_key = os.getenv("FIREBASE_PRIVATE_KEY", "").strip()
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                ",".join(_default_cors_origins()),
            ).split(",")
            if origin.strip()
        ]
        self.upload_dir = _resolve_data_path(
            os.getenv("UPLOAD_DIR"),
            BASE_DIR / "data" / "uploads",
        )
        self.document_index_path = _resolve_data_path(
            os.getenv("DOCUMENT_INDEX_PATH"),
            BASE_DIR / "data" / "documents.json",
        )
        self.max_upload_bytes = _as_int(os.getenv("MAX_UPLOAD_BYTES"), default=25 * 1024 * 1024)


settings = Settings()
