from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship, Column
import sqlalchemy as sa
from enum import Enum

from src.common.mixins import CommonFieldMixin
from src.common.utils import generate_public_id

if TYPE_CHECKING:
    from src.orders.models import Order
    from src.cart.models import Cart
    from src.wishlist.models import WishlistItem
    from src.addresses.models import Address


class UserRole(str, Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"


class User(CommonFieldMixin, table=True):
    __tablename__ = "users"

    name: str = Field(nullable=False, max_length=255)
    email: str = Field(unique=True, index=True, nullable=False, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    password_hash: str = Field(nullable=False, max_length=255)
    role: UserRole = Field(
        default=UserRole.CUSTOMER,
        sa_column=Column(sa.Enum(UserRole, native_enum=False), nullable=False, default=UserRole.CUSTOMER),
    )
    avatar_url: Optional[str] = Field(default=None, max_length=512)

    orders: list["Order"] = Relationship(back_populates="user")
    cart: Optional["Cart"] = Relationship(back_populates="user")
    wishlist_items: list["WishlistItem"] = Relationship(back_populates="user")
    addresses: list["Address"] = Relationship(back_populates="user")

    def __init__(self, **data):
        # Backward compatibility if full_name is passed
        if "full_name" in data and "name" not in data:
            data["name"] = data.pop("full_name")
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)

    @property
    def full_name(self) -> str:
        return self.name
