import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

celery_app = Celery(
    "docuchat",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "queues.document_tasks",
        "queues.webhook_tasks",
        "queues.external_api_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    task_track_started=True,

    task_default_queue="document-processing",

    task_acks_late=True,
    worker_prefetch_multiplier=1,

    result_expires=86400,

    task_default_retry_delay=2,
    task_annotations={
        "queues.document_tasks.process_document": {
            "max_retries": 2,
        }
    },
)

celery_app.conf.beat_schedule = {
    "recover-stuck-webhooks": {
        "task": "queues.webhook_tasks.recover_webhooks",
        "schedule": 60.0,
    },
}