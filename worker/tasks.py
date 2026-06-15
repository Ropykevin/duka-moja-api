from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.health_check")
def health_check() -> dict[str, str]:
    return {"status": "ok", "worker": "dukamoja"}


@celery_app.task(name="app.worker.tasks.send_welcome_email")
def send_welcome_email(tenant_id: str, user_email: str) -> dict[str, str]:
    """Placeholder for welcome email - implement in Phase 2."""
    return {"status": "queued", "tenant_id": tenant_id, "email": user_email}
