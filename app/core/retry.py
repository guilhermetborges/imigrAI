from __future__ import annotations

from sqlalchemy.exc import IntegrityError, OperationalError

from apps.roadmaps.llm import LLMProviderError, LLMProviderResponseError, LLMProviderTimeoutError


def is_transient_error(exc: Exception) -> bool:
    if is_definitive_error(exc):
        return False
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    if isinstance(exc, (OperationalError, LLMProviderTimeoutError)):
        return True
    if isinstance(exc, LLMProviderError) and not isinstance(exc, LLMProviderResponseError):
        return True
    # Default para erros desconhecidos: tratar como transitorio.
    return True


def is_definitive_error(exc: Exception) -> bool:
    if isinstance(exc, (ValueError, AssertionError, TypeError, IntegrityError)):
        return True
    if isinstance(exc, LLMProviderResponseError):
        return True
    return False
