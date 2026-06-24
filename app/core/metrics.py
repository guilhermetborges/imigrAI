from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
except ImportError:  # pragma: no cover - fallback for local env without dependency
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _MetricStub:
        def labels(self, **kwargs):
            _ = kwargs
            return self

        def inc(self, amount: float = 1.0) -> None:
            _ = amount

        def set(self, value: float) -> None:
            _ = value

        def observe(self, value: float) -> None:
            _ = value

    def _counter_stub(*args, **kwargs):
        _ = args, kwargs
        return _MetricStub()

    def _gauge_stub(*args, **kwargs):
        _ = args, kwargs
        return _MetricStub()

    def _histogram_stub(*args, **kwargs):
        _ = args, kwargs
        return _MetricStub()

    def _generate_latest_stub() -> bytes:
        return b""

    Counter = _counter_stub
    Gauge = _gauge_stub
    Histogram = _histogram_stub
    generate_latest = _generate_latest_stub


HTTP_REQUESTS_TOTAL = Counter(
    "imigrai_http_requests_total",
    "Total de requests HTTP recebidas.",
    labelnames=("method", "path", "status_code"),
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "imigrai_http_request_duration_seconds",
    "Latencia de requests HTTP por endpoint.",
    labelnames=("method", "path", "status_code"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

BUSINESS_SCORE_DURATION_SECONDS = Histogram(
    "imigrai_business_score_duration_seconds",
    "Duracao de processamento do score.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 40, 60),
)
BUSINESS_ROADMAP_DURATION_SECONDS = Histogram(
    "imigrai_business_roadmap_duration_seconds",
    "Duracao de processamento de roadmap.",
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 40, 90, 180),
)
BUSINESS_LLM_REQUESTS_TOTAL = Counter(
    "imigrai_business_llm_provider_requests_total",
    "Requests para provider LLM por status.",
    labelnames=("provider", "result"),
)
BUSINESS_FREE_TO_PRO_CONVERSIONS_TOTAL = Counter(
    "imigrai_business_free_to_pro_conversions_total",
    "Conversoes de plano free para pro.",
)

CELERY_QUEUE_JOBS = Gauge(
    "imigrai_celery_jobs",
    "Quantidade de jobs por fila e status.",
    labelnames=("queue", "status"),
)
SERVICE_UP = Gauge(
    "imigrai_service_up",
    "Disponibilidade do servico (1=up, 0=down).",
    labelnames=("service",),
)
SERVICE_HEARTBEAT_TIMESTAMP = Gauge(
    "imigrai_service_heartbeat_timestamp",
    "Timestamp UNIX do ultimo heartbeat por servico.",
    labelnames=("service",),
)
POSTGRES_ACTIVE_CONNECTIONS = Gauge(
    "imigrai_postgres_active_connections",
    "Conexoes ativas no Postgres.",
)
DB_QUERY_DURATION_SECONDS = Histogram(
    "imigrai_db_query_duration_seconds",
    "Duracao de queries SQL.",
    labelnames=("operation",),
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1, 2, 5),
)
DB_SLOW_QUERIES_TOTAL = Counter(
    "imigrai_db_slow_queries_total",
    "Quantidade de queries lentas.",
    labelnames=("operation",),
)
DB_TRANSACTION_ERRORS_TOTAL = Counter(
    "imigrai_db_transaction_errors_total",
    "Quantidade de erros de transacao no banco.",
    labelnames=("operation",),
)

JOB_TYPE_TO_QUEUE = {
    "score_job": "score_queue",
    "roadmap_job": "roadmap_queue",
}
QUEUE_STATUS_LABELS = ("pending", "running", "failed", "dead_letter", "completed")


def mark_service_up(service: str) -> None:
    SERVICE_UP.labels(service=service).set(1)


def mark_service_down(service: str) -> None:
    SERVICE_UP.labels(service=service).set(0)


def update_service_heartbeat(service: str, timestamp: float) -> None:
    SERVICE_HEARTBEAT_TIMESTAMP.labels(service=service).set(timestamp)
    mark_service_up(service)


def observe_http_request(
    *, method: str, path: str, status_code: int, duration_seconds: float
) -> None:
    labels = {
        "method": method.upper(),
        "path": path,
        "status_code": str(status_code),
    }
    HTTP_REQUESTS_TOTAL.labels(**labels).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(**labels).observe(duration_seconds)


def observe_score_duration(duration_seconds: float) -> None:
    BUSINESS_SCORE_DURATION_SECONDS.observe(duration_seconds)


def observe_roadmap_duration(duration_seconds: float) -> None:
    BUSINESS_ROADMAP_DURATION_SECONDS.observe(duration_seconds)


def increment_llm_provider(provider: str, result: str) -> None:
    BUSINESS_LLM_REQUESTS_TOTAL.labels(provider=provider, result=result).inc()


def increment_free_to_pro_conversion() -> None:
    BUSINESS_FREE_TO_PRO_CONVERSIONS_TOTAL.inc()


def observe_db_query(operation: str, duration_seconds: float) -> None:
    DB_QUERY_DURATION_SECONDS.labels(operation=operation.upper()).observe(duration_seconds)


def increment_slow_query(operation: str) -> None:
    DB_SLOW_QUERIES_TOTAL.labels(operation=operation.upper()).inc()


def increment_transaction_error(operation: str) -> None:
    DB_TRANSACTION_ERRORS_TOTAL.labels(operation=operation.upper()).inc()


async def refresh_operational_metrics(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as db:
        await _refresh_job_queue_metrics(db)
        await _refresh_postgres_connections(db)


async def _refresh_job_queue_metrics(db: AsyncSession) -> None:
    from apps.common.models import Job

    for queue in JOB_TYPE_TO_QUEUE.values():
        for status in QUEUE_STATUS_LABELS:
            CELERY_QUEUE_JOBS.labels(queue=queue, status=status).set(0)

    counts = await db.execute(
        select(Job.job_type, Job.status, func.count(Job.id))
        .group_by(Job.job_type, Job.status)
        .order_by(Job.job_type, Job.status)
    )
    for job_type, status, total in counts:
        queue = JOB_TYPE_TO_QUEUE.get(str(job_type), "default")
        CELERY_QUEUE_JOBS.labels(queue=queue, status=str(status)).set(int(total))


async def _refresh_postgres_connections(db: AsyncSession) -> None:
    try:
        result = await db.execute(
            text(
                "SELECT count(*)::int "
                "FROM pg_stat_activity "
                "WHERE datname = current_database() AND state = 'active'"
            )
        )
        active_connections = result.scalar_one()
    except Exception:
        active_connections = 0
    POSTGRES_ACTIVE_CONNECTIONS.set(int(active_connections))


def render_metrics_payload() -> tuple[bytes, str]:
    payload = generate_latest()
    return payload, CONTENT_TYPE_LATEST
