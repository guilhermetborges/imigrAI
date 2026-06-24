from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_LOG_CONTEXT_KEYS = ("trace_id", "user_id", "assessment_id", "roadmap_id")
_log_context: ContextVar[dict[str, str | None] | None] = ContextVar(
    "imigrai_log_context", default=None
)


def _empty_log_context() -> dict[str, str | None]:
    return dict.fromkeys(_LOG_CONTEXT_KEYS)


def get_log_context() -> dict[str, str | None]:
    context = _log_context.get() or _empty_log_context()
    return {key: context.get(key) for key in _LOG_CONTEXT_KEYS}


def bind_log_context(**kwargs: str | None) -> None:
    current = (_log_context.get() or _empty_log_context()).copy()
    for key in _LOG_CONTEXT_KEYS:
        if key in kwargs:
            current[key] = kwargs[key]
    _log_context.set(current)


def clear_log_context() -> None:
    _log_context.set(_empty_log_context())


@contextmanager
def log_context(**kwargs: str | None) -> Iterator[None]:
    previous = (_log_context.get() or _empty_log_context()).copy()
    bind_log_context(**kwargs)
    try:
        yield
    finally:
        _log_context.set(previous)
