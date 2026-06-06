from celery import Celery

from app.config import get_settings


settings = get_settings()

celery_app = Celery(
    "techleveler",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.health_tasks", "app.tasks.generation_tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    timezone="UTC",
)
