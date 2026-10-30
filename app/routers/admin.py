from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.publish_log import SystemSetting, PublishLog
from app.models.product import Product
from app.schemas.user import UserOut
from app.services.auth_service import hash_password
from app.services.facebook_service import facebook_service
from app.services.instagram_service import instagram_service
from app.dependencies import require_admin_user

router = APIRouter(prefix="/api/admin", tags=["Admin"])

class CreateUserRequest(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str
    role: str = "employee"

class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class SocialSettingsUpdate(BaseModel):
    fb_page_id: Optional[str] = None
    fb_page_token: Optional[str] = None
    ig_user_id: Optional[str] = None
    mock_publishing: Optional[bool] = None

@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin_user)):
    return db.query(User).order_by(User.id).all()

@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_new_user(user_req: CreateUserRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin_user)):
    if db.query(User).filter(User.username == user_req.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == user_req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user_req.username,
        email=user_req.email,
        full_name=user_req.full_name,
        hashed_password=hash_password(user_req.password),
        role=user_req.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/users/{user_id}", response_model=UserOut)
def update_user_details(
    user_id: int,
    user_req: UpdateUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin_user)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_req.full_name is not None:
        target_user.full_name = user_req.full_name
    if user_req.email is not None:
        target_user.email = user_req.email
    if user_req.role is not None:
        target_user.role = user_req.role
    if user_req.is_active is not None:
        target_user.is_active = user_req.is_active
    if user_req.password:
        target_user.hashed_password = hash_password(user_req.password)

    db.commit()
    db.refresh(target_user)
    return target_user

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db), admin: User = Depends(require_admin_user)):
    total_products = db.query(Product).count()
    published_count = db.query(Product).filter(Product.status == "Published").count()
    draft_count = db.query(Product).filter(Product.status == "Draft").count()
    total_users = db.query(User).count()
    
    total_publishes = db.query(PublishLog).count()
    successful_publishes = db.query(PublishLog).filter(PublishLog.status == "success").count()
    failed_publishes = db.query(PublishLog).filter(PublishLog.status == "failed").count()
    assisted_publishes = db.query(PublishLog).filter(PublishLog.status == "assisted").count()

    return {
        "products": {
            "total": total_products,
            "published": published_count,
            "draft": draft_count
        },
        "publishing": {
            "total": total_publishes,
            "success": successful_publishes,
            "failed": failed_publishes,
            "assisted": assisted_publishes
        },
        "users": total_users
    }

@router.get("/connections/test")
async def test_social_connections(admin: User = Depends(require_admin_user)):
    fb_status = await facebook_service.verify_connection()
    ig_status = await instagram_service.verify_connection()
    return {
        "facebook_page": fb_status,
        "instagram": ig_status
    }
