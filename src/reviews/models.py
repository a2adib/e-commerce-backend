from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship
from src.common.mixins import CommonFieldMixin
from src.common.utils import generate_public_id

if TYPE_CHECKING:
    from src.auth.models import User
    from src.products.models import Product


class Review(CommonFieldMixin, table=True):
    __tablename__ = "reviews"

    product_id: int = Field(foreign_key="products.id", index=True, nullable=False)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    rating: int = Field(nullable=False, ge=1, le=5)
    title: Optional[str] = Field(default=None, max_length=150)
    comment: str = Field(nullable=False, max_length=2000)
    is_verified_purchase: bool = Field(default=False, nullable=False)

    user: Optional["User"] = Relationship()
    product: Optional["Product"] = Relationship()

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)
