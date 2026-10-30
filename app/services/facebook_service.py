import json
import uuid
import httpx
from typing import Dict, Any, List, Optional
from app.config import settings
from app.models.product import Product

class FacebookService:
    def __init__(self, page_id: Optional[str] = None, page_token: Optional[str] = None):
        self.page_id = page_id or settings.FB_PAGE_ID
        self.page_token = page_token or settings.FB_PAGE_ACCESS_TOKEN
        self.api_version = settings.META_GRAPH_API_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def is_configured(self) -> bool:
        return bool(self.page_id and self.page_token and self.page_token.strip() != "")

    def format_page_caption(self, product: Product, custom_caption: Optional[str] = None) -> str:
        if custom_caption and custom_caption.strip():
            return custom_caption.strip()

        # Build engaging, clear retail caption for Baltimore store
        price_line = f"${product.price:,.2f}"
        if product.original_price and product.original_price > product.price:
            savings = product.original_price - product.price
            price_line += f" (Retail: ${product.original_price:,.2f} - Save ${savings:,.2f}!)"

        details = []
        if product.brand:
            details.append(f"🏷️ Brand: {product.brand}")
        if product.condition:
            details.append(f"✨ Condition: {product.condition}")
        if product.dimensions:
            details.append(f"📐 Dimensions: {product.dimensions}")
        if product.color:
            details.append(f"🎨 Color: {product.color}")
        details.append(f"📦 Availability: {product.availability}")

        details_str = "\n".join(details)
        desc_str = f"\n{product.description}\n" if product.description else ""

        caption = (
            f"🛋️ NEW INVENTORY: {product.title}\n"
            f"💰 Price: {price_line}\n\n"
            f"{details_str}\n"
            f"{desc_str}\n"
            f"📍 Available now at Overstock Outlet\n"
            f"📌 Baltimore, MD | First come, first served!\n"
            f"📞 Call/Text: {settings.STORE_PHONE}\n"
            f"🕒 Hours: {settings.STORE_HOURS}\n\n"
            f"#OverstockOutlet #BaltimoreFurniture #FurnitureDeals #BmoreOutlet #FurnitureForSale"
        )
        return caption

    async def verify_connection(self) -> Dict[str, Any]:
        """Check if Page Access Token and Page ID are valid and have necessary permissions."""
        if not self.is_configured():
            return {
                "valid": False,
                "mode": "mock",
                "message": "Facebook Page credentials are not configured. Currently running in simulation mode."
            }

        url = f"{self.base_url}/{self.page_id}"
        params = {
            "access_token": self.page_token,
            "fields": "id,name,category,link,is_published"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, params=params)
                data = response.json()
                if response.status_code == 200 and "id" in data:
                    return {
                        "valid": True,
                        "mode": "live",
                        "page_name": data.get("name"),
                        "page_link": data.get("link", settings.STORE_FACEBOOK_PAGE_URL),
                        "message": f"Successfully connected to Page: {data.get('name')} (ID: {data.get('id')})"
                    }
                else:
                    error_msg = data.get("error", {}).get("message", "Unknown Facebook API error")
                    error_code = data.get("error", {}).get("code", response.status_code)
                    return {
                        "valid": False,
                        "mode": "error",
                        "message": f"Graph API Error [{error_code}]: {error_msg}"
                    }
            except Exception as e:
                return {
                    "valid": False,
                    "mode": "error",
                    "message": f"Connection failed: {str(e)}"
                }

    async def publish_product(
        self,
        product: Product,
        custom_caption: Optional[str] = None,
        base_app_url: str = "http://localhost:8000"
    ) -> Dict[str, Any]:
        """
        Publishes product to Facebook Business Page.
        Uses live Meta Graph API if configured; otherwise gracefully executes simulation.
        """
        caption = self.format_page_caption(product, custom_caption)
        
        # Check if live mode is enabled and credentials present
        if not self.is_configured() or settings.MOCK_SOCIAL_PUBLISHING:
            # Simulation / Demo Mode
            mock_post_id = f"{self.page_id or '108293847291'}_{int(uuid.uuid4().int % 1000000000000)}"
            mock_url = f"{settings.STORE_FACEBOOK_PAGE_URL}/posts/{mock_post_id.split('_')[-1]}"
            return {
                "success": True,
                "mode": "simulation",
                "external_id": mock_post_id,
                "post_url": mock_url,
                "caption": caption,
                "message": f"[Simulation] Post published successfully to Overstock Outlet Page! (Post ID: {mock_post_id})"
            }

        # LIVE PUBLISH VIA GRAPH API
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # 1. Check images
                if not product.images:
                    # Text-only post
                    feed_url = f"{self.base_url}/{self.page_id}/feed"
                    res = await client.post(feed_url, data={
                        "message": caption,
                        "access_token": self.page_token
                    })
                    data = res.json()
                    if res.status_code == 200 and "id" in data:
                        post_id = data["id"]
                        return {
                            "success": True,
                            "mode": "live",
                            "external_id": post_id,
                            "post_url": f"{settings.STORE_FACEBOOK_PAGE_URL}/posts/{post_id.split('_')[-1]}",
                            "caption": caption,
                            "message": f"Published text post to Facebook Page! ID: {post_id}"
                        }
                    else:
                        err = data.get("error", {}).get("message", res.text)
                        return {"success": False, "mode": "live", "error": f"FB Post failed: {err}"}

                # 2. Multi-image or Single-image post
                # Upload photos as unpublished
                media_ids = []
                for img in product.images:
                    local_file = settings.UPLOAD_DIR / img.filename
                    if not local_file.exists():
                        continue
                    
                    photo_upload_url = f"{self.base_url}/{self.page_id}/photos"
                    with open(local_file, "rb") as f:
                        files = {"source": (img.filename, f, "image/jpeg")}
                        data = {
                            "published": "false",
                            "access_token": self.page_token
                        }
                        res = await client.post(photo_upload_url, data=data, files=files)
                        res_data = res.json()
                        if "id" in res_data:
                            media_ids.append(res_data["id"])

                if not media_ids:
                    return {"success": False, "mode": "live", "error": "Could not upload images to Facebook"}

                # Create multi-photo feed post
                feed_url = f"{self.base_url}/{self.page_id}/feed"
                payload = {
                    "message": caption,
                    "access_token": self.page_token
                }
                for i, media_id in enumerate(media_ids):
                    payload[f"attached_media[{i}]"] = json.dumps({"media_fbid": media_id})

                feed_res = await client.post(feed_url, data=payload)
                feed_data = feed_res.json()

                if feed_res.status_code == 200 and "id" in feed_data:
                    post_id = feed_data["id"]
                    return {
                        "success": True,
                        "mode": "live",
                        "external_id": post_id,
                        "post_url": f"{settings.STORE_FACEBOOK_PAGE_URL}/posts/{post_id.split('_')[-1]}",
                        "caption": caption,
                        "message": f"Successfully published to Overstock Outlet Facebook Page! Post ID: {post_id}"
                    }
                else:
                    err = feed_data.get("error", {}).get("message", feed_res.text)
                    return {"success": False, "mode": "live", "error": f"Failed creating FB feed post: {err}"}

            except Exception as e:
                return {
                    "success": False,
                    "mode": "error",
                    "error": f"Facebook network/API error: {str(e)}"
                }

facebook_service = FacebookService()

