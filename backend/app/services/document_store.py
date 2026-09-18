from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.database import MongoDatabase


class DocumentStore:
    def __init__(
        self,
        database: MongoDatabase,
        upload_dir: Path,
        index_path: Path,
    ) -> None:
        self.database = database
        self.upload_dir = upload_dir
        self.index_path = index_path
        self._lock = threading.Lock()
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self.index_path.write_text("[]", encoding="utf-8")

    def _mongo_collection(self):
        if self.database.client is None:
            return None
        try:
            return self.database.database["documents"]
        except RuntimeError:
            return None

    def _read_file_index(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []

    def _write_file_index(self, documents: list[dict[str, Any]]) -> None:
        self.index_path.write_text(json.dumps(documents, indent=2), encoding="utf-8")

    def _mongo_call(self, operation):
        collection = self._mongo_collection()
        if collection is None:
            return None
        try:
            return operation(collection)
        except Exception:
            return None

    def list_documents(self, query: str = "") -> list[dict[str, Any]]:
        with self._lock:
            documents = self._read_file_index()
        if not documents:
            mongo_documents = self._mongo_call(
                lambda collection: list(collection.find({}, projection={"_id": 0}))
            )
            if isinstance(mongo_documents, list) and mongo_documents:
                documents = mongo_documents

        documents.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        needle = query.strip().lower()
        if needle:
            def searchable_text(item: dict[str, Any]) -> str:
                values: list[str] = [
                    str(item.get("name", "")),
                    str(item.get("type", "")),
                    str(item.get("status", "")),
                    str(item.get("owner", "")),
                    str(item.get("excerpt", "")),
                    str(item.get("date", "")),
                ]
                for key in ("columns", "metrics", "series", "categories", "alerts"):
                    value = item.get(key, [])
                    if isinstance(value, (list, dict)):
                        values.append(json.dumps(value, ensure_ascii=False))
                    else:
                        values.append(str(value))
                return " ".join(values).lower()

            documents = [
                item
                for item in documents
                if needle in searchable_text(item)
            ]
        return documents

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with self._lock:
            for item in self._read_file_index():
                if item.get("id") == document_id:
                    return item
        document = self._mongo_call(
            lambda collection: collection.find_one({"id": document_id}, projection={"_id": 0})
        )
        return dict(document) if isinstance(document, dict) else None

    def save_document(self, document: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            documents = self._read_file_index()
            documents = [item for item in documents if item.get("id") != document["id"]]
            documents.append(document)
            self._write_file_index(documents)
        self._mongo_call(
            lambda collection: collection.replace_one({"id": document["id"]}, document, upsert=True)
        )
        return document

    def delete_document(self, document_id: str) -> bool:
        existing = self.get_document(document_id)
        if existing is None:
            return False
        file_path = existing.get("file_path")
        if file_path:
            path = Path(file_path)
            if path.exists():
                path.unlink()
        with self._lock:
            documents = [item for item in self._read_file_index() if item.get("id") != document_id]
            self._write_file_index(documents)
        self._mongo_call(lambda collection: collection.delete_one({"id": document_id}))
        return True

    def create_document(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        owner: str,
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        document_id = str(uuid.uuid4())
        stored_name = f"{document_id}_{Path(filename).name}"
        stored_path = self.upload_dir / stored_name
        stored_path.write_bytes(content)
        created_at = datetime.now(timezone.utc).isoformat()
        document = {
            "id": document_id,
            "name": filename,
            "type": analysis.get("type") or Path(filename).suffix.lstrip(".").upper(),
            "status": analysis.get("status", "Uploaded"),
            "owner": owner,
            "date": created_at[:10],
            "created_at": created_at,
            "size_bytes": len(content),
            "content_type": content_type,
            "file_path": str(stored_path),
            "excerpt": analysis.get("excerpt", ""),
            "row_count": analysis.get("row_count", 0),
            "columns": analysis.get("columns", []),
            "metrics": analysis.get("metrics", {"revenue": 0, "expenses": 0, "profit": 0}),
            "series": analysis.get("series", []),
            "categories": analysis.get("categories", []),
            "locations": analysis.get("locations", []),
            "alerts": analysis.get("alerts", []),
            "analysis": analysis.get("analysis"),
        }
        return self.save_document(document)
