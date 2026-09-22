from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from pwdlib import PasswordHash
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.common.exceptions import http_400, http_401, http_403
from src.common.queries import create_instance
from src.common.redis import get_redis_client
from src.auth.models import User, UserRole

# Recommended modern password hasher using pwdlib
password_hash_helper = PasswordHash.recommended()

# In-memory token blacklist fallback when Redis isn't running
_blacklisted_tokens: set[str] = set()


def hash_password(password: str) -> str:
    return password_hash_helper.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return password_hash_helper.verify(plain, hashed)


def create_access_token(public_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": public_id,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(public_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": public_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.PyJWTError:
        raise http_401("Invalid or expired token", code="INVALID_TOKEN")


async def blacklist_token(token: str):
    try:
        payload = decode_token(token)
        exp = payload.get("exp")
        ttl = max(0, int(exp - datetime.now(timezone.utc).timestamp())) if exp else 3600
        redis = await get_redis_client()
        if redis:
            await redis.setex(f"blacklist:{token}", ttl, "1")
        else:
            _blacklisted_tokens.add(token)
    except Exception:
        _blacklisted_tokens.add(token)


async def is_token_blacklisted(token: str) -> bool:
    redis = await get_redis_client()
    if redis:
        try:
            return bool(await redis.exists(f"blacklist:{token}"))
        except Exception:
            pass
    return token in _blacklisted_tokens


async def register_customer(
    session: AsyncSession, name: str, email: str, password: str, phone: Optional[str] = None
) -> User:
    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise http_400("Email already registered", code="EMAIL_ALREADY_EXISTS")

    user = await create_instance(
        session,
        User,
        name=name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=UserRole.CUSTOMER,
    )
    return user


async def create_admin(
    session: AsyncSession, name: str, email: str, password: str, setup_key: str, phone: Optional[str] = None
) -> User:
    if setup_key != settings.ADMIN_SETUP_KEY:
        raise http_403("Invalid setup key", code="INVALID_SETUP_KEY")

    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise http_400("Email already registered", code="EMAIL_ALREADY_EXISTS")

    user = await create_instance(
        session,
        User,
        name=name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        role=UserRole.ADMIN,
    )
    return user


async def authenticate_user(
    session: AsyncSession, email: str, password: str
) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise http_401("Invalid email or password", code="INVALID_CREDENTIALS")
    if not user.is_active:
        raise http_401("Account is deactivated", code="ACCOUNT_DEACTIVATED")
    return user


async def refresh_user_tokens(
    session: AsyncSession, refresh_token: str
) -> tuple[str, str]:
    if await is_token_blacklisted(refresh_token):
        raise http_401("Token has been revoked", code="TOKEN_REVOKED")

    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise http_401("Invalid token type", code="INVALID_TOKEN_TYPE")

    public_id = payload.get("sub")
    result = await session.execute(
        select(User).where(User.public_id == public_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise http_401("User not found or inactive", code="USER_INACTIVE")

    # Blacklist old refresh token to enforce refresh token rotation
    await blacklist_token(refresh_token)

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    new_access = create_access_token(user.public_id, role_str)
    new_refresh = create_refresh_token(user.public_id)
    return new_access, new_refresh
