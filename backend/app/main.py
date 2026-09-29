from contextlib import asynccontextmanager
import logging
import re
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.auth import FirebaseAuthService
from app.config import Settings
from app.database import MongoDatabase
from app.services.document_store import DocumentStore


def create_app() -> FastAPI:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app_settings = Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database = MongoDatabase(
            uri=app_settings.mongodb_uri,
            database_name=app_settings.mongodb_database,
            server_selection_timeout_ms=app_settings.mongodb_server_selection_timeout_ms,
        )
        firebase_auth = FirebaseAuthService(
            project_id=app_settings.firebase_project_id,
            client_email=app_settings.firebase_client_email,
            private_key=app_settings.firebase_private_key,
        )
        application.state.database = database
        application.state.firebase_auth = firebase_auth
        if not database.connect():
            error = database.last_error
            logger = logging.getLogger(__name__)
            logger.error(
                "MongoDB initialization failed (%s): %s",
                type(error).__name__ if error else "UnknownError",
                _safe_error_message(error, (database.uri,)) if error else "No error details available",
            )
        if not firebase_auth.initialize():
            error = getattr(firebase_auth, "last_error", None)
            logger = logging.getLogger(__name__)
            if firebase_auth.configured:
                logger.error(
                    "Firebase initialization failed (%s): %s",
                    type(error).__name__ if error else "UnknownError",
                    _safe_error_message(error, (getattr(firebase_auth, "private_key", ""),)) if error else "No error details available",
                )
            else:
                missing = [
                    name for name, value in (
                        ("FIREBASE_PROJECT_ID", getattr(firebase_auth, "project_id", "")),
                        ("FIREBASE_CLIENT_EMAIL", getattr(firebase_auth, "client_email", "")),
                        ("FIREBASE_PRIVATE_KEY", getattr(firebase_auth, "private_key", "")),
                    ) if not value
                ]
                logger.error(
                    "Firebase initialization skipped: missing %s",
                    ", ".join(missing) if missing else "service configuration",
                )
        application.state.document_store = DocumentStore(
            database=database,
            upload_dir=app_settings.upload_dir,
            index_path=app_settings.document_index_path,
        )
        try:
            yield
        finally:
            database.close()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.version,
        debug=app_settings.debug,
        description="Inferra AI backend API",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_origin_regex=(
            r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|"
            r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?$"
            if app_settings.app_environment == "development"
            else None
        ),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.state.settings = app_settings
    app.include_router(api_router)

    @app.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {
            "service": app_settings.app_name,
            "status": "ok",
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


def _safe_error_message(error: Exception, secrets: tuple[str, ...]) -> str:
    """Return useful exception context without echoing configured credentials."""
    message = str(error)
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[REDACTED]")
            message = message.replace(secret.replace("\n", "\\n"), "[REDACTED]")
    # MongoDB driver errors can include the complete URI, including query options.
    message = re.sub(r"mongodb(?:\+srv)?://[^\s\"']+", "[REDACTED_MONGODB_URI]", message, flags=re.IGNORECASE)
    message = re.sub(r"-----BEGIN [^-]+PRIVATE KEY-----.*?-----END [^-]+PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]", message, flags=re.DOTALL)
    return message[:1000]


app = create_app()
