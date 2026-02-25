import logging
from datetime import UTC, datetime

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="apps.common.tasks.heartbeat")
def heartbeat() -> str:
    now = datetime.now(UTC).isoformat()
    logger.info("celery_heartbeat", extra={"at": now})
    return now
