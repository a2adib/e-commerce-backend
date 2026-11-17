from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class StoreSettingsUpdate(BaseModel):
    brand_name: str
    logo_url: Optional[str] = None

class StoreSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    brand_name: str
    logo_url: Optional[str] = None
    updated_at: datetime
