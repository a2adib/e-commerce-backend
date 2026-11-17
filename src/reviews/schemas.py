from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: Optional[str] = Field(default=None, max_length=150)
    comment: str = Field(min_length=3, max_length=2000)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    user_name: str
    rating: int
    title: Optional[str] = None
    comment: str
    is_verified_purchase: bool
    created_at: datetime


class ProductReviewsSummary(BaseModel):
    avg_rating: float
    total_reviews: int
    rating_distribution: Dict[str, int]
    reviews: List[ReviewResponse]
