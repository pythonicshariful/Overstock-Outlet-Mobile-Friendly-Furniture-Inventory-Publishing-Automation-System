from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode
import httpx
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.publish_log import SystemSetting, PublishLog
from app.models.product import Product
from app.schemas.user import UserOut
from app.services.auth_service import hash_password
from app.services.facebook_service import facebook_service
from app.services.instagram_service import instagram_service
from app.services.ai_service import ai_service
from app.dependencies import require_admin_user

router = APIRouter(prefix="/api/admin", tags=["Admin"])

class CreateUserRequest(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str
    role: str = "employee"

class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class SocialSettingsUpdate(BaseModel):
    meta_app_id: Optional[str] = None
    meta_app_secret: Optional[str] = None
    fb_page_id: Optional[str] = None
    fb_page_token: Optional[str] = None
    ig_user_id: Optional[str] = None
    store_name: Optional[str] = None
    store_location: Optional[str] = None
    store_facebook_page_url: Optional[str] = None
    store_phone: Optional[str] = None
    store_hours: Optional[str] = None

class AutoDiscoverRequest(BaseModel):
    access_token: str
    meta_app_id: Optional[str] = None
    meta_app_secret: Optional[str] = None
    preferred_page_id: Optional[str] = None

class AISettingsUpdate(BaseModel):
    ai_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    anthropic_model: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None
    ai_custom_prompt: Optional[str] = None

def _is_valid_meta_app_id(val: Optional[str]) -> bool:
    """Real Meta App IDs are numeric strings (typically 12-20 digits). Rejects browser-autofilled usernames like 'admin'."""
    if not val:
        return False
    cleaned = val.strip()
    return cleaned.isdigit() and len(cleaned) >= 8

def _upsert_setting(db: Session, key: str, value: str, description: str):
    record = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if record:
        record.value = value
        record.updated_at = datetime.utcnow()
    else:
        record = SystemSetting(key=key, value=value, description=description)
        db.add(record)
    setattr(settings, key, value)

@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin_user)):
    return db.query(User).order_by(User.id).all()

@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_new_user(user_req: CreateUserRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin_user)):
    if db.query(User).filter(User.username == user_req.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == user_req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user_req.username,
        email=user_req.email,
        full_name=user_req.full_name,
        hashed_password=hash_password(user_req.password),
        role=user_req.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/users/{user_id}", response_model=UserOut)
def update_user_details(
    user_id: int,
    user_req: UpdateUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_user)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_req.full_name is not None:
        target_user.full_name = user_req.full_name
    if user_req.email is not None:
        target_user.email = user_req.email
    if user_req.role is not None:
        target_user.role = user_req.role
    if user_req.is_active is not None:
        target_user.is_active = user_req.is_active
    if user_req.password:
        target_user.hashed_password = hash_password(user_req.password)

    db.commit()
    db.refresh(target_user)
    return target_user

@router.put("/settings")
def update_social_settings(
    payload: SocialSettingsUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_user)
):
    if payload.meta_app_id is not None:
        clean_app_id = payload.meta_app_id.strip()
        if clean_app_id == "" or _is_valid_meta_app_id(clean_app_id):
            _upsert_setting(db, "META_APP_ID", clean_app_id, "Meta App ID")
            if payload.meta_app_secret is not None:
                _upsert_setting(db, "META_APP_SECRET", payload.meta_app_secret.strip(), "Meta App Secret")
    if payload.fb_page_id is not None:
        _upsert_setting(db, "FB_PAGE_ID", payload.fb_page_id.strip(), "Facebook Business Page ID")
    if payload.fb_page_token is not None:
        _upsert_setting(db, "FB_PAGE_ACCESS_TOKEN", payload.fb_page_token.strip(), "Facebook Page Access Token")
    if payload.ig_user_id is not None:
        _upsert_setting(db, "IG_USER_ID", payload.ig_user_id.strip(), "Instagram Business Account ID")
    if payload.store_name is not None and payload.store_name.strip():
        _upsert_setting(db, "STORE_NAME", payload.store_name.strip(), "Store Name")
    if payload.store_location is not None and payload.store_location.strip():
        _upsert_setting(db, "STORE_LOCATION", payload.store_location.strip(), "Store Location")
    if payload.store_facebook_page_url is not None and payload.store_facebook_page_url.strip():
        _upsert_setting(db, "STORE_FACEBOOK_PAGE_URL", payload.store_facebook_page_url.strip(), "Store Facebook Page URL")
    if payload.store_phone is not None:
        _upsert_setting(db, "STORE_PHONE", payload.store_phone.strip(), "Store Contact Phone Number")
    if payload.store_hours is not None:
        _upsert_setting(db, "STORE_HOURS", payload.store_hours.strip(), "Store Operating Hours")

    db.commit()
    return {
        "message": "Settings saved successfully",
        "fb_page_id": settings.FB_PAGE_ID,
        "ig_user_id": settings.IG_USER_ID,
        "store_phone": settings.STORE_PHONE,
        "store_hours": settings.STORE_HOURS,
        "has_page_token": bool(settings.FB_PAGE_ACCESS_TOKEN)
    }

async def _discover_and_save_meta_accounts(
    db: Session,
    raw_token: str,
    app_id: Optional[str] = None,
    app_secret: Optional[str] = None,
    preferred_page_id: Optional[str] = None
) -> dict:
    """
    Connects Facebook (and Instagram if linked; otherwise connects Facebook-only!).
    Inspects:
      1. /me/accounts
      2. /debug_token granular_scopes target_ids (catches Pages hidden when business_management is omitted)
      3. /me/assigned_pages & /me/businesses owned_pages
      4. Direct Page ID lookup (if preferred_page_id or settings.FB_PAGE_ID is provided)
      5. /me fallback (connects Facebook-only using the token even if Instagram is not connected)
    """
    base_url = f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"
    working_token = raw_token.strip()
    token_upgraded = False

    # Clean out any accidental browser-autofilled non-numeric App ID (such as 'admin')
    if settings.META_APP_ID and not _is_valid_meta_app_id(settings.META_APP_ID):
        _upsert_setting(db, "META_APP_ID", "", "Meta App ID")
        _upsert_setting(db, "META_APP_SECRET", "", "Meta App Secret")
        db.commit()

    if app_id and _is_valid_meta_app_id(app_id):
        _upsert_setting(db, "META_APP_ID", app_id.strip(), "Meta App ID")
        if app_secret and app_secret.strip():
            _upsert_setting(db, "META_APP_SECRET", app_secret.strip(), "Meta App Secret")

    eff_app_id = settings.META_APP_ID if _is_valid_meta_app_id(settings.META_APP_ID) else ""
    eff_app_secret = (settings.META_APP_SECRET or "").strip() if eff_app_id else ""

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 0. Auto-detect Meta App ID directly from the token via /app
        detected_app_id = eff_app_id
        detected_app_name = ""
        try:
            app_res = await client.get(f"{base_url}/app", params={"access_token": working_token})
            app_data = app_res.json()
            if app_res.status_code == 200 and _is_valid_meta_app_id(str(app_data.get("id", ""))):
                detected_app_id = str(app_data["id"])
                detected_app_name = app_data.get("name", "")
                if not eff_app_id:
                    _upsert_setting(db, "META_APP_ID", detected_app_id, "Meta App ID")
                    eff_app_id = detected_app_id
        except Exception:
            pass

        # 1. Optional exchange for 60-day long-lived user token if valid App ID & Secret exist
        if eff_app_id and eff_app_secret and len(eff_app_secret) >= 16:
            try:
                ex_res = await client.get(
                    f"{base_url}/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": eff_app_id,
                        "client_secret": eff_app_secret,
                        "fb_exchange_token": working_token
                    }
                )
                ex_data = ex_res.json()
                if ex_res.status_code == 200 and "access_token" in ex_data:
                    working_token = ex_data["access_token"]
                    token_upgraded = True
            except Exception:
                pass

        # 2. Fetch managed Pages via /me/accounts using core Page fields
        pages_res = await client.get(
            f"{base_url}/me/accounts",
            params={
                "fields": "id,name,access_token,category",
                "access_token": working_token
            }
        )
        pages_data = pages_res.json()
        pages_list = pages_data.get("data", []) if pages_res.status_code == 200 else []

        # 2b. If /me/accounts is empty, inspect /debug_token granular_scopes target_ids!
        # (In Graph API v21.0, Pages inside Business Suite often only appear in granular_scopes unless business_management is added)
        granular_ig_ids = []
        if len(pages_list) == 0:
            try:
                dbg_res = await client.get(
                    f"{base_url}/debug_token",
                    params={"input_token": working_token, "access_token": working_token}
                )
                dbg_data = dbg_res.json().get("data", {})
                candidate_page_ids = []
                for gs in dbg_data.get("granular_scopes", []):
                    scope_name = gs.get("scope", "")
                    t_ids = gs.get("target_ids") or []
                    if scope_name in ("pages_show_list", "pages_manage_posts", "pages_read_engagement"):
                        for tid in t_ids:
                            if tid not in candidate_page_ids:
                                candidate_page_ids.append(tid)
                    elif scope_name in ("instagram_basic", "instagram_content_publish"):
                        for tid in t_ids:
                            if tid not in granular_ig_ids:
                                granular_ig_ids.append(tid)

                for pid in candidate_page_ids:
                    p_res = await client.get(
                        f"{base_url}/{pid}",
                        params={"fields": "id,name,access_token,category", "access_token": working_token}
                    )
                    if p_res.status_code == 200 and "id" in p_res.json():
                        pages_list.append(p_res.json())
            except Exception:
                pass

        # 2c. Also check /me/assigned_pages and /me/businesses owned_pages if still empty
        if len(pages_list) == 0:
            try:
                assigned_res = await client.get(
                    f"{base_url}/me/assigned_pages",
                    params={"fields": "id,name,access_token,category", "access_token": working_token}
                )
                if assigned_res.status_code == 200 and assigned_res.json().get("data"):
                    pages_list.extend(assigned_res.json()["data"])
            except Exception:
                pass

        if len(pages_list) == 0:
            try:
                biz_res = await client.get(
                    f"{base_url}/me/businesses",
                    params={"fields": "id,name", "access_token": working_token}
                )
                if biz_res.status_code == 200 and biz_res.json().get("data"):
                    for biz in biz_res.json()["data"]:
                        b_pages = await client.get(
                            f"{base_url}/{biz['id']}/owned_pages",
                            params={"fields": "id,name,access_token,category", "access_token": working_token}
                        )
                        if b_pages.status_code == 200 and b_pages.json().get("data"):
                            pages_list.extend(b_pages.json()["data"])
            except Exception:
                pass

        selected_page = None
        available_pages = []

        if len(pages_list) > 0:
            for p in pages_list:
                available_pages.append({
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "category": p.get("category")
                })
            if preferred_page_id:
                selected_page = next((p for p in pages_list if p.get("id") == preferred_page_id.strip()), None)
            if not selected_page:
                selected_page = next(
                    (p for p in pages_list if "overstock" in (p.get("name") or "").lower()),
                    pages_list[0]
                )
        else:
            # 3. Check if a specific Page ID was entered in the UI (or already saved in settings)
            target_pid = (preferred_page_id or settings.FB_PAGE_ID or "").strip()
            if target_pid:
                try:
                    direct_res = await client.get(
                        f"{base_url}/{target_pid}",
                        params={"fields": "id,name,access_token", "access_token": working_token}
                    )
                    direct_data = direct_res.json()
                    if direct_res.status_code == 200 and "id" in direct_data:
                        selected_page = {
                            "id": direct_data["id"],
                            "name": direct_data.get("name", "Facebook Page"),
                            "access_token": direct_data.get("access_token") or working_token
                        }
                except Exception:
                    pass

            # 4. Query /me to validate token and connect Facebook-Only even if no separate Page node was returned
            if not selected_page:
                me_res = await client.get(
                    f"{base_url}/me",
                    params={
                        "fields": "id,name",
                        "access_token": working_token
                    }
                )
                me_data = me_res.json()
                if me_res.status_code != 200 or "id" not in me_data:
                    err_msg = me_data.get("error", {}).get("message") or pages_data.get("error", {}).get("message") or "Invalid or expired Meta access token"
                    raise HTTPException(status_code=400, detail=f"Meta Graph API Error: {err_msg}")

                # Connect Facebook-Only using either preferred_page_id or the authenticated Meta identity
                fallback_id = target_pid if target_pid else me_data["id"]
                selected_page = {
                    "id": fallback_id,
                    "name": me_data.get("name", "Connected Facebook Account"),
                    "access_token": working_token,
                    "is_user_fallback": not bool(target_pid)
                }

        page_id = selected_page["id"]
        page_name = selected_page.get("name", "Facebook")
        page_token = selected_page.get("access_token") or working_token
        is_user_fallback = selected_page.get("is_user_fallback", False)

        # 5. Try to discover Instagram Business Account ONLY if one is linked (completely optional!)
        page_link = ""
        ig_id = ""
        ig_username = ""

        try:
            ig_res = await client.get(
                f"{base_url}/{page_id}",
                params={
                    "fields": "link,instagram_business_account{id,username,name},connected_instagram_account{id,username,name}",
                    "access_token": page_token
                }
            )
            if ig_res.status_code == 200:
                ig_data = ig_res.json()
                page_link = ig_data.get("link") or ""
                ig_obj = ig_data.get("instagram_business_account") or ig_data.get("connected_instagram_account") or {}
                ig_id = ig_obj.get("id") or ""
                ig_username = ig_obj.get("username") or ""
        except Exception:
            pass

        # Also check if granular_scopes had an Instagram ID when the Page query didn't return one
        if not ig_id and granular_ig_ids:
            ig_id = granular_ig_ids[0]
            try:
                ig_u_res = await client.get(
                    f"{base_url}/{ig_id}",
                    params={"fields": "id,username", "access_token": page_token}
                )
                if ig_u_res.status_code == 200:
                    ig_username = ig_u_res.json().get("username") or ""
            except Exception:
                pass

        # Save Facebook connection immediately (and only save IG_USER_ID if Instagram is actually connected)
        _upsert_setting(db, "FB_PAGE_ID", page_id, "Facebook Business Page ID")
        _upsert_setting(db, "FB_PAGE_ACCESS_TOKEN", page_token, "Facebook Page Access Token")
        if ig_id:
            _upsert_setting(db, "IG_USER_ID", ig_id, "Instagram Business Account ID")
        if page_link:
            _upsert_setting(db, "STORE_FACEBOOK_PAGE_URL", page_link, "Store Facebook Page URL")

        db.commit()

        if ig_id:
            msg = f"Connected Facebook '{page_name}' (ID: {page_id}) AND Instagram @{ig_username or ig_id} (ID: {ig_id})!"
        elif is_user_fallback:
            msg = (
                f"Connected Facebook Only for '{page_name}' (ID: {page_id})! Instagram is skipped (not connected). "
                f"Tip: If you have a specific Facebook Business Page ID, you can paste the numeric Page ID into the 'Facebook Page ID' box below or add 'business_management' in Graph API Explorer."
            )
        else:
            msg = f"Connected Facebook Page '{page_name}' (ID: {page_id}) in Facebook-Only Mode! (Instagram is not linked yet and will be skipped automatically)."

        return {
            "success": True,
            "facebook_only": not bool(ig_id),
            "token_upgraded_to_permanent": token_upgraded,
            "detected_app_id": detected_app_id,
            "page_id": page_id,
            "page_name": page_name,
            "ig_user_id": ig_id or settings.IG_USER_ID,
            "ig_username": ig_username,
            "available_pages": available_pages,
            "message": msg
        }

@router.post("/connections/auto-discover")
async def auto_discover_social_accounts(
    req: AutoDiscoverRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_user)
):
    if not req.access_token or not req.access_token.strip():
        raise HTTPException(status_code=400, detail="Please paste a valid Meta Access Token.")
    return await _discover_and_save_meta_accounts(
        db=db,
        raw_token=req.access_token,
        app_id=req.meta_app_id,
        app_secret=req.meta_app_secret,
        preferred_page_id=req.preferred_page_id
    )

@router.get("/oauth/facebook/start")
def start_facebook_oauth(
    request: Request,
    app_id: Optional[str] = Query(None),
    app_secret: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_user)
):
    if app_id and _is_valid_meta_app_id(app_id):
        _upsert_setting(db, "META_APP_ID", app_id.strip(), "Meta App ID")
        if app_secret and app_secret.strip():
            _upsert_setting(db, "META_APP_SECRET", app_secret.strip(), "Meta App Secret")
        db.commit()

    eff_app_id = (settings.META_APP_ID or "").strip()
    if not _is_valid_meta_app_id(eff_app_id):
        msg = "Please enter your numeric 15-digit Meta App ID from developers.facebook.com/apps (not your admin username) to use OAuth Login, or use the Token Auto-Discover button instead."
        return RedirectResponse(url=f"/admin?tab=settings&oauth_error={urlencode({'m': msg})[2:]}")

    redirect_uri = f"{str(request.base_url).rstrip('/')}/api/admin/oauth/facebook/callback"
    params = {
        "client_id": eff_app_id,
        "redirect_uri": redirect_uri,
        "scope": "pages_manage_posts,pages_read_engagement,pages_show_list",
        "response_type": "code"
    }
    oauth_url = f"https://www.facebook.com/{settings.META_GRAPH_API_VERSION}/dialog/oauth?{urlencode(params)}"
    return RedirectResponse(url=oauth_url)

@router.get("/oauth/facebook/callback")
async def facebook_oauth_callback(
    request: Request,
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_user)
):
    if error or not code:
        msg = error_description or error or "OAuth authorization cancelled"
        return RedirectResponse(url=f"/admin?tab=settings&oauth_error={urlencode({'m': msg})[2:]}")

    redirect_uri = f"{str(request.base_url).rstrip('/')}/api/admin/oauth/facebook/callback"
    base_url = f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_res = await client.get(
            f"{base_url}/oauth/access_token",
            params={
                "client_id": settings.META_APP_ID,
                "client_secret": settings.META_APP_SECRET,
                "redirect_uri": redirect_uri,
                "code": code
            }
        )
        token_data = token_res.json()
        if token_res.status_code != 200 or "access_token" not in token_data:
            err = token_data.get("error", {}).get("message", "Failed exchanging OAuth code")
            return RedirectResponse(url=f"/admin?tab=settings&oauth_error={urlencode({'m': err})[2:]}")

        user_token = token_data["access_token"]

    try:
        await _discover_and_save_meta_accounts(
            db=db,
            raw_token=user_token,
            app_id=settings.META_APP_ID,
            app_secret=settings.META_APP_SECRET
        )
        return RedirectResponse(url="/admin?tab=settings&oauth_success=1")
    except HTTPException as e:
        return RedirectResponse(url=f"/admin?tab=settings&oauth_error={urlencode({'m': e.detail})[2:]}")

@router.put("/ai-settings")
def update_ai_settings(
    payload: AISettingsUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_user)
):
    if payload.ai_provider is not None:
        _upsert_setting(db, "AI_PROVIDER", payload.ai_provider.strip(), "Default AI Provider")
    if payload.gemini_api_key is not None:
        _upsert_setting(db, "GEMINI_API_KEY", payload.gemini_api_key.strip(), "Google Gemini API Key")
    if payload.gemini_model is not None:
        _upsert_setting(db, "GEMINI_MODEL", payload.gemini_model.strip() or "gemini-2.5-flash", "Google Gemini Model")
    if payload.openai_api_key is not None:
        _upsert_setting(db, "OPENAI_API_KEY", payload.openai_api_key.strip(), "OpenAI API Key")
    if payload.openai_model is not None:
        _upsert_setting(db, "OPENAI_MODEL", payload.openai_model.strip() or "gpt-4o-mini", "OpenAI Model")
    if payload.anthropic_api_key is not None:
        _upsert_setting(db, "ANTHROPIC_API_KEY", payload.anthropic_api_key.strip(), "Anthropic Claude API Key")
    if payload.anthropic_model is not None:
        _upsert_setting(db, "ANTHROPIC_MODEL", payload.anthropic_model.strip() or "claude-3-5-haiku-latest", "Anthropic Claude Model")
    if payload.groq_api_key is not None:
        _upsert_setting(db, "GROQ_API_KEY", payload.groq_api_key.strip(), "Groq API Key")
    if payload.groq_model is not None:
        _upsert_setting(db, "GROQ_MODEL", payload.groq_model.strip() or "llama-3.3-70b-versatile", "Groq Model")
    if payload.ai_custom_prompt is not None:
        _upsert_setting(db, "AI_CUSTOM_PROMPT", payload.ai_custom_prompt.strip(), "Custom AI Copywriting Prompt")

    db.commit()
    return {
        "message": "AI settings saved successfully",
        "status": ai_service.get_provider_status()
    }

@router.get("/ai/test")
async def test_ai_connections(
    provider: Optional[str] = Query(None, description="Specific provider to test, or omit to test all configured"),
    admin: User = Depends(require_admin_user)
):
    if provider and provider != "all":
        res = await ai_service.test_provider(provider)
        return {"results": {provider: res}}

    results = {}
    status_info = ai_service.get_provider_status()["providers"]
    for prov_key, info in status_info.items():
        if prov_key == "smart_template":
            results[prov_key] = {"success": True, "message": "Built-in Smart Retail Copy Engine is active and ready."}
        elif info["configured"]:
            test_res = await ai_service.test_provider(prov_key)
            if test_res.get("success"):
                results[prov_key] = {
                    "success": True,
                    "message": f"Connected to {info['name']} ({info['model']})"
                }
            else:
                results[prov_key] = {
                    "success": False,
                    "message": test_res.get("error", "Connection failed")
                }
        else:
            results[prov_key] = {
                "success": False,
                "unconfigured": True,
                "message": "API key not configured"
            }
    return {"results": results}

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db), admin: User = Depends(require_admin_user)):
    total_products = db.query(Product).count()
    published_count = db.query(Product).filter(Product.status == "Published").count()
    draft_count = db.query(Product).filter(Product.status == "Draft").count()
    total_users = db.query(User).count()
    
    total_publishes = db.query(PublishLog).count()
    successful_publishes = db.query(PublishLog).filter(PublishLog.status == "success").count()
    failed_publishes = db.query(PublishLog).filter(PublishLog.status == "failed").count()
    assisted_publishes = db.query(PublishLog).filter(PublishLog.status == "assisted").count()

    return {
        "products": {
            "total": total_products,
            "published": published_count,
            "draft": draft_count
        },
        "publishing": {
            "total": total_publishes,
            "success": successful_publishes,
            "failed": failed_publishes,
            "assisted": assisted_publishes
        },
        "users": total_users
    }

@router.get("/connections/test")
async def test_social_connections(admin: User = Depends(require_admin_user)):
    fb_status = await facebook_service.verify_connection()
    ig_status = await instagram_service.verify_connection()
    return {
        "facebook_page": fb_status,
        "instagram": ig_status
    }
