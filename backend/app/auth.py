from __future__ import annotations

from typing import Any

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from firebase_admin.exceptions import FirebaseError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


class FirebaseAuthService:
    def __init__(
        self,
        project_id: str,
        client_email: str,
        private_key: str,
    ) -> None:
        self.project_id = project_id
        self.client_email = client_email
        self.private_key = private_key.replace("\\n", "\n")
        self.app: firebase_admin.App | None = None
        self.last_error: Exception | None = None

    @property
    def configured(self) -> bool:
        return all((self.project_id, self.client_email, self.private_key))

    def initialize(self) -> bool:
        if not self.configured:
            return False

        try:
            try:
                self.app = firebase_admin.get_app()
            except ValueError:
                service_account = credentials.Certificate(
                    {
                        "type": "service_account",
                        "project_id": self.project_id,
                        "client_email": self.client_email,
                        "private_key": self.private_key,
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                )
                self.app = firebase_admin.initialize_app(
                    service_account,
                    {"projectId": self.project_id},
                )
        except (FirebaseError, ValueError, TypeError) as error:
            self.last_error = error
            self.app = None
            return False

        self.last_error = None
        return True

    def verify_id_token(self, token: str) -> dict[str, Any]:
        if self.app is None:
            raise RuntimeError("Firebase authentication is not configured")

        decoded_token = firebase_auth.verify_id_token(token, app=self.app)
        if not decoded_token.get("uid"):
            raise ValueError("Firebase token has no uid")
        return decoded_token


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials_header: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials_header is None or credentials_header.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    firebase_service: FirebaseAuthService | None = getattr(
        request.app.state,
        "firebase_auth",
        None,
    )
    if firebase_service is None or not firebase_service.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured",
        )

    try:
        return firebase_service.verify_id_token(credentials_header.credentials)
    except (FirebaseError, RuntimeError, TypeError, ValueError, KeyError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
