from typing import Optional, TYPE_CHECKING, List
from sqlmodel import Field, Relationship, UniqueConstraint

from src.common.mixins import CommonFieldMixin
from src.common.utils import generate_public_id

if TYPE_CHECKING:
    from src.auth.models import User
    from src.products.models import Product


class Cart(CommonFieldMixin, table=True):
    __tablename__ = "carts"

    user_id: int = Field(
        foreign_key="users.id", unique=True, index=True, nullable=False
    )

    user: Optional["User"] = Relationship(back_populates="cart")
    items: List["CartItem"] = Relationship(
        back_populates="cart",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)


class CartItem(CommonFieldMixin, table=True):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
    )

    cart_id: int = Field(
        foreign_key="carts.id", index=True, nullable=False
    )
    product_id: int = Field(
        foreign_key="products.id", index=True, nullable=False
    )
    quantity: int = Field(default=1, nullable=False, ge=1)

    cart: Optional["Cart"] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship(back_populates="cart_items")

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)
