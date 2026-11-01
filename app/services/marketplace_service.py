from typing import Dict, Any, List
from app.config import settings
from app.models.product import Product

class MarketplaceService:
    def format_marketplace_title(self, product: Product) -> str:
        # Marketplace titles perform best at ~50-80 chars: Brand + Item + Key Feature + Condition
        title = product.title.strip()
        if product.brand and product.brand.lower() not in title.lower():
            title = f"{product.brand} - {title}"
        if product.condition and product.condition != "Brand New":
            title = f"{title} ({product.condition})"
        return title[:95]  # Meta limit is 100

    def format_marketplace_description(self, product: Product) -> str:
        lines = []
        lines.append(f"🛋️ {product.title}")
        lines.append(f"💵 Price: ${product.price:,.2f}")
        if product.original_price and product.original_price > product.price:
            savings = product.original_price - product.price
            lines.append(f"🔥 Compare at ${product.original_price:,.2f} (Save ${savings:,.2f}!)")
        lines.append("")
        
        lines.append("--- SPECIFICATIONS ---")
        lines.append(f"• Condition: {product.condition}")
        lines.append(f"• Category: {product.category}")
        lines.append(f"• Availability: {product.availability}")
        if product.dimensions:
            lines.append(f"• Dimensions: {product.dimensions}")
        if product.color:
            lines.append(f"• Color: {product.color}")
        if product.brand:
            lines.append(f"• Brand: {product.brand}")
        lines.append("")

        if product.description and product.description.strip():
            lines.append("--- DESCRIPTION ---")
            lines.append(product.description.strip())
            lines.append("")

        lines.append("--- STORE LOCATION & PICKUP ---")
        lines.append(f"📍 {settings.STORE_NAME} - {settings.STORE_LOCATION}")
        if settings.STORE_HOURS and settings.STORE_HOURS.strip():
            lines.append(f"🕒 Hours: {settings.STORE_HOURS.strip()}")
        if settings.STORE_PHONE and settings.STORE_PHONE.strip():
            lines.append(f"📞 Questions / Hold: Call or Text {settings.STORE_PHONE.strip()}")
        else:
            lines.append("💬 Questions / Hold: Message us directly on Facebook!")
        lines.append("🚚 Local delivery available upon request!")
        lines.append("💳 We accept Cash, Cards, and Digital Payments.")
        lines.append("⚡ First come, first served. Message us to confirm availability before heading over!")

        return "\n".join(lines)

    def get_suggested_tags(self, product: Product) -> List[str]:
        tags = ["furniture", "baltimore", "outlet", "discount", "clearance"]
        if product.category:
            tags.append(product.category.lower().replace(" ", ""))
        if product.color:
            tags.append(product.color.lower())
        if product.brand:
            tags.append(product.brand.lower().replace(" ", ""))
        return tags[:10]

    def get_assisted_guide(self, product: Product, base_app_url: str = "http://localhost:8000") -> Dict[str, Any]:
        """Returns structured payload to render the assisted publishing UI."""
        images_data = []
        for i, img in enumerate(product.images):
            images_data.append({
                "index": i + 1,
                "url": f"{base_app_url}{img.filepath}",
                "thumbnail_url": f"{base_app_url}{img.thumbnail_path or img.filepath}",
                "filename": img.filename,
                "is_primary": img.is_primary
            })

        instructions = [
            "1. Click 'Copy Title' below, then tap 'Open Facebook Marketplace'.",
            "2. In Facebook, tap 'Add Photos' and select the saved product photos in order.",
            "3. Paste the Title and enter the Price.",
            "4. Select the Category (e.g. Furniture > Living Room).",
            "5. Select the Condition.",
            "6. Click 'Copy Description' and paste into the Description box.",
            "7. Ensure Location is set to Baltimore, MD and tap 'Publish'!",
            "8. Return here and tap 'Mark as Published on Marketplace'."
        ]

        return {
            "product_id": product.id,
            "product_code": product.product_code,
            "title": self.format_marketplace_title(product),
            "price": product.price,
            "original_price": product.original_price,
            "category": product.category,
            "condition": product.condition,
            "location": settings.STORE_LOCATION,
            "description": self.format_marketplace_description(product),
            "suggested_tags": self.get_suggested_tags(product),
            "marketplace_url": "https://www.facebook.com/marketplace/create/item",
            "images": images_data,
            "instructions": instructions
        }

marketplace_service = MarketplaceService()
