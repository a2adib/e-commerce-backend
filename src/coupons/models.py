from typing import Optional
from datetime import datetime
from sqlmodel import Field
from src.common.mixins import CommonFieldMixin
from src.common.utils import generate_public_id


class Coupon(CommonFieldMixin, table=True):
    __tablename__ = "coupons"

    code: str = Field(unique=True, index=True, nullable=False, max_length=50)
    discount_type: str = Field(default="percentage", max_length=20)  # "percentage" | "fixed"
    discount_value: float = Field(nullable=False, ge=0)
    min_order_amount: float = Field(default=0.0, ge=0)
    max_discount_amount: Optional[float] = Field(default=None, ge=0)
    usage_limit: Optional[int] = Field(default=None, ge=1)
    used_count: int = Field(default=0, ge=0)
    valid_until: Optional[datetime] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=255)

    def __init__(self, **data):
        if "public_id" not in data:
            data["public_id"] = generate_public_id()
        if "code" in data and isinstance(data["code"], str):
            data["code"] = data["code"].strip().upper()
        super().__init__(**data)
