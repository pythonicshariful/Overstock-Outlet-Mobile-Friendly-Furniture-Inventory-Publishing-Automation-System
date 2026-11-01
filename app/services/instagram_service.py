import httpx
from typing import Dict, Any, Optional
from app.config import settings
from app.models.product import Product

class InstagramService:
    def __init__(self, ig_user_id: Optional[str] = None, page_token: Optional[str] = None):
        self._ig_user_id = ig_user_id
        self._access_token = page_token

    @property
    def ig_user_id(self) -> str:
        return (self._ig_user_id or settings.IG_USER_ID or "").strip()

    @property
    def access_token(self) -> str:
        return (self._access_token or settings.FB_PAGE_ACCESS_TOKEN or "").strip()

    @property
    def api_version(self) -> str:
        return settings.META_GRAPH_API_VERSION

    @property
    def base_url(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}"

    def is_configured(self) -> bool:
        return bool(self.ig_user_id and self.access_token)

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

        contact_line = (
            f"📞 Call/DM to claim: {settings.STORE_PHONE.strip()}\n"
            if settings.STORE_PHONE and settings.STORE_PHONE.strip()
            else "📩 DM us to claim or check availability!\n"
        )
        hours_line = (
            f"🕒 Hours: {settings.STORE_HOURS.strip()}\n\n"
            if settings.STORE_HOURS and settings.STORE_HOURS.strip()
            else "\n"
        )

        caption += (
            f"\n📍 {settings.STORE_NAME} | {settings.STORE_LOCATION}\n"
            f"{contact_line}"
            f"{hours_line}"
            f"#overstockoutlet #baltimore #baltimorefurniture #furnitureoutlet "
            f"#marylandhomes #furniturefinds #homedecor #clearancefurniture"
        )
        return caption

    async def verify_connection(self) -> Dict[str, Any]:
        """Verify Instagram Business Account access and token."""
        if not self.is_configured():
            return {
                "valid": False,
                "mode": "unconfigured",
                "message": "Instagram Business Account credentials (IG_USER_ID and FB_PAGE_ACCESS_TOKEN) are not configured."
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
        Publishes product to Instagram Business account via live Meta Graph API.
        Supports single image or multi-image carousel (up to 10 images).
        """
        caption = self.format_ig_caption(product, custom_caption)

        if not self.is_configured():
            return {
                "success": False,
                "mode": "unconfigured",
                "caption": caption,
                "error": "Instagram Business credentials (IG_USER_ID and FB_PAGE_ACCESS_TOKEN) are not configured. Configure them in Admin > Social Media & API Settings."
            }

        if not product.images:
            return {
                "success": False,
                "mode": "live",
                "caption": caption,
                "error": "Instagram requires at least one product photo to publish."
            }

        container_url = f"{self.base_url}/{self.ig_user_id}/media"
        pub_url = f"{self.base_url}/{self.ig_user_id}/media_publish"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if len(product.images) == 1:
                    image_url = f"{base_app_url}{product.images[0].filepath}"
                    payload = {
                        "image_url": image_url,
                        "caption": caption,
                        "access_token": self.access_token
                    }
                    c_res = await client.post(container_url, data=payload)
                    c_data = c_res.json()

                    if c_res.status_code != 200 or "id" not in c_data:
                        err = c_data.get("error", {}).get("message", c_res.text)
                        return {"success": False, "mode": "live", "caption": caption, "error": f"Instagram container creation failed: {err}"}

                    creation_id = c_data["id"]
                else:
                    # Multi-image carousel (Instagram supports 2 to 10 items)
                    child_ids = []
                    for img in product.images[:10]:
                        image_url = f"{base_app_url}{img.filepath}"
                        item_res = await client.post(container_url, data={
                            "image_url": image_url,
                            "is_carousel_item": "true",
                            "access_token": self.access_token
                        })
                        item_data = item_res.json()
                        if item_res.status_code == 200 and "id" in item_data:
                            child_ids.append(item_data["id"])
                        else:
                            err = item_data.get("error", {}).get("message", item_res.text)
                            return {"success": False, "mode": "live", "caption": caption, "error": f"Instagram carousel item creation failed: {err}"}

                    c_res = await client.post(container_url, data={
                        "media_type": "CAROUSEL",
                        "children": ",".join(child_ids),
                        "caption": caption,
                        "access_token": self.access_token
                    })
                    c_data = c_res.json()
                    if c_res.status_code != 200 or "id" not in c_data:
                        err = c_data.get("error", {}).get("message", c_res.text)
                        return {"success": False, "mode": "live", "caption": caption, "error": f"Instagram carousel container failed: {err}"}

                    creation_id = c_data["id"]

                # Publish container
                p_res = await client.post(pub_url, data={
                    "creation_id": creation_id,
                    "access_token": self.access_token
                })
                p_data = p_res.json()

                if p_res.status_code == 200 and "id" in p_data:
                    post_id = p_data["id"]
                    # Fetch canonical Instagram permalink from Graph API
                    permalink = None
                    try:
                        perm_res = await client.get(
                            f"{self.base_url}/{post_id}",
                            params={"fields": "permalink", "access_token": self.access_token}
                        )
                        if perm_res.status_code == 200:
                            permalink = perm_res.json().get("permalink")
                    except Exception:
                        pass

                    return {
                        "success": True,
                        "mode": "live",
                        "external_id": post_id,
                        "post_url": permalink or "https://www.instagram.com/",
                        "caption": caption,
                        "message": f"Successfully published to Instagram! Media ID: {post_id}"
                    }
                else:
                    err = p_data.get("error", {}).get("message", p_res.text)
                    return {"success": False, "mode": "live", "caption": caption, "error": f"Instagram publish failed: {err}"}

            except Exception as e:
                return {"success": False, "mode": "error", "caption": caption, "error": f"Instagram network error: {str(e)}"}

instagram_service = InstagramService()
