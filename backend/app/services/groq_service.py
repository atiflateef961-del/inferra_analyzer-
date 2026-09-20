from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
FALLBACK_GROQ_MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b")


class GroqService:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        if api_key is not None:
            self.api_key = api_key.strip()
        else:
            self.api_key = os.getenv("GROQ_API_KEY", "").strip()

        if model is not None:
            self.model = model.strip()
        else:
            self.model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL

        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required")

    def build_payload(
        self,
        user_prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 2048,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        return payload

    def generate(
        self,
        user_prompt: str,
        *,
        system_prompt: str | None = None,
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        models_to_try: list[str] = []
        for candidate in (self.model, *FALLBACK_GROQ_MODELS):
            if candidate and candidate not in models_to_try:
                models_to_try.append(candidate)

        last_error: str | None = None
        for model in models_to_try:
            payload = self.build_payload(
                user_prompt,
                system_prompt=system_prompt,
                model=model,
                response_format=response_format,
            )
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return {
                    "model": data.get("model", model),
                    "content": content,
                    "provider": "groq",
                    "raw": data,
                }

            detail = _groq_error_detail(response)
            last_error = detail
            if response.status_code in {400, 404} and _is_unavailable_model(detail):
                continue
            raise RuntimeError(detail)

        raise RuntimeError(last_error or "The Groq model is unavailable.")


def _groq_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(payload, dict) and payload.get("message"):
            return str(payload["message"])
    except ValueError:
        pass
    text = response.text.strip()
    return text or f"Groq request failed with status {response.status_code}"


def _is_unavailable_model(detail: str) -> bool:
    lowered = detail.lower()
    return any(
        token in lowered
        for token in (
            "decommissioned",
            "does not exist",
            "model_not_found",
            "unknown model",
            "invalid model",
            "not found",
        )
    )
