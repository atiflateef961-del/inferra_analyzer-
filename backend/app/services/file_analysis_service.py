from __future__ import annotations

import json
import logging
from typing import Any

from app.services.groq_service import GroqService

logger = logging.getLogger(__name__)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()][:6]


def _parse_provider_json(content: str) -> dict[str, Any]:
    """Accept valid JSON plus the markdown wrappers providers commonly add."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("The AI provider returned an invalid analysis response.")
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as error:
            raise RuntimeError("The AI provider returned an invalid analysis response.") from error

    if not isinstance(parsed, dict):
        raise RuntimeError("The AI provider returned an incomplete analysis response.")
    return parsed


def _local_analysis(*, filename: str, analysis: dict[str, Any], reason: str) -> dict[str, Any]:
    metrics = analysis.get("metrics") or {}
    revenue = float(metrics.get("revenue") or 0)
    expenses = float(metrics.get("expenses") or 0)
    profit = float(metrics.get("profit") or 0)
    row_count = int(analysis.get("row_count") or 0)
    columns = [str(column) for column in analysis.get("columns") or []]
    summary = (
        f"{filename} contains {row_count} data rows and {len(columns)} detected columns. "
        f"Calculated revenue is {revenue:,.2f}, expenses are {expenses:,.2f}, and profit is {profit:,.2f}."
        if columns or row_count
        else f"{filename} was read successfully. The extracted document contains {len(str(analysis.get('excerpt') or '')):,} characters."
    )
    insights = []
    if revenue:
        insights.append(f"Calculated profit margin is {(profit / revenue) * 100:.1f}%.")
    if columns:
        insights.append(f"The extracted table contains {len(columns)} columns: {', '.join(columns[:8])}.")
    if not insights:
        insights.append("The file was extracted successfully and is available for review in the document details.")
    return {
        "summary": summary,
        "key_insights": insights,
        "recommendations": ["Review the extracted content and calculated metrics for the next business decision."],
        "provider": "local",
        "model": "deterministic-fallback",
        "warning": reason,
    }


def analyze_file(*, filename: str, analysis: dict[str, Any], api_key: str, model: str) -> dict[str, Any]:
    """Ask the configured provider to interpret extracted file content and local facts."""
    excerpt = str(analysis.get("excerpt") or "").strip()
    if not excerpt:
        raise ValueError("No readable content was extracted, so analysis cannot start.")

    facts = {
        "filename": filename,
        "file_type": analysis.get("type"),
        "rows": analysis.get("row_count", 0),
        "columns": analysis.get("columns", []),
        "metrics": analysis.get("metrics", {}),
        "categories": analysis.get("categories", [])[:12],
        "locations": analysis.get("locations", [])[:12],
    }
    prompt = (
        "Analyze this uploaded business file. Use only the supplied extracted content and deterministic facts. "
        "Do not invent numbers or claim data that is not present. Return one JSON object with exactly these keys: "
        'summary (string), key_insights (array of strings), recommendations (array of strings).\n\n'
        f"Deterministic facts:\n{json.dumps(facts, ensure_ascii=False)}\n\n"
        f"Extracted content (possibly truncated):\n{excerpt[:12000]}"
    )
    logger.info("[AI] Request start filename=%s extracted_chars=%d", filename, len(excerpt))
    service = GroqService(api_key=api_key, model=model)
    result = service.generate(
        prompt,
        system_prompt="You are an accurate business-data analyst. Return valid JSON only.",
    )
    content = str(result.get("content") or "").strip()
    try:
        parsed = _parse_provider_json(content)
        if not isinstance(parsed.get("summary"), str) or not parsed["summary"].strip():
            raise RuntimeError("The AI provider returned an incomplete analysis response.")
    except RuntimeError as error:
        logger.warning("[AI] Invalid structured response filename=%s; using deterministic fallback", filename)
        return _local_analysis(filename=filename, analysis=analysis, reason=str(error))
    output = {
        "summary": parsed["summary"].strip(),
        "key_insights": _string_list(parsed.get("key_insights")),
        "recommendations": _string_list(parsed.get("recommendations")),
        "provider": result.get("provider", "groq"),
        "model": result.get("model", model),
    }
    logger.info("[AI] Response received filename=%s insights=%d", filename, len(output["key_insights"]))
    return output
