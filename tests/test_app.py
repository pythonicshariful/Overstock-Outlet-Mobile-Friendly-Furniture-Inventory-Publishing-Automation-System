import pytest
from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.product import Product
from app.models.user import User
from app.services.auth_service import init_default_users
from app.services.facebook_service import facebook_service
from app.services.instagram_service import instagram_service
from app.services.marketplace_service import marketplace_service

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    init_default_users(db)
    db.close()
    yield

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
    res = client.get("/api/products")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data

def test_create_product_and_duplicate_prevention():
    import uuid
    unique_suffix = uuid.uuid4().hex[:6]
    # Login as employee
    login_res = client.post("/api/auth/login", data={"username": "employee", "password": "overstock123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

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
    login_res = client.post("/api/auth/login", data={"username": "employee", "password": "overstock123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create dummy product
    create_res = client.post("/api/products", json={
        "title": "Test Accent Chair For Photo Upload",
        "price": 149.00,
        "category": "Living Room",
        "condition": "Brand New"
    }, headers=headers)
    pid = create_res.json()["id"]

    # Create fake in-memory image
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

def test_facebook_caption_and_simulation():
    db = SessionLocal()
    prod = db.query(Product).first()
    db.close()
    if prod:
        caption = facebook_service.format_page_caption(prod)
        assert prod.title in caption
        assert "Baltimore, MD" in caption
        assert "Overstock Outlet" in caption

def test_instagram_caption_and_simulation():
    db = SessionLocal()
    prod = db.query(Product).first()
    db.close()
    if prod:
        caption = instagram_service.format_ig_caption(prod)
        assert prod.title in caption
        assert "@overstockoutletbmore" or "#overstockoutlet" in caption

def test_marketplace_assisted_guide():
    db = SessionLocal()
    try:
        prod = db.query(Product).first()
        if prod:
            guide = marketplace_service.get_assisted_guide(prod)
            assert guide["product_id"] == prod.id
            assert guide["marketplace_url"] == "https://www.facebook.com/marketplace/create/item"
            assert len(guide["instructions"]) > 0
            assert "Baltimore, MD" in guide["description"]
    finally:
        db.close()

def test_web_routes_accessibility():
    # Should redirect root to /dashboard
    res_root = client.get("/", follow_redirects=False)
    assert res_root.status_code == 302
    assert res_root.headers["location"] == "/dashboard"

    # Login page should return 200
    res_login = client.get("/login")
    assert res_login.status_code == 200
    assert "Overstock Outlet" in res_login.text

    # Login as employee to get cookie
    login_res = client.post("/api/auth/login", data={"username": "employee", "password": "overstock123"})
    assert login_res.status_code == 200

    # Test /products/new renders without 500 error
    res_new = client.get("/products/new")
    assert res_new.status_code == 200
    assert "Product Photos" in res_new.text

    # Test dashboard renders
    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 200

    # Test product detail, edit, preview, assistant
    db = SessionLocal()
    prod = db.query(Product).first()
    db.close()
    if prod:
        res_detail = client.get(f"/products/{prod.id}")
        assert res_detail.status_code == 200

        res_edit = client.get(f"/products/{prod.id}/edit")
        assert res_edit.status_code == 200

        res_prev = client.get(f"/products/{prod.id}/preview")
        assert res_prev.status_code == 200

        res_assist = client.get(f"/products/{prod.id}/marketplace-assistant")
        assert res_assist.status_code == 200
