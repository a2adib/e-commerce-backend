from typing import Optional
from sqlmodel import Field
from src.common.mixins import IDMixin, TimestampMixin
from src.common.utils import generate_public_id

class StoreSettings(IDMixin, TimestampMixin, table=True):
    __tablename__ = "store_settings"

    brand_name: str = Field(default="My Store", nullable=False)
    logo_url: Optional[str] = Field(default=None, nullable=True)

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)
