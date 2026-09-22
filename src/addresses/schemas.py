from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AddressBase(BaseModel):
    full_name: str
    phone: str
    address_line: str
    city: str
    district: str
    postal_code: Optional[str] = None
    is_default: bool = False


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    postal_code: Optional[str] = None
    is_default: Optional[bool] = None


class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    full_name: str
    phone: str
    address_line: str
    city: str
    district: str
    postal_code: Optional[str] = None
    is_default: bool
    created_at: datetime
