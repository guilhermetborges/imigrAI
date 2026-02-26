import logging
from datetime import UTC, datetime

from app.core.celery_app import celery_app
from app.core.metrics import update_service_heartbeat

logger = logging.getLogger(__name__)


@celery_app.task(name="apps.common.tasks.heartbeat")
def heartbeat() -> str:
    now = datetime.now(UTC).isoformat()
    update_service_heartbeat("worker", datetime.now(UTC).timestamp())
    logger.info("celery_heartbeat", extra={"at": now})
    return now


@celery_app.task(name="apps.common.tasks.dead_letter_event")
def dead_letter_event(*, source: str, payload: dict) -> dict:
    logger.error("dead_letter_event", extra={"source": source, "payload": payload})
    return {"source": source, "received": True}
