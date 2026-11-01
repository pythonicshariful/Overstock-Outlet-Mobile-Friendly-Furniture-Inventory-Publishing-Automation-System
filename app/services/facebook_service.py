import json
import httpx
from typing import Dict, Any, Optional
from app.config import settings
from app.models.product import Product

class FacebookService:
    def __init__(self, page_id: Optional[str] = None, page_token: Optional[str] = None):
        self._page_id = page_id
        self._page_token = page_token

    @property
    def page_id(self) -> str:
        return (self._page_id or settings.FB_PAGE_ID or "").strip()

    @property
    def page_token(self) -> str:
        return (self._page_token or settings.FB_PAGE_ACCESS_TOKEN or "").strip()

    @property
    def api_version(self) -> str:
        return settings.META_GRAPH_API_VERSION

    @property
    def base_url(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}"

    def is_configured(self) -> bool:
        return bool(self.page_id and self.page_token)

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

        contact_lines = [
            f"📍 Available now at {settings.STORE_NAME}",
            f"📌 {settings.STORE_LOCATION} | First come, first served!",
        ]
        if settings.STORE_PHONE and settings.STORE_PHONE.strip():
            contact_lines.append(f"📞 Call/Text: {settings.STORE_PHONE.strip()}")
        if settings.STORE_HOURS and settings.STORE_HOURS.strip():
            contact_lines.append(f"🕒 Hours: {settings.STORE_HOURS.strip()}")

        contact_block = "\n".join(contact_lines)

        caption = (
            f"🛋️ NEW INVENTORY: {product.title}\n"
            f"💰 Price: {price_line}\n\n"
            f"{details_str}\n"
            f"{desc_str}\n"
            f"{contact_block}\n\n"
            f"#OverstockOutlet #BaltimoreFurniture #FurnitureDeals #BmoreOutlet #FurnitureForSale"
        )
        return caption

    async def verify_connection(self) -> Dict[str, Any]:
        """Check if Page Access Token and Page ID are valid and have necessary permissions."""
        if not self.is_configured():
            return {
                "valid": False,
                "mode": "unconfigured",
                "message": "Facebook Page credentials (FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN) are not configured."
            }

        url = f"{self.base_url}/{self.page_id}"
        params = {
            "access_token": self.page_token,
            "fields": "id,name"
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
                        "page_link": settings.STORE_FACEBOOK_PAGE_URL,
                        "message": f"Successfully connected to Facebook: {data.get('name')} (ID: {data.get('id')})"
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
        Publishes product to Facebook Business Page via live Meta Graph API.
        """
        caption = self.format_page_caption(product, custom_caption)

        if not self.is_configured():
            return {
                "success": False,
                "mode": "unconfigured",
                "caption": caption,
                "error": "Facebook Page credentials (FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN) are not configured. Configure them in Admin > Social Media & API Settings."
            }

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
                        return {"success": False, "mode": "live", "caption": caption, "error": f"FB Post failed: {err}"}

                # 2. Multi-image or Single-image post
                # Upload photos as unpublished
                media_ids = []
                upload_errors = []
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
                        if res.status_code == 200 and "id" in res_data:
                            media_ids.append(res_data["id"])
                        else:
                            err_detail = res_data.get("error", {}).get("message", res.text)
                            upload_errors.append(err_detail)

                if not media_ids:
                    err_reason = "; ".join(upload_errors) if upload_errors else "Image files not found on disk"
                    return {
                        "success": False,
                        "mode": "live",
                        "caption": caption,
                        "error": f"Could not upload images to Facebook: {err_reason}"
                    }

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
                    return {"success": False, "mode": "live", "caption": caption, "error": f"Failed creating FB feed post: {err}"}

            except Exception as e:
                return {
                    "success": False,
                    "mode": "error",
                    "caption": caption,
                    "error": f"Facebook network/API error: {str(e)}"
                }

facebook_service = FacebookService()
