from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CartItemAdd(BaseModel):
    product_public_id: str
    quantity: int = Field(default=1, ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    product_public_id: str
    product_name: str
    product_slug: str
    product_price: float
    product_image: Optional[str] = None
    quantity: int
    line_total: float
    is_available: bool
    stock_qty: int


class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    items: List[CartItemResponse]
    subtotal: float
    total_items: int
