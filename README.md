# Overstock Outlet – Mobile-Friendly Furniture Inventory & Publishing Automation System

[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()
[![Zero .env Required](https://img.shields.io/badge/Setup-100%25%20Web%20UI%20Driven-orange.svg)]()
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Meta Graph API](https://img.shields.io/badge/Meta%20Graph%20API-v21.0-1877F2.svg)](https://developers.facebook.com/)
[![Multi-AI Ready](https://img.shields.io/badge/AI-Gemini%20%7C%20OpenAI%20%7C%20Claude%20%7C%20Groq-purple.svg)]()

A mobile-first inventory management, AI copywriting, and multi-channel social publishing system custom-engineered for **Overstock Outlet**, a retail furniture showroom in Baltimore, MD.

- **Store Name:** Overstock Outlet
- **Location:** Baltimore, MD, USA
- **Official Facebook Page:** [https://www.facebook.com/overstockoutletbmore](https://www.facebook.com/overstockoutletbmore)
- **Zero `.env` Required:** Facebook Page, Instagram Business, Store Details, and all 4 AI Providers can be connected, tested, and controlled **100% from the Web UI** (saved persistently in `overstock.db`).
- **Built-In Interactive User Manual:** Every screen in the web application includes a clickable **"📖 User Manual"** button with step-by-step setup guides, direct external links, and 1-tap copy helpers.

---

## 📑 Table of Contents

1. [Key Features & Production Architecture](#1-key-features--production-architecture)
2. [Quick Start & Installation (No `.env` Required)](#2-quick-start--installation-no-env-required)
3. [Built-In Interactive User Manuals (Available on Every Screen)](#3-built-in-interactive-user-manuals-available-on-every-screen)
4. [Connecting Facebook Page & Instagram from the Web UI](#4-connecting-facebook-page--instagram-from-the-web-ui)
5. [Multi-Client AI Description & Vision Generator (UI Controlled)](#5-multi-client-ai-description--vision-generator-ui-controlled)
6. [Facebook Marketplace 1-Tap Assisted Publishing Workflow](#6-facebook-marketplace-1-tap-assisted-publishing-workflow)
7. [Day-to-Day Employee Workflow (60-Second Listing)](#7-day-to-day-employee-workflow-60-second-listing)
8. [Administrator Guide & Production Deployment](#8-administrator-guide--production-deployment)

---

## 1. Key Features & Production Architecture

- **100% Web UI Configuration (No `.env` Editing Needed):**
  - All credentials (`META_APP_ID`, `META_APP_SECRET`, `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`, `IG_USER_ID`, `STORE_*`, and AI API keys/models) are managed directly in `/admin` and persisted in the `system_settings` table inside `overstock.db`.
- **1-Click Facebook & Instagram Auto-Connect Wizard + OAuth Login:**
  - Paste any Meta token in `/admin` and click **"Auto-Discover & Connect Both Now"** — or click **"Connect with Facebook Login (OAuth)"**. The backend automatically exchanges short-lived tokens for a 60-day/never-expiring Page Access Token, discovers your Facebook Page ID, detects your linked Instagram Business Account (`@username`), and saves everything automatically.
- **Real Meta Graph API v21.0 Publishing:**
  - **Facebook Business Page:** Publishes single-photo posts and multi-photo batch galleries (`attached_media`).
  - **Instagram Business Account:** Publishes single-photo posts and multi-photo `CAROUSEL` albums (up to 10 photos) with canonical permalink tracking.
- **Multi-Client AI Copywriting & Multimodal Photo Vision:**
  - Supports **Google Gemini** (Vision + Text), **OpenAI GPT-4o** (Vision + Text), **Anthropic Claude** (Vision + Text), **Groq Llama** (Ultra-Fast Text), and a **Built-In Smart Retail Copy Engine** (100% free/offline, zero API keys needed).
  - Staff can choose their preferred AI engine per item on the Add/Edit Product screen, or let **Auto Mode** pick the best connected provider and gracefully fall back to the Smart Retail Engine.
- **Mobile Camera & Image Processing Pipeline:**
  - Automatic EXIF orientation correction (no sideways phone photos), high-resolution 1600px Lanczos normalization, 400x400 fast mobile thumbnails, and SHA-256 content fingerprinting.
- **Security & Duplicate Protection:**
  - Passwords hashed with **PBKDF2-HMAC-SHA256 (100,000 iterations)** + HTTP-only JWT session cookies + Role-Based Access Control (`admin` vs `employee`).
  - 7-day duplicate listing guard prevents accidental double-posting while allowing an explicit override for multiple identical showroom items.

---

## 2. Quick Start & Installation (No `.env` Required)

### Option A: Windows Store Computer (One-Click Launch)
1. Double-click **`run.bat`** in the project folder.
2. The script automatically creates the Python virtual environment (`venv`), installs dependencies from `requirements.txt`, initializes `overstock.db`, and launches the server at `http://localhost:8000`.

### Option B: Manual Command Line (Windows / macOS / Linux)
```bash
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate        # On macOS/Linux: source venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Launch application (no .env file required!)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Accessing the Application
- **On the Host Computer:** Open `http://localhost:8000`
- **On Store Floor Smartphones (Same Wi-Fi):**
  1. Run `ipconfig` (Windows) or `ifconfig` (Mac/Linux) on the host computer to find its local IPv4 address (e.g., `192.168.1.50`).
  2. Open `http://192.168.1.50:8000` on any phone browser (Safari / Chrome).
  3. Tap **"Add to Home Screen"** for a full-screen mobile app experience.

### Default Login Accounts

| Role | Username | Password | Capabilities |
| :--- | :--- | :--- | :--- |
| **Store Manager (Admin)** | `admin` | `admin123` | Connect Facebook, Instagram & AI in UI, manage staff accounts, view/retry publish logs, manage inventory |
| **Floor Associate (Staff)** | `employee` | `overstock123` | Capture mobile photos, generate AI descriptions, publish to FB/IG/Marketplace, manage inventory |

*(Change default passwords after first login via `/admin` -> Staff Accounts)*

---

## 3. Built-In Interactive User Manuals (Available on Every Screen)

Every page in the application includes a clickable **"📖 User Manual"** button so anyone can connect accounts or train staff without leaving the browser:

- **Top Navigation Bar (`app/templates/base.html`):** Clicking **"📖 User Manual"** opens a 4-tab interactive modal:
  1. **Connect FB & IG:** Step-by-step instructions with direct links to Meta for Developers & Graph API Explorer, 1-click copy badges for all 5 required permissions, and instructions for the 1-Click Auto-Connect Wizard.
  2. **Connect AI Clients:** Step-by-step guides and direct API key links for Google Gemini, OpenAI, Anthropic Claude, and Groq.
  3. **Marketplace Guide:** How to use the 1-Tap Copy Pack to post safely to Facebook Marketplace in 30 seconds.
  4. **Staff Daily Guide:** Complete 60-second floor workflow for store associates.
- **Admin Dashboard (`app/templates/admin/dashboard.html`):** Includes a collapsible **Step-by-Step Meta Setup Manual** right inside the Connect FB & IG tab, plus individual **"📖 How to Connect (Manual)"** dropdowns inside each of the 4 AI provider cards.
- **Add/Edit Product (`app/templates/product_form.html`), Product Detail (`app/templates/product_detail.html`), Inventory Dashboard (`app/templates/dashboard.html`), Marketplace Assistant (`app/templates/marketplace_assistant.html`), and Live Previews (`app/templates/product_preview.html`):** Each screen displays live connection badges (`Connected` vs `Click to Connect in UI`) and quick buttons to open the relevant manual section.

---

## 4. Connecting Facebook Page & Instagram from the Web UI

Log in as `admin`, open **Admin (`/admin`)**, and click the **`Connect FB & IG`** tab. You have two fast ways to connect both accounts from the browser:

### Method A: 1-Click Token Auto-Discover Wizard (Fastest — 60 Seconds)
1. Click the link in the built-in manual to open [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/).
2. Select your Meta App and add these 5 permissions (clickable 1-tap copy badges are provided right in the UI):
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`
### Method A: 1-Click Token Auto-Discover Wizard (Fastest — 60 Seconds)
1. Click the link in the built-in manual to open [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/).
2. Select your Meta App and add these permissions (clickable 1-tap copy badges are provided right in the UI):
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`
   - `business_management`
   - `instagram_basic` *(optional if connecting Facebook only)*
   - `instagram_content_publish` *(optional if connecting Facebook only)*
3. Click **Generate Access Token**, approve your **Overstock Outlet** Facebook Page, and copy the token.
4. Paste the token into the **1-Click Facebook Page & Instagram Auto-Connect Wizard** in `/admin` (optionally enter your Meta App ID & App Secret to automatically upgrade it into a **Never-Expiring Page Token**).
5. Click **"Auto-Discover & Connect FB + IG"**.
   - **Facebook + Instagram Mode:** If an Instagram Business account is linked to your Facebook Page, both `FB_PAGE_ID` and `IG_USER_ID` are connected and saved into `overstock.db`.
   - **Facebook-Only Mode (Automatic Fallback):** If Instagram is **not** connected yet, the system automatically connects **Facebook Only** (`FB_PAGE_ID` and `FB_PAGE_ACCESS_TOKEN`) and leaves the Instagram toggle unchecked by default on `/products/new` so you can publish to Facebook immediately without any Instagram errors!

### Method B: 1-Click Facebook Login Redirect (OAuth)
1. Enter your numeric **Meta App ID** and **Meta App Secret** in `/admin` -> **Connect FB & IG**.
2. Add `http://localhost:8000/api/admin/oauth/facebook/callback` (or your domain callback URL) under **Facebook Login > Settings > Valid OAuth Redirect URIs** in your Meta App.
3. Click **"Connect with Facebook Login (OAuth)"** in the Admin UI to authorize in one click.

---

### How to Connect Instagram with Your Facebook Page (Step-by-Step)

To enable automatic Instagram feed and multi-photo carousel publishing alongside Facebook:

1. **Switch Instagram to a Professional Business Account (on Mobile App):**
   - Open the **Instagram** app on your phone and go to your **Profile**.
   - Tap the **Menu (☰)** in the top right -> **Account type and tools** -> **Switch to professional account**.
   - Choose **Business**, select a category (e.g., *Furniture Store* / *Shopping & Retail*), and complete the setup.
2. **Link Instagram to Your Facebook Business Page:**
   - Open [Facebook](https://www.facebook.com/) on a computer and switch into your **Overstock Outlet** Facebook Page profile.
   - In the left sidebar, click **Settings** (or **Manage** -> **Professional Dashboard**) -> **Linked Accounts** -> **Instagram**.
   - Click **Connect Account**, click **Continue**, and log in with your Instagram Business username and password.
3. **Authorize & Auto-Discover in Overstock Outlet Admin UI:**
   - Open [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/), ensure `instagram_basic` and `instagram_content_publish` permissions are added, and click **Generate Access Token** (selecting both your Facebook Page and linked Instagram account in the popup).
   - Paste the token into `/admin` -> **Connect FB & IG** -> **Auto-Discover & Connect FB + IG**.
   - The system will automatically detect your `IG_USER_ID` (`@username`) and enable the Instagram publish switch across the app!

*(Note for Instagram Publishing: Meta's Instagram servers download product photos from your server's public URL when creating media containers. Ensure your app is accessed via a public HTTPS domain or Cloudflare Tunnel when publishing live to Instagram).*

---

## 5. Multi-Client AI Description & Vision Generator (UI Controlled)

When adding or editing an item on `/products/new`, the **Description & Notes** section lets you select how descriptions are generated:

| Engine Option | Capabilities | Where to Connect API Key |
| :--- | :--- | :--- |
| **⚡ Auto (Best Connected AI)** | Automatically uses the first connected AI provider below, or falls back to the Smart Retail Engine if no keys are configured | `/admin` -> **AI Copywriting** |
| **✨ Google Gemini** (`gemini-2.5-flash`) | **Multimodal Photo Vision + Text:** Inspects the actual uploaded furniture photo (fabric, silhouette, color, seating style) + form specs | [Google AI Studio](https://aistudio.google.com/app/apikey) -> Paste in `/admin` |
| **🧠 OpenAI GPT-4o** (`gpt-4o-mini` / `gpt-4o`) | **Multimodal Photo Vision + Text:** Inspects the uploaded furniture photo + form specs | [OpenAI API Keys](https://platform.openai.com/api-keys) -> Paste in `/admin` |
| **🤖 Anthropic Claude** (`claude-3-5-haiku-latest`) | **Multimodal Photo Vision + Text:** Inspects the uploaded furniture photo + form specs | [Anthropic Console](https://console.anthropic.com/settings/keys) -> Paste in `/admin` |
| **🚀 Groq Llama** (`llama-3.3-70b-versatile`) | **Ultra-Fast Text Generation:** Generates high-converting showroom copy in <1 second | [GroqCloud Console](https://console.groq.com/keys) -> Paste in `/admin` |
| **🏷️ Smart Retail Copy Engine** | **100% Built-In & Offline (Zero Keys Needed):** Generates category-aware hooks, retail vs. outlet dollar/percent savings callouts, condition descriptions, bulleted specs, and store pickup details | Ready out of the box (no key needed) |

You can also customize the store's **Custom AI Instructions / Tone** in `/admin` -> **AI Copywriting** and test all AI providers with the **"Test All AI Providers"** button.

---

## 6. Facebook Marketplace 1-Tap Assisted Publishing Workflow

Meta prohibits third-party bots from auto-posting to personal Facebook Marketplace consumer feeds. To protect your store accounts from bans while keeping listing time under 30 seconds, the system includes the **Marketplace Publishing Assistant** (`/products/{id}/marketplace-assistant`):

1. **1-Tap Copy Pack:** Tap to copy the pre-formatted **Listing Title**, **Price**, **Optimized Description** (with specs, savings, and Baltimore showroom pickup info), and **Search Tags**.
2. **Ordered Photo Pack:** Displays your normalized product photos in exact upload order (`#1`, `#2`, `#3`) with 1-tap download buttons.
3. **Direct Marketplace Launcher:** Tap **"1. Open Facebook Marketplace"** to launch `https://www.facebook.com/marketplace/create/item`, paste the fields, and publish.
4. **Status Sync:** Tap **"Mark as Published on Marketplace"** to log the publication and update the item's status to `Published` on the dashboard.

---

## 7. Day-to-Day Employee Workflow (60-Second Listing)

```text
[1. Tap "+ Add Item"] ➔ [2. Snap 1-4 Photos] ➔ [3. Enter Title & Price] ➔ [4. Tap "Auto-Generate" 🪄] ➔ [5. Tap "Save & Publish"]
```

1. **Capture Photos:** Tap **"Open Camera"** on your phone to snap photos of the furniture piece on the showroom floor.
2. **Enter Core Info:** Fill in **Product Title**, **Outlet Price ($)**, optional **Retail Price ($)** (auto-calculates savings), **Category**, and **Condition**.
3. **Auto-Generate Copy:** Choose an AI Engine (or leave on **⚡ Auto**) and tap **"Auto-Generate"** to write the full retail description.
4. **Publish:** Toggle **Facebook Business Page**, **Instagram Business Account**, and **Facebook Marketplace (Assisted)**, then tap **"Save & Publish"**.

---

## 8. Administrator Guide & Production Deployment

### Admin Control Center (`/admin`)
- **Publish Logs Tab:** View every Facebook Page, Instagram, and Marketplace publish event with timestamps, links to live posts, error messages, and 1-click **Retry** buttons.
- **Connect FB & IG Tab:** Run the 1-Click Auto-Discover Wizard, launch Facebook OAuth, test live Meta Graph API connectivity, and update Store Name, Location, Phone, and Hours.
- **AI Copywriting Tab:** Connect/switch between Gemini, OpenAI, Claude, Groq, and the Smart Retail Copy Engine, and test all connected AI keys in one click.
- **Staff Accounts Tab:** Create or disable employee logins at any time.

### Docker Deployment (Optional)
```bash
docker-compose up -d --build
```
All settings configured in the Web UI are persisted inside `overstock.db`, and uploaded images are stored in `uploads/`.
