import logging
from celery import Celery
from src.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "ecommerce_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="send_order_confirmation_email")
def send_order_confirmation_email(order_number: str, customer_email: str, total_amount: float):
    """
    Simulates sending order confirmation email asynchronously via Celery worker.
    """
    logger.info(
        f"[CELERY] Sending order confirmation email for Order #{order_number} to {customer_email}. Total: {total_amount}"
    )
    return {"status": "sent", "order_number": order_number, "to": customer_email}
