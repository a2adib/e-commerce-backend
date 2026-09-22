from typing import Optional, TYPE_CHECKING, List
from sqlmodel import Field, Relationship

from src.common.mixins import CommonFieldMixin
from src.common.utils import generate_public_id

if TYPE_CHECKING:
    from src.products.models import Product


class Category(CommonFieldMixin, table=True):
    __tablename__ = "categories"

    name: str = Field(nullable=False, max_length=255)
    slug: str = Field(unique=True, index=True, nullable=False, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1024)
    image_url: Optional[str] = Field(default=None, max_length=512)
    parent_id: Optional[int] = Field(
        default=None, foreign_key="categories.id", nullable=True
    )

    parent: Optional["Category"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Category.id"},
    )
    children: List["Category"] = Relationship(back_populates="parent")
    products: List["Product"] = Relationship(back_populates="category")

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        super().__init__(**data)
