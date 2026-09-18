from __future__ import annotations

from typing import Any


def _delta(current: float, previous: float) -> tuple[str, str]:
    if previous == 0:
        if current == 0:
            return "0.0%", "up"
        return "+100.0%", "up"
    change = ((current - previous) / abs(previous)) * 100
    sign = "+" if change >= 0 else ""
    trend = "up" if change >= 0 else "down"
    return f"{sign}{change:.1f}%", trend


def build_workspace_analytics(documents: list[dict[str, Any]]) -> dict[str, Any]:
    revenue = 0.0
    expenses = 0.0
    profit = 0.0
    series_map: dict[str, dict[str, float]] = {}
    category_map: dict[str, float] = {}
    location_map: dict[str, dict[str, float]] = {}
    alerts: list[dict[str, str]] = []
    insights: list[dict[str, str]] = []
    processed = 0

    for document in documents:
        processed += 1
        metrics = document.get("metrics") or {}
        revenue += float(metrics.get("revenue") or 0)
        expenses += float(metrics.get("expenses") or 0)
        profit += float(metrics.get("profit") or 0)
        for point in document.get("series") or []:
            label = str(point.get("month") or "Total")
            bucket = series_map.setdefault(label, {"revenue": 0.0, "expense": 0.0, "profit": 0.0})
            bucket["revenue"] += float(point.get("revenue") or 0)
            bucket["expense"] += float(point.get("expense") or 0)
            bucket["profit"] += float(point.get("profit") or 0)
        for item in document.get("categories") or []:
            name = str(item.get("category") or "Other")
            category_map[name] = category_map.get(name, 0.0) + float(item.get("sales") or 0)
        for item in document.get("locations") or []:
            name = str(item.get("name") or "Unknown")
            bucket = location_map.setdefault(name, {"revenue": 0.0, "expense": 0.0, "profit": 0.0})
            bucket["revenue"] += float(item.get("revenue") or 0)
            bucket["expense"] += float(item.get("expense") or 0)
            bucket["profit"] += float(item.get("profit") or 0)
        for alert in document.get("alerts") or []:
            alerts.append(alert)
        ai_analysis = document.get("analysis") or {}
        for detail in ai_analysis.get("key_insights") or []:
            if isinstance(detail, str) and detail.strip():
                insights.append({"title": "AI file insight", "detail": detail.strip(), "tone": "violet"})

    margin = (profit / revenue * 100) if revenue else 0.0
    series = [
        {
            "month": label,
            "revenue": round(values["revenue"], 2),
            "expense": round(values["expense"], 2),
            "profit": round(values["profit"], 2),
        }
        for label, values in series_map.items()
    ]
    categories = [
        {"category": name, "sales": round(value, 2)}
        for name, value in sorted(category_map.items(), key=lambda item: item[1], reverse=True)
    ]
    locations = [
        {
            "name": name,
            "revenue": round(values["revenue"], 2),
            "expense": round(values["expense"], 2),
            "profit": round(values["profit"], 2),
        }
        for name, values in sorted(
            location_map.items(),
            key=lambda item: abs(item[1]["revenue"] or item[1]["profit"]),
            reverse=True,
        )
    ]

    if processed == 0:
        insights = [
            {
                "title": "Upload business files",
                "detail": "Import CSV, Excel, PDF, or DOCX files to generate live KPIs, charts, and AI recommendations.",
                "tone": "violet",
            }
        ]
    else:
        if revenue:
            insights.append(
                {
                    "title": "Revenue captured",
                    "detail": f"Imported documents currently total ${revenue:,.2f} in recognized revenue.",
                    "tone": "emerald",
                }
            )
        if expenses > revenue and revenue > 0:
            insights.append(
                {
                    "title": "Cost pressure",
                    "detail": "Recognized expenses are higher than revenue. Review supplier and operating costs.",
                    "tone": "amber",
                }
            )
        elif profit:
            insights.append(
                {
                    "title": "Profit signal",
                    "detail": f"Net profit across processed files is ${profit:,.2f} ({margin:.1f}% margin).",
                    "tone": "emerald",
                }
            )
        if categories:
            leader = categories[0]
            insights.append(
                {
                    "title": "Category concentration",
                    "detail": f"{leader['category']} is the strongest revenue stream at ${leader['sales']:,.2f}.",
                    "tone": "violet",
                }
            )
        if not insights:
            insights.append(
                {
                    "title": "Documents indexed",
                    "detail": "Files are stored and searchable. Tabular financial columns were not detected, so KPIs stay at zero until a sales spreadsheet is imported.",
                    "tone": "sky",
                }
            )

    revenue_delta, revenue_trend = _delta(revenue, expenses)
    expense_delta, expense_trend = _delta(expenses, revenue if revenue else expenses)
    profit_delta, profit_trend = _delta(profit, revenue * 0.2 if revenue else 0)
    margin_delta, margin_trend = _delta(margin, 20.0)

    reports = [
        {
            "title": "Business summary",
            "description": "Totals computed from imported documents",
            "value": f"${revenue:,.0f}" if revenue else "No data",
            "accent": "emerald",
        },
        {
            "title": "AI insight report",
            "description": "Issues and recommendations from the latest files",
            "value": f"{len(insights)} insights",
            "accent": "violet",
        },
        {
            "title": "Forecast update",
            "description": "Margin implied by current imported numbers",
            "value": f"{margin:.1f}%",
            "accent": "sky",
        },
    ]

    return {
        "kpis": {
            "revenue": revenue,
            "expenses": expenses,
            "profit": profit,
            "margin": margin,
            "revenue_delta": revenue_delta,
            "revenue_trend": revenue_trend,
            "expense_delta": expense_delta,
            "expense_trend": expense_trend,
            "profit_delta": profit_delta,
            "profit_trend": profit_trend,
            "margin_delta": margin_delta,
            "margin_trend": margin_trend,
        },
        "summary": {
            "documents_analyzed": processed,
            "alerts_tracked": len(alerts),
            "system_health": "Ready" if processed else "Waiting",
            "ai_signal": "Strong" if revenue else "Idle",
        },
        "series": series,
        "categories": categories,
        "locations": locations,
        "insights": insights[:6],
        "alerts": alerts[:8] or ([{"label": "No imported issues", "status": "Monitoring"}] if processed else []),
        "reports": reports,
        "headline_insights": [item["detail"] for item in insights[:3]],
    }


def build_agent_context(documents: list[dict[str, Any]], analytics: dict[str, Any]) -> str:
    excerpts = []
    for document in documents[:8]:
        excerpt = str(document.get("excerpt") or "").strip()
        if excerpt:
            excerpts.append(f"File: {document.get('name')}\n{excerpt[:2500]}")
    return (
        "You are Inferra AI, a business document intelligence agent. "
        "Answer only from the imported workspace analytics and document excerpts. "
        "If the files do not contain the answer, say so clearly.\n\n"
        f"Analytics JSON:\n{analytics}\n\n"
        "Document excerpts:\n"
        + ("\n\n".join(excerpts) if excerpts else "No document excerpts are available yet.")
    )
