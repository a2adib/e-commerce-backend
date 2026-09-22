from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database import get_session
from src.common.response import StandardResponse
from src.webhooks.services import process_stripe_webhook

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    result = await process_stripe_webhook(session, payload, sig_header)
    return StandardResponse(data=result)
