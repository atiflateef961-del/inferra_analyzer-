from pathlib import Path
from io import BytesIO

from openpyxl import Workbook
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.document_processor import process_document
from app.services.file_analysis_service import analyze_file


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("DOCUMENT_INDEX_PATH", str(tmp_path / "documents.json"))
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    class FakeFileGroq:
        def __init__(self, **kwargs):
            pass

        def generate(self, *args, **kwargs):
            return {
                "provider": "groq",
                "model": "test-model",
                "content": '{"summary":"Analysis is based on the uploaded file.","key_insights":["Revenue is present in the uploaded data."],"recommendations":["Review the recorded costs."]}',
            }

    monkeypatch.setattr("app.services.file_analysis_service.GroqService", FakeFileGroq)
    return TestClient(create_app())


def test_csv_processor_extracts_financials():
    csv_bytes = (
        b"month,category,revenue,expense\n"
        b"Jan,Electronics,1000,400\n"
        b"Feb,Apparel,800,350\n"
    )
    result = process_document("sales.csv", csv_bytes)
    assert result["status"] == "Analyzed"
    assert result["metrics"]["revenue"] == 1800
    assert result["metrics"]["expenses"] == 750
    assert result["metrics"]["profit"] == 1050
    assert result["categories"][0]["category"] == "Electronics"


def test_sales_fixture_is_analyzed_from_its_actual_values():
    csv_bytes = (Path(__file__).parent / "inferra_sales_test.csv").read_bytes()
    result = process_document("inferra_sales_test.csv", csv_bytes)
    assert result["row_count"] == 5
    assert result["metrics"] == {"revenue": 21600.0, "expenses": 15600.0, "profit": 6000.0}


def test_txt_file_containing_csv_table_is_analyzed_as_tabular_data():
    result = process_document(
        "data_search.txt",
        b"Order_ID,Date,Product,Category,Region,Revenue,Cost,Profit\n"
        b"ORD001,2026-01-05,Laptop,Electronics,North,2550,1950,600\n"
        b"ORD002,2026-01-07,Monitor,Electronics,South,1100,750,350\n"
        b"ORD003,2026-01-10,Chair,Furniture,East,720,480,240\n",
    )
    assert result["row_count"] == 3
    assert result["columns"] == ["Order_ID", "Date", "Product", "Category", "Region", "Revenue", "Cost", "Profit"]
    assert result["metrics"] == {"revenue": 4370.0, "expenses": 3180.0, "profit": 1190.0}
    assert result["series"]
    assert result["categories"]
    assert result["locations"]


def test_xlsx_upload_preserves_headers_rows_and_analysis(tmp_path, monkeypatch):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Date", "Product", "Revenue", "Cost"])
    sheet.append(["2026-01-05", "Laptop", 4500, 3500])
    sheet.append(["2026-01-07", "Phone", 6000, 4200])
    output = BytesIO()
    workbook.save(output)

    with _client(tmp_path, monkeypatch) as client:
        response = client.post(
            "/api/documents",
            files={"file": ("sales.xlsx", output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["success"] is True
    assert payload["document"]["columns"] == ["Date", "Product", "Revenue", "Cost"]
    assert payload["document"]["row_count"] == 2
    assert payload["document"]["metrics"] == {"revenue": 10500.0, "expenses": 7700.0, "profit": 2800.0}
    assert payload["analysis"]["summary"]


def test_ai_analysis_accepts_markdown_wrapped_json(monkeypatch):
    class MarkdownGroq:
        def __init__(self, **kwargs):
            pass

        def generate(self, *args, **kwargs):
            return {
                "provider": "groq",
                "model": "test-model",
                "content": 'Here is the result:\n```json\n{"summary":"Wrapped result","key_insights":["Insight"],"recommendations":["Action"]}\n```',
            }

    monkeypatch.setattr("app.services.file_analysis_service.GroqService", MarkdownGroq)
    result = analyze_file(
        filename="sales.csv",
        analysis={"type": "CSV", "excerpt": "revenue,expense\n100,40", "metrics": {"revenue": 100}},
        api_key="test-key",
        model="test-model",
    )
    assert result["summary"] == "Wrapped result"
    assert result["key_insights"] == ["Insight"]


def test_ai_analysis_falls_back_to_real_local_metrics_when_provider_json_is_invalid(monkeypatch):
    class InvalidGroq:
        def __init__(self, **kwargs):
            pass

        def generate(self, *args, **kwargs):
            return {"provider": "groq", "model": "test-model", "content": "not JSON"}

    monkeypatch.setattr("app.services.file_analysis_service.GroqService", InvalidGroq)
    result = analyze_file(
        filename="sales.csv",
        analysis={
            "type": "CSV",
            "excerpt": "revenue,expense\n100,40",
            "row_count": 1,
            "columns": ["revenue", "expense"],
            "metrics": {"revenue": 100, "expenses": 40, "profit": 60},
        },
        api_key="test-key",
        model="test-model",
    )
    assert result["provider"] == "local"
    assert "100.00" in result["summary"]
    assert result["warning"]


def test_upload_list_analytics_and_delete(tmp_path, monkeypatch):
    csv_bytes = b"month,revenue,expense\nJan,5000,2000\nFeb,7000,2500\n"
    with _client(tmp_path, monkeypatch) as client:
        upload = client.post(
            "/api/documents",
            files={"file": ("q1-sales.csv", csv_bytes, "text/csv")},
        )
        assert upload.status_code == 200, upload.text
        assert upload.json()["success"] is True
        document_id = upload.json()["document"]["id"]
        assert upload.json()["document"]["status"] == "Analyzed"
        assert upload.json()["analysis"]["summary"] == "Analysis is based on the uploaded file."

        listed = client.get("/api/documents")
        assert listed.status_code == 200
        assert listed.json()["count"] == 1
        assert listed.json()["items"][0]["name"] == "q1-sales.csv"

        searched = client.get("/api/documents", params={"q": "sales"})
        assert searched.json()["count"] == 1

        analytics = client.get("/api/analytics")
        assert analytics.status_code == 200
        data = analytics.json()
        assert data["kpis"]["revenue"] == 12000
        assert data["kpis"]["expenses"] == 4500
        assert data["summary"]["documents_analyzed"] == 1
        assert data["reports"]

        deleted = client.delete(f"/api/documents/{document_id}")
        assert deleted.status_code == 200
        assert client.get("/api/documents").json()["count"] == 0


def test_documents_search_matches_excerpt_and_salary_metrics(tmp_path, monkeypatch):
    csv_bytes = b"id,name,salary,bonus\n1,Alice,2500,300\n2,Bob,3000,400\n"
    with _client(tmp_path, monkeypatch) as client:
        upload = client.post(
            "/api/documents",
            files={"file": ("payroll.csv", csv_bytes, "text/csv")},
        )
        assert upload.status_code == 200, upload.text
        payload = upload.json()
        assert payload["metrics"]["expenses"] > 0
        assert payload["metrics"]["profit"] != 0

        by_name = client.get("/api/documents", params={"q": "alice"})
        assert by_name.status_code == 200
        assert by_name.json()["count"] == 1

        by_excerpt = client.get("/api/documents", params={"q": "bonus"})
        assert by_excerpt.status_code == 200
        assert by_excerpt.json()["count"] == 1


def test_numeric_table_without_financial_headers_creates_chart_series():
    result = process_document(
        "inventory.csv",
        b"item,units,valuation\nWidget,10,2500\nGadget,5,1000\n",
    )
    assert result["metrics"]["revenue"] == 3500
    assert result["series"] == [{"month": "Total", "revenue": 3500.0, "expense": 15.0, "profit": 3485.0}]


def test_location_columns_create_geographic_financial_data():
    result = process_document(
        "regional-sales.csv",
        b"country,revenue,expense\nUnited States,10000,4000\nGermany,6000,2500\n",
    )
    assert result["locations"] == [
        {"name": "United States", "revenue": 10000.0, "expense": 4000.0, "profit": 6000.0},
        {"name": "Germany", "revenue": 6000.0, "expense": 2500.0, "profit": 3500.0},
    ]


def test_rejected_file_type(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        response = client.post(
            "/api/documents",
            files={"file": ("malware.exe", b"abc", "application/octet-stream")},
        )
    assert response.status_code == 400


def test_image_upload_explains_that_ocr_is_not_available(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        response = client.post("/api/documents", files={"file": ("receipt.png", b"not-a-real-image", "image/png")})
    assert response.status_code == 422
    assert "OCR" in response.json()["detail"]


def test_empty_and_invalid_json_files_are_rejected(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        empty = client.post("/api/documents", files={"file": ("empty.txt", b"", "text/plain")})
        invalid_json = client.post("/api/documents", files={"file": ("bad.json", b"{oops", "application/json")})
    assert empty.status_code == 400
    assert invalid_json.status_code == 400


def test_json_and_text_upload_return_ai_analysis(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        for filename, content, content_type in (
            ("data.json", b'{"revenue": 1200, "expense": 500}', "application/json"),
            ("notes.txt", b"Revenue: 1200\\nExpenses: 500", "text/plain"),
        ):
            response = client.post("/api/documents", files={"file": (filename, content, content_type)})
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["success"] is True
            assert payload["analysis"]["summary"]


def test_agent_chat_uses_document_context(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")

    class FakeGroq:
        def __init__(self, api_key: str, model: str) -> None:
            self.api_key = api_key
            self.model = model

        def generate(self, user_prompt: str, *, system_prompt: str | None = None):
            assert "profit" in user_prompt.lower()
            assert system_prompt is not None
            assert "sales.csv" in system_prompt
            return {
                "model": self.model,
                "content": "Profit is $300 because revenue exceeded expenses.",
                "provider": "groq",
            }

    monkeypatch.setattr("app.api.routes.agent.GroqService", FakeGroq)

    with _client(tmp_path, monkeypatch) as client:
        client.post(
            "/api/documents",
            files={"file": ("sales.csv", b"month,revenue,expense\nJan,800,500\n", "text/csv")},
        )
        response = client.post("/api/agent/chat", json={"message": "Why did profit change?"})

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "groq"
    assert "Profit" in body["content"]
    assert body["documents_used"] == 1
