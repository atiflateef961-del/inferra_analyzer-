from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_document_store, get_workspace_user
from app.services.analytics_engine import build_workspace_analytics
from app.services.document_store import DocumentStore

router = APIRouter(tags=["analytics"])


@router.get("/analytics")
def get_analytics(
    store: DocumentStore = Depends(get_document_store),
    current_user: dict[str, Any] = Depends(get_workspace_user),
) -> dict[str, Any]:
    analytics = build_workspace_analytics(store.list_documents())
    analytics["owner"] = current_user.get("email")
    return analytics


@router.get("/reports")
def get_reports(
    store: DocumentStore = Depends(get_document_store),
    current_user: dict[str, Any] = Depends(get_workspace_user),
) -> dict[str, Any]:
    analytics = build_workspace_analytics(store.list_documents())
    return {"items": analytics["reports"], "owner": current_user.get("email")}
