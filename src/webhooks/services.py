import stripe
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.orders.models import Order, OrderStatus
from src.common.exceptions import http_400


async def process_stripe_webhook(
    session: AsyncSession, payload: bytes, sig_header: str
) -> dict:
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise http_400("Invalid webhook signature")

    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        payment_intent = data.get("payment_intent")
        if payment_intent:
            result = await session.execute(
                select(Order).where(
                    Order.stripe_payment_intent_id == payment_intent
                )
            )
            order = result.scalar_one_or_none()
            if order:
                order.status = OrderStatus.CONFIRMED
                session.add(order)
                await session.commit()
                await session.refresh(order)

        return {"received": True, "status": "confirmed"}

    if event_type == "payment_intent.payment_failed":
        payment_intent = data.get("id")
        if payment_intent:
            result = await session.execute(
                select(Order).where(
                    Order.stripe_payment_intent_id == payment_intent
                )
            )
            order = result.scalar_one_or_none()
            if order:
                from src.common.queries import soft_delete_instance
                await soft_delete_instance(session, order)

        return {"received": True, "status": "failed"}

    return {"received": True, "type": event_type}
