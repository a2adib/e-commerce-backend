from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship, UniqueConstraint

from src.common.mixins import CommonFieldMixin
from src.common.utils import generate_public_id

if TYPE_CHECKING:
    from src.auth.models import User
    from src.products.models import Product


class WishlistItem(CommonFieldMixin, table=True):
    __tablename__ = "wishlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_user_wishlist_product"),
    )

    user_id: int = Field(
        foreign_key="users.id", index=True, nullable=False
    )
    product_id: int = Field(
        foreign_key="products.id", index=True, nullable=False
    )

    user: Optional["User"] = Relationship(back_populates="wishlist_items")
    product: Optional["Product"] = Relationship(back_populates="wishlist_items")

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)
