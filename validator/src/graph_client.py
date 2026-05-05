"""Matrix fetcher backed by Azure Blob Storage.

Class name kept as `SharePointListFetcher` for backward compatibility with
existing tests/imports. Reads JSON arrays from blobs in a single container.

Env vars:
- MATRIX_CONNECTION_STRING (or AZURE_TABLE_CONNECTION_STRING / AzureWebJobsStorage)
- MATRIX_CONTAINER (default: "matrices")
- PERMISSION_MATRIX_BLOB (default: "permission_matrix.json")
- ESCALATION_MATRIX_BLOB (default: "escalation_matrix.json")
"""

import json
import logging
import os
from functools import lru_cache
from typing import Dict, List

from azure.storage.blob import BlobServiceClient


def _conn_string() -> str:
    for name in ("MATRIX_CONNECTION_STRING", "AZURE_TABLE_CONNECTION_STRING", "AzureWebJobsStorage"):
        v = os.getenv(name)
        if v:
            return v
    return ""


class SharePointListFetcher:  # name kept for compat
    """Reads governance matrices from Azure Blob Storage."""

    def __init__(self):
        self.conn = _conn_string()
        self.container = os.getenv("MATRIX_CONTAINER", "matrices")
        self.permission_blob = os.getenv("PERMISSION_MATRIX_BLOB", "permission_matrix.json")
        self.escalation_blob = os.getenv("ESCALATION_MATRIX_BLOB", "escalation_matrix.json")
        self._client = None
        if self.conn:
            try:
                self._client = BlobServiceClient.from_connection_string(self.conn)
            except Exception as exc:
                logging.error("Failed to init BlobServiceClient: %s", exc)

    def _read_json_blob(self, blob_name: str) -> List[Dict]:
        if not self._client:
            return []
        try:
            blob = self._client.get_blob_client(container=self.container, blob=blob_name)
            data = blob.download_blob().readall()
            payload = json.loads(data)
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict) and "items" in payload:
                return payload["items"]
            logging.warning("Blob %s/%s payload not a list", self.container, blob_name)
            return []
        except Exception as exc:
            logging.warning("Blob fetch failed (%s/%s): %s", self.container, blob_name, exc)
            return []

    @lru_cache(maxsize=1)
    def fetch_permission_matrix(self) -> List[Dict]:
        return self._read_json_blob(self.permission_blob)

    @lru_cache(maxsize=1)
    def fetch_escalation_matrix(self) -> List[Dict]:
        return self._read_json_blob(self.escalation_blob)
