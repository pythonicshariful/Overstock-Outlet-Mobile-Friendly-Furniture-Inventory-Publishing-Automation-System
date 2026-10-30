# Overstock Outlet – Testing Instructions 🧪

This document provides complete instructions for executing automated tests, running integration tests, and manually verifying all user flows.

---

## 1. Running Automated Tests

Run the full automated test suite with pytest:

```bash
# Windows (from project directory)
.\venv\Scripts\python.exe -m pytest tests/ -v
```

### Expected Output:
```
tests/test_app.py::test_login_success PASSED                             [ 11%]
tests/test_app.py::test_login_invalid_password PASSED                    [ 22%]
tests/test_app.py::test_list_products_api PASSED                         [ 33%]
tests/test_app.py::test_create_product_and_duplicate_prevention PASSED   [ 44%]
tests/test_app.py::test_image_upload_and_thumbnail PASSED                [ 55%]
tests/test_app.py::test_facebook_caption_and_simulation PASSED           [ 66%]
tests/test_app.py::test_instagram_caption_and_simulation PASSED          [ 77%]
tests/test_app.py::test_marketplace_assisted_guide PASSED                [ 88%]
tests/test_app.py::test_web_routes_accessibility PASSED                  [100%]

============================== 9 passed in 1.65s ==============================
```

---

## 2. Test Coverage Breakdown

| Test Name | Feature Tested | Verification |
|---|---|---|
| `test_login_success` | Authentication | Verifies JWT generation and employee role. |
| `test_login_invalid_password` | Security | Confirms 401 Unauthorized on invalid password. |
| `test_list_products_api` | Product Inventory | Tests product retrieval and JSON serialization. |
| `test_create_product_and_duplicate_prevention` | Inventory Logic | Verifies product creation and checks 409 Conflict rejection for accidental duplicate listings within 7 days. |
| `test_image_upload_and_thumbnail` | Media Processing | Tests multipart image upload, PIL image resizing, and thumbnail generation. |
| `test_facebook_caption_and_simulation` | Social Integration | Tests Facebook Page caption builder with store tags and Baltimore address. |
| `test_instagram_caption_and_simulation` | Social Integration | Tests Instagram caption format and hashtags. |
| `test_marketplace_assisted_guide` | Assisted Workflow | Tests generation of 1-tap copy payloads and instruction steps. |
| `test_web_routes_accessibility` | Frontend / Web | Tests redirect and HTTP status codes for core pages. |

---

## 3. Manual End-to-End Test Walkthrough

### Test Case 1: Employee Mobile Experience
1. Start the server using `run.bat` or `python -m uvicorn app.main:app --reload`.
2. Open `http://localhost:8000` (or phone browser with computer IP).
3. Log in with `employee` / `overstock123`.
4. Tap **"Add New Product"**.
5. Upload 1 or 2 test images.
6. Enter title: `Tufted Velvet Storage Ottoman` and price: `129.00`.
7. Tap the **Magic Wand (Auto-Generate)** button to auto-fill the description.
8. Tap **Save & Publish**.
9. Verify the Marketplace Assistant appears with pre-filled title, price, description, and copy buttons.
10. Tap **"Mark as Published on Marketplace"** and verify the item shows as Published in the inventory dashboard.

### Test Case 2: Accidental Duplicate Prevention
1. Go to Add Product.
2. Enter the exact same Title and Price as an item added within the last 7 days.
3. Click Save.
4. Verify an orange warning banner appears notifying that a duplicate exists.

### Test Case 3: Admin Monitoring & Retry
1. Log in with `admin` / `admin123`.
2. Go to `/admin`.
3. Verify overview metrics (Total items, Published, Drafts, Failed).
4. Inspect the Publishing Activity table.
5. Create a new employee account in the User Management tab and test logging in with it.

