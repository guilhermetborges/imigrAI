import logging
import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Request
from pythonjsonlogger.json import JsonFormatter
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.log_context import bind_log_context, clear_log_context, get_log_context
from app.core.metrics import observe_http_request


class UTCJsonFormatter(JsonFormatter):
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(UTC).isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["trace_id"] = getattr(record, "trace_id", None)
        log_record["user_id"] = getattr(record, "user_id", None)
        log_record["assessment_id"] = getattr(record, "assessment_id", None)
        log_record["roadmap_id"] = getattr(record, "roadmap_id", None)


class ContextEnrichmentFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = get_log_context()
        for key, value in context.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or str(uuid4())
        request.state.trace_id = trace_id
        clear_log_context()
        bind_log_context(trace_id=trace_id)
        start = time.perf_counter()
        response = None
        status_code = 500
        path = self._resolve_path_template(request)

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["x-trace-id"] = trace_id
            return response
        finally:
            latency_seconds = max(0.0, time.perf_counter() - start)
            latency_ms = round(latency_seconds * 1000, 2)
            observe_http_request(
                method=request.method,
                path=path,
                status_code=status_code,
                duration_seconds=latency_seconds,
            )
            bind_log_context(
                assessment_id=request.path_params.get("assessment_id"),
                roadmap_id=request.path_params.get("roadmap_id"),
            )
            logging.getLogger("http.access").info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": path,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                },
            )
            clear_log_context()

    def _resolve_path_template(self, request: Request) -> str:
        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            return str(route.path)
        return request.url.path


def configure_logging(log_level: str) -> None:
    handler = logging.StreamHandler()
    formatter = UTCJsonFormatter("%(message)s")
    handler.setFormatter(formatter)
    handler.addFilter(ContextEnrichmentFilter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())
