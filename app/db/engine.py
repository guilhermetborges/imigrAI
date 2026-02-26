import logging
import time

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.metrics import increment_slow_query, increment_transaction_error, observe_db_query

settings = get_settings()
logger = logging.getLogger("db.query")

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout_seconds,
)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


def _statement_operation(statement: str) -> str:
    operation = (statement or "").strip().split(" ", 1)[0]
    return operation.upper() or "UNKNOWN"


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    _ = conn, cursor, parameters, executemany
    context._query_start_time = time.perf_counter()
    context._query_operation = _statement_operation(statement)


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    _ = conn, cursor, parameters, executemany, statement
    started = getattr(context, "_query_start_time", None)
    operation = getattr(context, "_query_operation", "UNKNOWN")
    if started is None:
        return
    duration_seconds = max(0.0, time.perf_counter() - started)
    duration_ms = round(duration_seconds * 1000, 2)
    observe_db_query(operation, duration_seconds)
    if duration_ms >= settings.db_slow_query_threshold_ms:
        increment_slow_query(operation)
        logger.warning(
            "db_slow_query",
            extra={
                "operation": operation,
                "duration_ms": duration_ms,
            },
        )


@event.listens_for(engine.sync_engine, "handle_error")
def handle_db_error(context):
    operation = _statement_operation(str(getattr(context, "statement", "")))
    increment_transaction_error(operation)
