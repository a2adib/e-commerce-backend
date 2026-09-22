from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship

from src.common.mixins import CommonFieldMixin
from src.common.utils import generate_public_id

if TYPE_CHECKING:
    from src.auth.models import User


class Address(CommonFieldMixin, table=True):
    __tablename__ = "addresses"

    user_id: int = Field(
        foreign_key="users.id", index=True, nullable=False
    )
    full_name: str = Field(nullable=False, max_length=255)
    phone: str = Field(nullable=False, max_length=50)
    address_line: str = Field(nullable=False, max_length=500)
    city: str = Field(nullable=False, max_length=100)
    district: str = Field(nullable=False, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    is_default: bool = Field(default=False, nullable=False)

    user: Optional["User"] = Relationship(back_populates="addresses")

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)
