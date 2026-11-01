from typing import Dict, Any, Optional
import httpx
from app.config import settings

CATEGORY_HIGHLIGHTS = {
    "Living Room": "Designed for everyday comfort and style, making it a standout centerpiece for your living room or family den.",
    "Bedroom": "Crafted to bring restful comfort, durability, and timeless style to your bedroom suite.",
    "Dining Room": "Built for memorable gatherings and daily meals with sturdy construction and an inviting finish.",
    "Office": "Engineered for productive comfort and clean organization in your home office or workspace.",
    "Outdoor": "Weather-ready durability meets relaxed outdoor lounging for your patio, deck, or porch.",
    "Decor & Rugs": "Adds instant warmth, texture, and designer character to elevate any room in your home.",
    "Mattresses": "Delivers supportive, pressure-relieving sleep comfort at an unbeatable outlet value.",
    "Clearance": "Priced for immediate showroom clearance—an exceptional value on quality home furniture.",
    "Other": "Built with quality materials and versatile styling to complement your home."
}

CONDITION_NOTES = {
    "Brand New": "Factory-fresh, brand new condition and ready for immediate showroom pickup.",
    "Like New": "In pristine, like-new condition with minimal to zero signs of wear—inspected and showroom-ready.",
    "Floor Model": "Well-maintained showroom display model offering designer quality at a deep outlet markdown.",
    "Excellent": "Gently handled and in excellent structural and cosmetic condition.",
    "Good": "Solid, dependable construction in good condition, priced for outstanding value.",
    "Clearance": "Final-markdown clearance piece sold as-is for maximum savings."
}


class AIService:
    """
    Multi-provider AI & Smart Template copywriting service.
    Supports Google Gemini, OpenAI, Anthropic Claude, Groq, and the built-in Smart Retail Template engine.
    """

    def get_provider_status(self) -> Dict[str, Any]:
        return {
            "active_provider": settings.AI_PROVIDER or "auto",
            "providers": {
                "gemini": {
                    "name": "Google Gemini (Vision + Text)",
                    "configured": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()),
                    "model": settings.GEMINI_MODEL or "gemini-2.5-flash"
                },
                "openai": {
                    "name": "OpenAI GPT (Vision + Text)",
                    "configured": bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip()),
                    "model": settings.OPENAI_MODEL or "gpt-4o-mini"
                },
                "anthropic": {
                    "name": "Anthropic Claude (Vision + Text)",
                    "configured": bool(settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.strip()),
                    "model": settings.ANTHROPIC_MODEL or "claude-3-5-haiku-latest"
                },
                "groq": {
                    "name": "Groq Llama (Fast Text)",
                    "configured": bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip()),
                    "model": settings.GROQ_MODEL or "llama-3.3-70b-versatile"
                },
                "smart_template": {
                    "name": "Smart Retail Copy Engine (Built-In, No Key Required)",
                    "configured": True,
                    "model": "rule-based-v2"
                }
            }
        }

    def _build_prompt(
        self,
        title: str,
        category: str,
        condition: str,
        price: Optional[float] = None,
        original_price: Optional[float] = None,
        brand: Optional[str] = None,
        color: Optional[str] = None,
        dimensions: Optional[str] = None,
        has_image: bool = False
    ) -> str:
        specs = []
        if title:
            specs.append(f"Item Title: {title}")
        if category:
            specs.append(f"Category: {category}")
        if condition:
            specs.append(f"Condition: {condition}")
        if brand:
            specs.append(f"Brand/Maker: {brand}")
        if color:
            specs.append(f"Color/Finish: {color}")
        if dimensions:
            specs.append(f"Dimensions: {dimensions}")
        if price is not None and price > 0:
            specs.append(f"Outlet Price: ${price:,.2f}")
        if original_price is not None and price is not None and original_price > price:
            savings = original_price - price
            pct = int(round((savings / original_price) * 100))
            specs.append(f"Original Retail Price: ${original_price:,.2f} (Customer Saves ${savings:,.2f} / {pct}% OFF)")

        specs_block = "\n".join(specs) if specs else "Furniture item at Overstock Outlet"
        custom_instructions = (
            f"\nAdditional Store Owner Instructions: {settings.AI_CUSTOM_PROMPT.strip()}\n"
            if settings.AI_CUSTOM_PROMPT and settings.AI_CUSTOM_PROMPT.strip()
            else ""
        )
        vision_hint = (
            "Analyze the attached product photo closely to describe visible materials, upholstery/wood grain, "
            "silhouette, cushion style, and design details accurately.\n"
            if has_image
            else ""
        )

        return (
            f"You are an expert retail furniture copywriter for {settings.STORE_NAME} in {settings.STORE_LOCATION}.\n"
            f"{vision_hint}"
            f"Write a compelling, high-converting 3 to 4 sentence product description (approx. 55-90 words) based on these details:\n"
            f"{specs_block}\n"
            f"{custom_instructions}\n"
            "Guidelines:\n"
            "- Write natural, persuasive showroom copy suitable for Facebook, Instagram, and Facebook Marketplace.\n"
            "- Highlight quality, comfort/build, condition, and the outlet discount/savings if retail price is provided.\n"
            "- End with an invitation for immediate pickup at Overstock Outlet in Baltimore, MD.\n"
            "- Output ONLY the description paragraph itself, with no introductory filler, no markdown headers, and no hashtags."
        )

    def generate_smart_template(
        self,
        title: str,
        category: str = "Living Room",
        condition: str = "Brand New",
        price: Optional[float] = None,
        original_price: Optional[float] = None,
        brand: Optional[str] = None,
        color: Optional[str] = None,
        dimensions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Rich, category- and discount-aware retail copy generator that runs locally with zero external API keys."""
        clean_title = (title or "").strip() or f"{category} Furniture Piece"
        sentences = []

        # 1. Opening hook with Brand, Title, Color
        brand_prefix = f"{brand.strip()} " if brand and brand.strip() and brand.strip().lower() not in clean_title.lower() else ""
        color_phrase = f" in a versatile {color.strip()} finish" if color and color.strip() else ""
        sentences.append(f"Upgrade your space with this {brand_prefix}{clean_title}{color_phrase}.")

        # 2. Category & Condition selling points
        cat_line = CATEGORY_HIGHLIGHTS.get(category, CATEGORY_HIGHLIGHTS["Other"])
        sentences.append(cat_line)

        cond_line = CONDITION_NOTES.get(condition, f"Offered in {condition.lower()} condition.")
        if dimensions and dimensions.strip():
            sentences.append(f"{cond_line} Measures {dimensions.strip()} to fit comfortably in your room layout.")
        else:
            sentences.append(cond_line)

        # 3. Pricing / Savings value proposition + Store call to action
        if price is not None and original_price is not None and original_price > price > 0:
            savings = original_price - price
            pct = int(round((savings / original_price) * 100))
            sentences.append(
                f"Compare at ${original_price:,.0f} retail—grab it today at {settings.STORE_NAME} ({settings.STORE_LOCATION}) "
                f"for just ${price:,.0f} and save ${savings:,.0f} ({pct}% OFF)! First come, first served."
            )
        elif price is not None and price > 0:
            sentences.append(
                f"Priced at just ${price:,.0f} for immediate showroom pickup at {settings.STORE_NAME} in {settings.STORE_LOCATION}—first come, first served!"
            )
        else:
            sentences.append(
                f"Available now for immediate pickup at {settings.STORE_NAME} in {settings.STORE_LOCATION}—first come, first served!"
            )

        return {
            "success": True,
            "provider_used": "smart_template",
            "model_used": "Smart Retail Copy Engine",
            "description": " ".join(sentences)
        }

    async def _call_gemini(
        self,
        prompt: str,
        image_base64: Optional[str] = None,
        image_mime_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        api_key = (settings.GEMINI_API_KEY or "").strip()
        model = (settings.GEMINI_MODEL or "gemini-2.5-flash").strip()
        if not api_key:
            return {"success": False, "error": "Google Gemini API key is not configured in Admin > AI Settings."}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        parts = [{"text": prompt}]
        if image_base64:
            parts.insert(0, {
                "inline_data": {
                    "mime_type": image_mime_type,
                    "data": image_base64
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.65, "maxOutputTokens": 300}
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            res = await client.post(url, params={"key": api_key}, json=payload)
            data = res.json()
            if res.status_code == 200 and "candidates" in data and data["candidates"]:
                text_parts = data["candidates"][0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in text_parts).strip()
                if text:
                    return {
                        "success": True,
                        "provider_used": "gemini",
                        "model_used": model,
                        "description": text
                    }
            err_msg = data.get("error", {}).get("message", res.text)
            return {"success": False, "error": f"Gemini API error: {err_msg}"}

    async def _call_openai(
        self,
        prompt: str,
        image_base64: Optional[str] = None,
        image_mime_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        api_key = (settings.OPENAI_API_KEY or "").strip()
        model = (settings.OPENAI_MODEL or "gpt-4o-mini").strip()
        if not api_key:
            return {"success": False, "error": "OpenAI API key is not configured in Admin > AI Settings."}

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        if image_base64:
            user_content: Any = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{image_mime_type};base64,{image_base64}"}}
            ]
        else:
            user_content = prompt

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert retail furniture copywriter."},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.65,
            "max_tokens": 280
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            data = res.json()
            if res.status_code == 200 and "choices" in data and data["choices"]:
                text = data["choices"][0].get("message", {}).get("content", "").strip()
                if text:
                    return {
                        "success": True,
                        "provider_used": "openai",
                        "model_used": model,
                        "description": text
                    }
            err_msg = data.get("error", {}).get("message", res.text)
            return {"success": False, "error": f"OpenAI API error: {err_msg}"}

    async def _call_anthropic(
        self,
        prompt: str,
        image_base64: Optional[str] = None,
        image_mime_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        api_key = (settings.ANTHROPIC_API_KEY or "").strip()
        model = (settings.ANTHROPIC_MODEL or "claude-3-5-haiku-latest").strip()
        if not api_key:
            return {"success": False, "error": "Anthropic Claude API key is not configured in Admin > AI Settings."}

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        content_blocks = []
        if image_base64:
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_mime_type,
                    "data": image_base64
                }
            })
        content_blocks.append({"type": "text", "text": prompt})

        payload = {
            "model": model,
            "max_tokens": 280,
            "messages": [{"role": "user", "content": content_blocks}]
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            data = res.json()
            if res.status_code == 200 and "content" in data and data["content"]:
                text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text").strip()
                if text:
                    return {
                        "success": True,
                        "provider_used": "anthropic",
                        "model_used": model,
                        "description": text
                    }
            err_msg = data.get("error", {}).get("message", res.text)
            return {"success": False, "error": f"Anthropic API error: {err_msg}"}

    async def _call_groq(self, prompt: str) -> Dict[str, Any]:
        api_key = (settings.GROQ_API_KEY or "").strip()
        model = (settings.GROQ_MODEL or "llama-3.3-70b-versatile").strip()
        if not api_key:
            return {"success": False, "error": "Groq API key is not configured in Admin > AI Settings."}

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert retail furniture copywriter."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.65,
            "max_tokens": 280
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            data = res.json()
            if res.status_code == 200 and "choices" in data and data["choices"]:
                text = data["choices"][0].get("message", {}).get("content", "").strip()
                if text:
                    return {
                        "success": True,
                        "provider_used": "groq",
                        "model_used": model,
                        "description": text
                    }
            err_msg = data.get("error", {}).get("message", res.text)
            return {"success": False, "error": f"Groq API error: {err_msg}"}

    def _resolve_auto_provider(self) -> str:
        configured_default = (settings.AI_PROVIDER or "auto").strip().lower()
        if configured_default not in ("auto", ""):
            return configured_default
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            return "gemini"
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
            return "openai"
        if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.strip():
            return "anthropic"
        if settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip():
            return "groq"
        return "smart_template"

    async def generate_description(
        self,
        title: str,
        category: str = "Living Room",
        condition: str = "Brand New",
        price: Optional[float] = None,
        original_price: Optional[float] = None,
        brand: Optional[str] = None,
        color: Optional[str] = None,
        dimensions: Optional[str] = None,
        provider: Optional[str] = None,
        image_base64: Optional[str] = None,
        image_mime_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        requested = (provider or "auto").strip().lower()
        target_provider = self._resolve_auto_provider() if requested == "auto" else requested

        if target_provider == "smart_template":
            return self.generate_smart_template(
                title=title,
                category=category,
                condition=condition,
                price=price,
                original_price=original_price,
                brand=brand,
                color=color,
                dimensions=dimensions
            )

        prompt = self._build_prompt(
            title=title,
            category=category,
            condition=condition,
            price=price,
            original_price=original_price,
            brand=brand,
            color=color,
            dimensions=dimensions,
            has_image=bool(image_base64)
        )

        try:
            if target_provider == "gemini":
                res = await self._call_gemini(prompt, image_base64, image_mime_type)
            elif target_provider == "openai":
                res = await self._call_openai(prompt, image_base64, image_mime_type)
            elif target_provider == "anthropic":
                res = await self._call_anthropic(prompt, image_base64, image_mime_type)
            elif target_provider == "groq":
                res = await self._call_groq(prompt)
            else:
                return {"success": False, "error": f"Unknown AI provider: {target_provider}"}

            if res.get("success"):
                return res

            # If user selected 'auto' and the configured cloud key failed, fall back gracefully to smart_template
            if requested == "auto":
                fallback = self.generate_smart_template(
                    title=title,
                    category=category,
                    condition=condition,
                    price=price,
                    original_price=original_price,
                    brand=brand,
                    color=color,
                    dimensions=dimensions
                )
                fallback["fallback_notice"] = res.get("error")
                return fallback

            return res
        except Exception as e:
            if requested == "auto":
                fallback = self.generate_smart_template(
                    title=title,
                    category=category,
                    condition=condition,
                    price=price,
                    original_price=original_price,
                    brand=brand,
                    color=color,
                    dimensions=dimensions
                )
                fallback["fallback_notice"] = str(e)
                return fallback
            return {"success": False, "error": f"AI provider error ({target_provider}): {str(e)}"}

    async def test_provider(self, provider: str) -> Dict[str, Any]:
        """Tests connectivity and key validity for a specific AI provider."""
        test_prompt = "Reply with 'OK' in 2 words."
        try:
            if provider == "gemini":
                return await self._call_gemini(test_prompt)
            elif provider == "openai":
                return await self._call_openai(test_prompt)
            elif provider == "anthropic":
                return await self._call_anthropic(test_prompt)
            elif provider == "groq":
                return await self._call_groq(test_prompt)
            elif provider == "smart_template":
                return {
                    "success": True,
                    "provider_used": "smart_template",
                    "model_used": "Smart Retail Copy Engine",
                    "description": "Ready"
                }
            return {"success": False, "error": f"Unknown provider: {provider}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


ai_service = AIService()

