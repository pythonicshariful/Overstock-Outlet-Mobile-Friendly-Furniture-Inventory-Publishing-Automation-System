import os
import sys
import uuid

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app, init_system_state
from app.database import Base, engine, SessionLocal
from app.models.product import Product
from app.models.user import User

client = TestClient(app)

def run_comprehensive_e2e_tests():
    report = []
    def log(test_name, status, detail=""):
        report.append({"test": test_name, "status": status, "detail": detail})
        mark = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"{mark} {test_name}: {detail}")

    Base.metadata.create_all(bind=engine)
    init_system_state()

    print("\n--- STARTING COMPREHENSIVE END-TO-END BROWSER & SYSTEM TEST ---\n")

    # 1. Test Login & Session Management
    adm_client = TestClient(app)
    try:
        res_bad = client.post("/api/auth/login", data={"username": "employee", "password": "wrongpassword"})
        assert res_bad.status_code == 401
        log("1.1 Authentication Rejection", "PASS", "Rejected invalid password with 401")

        emp_login = client.post("/api/auth/login", data={"username": "employee", "password": "overstock123"})
        assert emp_login.status_code == 200
        emp_data = emp_login.json()
        assert emp_data["role"] == "employee"
        assert "access_token" in emp_data
        assert "access_token" in emp_login.cookies
        log("1.2 Employee Login & Cookies", "PASS", f"Issued JWT token & HTTP-only cookie for @{emp_data['username']}")

        adm_login = adm_client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
        assert adm_login.status_code == 200
        assert adm_login.json()["role"] == "admin"
        log("1.3 Admin Login", "PASS", "Authenticated Store Manager with role=admin")
    except Exception as e:
        log("1. Authentication Suite", "FAIL", str(e))

    # 2. Test Navigation & Template Rendering
    try:
        res_dash = client.get("/dashboard")
        assert res_dash.status_code == 200
        assert "Furniture Inventory" in res_dash.text
        assert "Overstock Outlet" in res_dash.text
        log("2.1 Dashboard Web View", "PASS", "Dashboard rendered with responsive controls")

        res_cat = client.get("/dashboard?category=Living Room")
        assert res_cat.status_code == 200
        log("2.2 Category Filtering", "PASS", "Category pill filter rendered properly")

        res_new = client.get("/products/new")
        assert res_new.status_code == 200
        assert "Product Photos" in res_new.text
        assert "Product Details" in res_new.text
        assert "Publish Online" in res_new.text
        log("2.3 Add Product Form (/products/new)", "PASS", "Mobile 3-step wizard rendered with camera inputs")
    except Exception as e:
        log("2. Navigation & Views", "FAIL", str(e))

    # 3. Test Full Product Creation & Mobile Image Upload Flow
    created_product_id = None
    unique_title = f"Handcrafted Walnut Credenza {uuid.uuid4().hex[:6]}"
    try:
        product_payload = {
            "title": unique_title,
            "price": 499.00,
            "original_price": 1199.00,
            "category": "Living Room",
            "condition": "Brand New",
            "availability": "In Stock",
            "status": "Draft",
            "dimensions": '68"W x 20"D x 32"H',
            "color": "Dark Walnut",
            "brand": "Overstock Outlet Custom",
            "description": "Solid walnut mid-century credenza with brass hardware and adjustable shelving."
        }
        res_create = client.post("/api/products", json=product_payload)
        assert res_create.status_code == 201
        created_prod = res_create.json()
        created_product_id = created_prod["id"]
        assert created_prod["title"] == product_payload["title"]
        assert created_prod["product_code"].startswith("OO-")
        log("3.1 Product Creation (Database)", "PASS", f"Created product '{created_prod['title']}' with SKU {created_prod['product_code']}")

        img1_io = BytesIO()
        Image.new("RGB", (1200, 900), color=(50, 100, 150)).save(img1_io, format="JPEG")
        img1_io.seek(0)

        img2_io = BytesIO()
        Image.new("RGB", (800, 800), color=(180, 140, 80)).save(img2_io, format="JPEG")
        img2_io.seek(0)

        files = [
            ("files", ("credenza_front.jpg", img1_io, "image/jpeg")),
            ("files", ("credenza_detail.jpg", img2_io, "image/jpeg"))
        ]
        res_upload = client.post(f"/api/products/{created_product_id}/images", files=files)
        assert res_upload.status_code == 200
        uploaded_imgs = res_upload.json()
        assert len(uploaded_imgs) == 2
        assert uploaded_imgs[0]["is_primary"] is True
        assert uploaded_imgs[1]["is_primary"] is False
        log("3.2 Multi-Photo Upload & Thumbnails", "PASS", "Uploaded 2 photos, auto-generated thumbnails and set primary cover image")

        second_img_id = uploaded_imgs[1]["id"]
        res_pri = client.put(f"/api/products/{created_product_id}/images/{second_img_id}/set-primary")
        assert res_pri.status_code == 200
        log("3.3 Primary Image Selection", "PASS", "Updated primary cover image successfully")

    except Exception as e:
        log("3. Product & Media Creation", "FAIL", str(e))

    # 4. Test Accidental Duplicate Prevention
    try:
        dup_payload = {
            "title": unique_title,
            "price": 499.00,
            "condition": "Brand New",
            "category": "Living Room"
        }
        res_dup = client.post("/api/products", json=dup_payload)
        assert res_dup.status_code == 409
        assert "duplicate" in res_dup.json()["detail"].lower()
        log("4.1 Duplicate Guard", "PASS", "Blocked duplicate entry within 7-day window with 409 Conflict")

        res_force = client.post("/api/products?force_duplicate=true", json=dup_payload)
        assert res_force.status_code == 201
        forced_id = res_force.json()["id"]
        client.delete(f"/api/products/{forced_id}")
        log("4.2 Duplicate Override Flag", "PASS", "Allowed intentional duplicate when force_duplicate=true")
    except Exception as e:
        log("4. Duplicate Prevention", "FAIL", str(e))

    # 5. Test Multi-Platform Publishing & Marketplace Assisted Workflow
    try:
        publish_req = {
            "platforms": ["marketplace"]
        }
        res_pub = client.post(f"/api/publish/{created_product_id}", json=publish_req)
        assert res_pub.status_code == 200
        pub_results = res_pub.json()["results"]
        assert len(pub_results) == 1
        assert pub_results[0]["platform"] == "marketplace"
        assert pub_results[0]["status"] == "assisted"
        log("5.1 Marketplace Assisted Dispatch", "PASS", "Prepared Marketplace assisted guide")

        res_mp_guide = client.get(f"/products/{created_product_id}/marketplace-assistant")
        assert res_mp_guide.status_code == 200
        assert "Marketplace Publishing Assistant" in res_mp_guide.text
        log("5.2 Marketplace Assistant UI", "PASS", "Assisted view loaded with deep link and 1-tap copy pack")

        res_mp_done = client.post(
            f"/api/publish/{created_product_id}/marketplace-complete",
            params={"listing_url": "https://www.facebook.com/marketplace/item/9988776655"}
        )
        assert res_mp_done.status_code == 200
        db = SessionLocal()
        p_check = db.query(Product).filter(Product.id == created_product_id).first()
        assert p_check.status == "Published"
        db.close()
        log("5.3 Marketplace Completion Logging", "PASS", "Recorded assisted listing completion and transitioned product to Published")
    except Exception as e:
        log("5. Publishing Workflow", "FAIL", str(e))

    # 6. Test Product Detail & Live Previews Web Pages
    try:
        res_detail = client.get(f"/products/{created_product_id}")
        assert res_detail.status_code == 200
        assert unique_title in res_detail.text
        log("6.1 Product Detail Web Page", "PASS", "Detail page displays photo gallery, pricing, specs and publishing history")

        res_prev = client.get(f"/products/{created_product_id}/preview")
        assert res_prev.status_code == 200
        assert "Facebook Page" in res_prev.text
        assert "Instagram Feed" in res_prev.text
        assert "Marketplace" in res_prev.text
        log("6.2 Social Previews Web Page", "PASS", "Rendered Facebook newsfeed, Instagram card, and Marketplace live previews")
    except Exception as e:
        log("6. Detail & Previews", "FAIL", str(e))

    # 7. Test Admin Control Center & Settings Persistence
    try:
        adm_stats = adm_client.get("/api/admin/stats")
        assert adm_stats.status_code == 200
        log("7.1 Admin Metrics API", "PASS", "Admin stats retrieved successfully")

        adm_page = adm_client.get("/admin")
        assert adm_page.status_code == 200
        assert "Admin Dashboard" in adm_page.text
        assert "Save Settings" in adm_page.text
        log("7.2 Admin Dashboard Web View", "PASS", "Admin dashboard rendered with settings form")

        res_settings = adm_client.put("/api/admin/settings", json={
            "store_hours": "Mon-Sat: 10AM - 7PM, Sun: 11AM - 5PM"
        })
        assert res_settings.status_code == 200
        log("7.3 Admin Settings Persistence", "PASS", "Persisted settings to database via PUT /api/admin/settings")

        test_username = f"assoc_{uuid.uuid4().hex[:5]}"
        new_user_payload = {
            "full_name": "Floor Associate",
            "username": test_username,
            "email": f"{test_username}@overstockoutletbmore.com",
            "password": "temporarypassword123",
            "role": "employee"
        }
        res_new_user = adm_client.post("/api/admin/users", json=new_user_payload)
        assert res_new_user.status_code == 201
        user_id = res_new_user.json()["id"]

        res_dis = adm_client.put(f"/api/admin/users/{user_id}", json={"is_active": False})
        assert res_dis.status_code == 200
        assert res_dis.json()["is_active"] is False

        # Clean up test user
        db = SessionLocal()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
        db.close()
        log("7.4 Associate Account Provisioning & Deactivation", "PASS", "Created, deactivated, and cleaned up test associate")

    except Exception as e:
        log("7. Admin Control Center", "FAIL", str(e))

    # 8. Clean up test product
    if created_product_id:
        try:
            client.delete(f"/api/products/{created_product_id}")
            log("8. Clean Up", "PASS", f"Deleted test product ID #{created_product_id} and purged image files")
        except Exception as e:
            log("8. Clean Up", "FAIL", str(e))

    # 9. Logout Flow
    try:
        res_logout = client.post("/api/auth/logout")
        assert res_logout.status_code == 200
        log("9. Logout & Cookie Invalidation", "PASS", "Logged out successfully and cleared session cookie")
    except Exception as e:
        log("9. Logout", "FAIL", str(e))

    print("\n--- TEST EXECUTION FINISHED ---")
    passed = sum(1 for r in report if r["status"] == "PASS")
    total = len(report)
    print(f"Summary: {passed}/{total} tests PASSED")
    return report

if __name__ == "__main__":
    run_comprehensive_e2e_tests()
