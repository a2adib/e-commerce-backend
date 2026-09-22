from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BasePublicID(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str


class BaseModelSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
