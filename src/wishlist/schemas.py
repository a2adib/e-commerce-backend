from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class WishlistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    product_public_id: str
    product_name: str
    product_slug: str
    product_price: float
    product_image: Optional[str] = None
    is_active: bool
    created_at: datetime
