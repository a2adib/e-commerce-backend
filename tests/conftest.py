import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.main import app
from src.database import get_session
from src.auth.models import User, UserRole
from src.auth.services import hash_password, create_access_token
from src.orders.tasks import celery_app

celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
    result_backend="cache+memory://",
    broker_url="memory://",
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

test_async_session_factory = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Setup test tables
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with test_async_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_auth(db_session: AsyncSession) -> tuple[User, dict]:
    admin = User(
        name="Admin Test",
        email="admin_test@example.com",
        password_hash=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    token = create_access_token(admin.public_id, "admin")
    return admin, {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def customer_auth(db_session: AsyncSession) -> tuple[User, dict]:
    customer = User(
        name="Customer Test",
        email="customer_test@example.com",
        password_hash=hash_password("CustomerPass123!"),
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    token = create_access_token(customer.public_id, "customer")
    return customer, {"Authorization": f"Bearer {token}"}
