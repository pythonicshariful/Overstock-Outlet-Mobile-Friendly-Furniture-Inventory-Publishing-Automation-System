from typing import List, Optional
from pydantic import BaseModel

class PublishRequest(BaseModel):
    platforms: List[str] = ["facebook_page"]  # ["facebook_page", "instagram", "marketplace"]
    custom_caption: Optional[str] = None

class PublishResult(BaseModel):
    platform: str
    status: str  # "success", "failed", "assisted"
    message: str
    external_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None

class BatchPublishResponse(BaseModel):
    product_id: int
    results: List[PublishResult]

class MarketplaceGuideResponse(BaseModel):
    product_id: int
    title: str
    price: float
    category: str
    condition: str
    description: str
    suggested_tags: List[str]
    marketplace_url: str
    images: List[dict]
    instructions: List[str]

