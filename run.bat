@echo off
title Overstock Outlet - Inventory & Publishing System
echo ==============================================================
echo    OVERSTOCK OUTLET - BALTIMORE, MD
echo    Mobile-Friendly Furniture Inventory & Publishing System
echo ==============================================================
echo.

IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [2/3] Installing dependencies...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate.bat
)

echo.
echo [3/3] Starting Overstock Outlet Server...
echo.
echo ==============================================================
echo    Local Access:   http://localhost:8000
echo    Mobile Access:  Connect phone to same WiFi and open:
echo                    http://[YOUR-PC-IP-ADDRESS]:8000
echo.
echo    Default Accounts:
echo    - Associate: username: employee  password: overstock123
echo    - Manager:   username: admin     password: admin123
echo ==============================================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause

