import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User

ITERATIONS = 100_000

def hash_password(password: str) -> str:
    """Hashes password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        ITERATIONS
    )
    return f"pbkdf2:sha256:{ITERATIONS}${salt}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against stored PBKDF2 hash."""
    try:
        if not hashed_password.startswith("pbkdf2:sha256:"):
            return False
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        iterations = int(parts[0].split(":")[2])
        salt = parts[1]
        expected_hex = parts[2]
        
        computed = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        return secrets.compare_digest(computed.hex(), expected_hex)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def init_default_users(db: Session):
    """Seed initial admin and employee accounts if database is fresh."""
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin_user = User(
            username="admin",
            email="admin@overstockoutletbmore.com",
            full_name="Store Manager",
            hashed_password=hash_password("admin123"),
            role="admin",
            is_active=True
        )
        db.add(admin_user)

    employee = db.query(User).filter(User.username == "employee").first()
    if not employee:
        emp_user = User(
            username="employee",
            email="team@overstockoutletbmore.com",
            full_name="Floor Associate",
            hashed_password=hash_password("overstock123"),
            role="employee",
            is_active=True
        )
        db.add(emp_user)

    db.commit()
