from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "Overstock Outlet - Inventory & Publishing"
    APP_ENV: str = "production"
    SECRET_KEY: str = "overstock-outlet-secret-key-change-in-production-2026-bmore"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days for mobile session ease
    
    # Store Info
    STORE_NAME: str = "Overstock Outlet"
    STORE_LOCATION: str = "Baltimore, MD, USA"
    STORE_FACEBOOK_PAGE_URL: str = "https://www.facebook.com/overstockoutletbmore"
    STORE_PHONE: str = ""
    STORE_HOURS: str = "Mon-Sat: 10AM - 7PM, Sun: 11AM - 5PM"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/overstock.db"
    
    # Storage
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    MAX_IMAGE_SIZE_MB: int = 15
    ALLOWED_EXTENSIONS: set = {"jpg", "jpeg", "png", "webp"}
    
    # Meta / Facebook & Instagram Graph API Configuration
    META_GRAPH_API_VERSION: str = "v21.0"
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    FB_PAGE_ID: str = ""
    FB_PAGE_ACCESS_TOKEN: str = ""
    IG_USER_ID: str = ""

    # Multi-Provider AI Copywriting & Vision Configuration
    AI_PROVIDER: str = "auto"  # "auto", "gemini", "openai", "anthropic", "groq", "smart_template"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-haiku-latest"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    AI_CUSTOM_PROMPT: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

settings = Settings()

# Ensure uploads directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(settings.UPLOAD_DIR / "thumbnails").mkdir(parents=True, exist_ok=True)
