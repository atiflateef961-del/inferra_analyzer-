from __future__ import annotations

from pymongo import MongoClient
from pymongo.errors import PyMongoError


class MongoDatabase:
    def __init__(self, uri: str, database_name: str, server_selection_timeout_ms: int) -> None:
        self.uri = uri
        self.database_name = database_name
        self.server_selection_timeout_ms = server_selection_timeout_ms
        self.client: MongoClient | None = None
        self.last_error: PyMongoError | None = None

    def connect(self) -> bool:
        client: MongoClient | None = None
        try:
            client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=self.server_selection_timeout_ms,
            )
            client.admin.command("ping")
        except PyMongoError as error:
            self.last_error = error
            if client is not None:
                client.close()
            self.client = None
            return False

        self.client = client
        self.last_error = None
        return True

    def ping(self) -> bool:
        if self.client is None:
            return self.connect()

        try:
            self.client.admin.command("ping")
        except PyMongoError as error:
            self.last_error = error
            return False

        self.last_error = None
        return True

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None

    @property
    def database(self):
        if self.client is None:
            raise RuntimeError("MongoDB is not connected")
        return self.client[self.database_name]
