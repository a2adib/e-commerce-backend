from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database import get_session
from src.common.response import StandardResponse
from src.common.filters import PaginationParams
from src.auth.dependencies import get_optional_current_user
from src.auth.models import User
from src.media.schemas import MediaUploadResponse
from src.media.services import (
    upload_media_service,
    reuse_media_service,
    list_media_gallery_service,
)

router = APIRouter(prefix="/media", tags=["Media"])


@router.post(
    "/upload",
    response_model=StandardResponse[MediaUploadResponse],
    status_code=201,
)
async def upload_media(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> StandardResponse[MediaUploadResponse]:
    contents = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    user_id = current_user.id if current_user else None
    asset = await upload_media_service(
        session, file.filename or "untitled", contents, mime_type, user_id
    )
    return StandardResponse(
        message="File uploaded successfully",
        data=MediaUploadResponse(
            public_id=asset.public_id,
            filename=asset.filename,
            url=asset.url,
            mime_type=asset.mime_type,
            size_bytes=asset.size_bytes,
            uploaded_by=asset.uploader.public_id if asset.uploader else None,
        ),
    )


@router.get(
    "/gallery",
    response_model=StandardResponse[list[MediaUploadResponse]],
)
async def list_media_gallery(
    pagination: PaginationParams = Depends(),
    mime_type: Optional[str] = Query(None, description="Filter by mime type prefix (e.g. image)"),
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[list[MediaUploadResponse]]:
    assets, total = await list_media_gallery_service(
        session, pagination.page, pagination.page_size, mime_type
    )
    return StandardResponse(
        data=[
            MediaUploadResponse(
                public_id=a.public_id,
                filename=a.filename,
                url=a.url,
                mime_type=a.mime_type,
                size_bytes=a.size_bytes,
                uploaded_by=a.uploader.public_id if a.uploader else None,
            )
            for a in assets
        ],
    )
