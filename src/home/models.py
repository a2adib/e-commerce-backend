from enum import Enum
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, JSON, Column
import sqlalchemy as sa
from sqlalchemy import DateTime

from src.common.mixins import IDMixin, TimestampMixin
from src.common.utils import generate_public_id


class HomePageStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class HomePage(IDMixin, table=True):
    __tablename__ = "home_pages"

    status: HomePageStatus = Field(
        default=HomePageStatus.DRAFT,
        sa_column=Column(sa.Enum(HomePageStatus, native_enum=False), default=HomePageStatus.DRAFT, nullable=False, index=True),
    )
    sections: List[dict] = Field(default=[], sa_column=Column(JSON, nullable=False))
    published_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)
