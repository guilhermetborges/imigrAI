from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

logger = logging.getLogger(__name__)


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
        supabase_url: str | None,
        service_role_key: str | None,
        local_fallback_dir: str,
    ) -> None:
        self.bucket = bucket
        self.supabase_url = (supabase_url or "").rstrip("/")
        self.service_role_key = service_role_key
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
        object_path = (
            f"{now:%Y/%m/%d}/{source_key}/{run_item_id}{extension}"
        )

        if self.supabase_url and self.service_role_key:
            try:
                uri = self._store_supabase(
                    object_path=object_path,
                    payload=payload,
                    content_type=content_type,
                )
                return StoredObject(
                    bucket=self.bucket,
                    path=object_path,
                    uri=uri,
                    metadata_json={"storage_backend": "supabase"},
                )
            except Exception as exc:  # pragma: no cover - network environment instability
                logger.warning(
                    "supabase_storage_fallback",
                    extra={"bucket": self.bucket, "object_path": object_path, "error": str(exc)},
                )

        local_uri = self._store_local(object_path=object_path, payload=payload)
        return StoredObject(
            bucket=self.bucket,
            path=object_path,
            uri=local_uri,
            metadata_json={"storage_backend": "local-fallback"},
        )

    def _store_supabase(self, *, object_path: str, payload: bytes, content_type: str | None) -> str:
        endpoint = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{object_path}"
        request = Request(
            endpoint,
            method="POST",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.service_role_key}",
                "apikey": self.service_role_key or "",
                "Content-Type": content_type or "application/octet-stream",
                "x-upsert": "true",
            },
        )
        try:
            with urlopen(request, timeout=30):  # noqa: S310
                pass
        except HTTPError as exc:
            raise RuntimeError(f"supabase storage upload failed HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"supabase storage upload failed: {exc.reason}") from exc

        return f"supabase://{self.bucket}/{object_path}"

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
