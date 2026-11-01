# Overstock Outlet – Administrator Guide 🛡️

This guide covers system management, employee account provisioning, Meta Graph API configuration, and publishing activity monitoring.

---

## 1. Accessing the Admin Control Center

1. Log in with an administrator account:
   - **Default Username:** `admin`
   - **Default Password:** `admin123`
2. Tap the user menu in the top right and select **"Admin Dashboard"** or navigate to `/admin`.

---

## 2. Managing Employee Accounts

In the Admin Dashboard, switch to the **"Employee Accounts"** tab:
- **Add Associate:** Fill out Full Name, Username, Email, Temporary Password, and Role (`employee` or `admin`).
- **Disable / Enable Account:** When staff members leave or change shifts, click the **"Disable"** button next to their name. Disabled users immediately lose login access.
- **Role Permissions:**
  - `employee`: Can add new inventory, upload photos, edit items, view social previews, and publish.
  - `admin`: Full access including user management, API keys, retry queues, and system statistics.

---

## 3. Monitoring Publishing Activity & Retries

Switch to the **"Publishing Activity & Retries"** tab:
- **Activity Table:** Displays every publishing attempt across Facebook Page, Instagram, and Facebook Marketplace.
- **Status Indicators:**
  - `Success`: Post is live online. Click the "View" icon to open the post directly.
  - `Assisted`: Completed through the Marketplace guided workflow.
  - `Failed`: Graph API error or missing credentials.
- **One-Click Retry:** If a post failed (e.g. temporary network glitch or after updating API credentials), click the yellow **"Retry"** button. The system will immediately attempt to re-publish the item.

---

## 4. Connecting Meta Graph API (Facebook Page & Instagram)

### Official Graph API Requirements

| Channel | Requirement | Permissions Needed |
|---|---|---|
| **Facebook Page** | Admin of Overstock Outlet Page | `pages_manage_posts`, `pages_read_engagement` |
| **Instagram** | Professional / Business Account linked to FB Page | `instagram_basic`, `instagram_content_publish` |

### Setup Steps:
1. Go to the [Meta for Developers Portal](https://developers.facebook.com/).
2. Create a Business App or select your existing app.
3. Add the **Facebook Login for Business** and **Instagram Graph API** products.
4. Generate a **Never-Expiring Page Access Token**:
   - In Graph API Explorer, select your App and get User Token with `pages_manage_posts` and `pages_read_engagement`.
   - Exchange the short-lived token for a long-lived Page Token via `https://graph.facebook.com/{version}/oauth/access_token?grant_type=fb_exchange_token...`.
5. Enter your credentials in the **Admin Dashboard > Social Media & API Settings** tab (and click **Save Settings**) or in the `.env` file:
   - `FB_PAGE_ID` (Found in Page About section)
   - `FB_PAGE_ACCESS_TOKEN` (Long-lived token)
   - `IG_USER_ID` (Linked Instagram Business ID)
   - `STORE_PHONE` & `STORE_HOURS`
6. Click **"Test Connection"** in the Admin Dashboard to verify live connectivity!

---

## 5. Database Backup & Maintenance

The SQLite database is stored locally at `overstock.db`.
- **Daily Backup:** Copy `overstock.db` to a backup drive or cloud folder.
- **Photos:** The `uploads/` folder contains all original and thumbnail photos. Include this folder in your regular backups.
- **PostgreSQL Upgrade:** To upgrade from SQLite to PostgreSQL for high-concurrency environments, set `DATABASE_URL=postgresql://user:pass@host:5432/dbname` in `.env`.
