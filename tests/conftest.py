import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from passlib.context import CryptContext

from database import Base, get_db
from models.user import User
from models.category import Category
from dependencies import encode_session, SESSION_COOKIE_NAME

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

test_async_session = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session() as session:
        yield session


@pytest_asyncio.fixture
async def app():
    from main import app as fastapi_app

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    hashed_password = pwd_context.hash("adminpass123")
    user = User(
        username="testadmin",
        display_name="Test Admin",
        hashed_password=hashed_password,
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def staff_user(db_session: AsyncSession) -> User:
    hashed_password = pwd_context.hash("staffpass123")
    user = User(
        username="teststaff",
        display_name="Test Staff",
        hashed_password=hashed_password,
        role="staff",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_cookies(admin_user: User) -> dict[str, str]:
    token = encode_session(admin_user)
    return {SESSION_COOKIE_NAME: token}


@pytest_asyncio.fixture
async def staff_cookies(staff_user: User) -> dict[str, str]:
    token = encode_session(staff_user)
    return {SESSION_COOKIE_NAME: token}


@pytest_asyncio.fixture
async def authenticated_admin_client(app, admin_cookies) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        cookies=admin_cookies,
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_staff_client(app, staff_cookies) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        cookies=staff_cookies,
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def sample_category(db_session: AsyncSession) -> Category:
    category = Category(
        name="Test Category",
        color="#3b82f6",
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category