from typing import Optional
import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.config import settings
from src.database import get_session
from src.common.exceptions import http_401, http_403
from src.auth.models import User, UserRole
from src.auth.services import is_token_blacklisted

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    token = credentials.credentials

    if await is_token_blacklisted(token):
        raise http_401("Token has been revoked", code="TOKEN_REVOKED")

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "access":
            raise http_401("Invalid token type", code="INVALID_TOKEN_TYPE")
        public_id: str = payload.get("sub")
        if not public_id:
            raise http_401("Invalid token", code="INVALID_TOKEN")
    except jwt.PyJWTError:
        raise http_401("Invalid or expired token", code="INVALID_TOKEN")

    stmt = select(User).where(User.public_id == public_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise http_401("User not found or inactive", code="USER_INACTIVE")
    return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    if credentials is None:
        return None
    token = credentials.credentials
    if await is_token_blacklisted(token):
        return None

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "access":
            return None
        public_id: str = payload.get("sub")
        if not public_id:
            return None
    except jwt.PyJWTError:
        return None

    stmt = select(User).where(User.public_id == public_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN and current_user.role != "admin":
        raise http_403("Admin privileges required", code="ADMIN_REQUIRED")
    return current_user


async def require_customer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.CUSTOMER and current_user.role != "customer":
        raise http_403("Customer access required", code="CUSTOMER_REQUIRED")
    return current_user
