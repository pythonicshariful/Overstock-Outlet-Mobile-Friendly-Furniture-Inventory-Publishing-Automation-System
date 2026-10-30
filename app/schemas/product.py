from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class ProductImageOut(BaseModel):
    id: int
    filename: str
    filepath: str
    thumbnail_path: Optional[str] = None
    is_primary: bool
    sort_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProductBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    price: float = Field(..., gt=0)
    original_price: Optional[float] = None
    description: Optional[str] = None
    category: str = "Living Room"
    condition: str = "Brand New"
    availability: str = "In Stock"
    dimensions: Optional[str] = None
    color: Optional[str] = None
    brand: Optional[str] = None

class ProductCreate(ProductBase):
    product_code: Optional[str] = None
    status: str = "Draft"

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None
    condition: Optional[str] = None
    availability: Optional[str] = None
    status: Optional[str] = None
    dimensions: Optional[str] = None
    color: Optional[str] = None
    brand: Optional[str] = None

class PublishLogOut(BaseModel):
    id: int
    platform: str
    status: str
    external_id: Optional[str] = None
    post_url: Optional[str] = None
    error_message: Optional[str] = None
    payload_summary: Optional[str] = None
    retries: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProductOut(ProductBase):
    id: int
    product_code: str
    status: str
    date_added: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None
    images: List[ProductImageOut] = []
    publish_logs: List[PublishLogOut] = []

    model_config = ConfigDict(from_attributes=True)

class ProductListResponse(BaseModel):
    total: int
    items: List[ProductOut]
