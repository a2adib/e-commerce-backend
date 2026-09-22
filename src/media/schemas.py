from typing import Optional
from pydantic import BaseModel, ConfigDict


class MediaUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    filename: str
    url: str
    mime_type: str
    size_bytes: int
    uploaded_by: Optional[str]


class MediaReuseRequest(BaseModel):
    media_public_id: str
