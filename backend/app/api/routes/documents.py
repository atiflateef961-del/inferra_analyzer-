from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status

from app.api.deps import get_document_store, get_workspace_user
from app.services.document_processor import ALLOWED_EXTENSIONS, IMAGE_EXTENSIONS, process_document
from app.services.document_store import DocumentStore
from app.services.file_analysis_service import analyze_file
import logging

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


@router.get("")
def list_documents(
    q: str = Query(default=""),
    store: DocumentStore = Depends(get_document_store),
    current_user: dict[str, Any] = Depends(get_workspace_user),
) -> dict[str, Any]:
    documents = store.list_documents(q)
    return {"items": documents, "count": len(documents), "owner": current_user.get("email")}


@router.post("")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    store: DocumentStore = Depends(get_document_store),
    current_user: dict[str, Any] = Depends(get_workspace_user),
) -> dict[str, Any]:
    filename = file.filename or "upload.bin"
    suffix = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Use PDF, Excel (.xlsx), CSV, DOCX, TXT, JSON, PNG, or JPG.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
    max_upload_bytes = request.app.state.settings.max_upload_bytes
    if len(content) > max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 25 MB upload limit.",
        )
    if suffix in IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image analysis is not available because this backend has no OCR extractor. Upload a text-based document instead.",
        )

    logger.info("[FILE] Received filename=%s type=%s size_bytes=%d", filename, suffix, len(content))

    try:
        analysis = process_document(filename, content)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    settings = request.app.state.settings
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GROQ_API_KEY is not configured; file analysis cannot run.",
        )
    try:
        analysis["analysis"] = analyze_file(
            filename=filename,
            analysis=analysis,
            api_key=settings.groq_api_key,
            model=settings.groq_model,
        )
        analysis["status"] = "Analyzed"
    except Exception as error:
        logger.exception("[ANALYSIS] Failed filename=%s", filename)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Analysis failed: {str(error).strip() or 'The AI provider did not return a usable result.'}",
        ) from error

    document = store.create_document(
        filename=filename,
        content=content,
        content_type=file.content_type or "application/octet-stream",
        owner=str(current_user.get("email") or current_user.get("uid") or "workspace"),
        analysis=analysis,
    )
    logger.info("[ANALYSIS] Complete filename=%s", filename)
    # Keep the original document fields at the top level for existing API consumers,
    # while exposing a predictable success envelope for the upload flow.
    return {**document, "success": True, "document": document, "analysis": document["analysis"]}


@router.get("/{document_id}")
def get_document(
    document_id: str,
    store: DocumentStore = Depends(get_document_store),
    current_user: dict[str, Any] = Depends(get_workspace_user),
) -> dict[str, Any]:
    document = store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    store: DocumentStore = Depends(get_document_store),
    current_user: dict[str, Any] = Depends(get_workspace_user),
) -> dict[str, str]:
    deleted = store.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {"status": "deleted", "id": document_id}
