from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings, BASE_DIR
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.product import Product, ProductImage
from app.models.publish_log import PublishLog, SystemSetting
from app.services.auth_service import init_default_users
from app.routers import auth, products, publish, admin, web

PERSISTED_SETTING_KEYS = {
    "META_APP_ID",
    "META_APP_SECRET",
    "FB_PAGE_ID",
    "FB_PAGE_ACCESS_TOKEN",
    "IG_USER_ID",
    "STORE_NAME",
    "STORE_PHONE",
    "STORE_HOURS",
    "STORE_LOCATION",
    "STORE_FACEBOOK_PAGE_URL",
    "AI_PROVIDER",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "AI_CUSTOM_PROMPT",
}

def init_system_state():
    """Initializes default user accounts and loads persisted system settings from the database."""
    db = SessionLocal()
    try:
        init_default_users(db)

        # Clean up any accidental browser-autofilled non-numeric META_APP_ID (e.g., 'admin')
        app_id_row = db.query(SystemSetting).filter(SystemSetting.key == "META_APP_ID").first()
        if app_id_row and app_id_row.value and not app_id_row.value.strip().isdigit():
            db.query(SystemSetting).filter(SystemSetting.key.in_(["META_APP_ID", "META_APP_SECRET"])).delete(synchronize_session=False)
            db.commit()

        stored_settings = db.query(SystemSetting).filter(
            SystemSetting.key.in_(PERSISTED_SETTING_KEYS)
        ).all()
        for item in stored_settings:
            if item.value is not None and hasattr(settings, item.key):
                setattr(settings, item.key, item.value)
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    init_system_state()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Mobile-Friendly Furniture Inventory & Publishing Automation System for Overstock Outlet, Baltimore MD",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Folders
STATIC_DIR = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/static_uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="static_uploads")

# Include Routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(publish.router)
app.include_router(admin.router)
app.include_router(web.router)
