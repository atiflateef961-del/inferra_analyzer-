from contextlib import asynccontextmanager
import logging
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
            uri_configured=app_settings.mongodb_uri_configured,
            uri_state=app_settings.mongodb_uri_state,
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
            reason = database.failure_reason or "initialization_failed"
            diagnostic = database.failure_diagnostic or {}
            _log_safely(
                logger.error,
                "MongoDB initialization failed: reason=%s configuration_state=%s missing=%s error_type=%s error_code=%s error_code_name=%s error_message=%s error_details=%s",
                reason,
                database.uri_state,
                ",".join(database.missing_configuration) or "none",
                diagnostic.get("error_type", type(error).__name__ if error else "UnknownError"),
                diagnostic.get("error_code", "none"),
                diagnostic.get("error_code_name", "none"),
                diagnostic.get("message", "MongoDB operation failed"),
                diagnostic.get("error_details", "none"),
            )
        if not firebase_auth.initialize():
            error = getattr(firebase_auth, "last_error", None)
            logger = logging.getLogger(__name__)
            if firebase_auth.configured:
                _log_safely(
                    logger.error,
                    "Firebase initialization failed: reason=%s error_type=%s",
                    getattr(firebase_auth, "failure_reason", None) or "initialization_failed",
                    type(error).__name__ if error else "UnknownError",
                )
            else:
                missing = getattr(firebase_auth, "missing_configuration", [])
                _log_safely(
                    logger.error,
                    "Firebase initialization skipped: reason=missing_configuration missing=%s",
                    ",".join(missing) if missing else "unknown",
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


def _log_safely(log_method, message: str, *args: object) -> None:
    """Keep optional diagnostics from interrupting application startup."""
    try:
        log_method(message, *args)
    except Exception:
        pass


app = create_app()
