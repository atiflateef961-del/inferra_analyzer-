from unittest.mock import Mock

import httpx

from app.services.groq_service import GroqService


def test_service_reads_groq_configuration(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")

    service = GroqService()

    assert service.api_key == "test-groq-key"
    assert service.model == "openai/gpt-oss-120b"


def test_service_builds_chat_payload():
    service = GroqService(api_key="test-key", model="openai/gpt-oss-120b")

    payload = service.build_payload("Why did profit decrease?")

    assert payload["model"] == "openai/gpt-oss-120b"
    assert payload["messages"][0]["role"] == "user"
    assert "profit" in payload["messages"][0]["content"].lower()


def test_service_raises_for_missing_key():
    try:
        GroqService(api_key="")
        assert False, "Expected ValueError for missing Groq key"
    except ValueError:
        pass


def test_service_falls_back_when_model_is_decommissioned(monkeypatch):
    service = GroqService(api_key="test-key", model="llama-3.3-70b-versatile")

    failed = Mock()
    failed.status_code = 400
    failed.json.return_value = {"error": {"message": "The model `llama-3.3-70b-versatile` has been decommissioned."}}
    failed.text = "decommissioned"

    success = Mock()
    success.status_code = 200
    success.json.return_value = {
        "model": "openai/gpt-oss-120b",
        "choices": [{"message": {"content": "Revenue is $1,800 from imported files."}}],
    }

    monkeypatch.setattr(httpx, "post", Mock(side_effect=[failed, success]))

    result = service.generate("What is revenue?")

    assert result["content"].startswith("Revenue")
    assert result["model"] == "openai/gpt-oss-120b"


def test_service_calls_groq_api(monkeypatch):
    service = GroqService(api_key="test-key", model="openai/gpt-oss-120b")

    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {
        "model": "openai/gpt-oss-120b",
        "choices": [{"message": {"content": "The profit issue is likely due to rising expenses."}}],
    }
    mock.raise_for_status = Mock()

    monkeypatch.setattr(httpx, "post", Mock(return_value=mock))

    result = service.generate("Why did profit decrease?")

    assert result["provider"] == "groq"
    assert "profit" in result["content"].lower()
    assert "gpt-oss-120b" in result["model"]
