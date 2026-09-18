from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import get_document_store, get_workspace_user
from app.services.analytics_engine import build_agent_context, build_workspace_analytics
from app.services.document_store import DocumentStore
from app.services.groq_service import GroqService

router = APIRouter(prefix="/agent", tags=["agent"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)


@router.post("/chat")
def chat_with_agent(
    payload: ChatRequest,
    request: Request,
    store: DocumentStore = Depends(get_document_store),
    current_user: dict[str, Any] = Depends(get_workspace_user),
) -> dict[str, Any]:
    app_settings = request.app.state.settings
    if not app_settings.groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GROQ_API_KEY is not configured",
        )

    documents = store.list_documents()
    analytics = build_workspace_analytics(documents)
    history_text = "\n".join(
        f"{item.role}: {item.content}" for item in payload.history[-8:] if item.content.strip()
    )
    user_prompt = payload.message.strip()
    if history_text:
        user_prompt = f"Conversation so far:\n{history_text}\n\nLatest question:\n{user_prompt}"

    try:
        service = GroqService(api_key=app_settings.groq_api_key, model=app_settings.groq_model)
        result = service.generate(
            user_prompt,
            system_prompt=build_agent_context(documents, analytics),
        )
    except Exception as error:
        detail = str(error).strip() or "The AI agent could not complete this request."
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        ) from error

    return {
        "content": result["content"],
        "model": result["model"],
        "provider": result["provider"],
        "owner": current_user.get("email"),
        "documents_used": len(documents),
    }
