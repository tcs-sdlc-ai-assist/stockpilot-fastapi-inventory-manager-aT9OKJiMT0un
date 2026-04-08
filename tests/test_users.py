import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from models.user import User
from tests.conftest import test_async_session


@pytest.mark.asyncio
async def test_list_users_as_admin(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.get("/users/", follow_redirects=False)
    assert response.status_code == 200
    assert b"User Management" in response.content


@pytest.mark.asyncio
async def test_list_users_as_staff_redirects(authenticated_staff_client: AsyncClient):
    response = await authenticated_staff_client.get("/users/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/inventory/"


@pytest.mark.asyncio
async def test_list_users_unauthenticated_redirects(client: AsyncClient):
    response = await client.get("/users/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/login/"


@pytest.mark.asyncio
async def test_create_user_as_admin(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/users/",
        data={
            "username": "newuser",
            "display_name": "New User",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/users/"

    async with test_async_session() as session:
        result = await session.execute(
            select(User).where(User.username == "newuser")
        )
        created_user = result.scalar_one_or_none()
        assert created_user is not None
        assert created_user.display_name == "New User"
        assert created_user.role == "staff"


@pytest.mark.asyncio
async def test_create_admin_user(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/users/",
        data={
            "username": "newadmin",
            "display_name": "New Admin",
            "password": "password123",
            "role": "admin",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    async with test_async_session() as session:
        result = await session.execute(
            select(User).where(User.username == "newadmin")
        )
        created_user = result.scalar_one_or_none()
        assert created_user is not None
        assert created_user.role == "admin"


@pytest.mark.asyncio
async def test_create_user_duplicate_username(
    authenticated_admin_client: AsyncClient,
    admin_user: User,
):
    response = await authenticated_admin_client.post(
        "/users/",
        data={
            "username": admin_user.username,
            "display_name": "Duplicate User",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"A user with this username already exists" in response.content


@pytest.mark.asyncio
async def test_create_user_short_username(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/users/",
        data={
            "username": "ab",
            "display_name": "Short Username",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Username must be at least 3 characters" in response.content


@pytest.mark.asyncio
async def test_create_user_short_password(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/users/",
        data={
            "username": "validuser",
            "display_name": "Valid User",
            "password": "short",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Password must be at least 8 characters" in response.content


@pytest.mark.asyncio
async def test_create_user_invalid_role(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/users/",
        data={
            "username": "roleuser",
            "display_name": "Role User",
            "password": "password123",
            "role": "superadmin",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Role must be either" in response.content


@pytest.mark.asyncio
async def test_create_user_invalid_username_chars(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/users/",
        data={
            "username": "bad user!",
            "display_name": "Bad Username",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"can only contain letters, numbers, and underscores" in response.content


@pytest.mark.asyncio
async def test_create_user_as_staff_denied(authenticated_staff_client: AsyncClient):
    response = await authenticated_staff_client.post(
        "/users/",
        data={
            "username": "staffcreated",
            "display_name": "Staff Created",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/inventory/"


@pytest.mark.asyncio
async def test_delete_user_as_admin(
    authenticated_admin_client: AsyncClient,
    db_session,
):
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with test_async_session() as session:
        target_user = User(
            username="deleteme",
            display_name="Delete Me",
            hashed_password=pwd_context.hash("password123"),
            role="staff",
        )
        session.add(target_user)
        await session.commit()
        await session.refresh(target_user)
        target_id = target_user.id

    response = await authenticated_admin_client.post(
        f"/users/{target_id}/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/users/"

    async with test_async_session() as session:
        result = await session.execute(
            select(User).where(User.id == target_id)
        )
        deleted_user = result.scalar_one_or_none()
        assert deleted_user is None


@pytest.mark.asyncio
async def test_delete_self_blocked(
    authenticated_admin_client: AsyncClient,
    admin_user: User,
):
    response = await authenticated_admin_client.post(
        f"/users/{admin_user.id}/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/users/"

    async with test_async_session() as session:
        result = await session.execute(
            select(User).where(User.id == admin_user.id)
        )
        user = result.scalar_one_or_none()
        assert user is not None


@pytest.mark.asyncio
async def test_delete_default_admin_blocked(
    authenticated_admin_client: AsyncClient,
    db_session,
):
    from passlib.context import CryptContext
    from config import settings

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with test_async_session() as session:
        result = await session.execute(
            select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME)
        )
        default_admin = result.scalar_one_or_none()

        if default_admin is None:
            default_admin = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                display_name="Administrator",
                hashed_password=pwd_context.hash(settings.DEFAULT_ADMIN_PASSWORD),
                role="admin",
            )
            session.add(default_admin)
            await session.commit()
            await session.refresh(default_admin)

        default_admin_id = default_admin.id

    response = await authenticated_admin_client.post(
        f"/users/{default_admin_id}/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/users/"

    async with test_async_session() as session:
        result = await session.execute(
            select(User).where(User.id == default_admin_id)
        )
        user = result.scalar_one_or_none()
        assert user is not None


@pytest.mark.asyncio
async def test_delete_nonexistent_user(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/users/99999/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/users/"


@pytest.mark.asyncio
async def test_delete_user_as_staff_denied(
    authenticated_staff_client: AsyncClient,
    admin_user: User,
):
    response = await authenticated_staff_client.post(
        f"/users/{admin_user.id}/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/inventory/"


@pytest.mark.asyncio
async def test_create_user_short_display_name(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/users/",
        data={
            "username": "validuser2",
            "display_name": "ab",
            "password": "password123",
            "role": "staff",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Display name must be at least 3 characters" in response.content


@pytest.mark.asyncio
async def test_users_page_shows_user_list(
    authenticated_admin_client: AsyncClient,
    admin_user: User,
    staff_user: User,
):
    response = await authenticated_admin_client.get("/users/", follow_redirects=False)
    assert response.status_code == 200
    assert admin_user.username.encode() in response.content
    assert staff_user.username.encode() in response.content