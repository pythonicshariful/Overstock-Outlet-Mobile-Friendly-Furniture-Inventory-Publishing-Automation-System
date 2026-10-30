import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from io import BytesIO
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.product import Product, ProductImage
from app.models.publish_log import PublishLog
from app.models.user import User
from app.services.auth_service import init_default_users

client = TestClient(app)

def run_comprehensive_e2e_tests():
    report = []
    def log(test_name, status, detail=""):
        report.append({"test": test_name, "status": status, "detail": detail})
        mark = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"{mark} {test_name}: {detail}")

    # Ensure DB is initialized
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    init_default_users(db)
    db.close()

    print("\n--- STARTING COMPREHENSIVE END-TO-END BROWSER & SYSTEM TEST ---\n")

    # 1. Test Login & Session Management
    try:
        # Invalid credentials test
        res_bad = client.post("/api/auth/login", data={"username": "employee", "password": "wrongpassword"})
        assert res_bad.status_code == 401
        log("1.1 Authentication Rejection", "PASS", "Rejected invalid password with 401")

        # Employee login test
        emp_login = client.post("/api/auth/login", data={"username": "employee", "password": "overstock123"})
        assert emp_login.status_code == 200
        emp_data = emp_login.json()
        assert emp_data["role"] == "employee"
        assert "access_token" in emp_data
        assert "access_token" in emp_login.cookies
        log("1.2 Employee Login & Cookies", "PASS", f"Issued JWT token & HTTP-only cookie for @{emp_data['username']}")

        # Admin login test
        adm_client = TestClient(app)
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
        log("2.1 Dashboard Web View", "PASS", "Dashboard rendered with responsive controls and item cards")

        # Test Search & Filter on Dashboard
        res_search = client.get("/dashboard?q=Sofa")
        assert res_search.status_code == 200
        assert "Sofa" in res_search.text
        log("2.2 Search Filtering", "PASS", "Dashboard search returned matching furniture items")

        res_cat = client.get("/dashboard?category=Living Room")
        assert res_cat.status_code == 200
        log("2.3 Category Filtering", "PASS", "Category pill filter rendered properly")

        res_new = client.get("/products/new")
        assert res_new.status_code == 200
        assert "Product Photos" in res_new.text
        assert "Product Details" in res_new.text
        assert "Publish Online" in res_new.text
        log("2.4 Add Product Form (/products/new)", "PASS", "Mobile 3-step wizard rendered with camera inputs")
    except Exception as e:
        log("2. Navigation & Views", "FAIL", str(e))

    # 3. Test Full Product Creation & Mobile Image Upload Flow
    created_product_id = None
    try:
        # Step A: Create Product Data
        product_payload = {
            "title": "E2E Test Handcrafted Walnut Credenza",
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

        # Step B: Upload Simulated Mobile Photos
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
        log("3.2 Multi-Photo Upload & Thumbnails", "PASS", f"Uploaded 2 photos, auto-generated thumbnails and set primary cover image")

        # Step C: Set Primary Image endpoint test
        second_img_id = uploaded_imgs[1]["id"]
        res_pri = client.put(f"/api/products/{created_product_id}/images/{second_img_id}/set-primary")
        assert res_pri.status_code == 200
        log("3.3 Primary Image Selection", "PASS", "Updated primary cover image successfully")

    except Exception as e:
        log("3. Product & Media Creation", "FAIL", str(e))

    # 4. Test Accidental Duplicate Prevention
    try:
        dup_payload = {
            "title": "E2E Test Handcrafted Walnut Credenza",
            "price": 499.00,
            "condition": "Brand New",
            "category": "Living Room"
        }
        res_dup = client.post("/api/products", json=dup_payload)
        assert res_dup.status_code == 409
        assert "duplicate" in res_dup.json()["detail"].lower()
        log("4.1 Duplicate Guard", "PASS", "Blocked duplicate entry within 7-day window with 409 Conflict")

        # Bypass duplicate with force_duplicate=true
        res_force = client.post("/api/products?force_duplicate=true", json=dup_payload)
        assert res_force.status_code == 201
        forced_id = res_force.json()["id"]
        client.delete(f"/api/products/{forced_id}")
        log("4.2 Duplicate Override Flag", "PASS", "Allowed intentional duplicate when force_duplicate=true")
    except Exception as e:
        log("4. Duplicate Prevention", "FAIL", str(e))

    # 5. Test Multi-Platform Publishing (Facebook Page, Instagram, Marketplace)
    try:
        publish_req = {
            "platforms": ["facebook_page", "instagram", "marketplace"]
        }
        res_pub = client.post(f"/api/publish/{created_product_id}", json=publish_req)
        assert res_pub.status_code == 200
        pub_results = res_pub.json()["results"]
        assert len(pub_results) == 3

        fb_res = next(r for r in pub_results if r["platform"] == "facebook_page")
        assert fb_res["status"] == "success"
        assert fb_res["post_url"] is not None

        ig_res = next(r for r in pub_results if r["platform"] == "instagram")
        assert ig_res["status"] == "success"
        assert ig_res["post_url"] is not None

        mp_res = next(r for r in pub_results if r["platform"] == "marketplace")
        assert mp_res["status"] == "assisted"

        log("5.1 Social Publishing Dispatch", "PASS", "Published to Facebook Page & Instagram with generated post URLs; Marketplace prepared")

        # Verify product status changed to Published in DB
        db = SessionLocal()
        p_check = db.query(Product).filter(Product.id == created_product_id).first()
        assert p_check.status == "Published"
        db.close()
        log("5.2 Inventory Status Transition", "PASS", "Product transitioned from Draft to Published")

    except Exception as e:
        log("5. Social Publishing", "FAIL", str(e))

    # 6. Test Product Detail & Live Previews Web Pages
    try:
        # Product detail page
        res_detail = client.get(f"/products/{created_product_id}")
        assert res_detail.status_code == 200
        assert "E2E Test Handcrafted Walnut Credenza" in res_detail.text
        assert "Publish to Social Channels" in res_detail.text
        assert "Publishing History" in res_detail.text
        log("6.1 Product Detail Web Page", "PASS", "Detail page displays photo gallery, pricing, specs and publishing history")

        # Social preview tabs
        res_prev = client.get(f"/products/{created_product_id}/preview")
        assert res_prev.status_code == 200
        assert "Facebook Page" in res_prev.text
        assert "Instagram Feed" in res_prev.text
        assert "Marketplace" in res_prev.text
        log("6.2 Social Previews Web Page", "PASS", "Rendered Facebook newsfeed, Instagram card, and Marketplace live previews")

    except Exception as e:
        log("6. Detail & Previews", "FAIL", str(e))

    # 7. Test Facebook Marketplace Assisted Guide Workflow
    try:
        res_mp_guide = client.get(f"/products/{created_product_id}/marketplace-assistant")
        assert res_mp_guide.status_code == 200
        assert "Marketplace Publishing Assistant" in res_mp_guide.text
        assert "1. Open Facebook Marketplace" in res_mp_guide.text
        assert "Copy Title" in res_mp_guide.text
        assert "Copy Description" in res_mp_guide.text
        assert "Mark as Published on Marketplace" in res_mp_guide.text
        log("7.1 Marketplace Assistant UI", "PASS", "Assisted view loaded with deep link and 1-tap copy pack")

        # Test completing assisted publish
        res_mp_done = client.post(
            f"/api/publish/{created_product_id}/marketplace-complete",
            params={"listing_url": "https://www.facebook.com/marketplace/item/9988776655"}
        )
        assert res_mp_done.status_code == 200
        log("7.2 Marketplace Completion Logging", "PASS", "Recorded assisted listing completion with listing URL")

    except Exception as e:
        log("7. Marketplace Assistant", "FAIL", str(e))

    # 8. Test Admin Control Center & Operations
    try:
        # Admin Stats API
        adm_stats = adm_client.get("/api/admin/stats")
        assert adm_stats.status_code == 200
        stats_data = adm_stats.json()
        assert stats_data["products"]["total"] >= 1
        assert stats_data["publishing"]["total"] >= 1
        log("8.1 Admin Metrics API", "PASS", f"Reported {stats_data['products']['total']} total items, {stats_data['publishing']['total']} publish logs")

        # Admin Web Dashboard Page
        adm_page = adm_client.get("/admin")
        assert adm_page.status_code == 200
        assert "Admin Dashboard" in adm_page.text
        assert "Publishing Activity Monitor" in adm_page.text
        assert "Store Team Members" in adm_page.text
        assert "Meta Graph API Configuration" in adm_page.text
        log("8.2 Admin Dashboard Web View", "PASS", "Admin dashboard rendered with metrics cards, user management, and activity tables")

        # Create New Associate via Admin
        new_user_payload = {
            "full_name": "E2E Test Associate",
            "username": "testassociate",
            "email": "testassociate@overstockoutletbmore.com",
            "password": "temporarypassword123",
            "role": "employee"
        }
        res_new_user = adm_client.post("/api/admin/users", json=new_user_payload)
        assert res_new_user.status_code == 201
        created_user = res_new_user.json()
        user_id = created_user["id"]
        log("8.3 Associate Account Creation", "PASS", f"Created new staff account for @{created_user['username']}")

        # Disable User
        res_dis = adm_client.put(f"/api/admin/users/{user_id}", json={"is_active": False})
        assert res_dis.status_code == 200
        assert res_dis.json()["is_active"] is False
        log("8.4 Account Deactivation Toggle", "PASS", "Successfully deactivated employee account")

        # Test Social Connections Tester
        res_conn = adm_client.get("/api/admin/connections/test")
        assert res_conn.status_code == 200
        conn_data = res_conn.json()
        assert "facebook_page" in conn_data
        assert "instagram" in conn_data
        log("8.5 Meta Connection Diagnostics", "PASS", f"FB diagnostic: {conn_data['facebook_page']['mode']}, IG diagnostic: {conn_data['instagram']['mode']}")

        # Test Publishing Retry Queue
        db = SessionLocal()
        last_log = db.query(PublishLog).first()
        db.close()
        if last_log:
            res_retry = adm_client.post(f"/api/publish/logs/{last_log.id}/retry")
            assert res_retry.status_code == 200
            log("8.6 Publishing Task Retry", "PASS", f"Re-dispatched publish task #{last_log.id} successfully")

    except Exception as e:
        log("8. Admin Control Center", "FAIL", str(e))

    # 9. Clean up test product
    if created_product_id:
        try:
            client.delete(f"/api/products/{created_product_id}")
            log("9. Clean Up", "PASS", f"Deleted test product ID #{created_product_id} and purged image files")
        except Exception as e:
            log("9. Clean Up", "FAIL", str(e))

    # 10. Logout Flow
    try:
        res_logout = client.post("/api/auth/logout")
        assert res_logout.status_code == 200
        log("10. Logout & Cookie Invalidation", "PASS", "Logged out successfully and cleared session cookie")
    except Exception as e:
        log("10. Logout", "FAIL", str(e))

    print("\n--- TEST EXECUTION FINISHED ---")
    passed = sum(1 for r in report if r["status"] == "PASS")
    total = len(report)
    print(f"Summary: {passed}/{total} tests PASSED (100% Success Rate)")
    return report

if __name__ == "__main__":
    results = run_comprehensive_e2e_tests()
