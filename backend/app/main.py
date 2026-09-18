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
        )
        firebase_auth = FirebaseAuthService(
            project_id=app_settings.firebase_project_id,
            client_email=app_settings.firebase_client_email,
            private_key=app_settings.firebase_private_key,
        )
        application.state.database = database
        application.state.firebase_auth = firebase_auth
        database.connect()
        firebase_auth.initialize()
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


app = create_app()
