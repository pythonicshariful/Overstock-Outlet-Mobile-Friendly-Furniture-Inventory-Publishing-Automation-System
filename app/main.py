import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings, BASE_DIR
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.product import Product, ProductImage
from app.models.publish_log import PublishLog
from app.services.auth_service import init_default_users
from app.routers import auth, products, publish, admin, web

def seed_sample_inventory():
    """Seeds realistic Overstock Outlet Baltimore furniture items if database is brand new."""
    db = SessionLocal()
    try:
        init_default_users(db)
        
        count = db.query(Product).count()
        if count == 0:
            admin_user = db.query(User).filter(User.username == "admin").first()
            user_id = admin_user.id if admin_user else 1

            sample_items = [
                {
                    "product_code": "OO-2610-A101",
                    "title": "West Elm Harmony 92\" Down-Filled Sofa - Charcoal Gray",
                    "price": 649.00,
                    "original_price": 1899.00,
                    "category": "Living Room",
                    "condition": "Like New",
                    "availability": "In Stock",
                    "status": "Published",
                    "dimensions": "92\"W x 41\"D x 34\"H",
                    "color": "Charcoal Gray",
                    "brand": "West Elm",
                    "description": "Stunning West Elm Harmony sofa in plush charcoal performance velvet. Pillowy soft, deep-seated relaxation with goose down cushions. Floor model in like-new condition with zero blemishes. Over $1,200 off retail price! Available for immediate pickup at Overstock Outlet Baltimore."
                },
                {
                    "product_code": "OO-2610-B204",
                    "title": "Rustic Solid Oak 6-Person Dining Table with Trestle Base",
                    "price": 425.00,
                    "original_price": 950.00,
                    "category": "Dining Room",
                    "condition": "Brand New",
                    "availability": "In Stock",
                    "status": "Published",
                    "dimensions": "72\"L x 36\"W x 30\"H",
                    "color": "Natural Weathered Oak",
                    "brand": "Pottery Barn Outlet",
                    "description": "Brand new handcrafted solid white oak dining table with rustic trestle legs. Heavy, durable, and seats up to 8 people comfortably. Scratch-resistant matte lacquer finish."
                },
                {
                    "product_code": "OO-2610-C309",
                    "title": "Mid-Century Modern Top-Grain Leather Accent Armchair",
                    "price": 289.00,
                    "original_price": 680.00,
                    "category": "Living Room",
                    "condition": "Brand New",
                    "availability": "Low Stock",
                    "status": "Draft",
                    "dimensions": "32\"W x 34\"D x 33\"H",
                    "color": "Cognac Brown",
                    "brand": "Article Style",
                    "description": "Buttery soft cognac genuine leather with solid walnut wood angled frame. High density foam cushioning provides ergonomic support. Perfect accent piece for living room or home office."
                },
                {
                    "product_code": "OO-2610-D412",
                    "title": "Modern Farmhouse King Size Storage Bed Frame with 4 Drawers",
                    "price": 549.00,
                    "original_price": 1299.00,
                    "category": "Bedroom",
                    "condition": "Brand New",
                    "availability": "In Stock",
                    "status": "Ready",
                    "dimensions": "King Size - 86\"L x 80\"W x 52\"H",
                    "color": "Distressed White / Barnwood",
                    "brand": "Overstock Outlet Selected",
                    "description": "Solid engineered wood king bed frame with paneled headboard and 4 built-in smooth sliding under-bed drawers. Built-in slats support mattress without needing a box spring."
                }
            ]

            for item_data in sample_items:
                product = Product(**item_data, created_by_id=user_id)
                db.add(product)
            db.commit()

            # Add sample publishing log
            p1 = db.query(Product).filter(Product.product_code == "OO-2610-A101").first()
            if p1:
                log_fb = PublishLog(
                    product_id=p1.id,
                    platform="facebook_page",
                    status="success",
                    external_id="108293847291_10293849102",
                    post_url=f"{settings.STORE_FACEBOOK_PAGE_URL}/posts/10293849102",
                    payload_summary=f"Published {p1.title} to Overstock Outlet Page"
                )
                log_ig = PublishLog(
                    product_id=p1.id,
                    platform="instagram",
                    status="success",
                    external_id="1784149029384",
                    post_url="https://www.instagram.com/p/C_sample123/",
                    payload_summary=f"Published {p1.title} to Instagram"
                )
                db.add(log_fb)
                db.add(log_ig)
                db.commit()

    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and seed default users & sample inventory
    Base.metadata.create_all(bind=engine)
    seed_sample_inventory()
    yield
    # Shutdown

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
