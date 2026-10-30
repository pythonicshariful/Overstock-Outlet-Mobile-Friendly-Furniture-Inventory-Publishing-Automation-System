from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_token, get_user_by_username

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_current_user_from_token(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    # Check header token or cookie token for seamless web + API support
    jwt_token = token
    if not jwt_token:
        jwt_token = request.cookies.get("access_token")
        if jwt_token and jwt_token.startswith("Bearer "):
            jwt_token = jwt_token[7:]

    if not jwt_token:
        return None

    payload = decode_token(jwt_token)
    if not payload:
        return None

    username: str = payload.get("sub")
    if not username:
        return None

    user = get_user_by_username(db, username=username)
    if not user or not user.is_active:
        return None
    return user

def require_current_user(
    current_user: Optional[User] = Depends(get_current_user_from_token)
) -> User:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

def require_admin_user(
    current_user: User = Depends(require_current_user)
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

