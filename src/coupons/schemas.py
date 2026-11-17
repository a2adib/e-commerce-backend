from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CouponValidateRequest(BaseModel):
    code: str
    subtotal: float = Field(ge=0)


class CouponValidateResponse(BaseModel):
    valid: bool
    code: str
    discount_type: str
    discount_value: float
    discount_amount: float
    new_subtotal: float
    message: str


class CouponCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    discount_type: str = Field(default="percentage", pattern="^(percentage|fixed)$")
    discount_value: float = Field(gt=0)
    min_order_amount: float = Field(default=0.0, ge=0)
    max_discount_amount: Optional[float] = Field(default=None, ge=0)
    usage_limit: Optional[int] = Field(default=None, ge=1)
    valid_until: Optional[datetime] = None
    description: Optional[str] = None


class CouponUpdate(BaseModel):
    discount_type: Optional[str] = Field(default=None, pattern="^(percentage|fixed)$")
    discount_value: Optional[float] = Field(default=None, gt=0)
    min_order_amount: Optional[float] = Field(default=None, ge=0)
    max_discount_amount: Optional[float] = Field(default=None, ge=0)
    usage_limit: Optional[int] = Field(default=None, ge=1)
    valid_until: Optional[datetime] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CouponResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    code: str
    discount_type: str
    discount_value: float
    min_order_amount: float
    max_discount_amount: Optional[float] = None
    usage_limit: Optional[int] = None
    used_count: int
    valid_until: Optional[datetime] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
