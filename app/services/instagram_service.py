import json
import uuid
import httpx
from typing import Dict, Any, List, Optional
from app.config import settings
from app.models.product import Product

class InstagramService:
    def __init__(self, ig_user_id: Optional[str] = None, page_token: Optional[str] = None):
        self.ig_user_id = ig_user_id or settings.IG_USER_ID
        self.access_token = page_token or settings.FB_PAGE_ACCESS_TOKEN
        self.api_version = settings.META_GRAPH_API_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def is_configured(self) -> bool:
        return bool(self.ig_user_id and self.access_token and self.access_token.strip() != "")

    def format_ig_caption(self, product: Product, custom_caption: Optional[str] = None) -> str:
        if custom_caption and custom_caption.strip():
            return custom_caption.strip()

        price_tag = f"${product.price:,.2f}"
        if product.original_price and product.original_price > product.price:
            price_tag += f" (Retail ${product.original_price:,.2f})"

        caption = (
            f"✨ JUST IN: {product.title}\n\n"
            f"💥 Deal Price: {price_tag}\n"
            f"🛋️ Category: {product.category}\n"
            f"⭐ Condition: {product.condition}\n"
            f"📦 Status: {product.availability}\n"
        )
        if product.dimensions:
            caption += f"📐 Size: {product.dimensions}\n"
        if product.color:
            caption += f"🎨 Color: {product.color}\n"
        if product.description:
            caption += f"\n{product.description}\n"

        caption += (
            f"\n📍 Overstock Outlet | Baltimore, MD\n"
            f"📞 Call/DM to claim: {settings.STORE_PHONE}\n"
            f"🕒 Open Mon-Sat 10am-7pm | Sun 11am-5pm\n\n"
            f"#overstockoutlet #baltimore #baltimorefurniture #furnitureoutlet "
            f"#marylandhomes #furniturefinds #homedecor #clearancefurniture"
        )
        return caption

    async def verify_connection(self) -> Dict[str, Any]:
        """Verify Instagram Business Account access and token."""
        if not self.is_configured():
            return {
                "valid": False,
                "mode": "mock",
                "message": "Instagram Business Account is not configured. Currently running in simulation mode."
            }

        url = f"{self.base_url}/{self.ig_user_id}"
        params = {
            "fields": "id,username,name,profile_picture_url",
            "access_token": self.access_token
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(url, params=params)
                data = res.json()
                if res.status_code == 200 and "id" in data:
                    return {
                        "valid": True,
                        "mode": "live",
                        "username": data.get("username"),
                        "message": f"Connected to @{data.get('username')} (ID: {data.get('id')})"
                    }
                else:
                    err = data.get("error", {}).get("message", res.text)
                    return {"valid": False, "mode": "error", "message": f"Instagram API Error: {err}"}
            except Exception as e:
                return {"valid": False, "mode": "error", "message": f"Connection error: {str(e)}"}

    async def publish_product(
        self,
        product: Product,
        custom_caption: Optional[str] = None,
        base_app_url: str = "http://localhost:8000"
    ) -> Dict[str, Any]:
        """
        Publishes product to Instagram Business account.
        Supports single image or multi-image carousel.
        """
        caption = self.format_ig_caption(product, custom_caption)

        if not self.is_configured() or settings.MOCK_SOCIAL_PUBLISHING:
            # Simulation / Demo Mode
            mock_ig_id = f"17841{int(uuid.uuid4().int % 10000000000)}"
            mock_post_url = f"https://www.instagram.com/p/C{mock_ig_id[-8:]}/"
            return {
                "success": True,
                "mode": "simulation",
                "external_id": mock_ig_id,
                "post_url": mock_post_url,
                "caption": caption,
                "message": f"[Simulation] Published to Instagram @overstockoutletbmore! (Media ID: {mock_ig_id})"
            }

        # LIVE INSTAGRAM GRAPH API PUBLISHING
        if not product.images:
            return {"success": False, "mode": "live", "error": "Instagram requires at least one image to post."}

        # Instagram API requires publicly reachable image URLs
        # Note: If localhost, inform user that a public domain / ngrok / CDN is required for Instagram's server to fetch image
        first_img = product.images[0]
        image_url = f"{base_app_url}{first_img.filepath}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # 1. Single image container
                container_url = f"{self.base_url}/{self.ig_user_id}/media"
                payload = {
                    "image_url": image_url,
                    "caption": caption,
                    "access_token": self.access_token
                }
                c_res = await client.post(container_url, data=payload)
                c_data = c_res.json()

                if c_res.status_code != 200 or "id" not in c_data:
                    err = c_data.get("error", {}).get("message", c_res.text)
                    return {"success": False, "mode": "live", "error": f"Instagram container creation failed: {err}"}

                creation_id = c_data["id"]

                # 2. Publish container
                pub_url = f"{self.base_url}/{self.ig_user_id}/media_publish"
                p_res = await client.post(pub_url, data={
                    "creation_id": creation_id,
                    "access_token": self.access_token
                })
                p_data = p_res.json()

                if p_res.status_code == 200 and "id" in p_data:
                    post_id = p_data["id"]
                    return {
                        "success": True,
                        "mode": "live",
                        "external_id": post_id,
                        "post_url": f"https://www.instagram.com/p/{post_id}/",
                        "caption": caption,
                        "message": f"Successfully published to Instagram! Media ID: {post_id}"
                    }
                else:
                    err = p_data.get("error", {}).get("message", p_res.text)
                    return {"success": False, "mode": "live", "error": f"Instagram publish failed: {err}"}

            except Exception as e:
                return {"success": False, "mode": "error", "error": f"Instagram network error: {str(e)}"}

instagram_service = InstagramService()

