from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import FirebaseAuthService, bearer_scheme
from app.services.document_store import DocumentStore


def get_document_store(request: Request) -> DocumentStore:
    store = getattr(request.app.state, "document_store", None)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document store is not initialized",
        )
    return store


def get_workspace_user(
    request: Request,
    credentials_header: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    settings = request.app.state.settings
    firebase_service: FirebaseAuthService | None = getattr(
        request.app.state,
        "firebase_auth",
        None,
    )
    if (
        credentials_header is not None
        and credentials_header.scheme.lower() == "bearer"
        and firebase_service is not None
        and firebase_service.configured
    ):
        try:
            return firebase_service.verify_id_token(credentials_header.credentials)
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from error

    if settings.app_environment == "development":
        return {
            "uid": "local-dev",
            "email": "local@inferra.dev",
            "name": "Local workspace",
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
