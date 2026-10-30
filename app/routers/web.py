from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.database import get_db
from app.models.user import User
from app.models.product import Product
from app.models.publish_log import PublishLog
from app.config import settings
from app.dependencies import get_current_user_from_token
from app.services.marketplace_service import marketplace_service

router = APIRouter(include_in_schema=False)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@router.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse(url="/dashboard", status_code=302)

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: Optional[User] = Depends(get_current_user_from_token)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"user": None}
    )

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    condition: Optional[str] = Query(None),
    availability: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_from_token)
):
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    query = db.query(Product)
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Product.title.ilike(term),
                Product.product_code.ilike(term),
                Product.brand.ilike(term),
                Product.description.ilike(term)
            )
        )
    if category and category.strip():
        query = query.filter(Product.category == category.strip())
    if condition and condition.strip():
        query = query.filter(Product.condition == condition.strip())
    if availability and availability.strip():
        query = query.filter(Product.availability == availability.strip())
    if status and status.strip():
        query = query.filter(Product.status == status.strip())

    products = query.order_by(desc(Product.date_added)).all()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "products": products,
            "query_q": q,
            "current_category": category,
            "current_availability": availability,
            "current_status": status,
            "active_page": "dashboard"
        }
    )

@router.get("/products/new", response_class=HTMLResponse)
def new_product_page(
    request: Request,
    user: Optional[User] = Depends(get_current_user_from_token)
):
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="product_form.html",
        context={
            "user": user,
            "product": None,
            "active_page": "new_product"
        }
    )

@router.get("/products/{product_id}", response_class=HTMLResponse)
def product_detail_page(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_from_token)
):
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return templates.TemplateResponse(
        request=request,
        name="product_detail.html",
        context={
            "user": user,
            "product": product,
            "settings": settings,
            "active_page": "inventory"
        }
    )

@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
def edit_product_page(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_from_token)
):
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return templates.TemplateResponse(
        request=request,
        name="product_form.html",
        context={
            "user": user,
            "product": product,
            "active_page": "edit_product"
        }
    )

@router.get("/products/{product_id}/preview", response_class=HTMLResponse)
def product_preview_page(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_from_token)
):
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return templates.TemplateResponse(
        request=request,
        name="product_preview.html",
        context={
            "user": user,
            "product": product,
            "active_page": "preview"
        }
    )

@router.get("/products/{product_id}/marketplace-assistant", response_class=HTMLResponse)
def marketplace_assistant_page(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_from_token)
):
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    base_url = str(request.base_url).rstrip("/")
    guide = marketplace_service.get_assisted_guide(product, base_app_url=base_url)

    return templates.TemplateResponse(
        request=request,
        name="marketplace_assistant.html",
        context={
            "user": user,
            "product": product,
            "guide": guide,
            "active_page": "marketplace"
        }
    )

@router.get("/admin", response_class=HTMLResponse)
def admin_page(
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_from_token)
):
    if not user or user.role != "admin":
        return RedirectResponse(url="/dashboard", status_code=302)

    total_products = db.query(Product).count()
    published_count = db.query(Product).filter(Product.status == "Published").count()
    draft_count = db.query(Product).filter(Product.status == "Draft").count()
    failed_publishes = db.query(PublishLog).filter(PublishLog.status == "failed").count()

    stats = {
        "products": {
            "total": total_products,
            "published": published_count,
            "draft": draft_count
        },
        "publishing": {
            "failed": failed_publishes
        }
    }

    users = db.query(User).order_by(User.id).all()
    logs = db.query(PublishLog).order_by(desc(PublishLog.created_at)).limit(50).all()

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "user": user,
            "stats": stats,
            "users": users,
            "logs": logs,
            "settings": settings,
            "active_page": "admin"
        }
    )
