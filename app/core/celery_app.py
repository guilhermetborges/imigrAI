from celery import Celery
from kombu import Queue

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "imigrai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "apps.common.tasks",
        "apps.assessments.tasks",
        "apps.roadmaps.tasks",
        "apps.ingestion.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_default_queue="default",
    task_queues=(
        Queue("default"),
        Queue("score_queue"),
        Queue("roadmap_queue"),
        Queue("ingestion_queue"),
    ),
    task_routes={
        "apps.assessments.tasks.process_assessment_task": {"queue": "score_queue"},
        "apps.roadmaps.tasks.generate_roadmap_task": {"queue": "roadmap_queue"},
        "apps.ingestion.tasks.ingest_source_task": {"queue": "ingestion_queue"},
    },
    task_queue_max_priority=10,
    broker_transport_options={
        "queue_order_strategy": "priority",
    },
    beat_schedule={
        "heartbeat-every-minute": {
            "task": "apps.common.tasks.heartbeat",
            "schedule": 60.0,
        },
        "dispatch-ingestion-every-6-hours": {
            "task": "apps.ingestion.tasks.dispatch_scheduled_ingestion",
            "schedule": 21600.0,
        }
    },
)
