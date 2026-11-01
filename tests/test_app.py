import uuid
import pytest
from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app, init_system_state
from app.database import Base, engine
from app.models.product import Product
from app.services.facebook_service import facebook_service
from app.services.instagram_service import instagram_service
from app.services.marketplace_service import marketplace_service
from app.services.ai_service import ai_service

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    init_system_state()
    yield

def _get_auth_headers(username: str = "employee", password: str = "overstock123") -> dict:
    res = client.post("/api/auth/login", data={"username": username, "password": password})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_login_success():
    res = client.post("/api/auth/login", data={"username": "employee", "password": "overstock123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "employee"

def test_login_invalid_password():
    res = client.post("/api/auth/login", data={"username": "employee", "password": "wrongpassword"})
    assert res.status_code == 401

def test_list_products_api():
    headers = _get_auth_headers()
    res = client.get("/api/products", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data

def test_create_product_and_duplicate_prevention():
    unique_suffix = uuid.uuid4().hex[:6]
    headers = _get_auth_headers()

    payload = {
        "title": f"Modern Scandinavian Oak Coffee Table {unique_suffix}",
        "price": 179.00,
        "original_price": 399.00,
        "category": "Living Room",
        "condition": "Brand New",
        "availability": "In Stock",
        "status": "Draft",
        "color": "Natural Oak",
        "brand": "Overstock Outlet",
        "description": "Minimalist coffee table with solid legs."
    }

    # 1. First creation should succeed
    res1 = client.post("/api/products", json=payload, headers=headers)
    assert res1.status_code == 201
    created1 = res1.json()
    product_id1 = created1["id"]
    assert created1["title"] == payload["title"]

    # 2. Immediate duplicate creation without force_duplicate should trigger 409 Conflict
    res2 = client.post("/api/products", json=payload, headers=headers)
    assert res2.status_code == 409
    assert "duplicate" in res2.json()["detail"].lower()

    # 3. Can bypass if force_duplicate=true
    res3 = client.post("/api/products?force_duplicate=true", json=payload, headers=headers)
    assert res3.status_code == 201
    product_id2 = res3.json()["id"]

    # Cleanup created test products
    client.delete(f"/api/products/{product_id1}", headers=headers)
    client.delete(f"/api/products/{product_id2}", headers=headers)

def test_image_upload_and_thumbnail():
    headers = _get_auth_headers()

    create_res = client.post("/api/products?force_duplicate=true", json={
        "title": f"Test Accent Chair {uuid.uuid4().hex[:6]}",
        "price": 149.00,
        "category": "Living Room",
        "condition": "Brand New"
    }, headers=headers)
    pid = create_res.json()["id"]

    file_io = BytesIO()
    img = Image.new("RGB", (600, 600), color="blue")
    img.save(file_io, format="JPEG")
    file_io.seek(0)

    files = [("files", ("chair_test.jpg", file_io, "image/jpeg"))]
    upload_res = client.post(f"/api/products/{pid}/images", files=files, headers=headers)
    assert upload_res.status_code == 200
    images = upload_res.json()
    assert len(images) == 1
    assert images[0]["is_primary"] is True

    # Cleanup
    client.delete(f"/api/products/{pid}", headers=headers)

def test_facebook_and_instagram_captions():
    sample = Product(
        id=1,
        product_code="OO-TEST-001",
        title="Solid Oak Dining Table",
        price=425.0,
        original_price=950.0,
        category="Dining Room",
        condition="Brand New",
        availability="In Stock",
        brand="Overstock Outlet"
    )
    fb_caption = facebook_service.format_page_caption(sample)
    assert "Solid Oak Dining Table" in fb_caption
    assert "Baltimore, MD" in fb_caption
    assert "Overstock Outlet" in fb_caption

    ig_caption = instagram_service.format_ig_caption(sample)
    assert "Solid Oak Dining Table" in ig_caption
    assert "#overstockoutlet" in ig_caption

def test_ai_multi_provider_and_smart_template():
    status = ai_service.get_provider_status()
    assert "gemini" in status["providers"]
    assert "openai" in status["providers"]
    assert "anthropic" in status["providers"]
    assert "groq" in status["providers"]
    assert "smart_template" in status["providers"]

    res = ai_service.generate_smart_template(
        title="West Elm Velvet Sectional Sofa",
        category="Living Room",
        condition="Like New",
        price=649.0,
        original_price=1899.0,
        brand="West Elm",
        color="Emerald Green",
        dimensions="92x41x34"
    )
    assert res["success"] is True
    assert "save $1,250" in res["description"].lower()

def test_marketplace_assisted_guide():
    sample = Product(
        id=1,
        product_code="OO-TEST-002",
        title="Velvet Sectional Sofa",
        price=649.0,
        original_price=1299.0,
        category="Living Room",
        condition="Like New",
        availability="In Stock"
    )
    sample.images = []
    guide = marketplace_service.get_assisted_guide(sample)
    assert guide["product_id"] == 1
    assert guide["marketplace_url"] == "https://www.facebook.com/marketplace/create/item"
    assert len(guide["instructions"]) > 0
    assert "Baltimore, MD" in guide["description"]

def test_admin_settings_persistence():
    admin_headers = _get_auth_headers("admin", "admin123")
    res = client.put("/api/admin/settings", json={
        "store_hours": "Mon-Sat: 10AM - 7PM, Sun: 11AM - 5PM",
        "store_phone": ""
    }, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["message"] == "Settings saved successfully"

    ai_res = client.put("/api/admin/ai-settings", json={
        "ai_provider": "auto",
        "gemini_model": "gemini-2.5-flash"
    }, headers=admin_headers)
    assert ai_res.status_code == 200

def test_web_routes_accessibility():
    res_root = client.get("/", follow_redirects=False)
    assert res_root.status_code == 302
    assert res_root.headers["location"] == "/dashboard"

    client.cookies.clear()
    res_login = client.get("/login")
    assert res_login.status_code == 200
    assert "Overstock Outlet" in res_login.text
    assert "One-Click Demo" not in res_login.text

    login_res = client.post("/api/auth/login", data={"username": "employee", "password": "overstock123"})
    assert login_res.status_code == 200

    res_new = client.get("/products/new")
    assert res_new.status_code == 200
    assert "Product Photos" in res_new.text

    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 200

    create_res = client.post("/api/products?force_duplicate=true", json={
        "title": f"Route Verification Sofa {uuid.uuid4().hex[:6]}",
        "price": 399.00,
        "category": "Living Room",
        "condition": "Brand New"
    })
    assert create_res.status_code == 201
    pid = create_res.json()["id"]

    try:
        assert client.get(f"/products/{pid}").status_code == 200
        assert client.get(f"/products/{pid}/edit").status_code == 200
        assert client.get(f"/products/{pid}/preview").status_code == 200
        assert client.get(f"/products/{pid}/marketplace-assistant").status_code == 200
    finally:
        client.delete(f"/api/products/{pid}")
