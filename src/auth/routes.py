from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession

from src.database import get_session
from src.common.response import StandardResponse
from src.common.rate_limiter import RateLimiter
from src.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    AdminCreateRequest,
    UserResponse,
)
from src.auth.services import (
    register_customer,
    create_admin,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    refresh_user_tokens,
    blacklist_token,
)
from src.auth.dependencies import get_current_user, security
from src.auth.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

# Rate limiters
auth_rate_limiter = RateLimiter(max_requests=10, window_seconds=60, prefix="rl:auth")


@router.post(
    "/register",
    response_model=StandardResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limiter)],
)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[UserResponse]:
    user = await register_customer(
        session, name=data.name, email=data.email, password=data.password, phone=data.phone
    )
    return StandardResponse(
        message="User registered successfully",
        data=UserResponse(
            public_id=user.public_id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.post(
    "/login",
    response_model=StandardResponse[TokenResponse],
    dependencies=[Depends(auth_rate_limiter)],
)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[TokenResponse]:
    user = await authenticate_user(session, data.email, data.password)
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    access = create_access_token(user.public_id, role_str)
    refresh = create_refresh_token(user.public_id)
    return StandardResponse(
        message="Login successful",
        data=TokenResponse(access_token=access, refresh_token=refresh),
    )


@router.post(
    "/refresh",
    response_model=StandardResponse[TokenResponse],
)
async def refresh(
    data: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[TokenResponse]:
    access, refresh_token = await refresh_user_tokens(session, data.refresh_token)
    return StandardResponse(
        message="Token refreshed successfully",
        data=TokenResponse(access_token=access, refresh_token=refresh_token),
    )


@router.post(
    "/logout",
    response_model=StandardResponse[None],
)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> StandardResponse[None]:
    await blacklist_token(credentials.credentials)
    return StandardResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=StandardResponse[UserResponse],
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> StandardResponse[UserResponse]:
    return StandardResponse(
        data=UserResponse(
            public_id=current_user.public_id,
            name=current_user.name,
            email=current_user.email,
            phone=current_user.phone,
            role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            avatar_url=current_user.avatar_url,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
        ),
    )


@router.post(
    "/admin/create",
    response_model=StandardResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_account(
    data: AdminCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> StandardResponse[UserResponse]:
    user = await create_admin(
        session, name=data.name, email=data.email, password=data.password, setup_key=data.setup_key, phone=data.phone
    )
    return StandardResponse(
        message="Admin account created successfully",
        data=UserResponse(
            public_id=user.public_id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )
