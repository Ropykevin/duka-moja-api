from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.health_check")
def health_check() -> dict[str, str]:
    return {"status": "ok", "worker": "dukamoja"}


@celery_app.task(name="app.worker.tasks.deliver_webhook_event")
def deliver_webhook_event(event_id: str, tenant_id: str) -> dict[str, str]:
    """Placeholder for webhook HTTP delivery — implement with httpx in production."""
    return {"status": "queued", "event_id": event_id, "tenant_id": tenant_id}
