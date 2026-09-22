from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    price: float = Field(ge=0)
    compare_at_price: Optional[float] = Field(default=None, ge=0)
    sku: Optional[str] = None
    stock_qty: int = Field(default=0, ge=0)
    images: List[str] = []
    is_featured: bool = False
    category_public_id: str


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    compare_at_price: Optional[float] = Field(default=None, ge=0)
    sku: Optional[str] = None
    stock_qty: Optional[int] = Field(default=None, ge=0)
    images: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    category_public_id: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    name: str
    slug: str
    description: Optional[str] = None
    price: float
    compare_at_price: Optional[float] = None
    sku: Optional[str] = None
    stock_qty: int
    images: List[str]
    is_featured: bool
    category_public_id: str
    category_name: Optional[str] = None
    is_active: bool
    created_at: datetime


class ProductToggleActiveResponse(BaseModel):
    public_id: str
    is_active: bool
