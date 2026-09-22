from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

from src.common.mixins import CommonFieldMixin
from src.common.utils import generate_public_id

if TYPE_CHECKING:
    from src.auth.models import User


class MediaAsset(CommonFieldMixin, table=True):
    __tablename__ = "media_assets"

    filename: str = Field(nullable=False, max_length=512)
    url: str = Field(unique=True, index=True, nullable=False, max_length=1024)
    mime_type: str = Field(nullable=False, max_length=128)
    size_bytes: int = Field(nullable=False, ge=0)

    uploaded_by: Optional[int] = Field(
        default=None, foreign_key="users.id", nullable=True
    )

    uploader: Optional["User"] = Relationship(back_populates="uploads")

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)
