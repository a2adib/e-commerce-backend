from typing import Optional, TYPE_CHECKING, List
from sqlmodel import Field, Relationship, JSON, Column

from src.common.mixins import CommonFieldMixin
from src.common.utils import generate_public_id

if TYPE_CHECKING:
    from src.categories.models import Category
    from src.orders.models import OrderItem
    from src.cart.models import CartItem
    from src.wishlist.models import WishlistItem


class Product(CommonFieldMixin, table=True):
    __tablename__ = "products"

    name: str = Field(nullable=False, max_length=255)
    slug: str = Field(unique=True, index=True, nullable=False, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4096)
    price: float = Field(nullable=False, ge=0)
    compare_at_price: Optional[float] = Field(default=None, ge=0)
    sku: Optional[str] = Field(default=None, index=True, max_length=100)
    stock_qty: int = Field(default=0, nullable=False, ge=0)
    images: List[str] = Field(
        default=[], sa_column=Column(JSON, nullable=False)
    )
    is_featured: bool = Field(default=False, nullable=False)

    category_id: int = Field(
        default=None, foreign_key="categories.id", nullable=False
    )

    category: Optional["Category"] = Relationship(back_populates="products")
    order_items: List["OrderItem"] = Relationship(back_populates="product")
    cart_items: List["CartItem"] = Relationship(back_populates="product")
    wishlist_items: List["WishlistItem"] = Relationship(back_populates="product")

    def __init__(self, **data):
        # Backward compatibility for stock_quantity / image_urls if passed
        if "stock_quantity" in data and "stock_qty" not in data:
            data["stock_qty"] = data.pop("stock_quantity")
        if "image_urls" in data and "images" not in data:
            data["images"] = data.pop("image_urls")
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)

    @property
    def stock_quantity(self) -> int:
        return self.stock_qty

    @property
    def image_urls(self) -> List[str]:
        return self.images
