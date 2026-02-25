from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from email.message import Message
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from apps.ingestion.models import SourceRegistry, SourceType

logger = logging.getLogger(__name__)


class RobotsPolicyError(PermissionError):
    pass


@dataclass(slots=True)
class FetchResult:
    source_url: str
    final_url: str
    content: bytes
    content_type: str | None
    content_length: int | None
    title: str
    etag: str | None
    last_modified: str | None
    metadata_json: dict


class SourceFetcher:
    def __init__(
        self,
        *,
        user_agent: str,
        timeout_seconds: int,
        enforce_robots: bool = True,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.enforce_robots = enforce_robots

    def fetch(self, source: SourceRegistry) -> FetchResult:
        self._validate_robots(source)

        request = Request(
            source.source_url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "*/*",
            },
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                body = response.read()
                headers = response.headers
                final_url = response.geturl()
                content_type = self._header(headers, "Content-Type")
                content_length = self._parse_content_length(self._header(headers, "Content-Length"))
                etag = self._header(headers, "ETag")
                last_modified = self._header(headers, "Last-Modified")
        except HTTPError as exc:
            raise RuntimeError(f"source fetch failed with HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"source fetch failed: {exc.reason}") from exc

        if source.source_type == SourceType.api:
            body, content_type = self._normalize_api_payload(body, content_type)

        title = self._resolve_title(body, content_type, source.source_key)
        return FetchResult(
            source_url=source.source_url,
            final_url=final_url,
            content=body,
            content_type=content_type,
            content_length=content_length if content_length is not None else len(body),
            title=title,
            etag=etag,
            last_modified=last_modified,
            metadata_json={
                "fetcher": "urllib",
                "source_type": source.source_type.value,
            },
        )

    def _validate_robots(self, source: SourceRegistry) -> None:
        if not self.enforce_robots:
            return

        robots_url = source.robots_url or self._build_default_robots_url(source.source_url)
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
        except Exception as exc:  # pragma: no cover - network/robots instability
            raise RobotsPolicyError(f"could not read robots.txt ({robots_url}): {exc}") from exc

        if not parser.can_fetch(self.user_agent, source.source_url):
            raise RobotsPolicyError(f"robots policy disallows fetch: {source.source_url}")

    def _build_default_robots_url(self, source_url: str) -> str:
        parsed = urlparse(source_url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def _header(self, headers: Message, key: str) -> str | None:
        value = headers.get(key)
        return value.strip() if value else None

    def _parse_content_length(self, value: str | None) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _normalize_api_payload(self, body: bytes, content_type: str | None) -> tuple[bytes, str]:
        try:
            parsed = json.loads(body.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"api source returned invalid JSON: {exc}") from exc

        normalized = json.dumps(parsed, ensure_ascii=True, sort_keys=True, indent=2)
        return normalized.encode("utf-8"), content_type or "application/json"

    def _resolve_title(self, body: bytes, content_type: str | None, fallback: str) -> str:
        lowered = (content_type or "").lower()
        if "text/html" in lowered:
            text = body.decode("utf-8", errors="ignore")
            match = re.search(r"<title>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return self._normalize_whitespace(match.group(1))[:255]
        if "application/json" in lowered:
            return f"{fallback} json payload"
        if "application/pdf" in lowered:
            return f"{fallback} pdf document"
        return fallback

    def _normalize_whitespace(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()
