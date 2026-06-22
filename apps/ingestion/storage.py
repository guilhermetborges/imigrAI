from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID


@dataclass(slots=True)
class StoredObject:
    bucket: str
    path: str
    uri: str
    metadata_json: dict


class BronzeStorageClient:
    def __init__(
        self,
        *,
        bucket: str,
        local_fallback_dir: str,
    ) -> None:
        self.bucket = bucket
        self.local_fallback_dir = Path(local_fallback_dir)

    def store(
        self,
        *,
        source_key: str,
        run_item_id: UUID,
        payload: bytes,
        content_type: str | None,
    ) -> StoredObject:
        now = datetime.now(UTC)
        extension = self._guess_extension(content_type)
        object_path = f"{now:%Y/%m/%d}/{source_key}/{run_item_id}{extension}"

        local_uri = self._store_local(object_path=object_path, payload=payload)
        return StoredObject(
            bucket=self.bucket,
            path=object_path,
            uri=local_uri,
            metadata_json={"storage_backend": "local"},
        )

    def _store_local(self, *, object_path: str, payload: bytes) -> str:
        file_path = self.local_fallback_dir / self.bucket / object_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(payload)
        return str(file_path)

    def _guess_extension(self, content_type: str | None) -> str:
        lowered = (content_type or "").lower()
        if "pdf" in lowered:
            return ".pdf"
        if "json" in lowered:
            return ".json"
        if "html" in lowered:
            return ".html"
        return ".bin"
