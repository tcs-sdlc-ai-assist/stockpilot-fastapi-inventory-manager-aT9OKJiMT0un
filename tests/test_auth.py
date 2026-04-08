import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from models.user import User
from dependencies import SESSION_COOKIE_NAME


@pytest.mark.asyncio
async def test_login_page_renders(client: AsyncClient):
    response = await client.get("/login/")
    assert response.status_code == 200
    assert "Sign in to StockPilot" in response.text


@pytest.mark.asyncio
async def test_login_page_redirects_authenticated_admin(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.get("/login/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard/"


@pytest.mark.asyncio
async def test_login_page_redirects_authenticated_staff(authenticated_staff_client: AsyncClient):
    response = await authenticated_staff_client.get("/login/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/inventory/"


@pytest.mark.asyncio
async def test_login_valid_admin_credentials(client: AsyncClient, admin_user: User):
    response = await client.post(
        "/login/",
        data={"username": "testadmin", "password": "adminpass123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard/"
    assert SESSION_COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_login_valid_staff_credentials(client: AsyncClient, staff_user: User):
    response = await client.post(
        "/login/",
        data={"username": "teststaff", "password": "staffpass123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/inventory/"
    assert SESSION_COOKIE_NAME in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, admin_user: User):
    response = await client.post(
        "/login/",
        data={"username": "testadmin", "password": "wrongpassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Invalid username or password" in response.text
    assert SESSION_COOKIE_NAME not in response.cookies


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    response = await client.post(
        "/login/",
        data={"username": "nonexistent", "password": "somepassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Invalid username or password" in response.text
    assert SESSION_COOKIE_NAME not in response.cookies


@pytest.mark.asyncio
async def test_login_empty_username(client: AsyncClient):
    response = await client.post(
        "/login/",
        data={"username": "", "password": "somepassword"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Username is required" in response.text


@pytest.mark.asyncio
async def test_login_empty_password(client: AsyncClient):
    response = await client.post(
        "/login/",
        data={"username": "testadmin", "password": ""},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Password is required" in response.text


@pytest.mark.asyncio
async def test_login_empty_both_fields(client: AsyncClient):
    response = await client.post(
        "/login/",
        data={"username": "", "password": ""},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Username is required" in response.text
    assert "Password is required" in response.text


@pytest.mark.asyncio
async def test_register_page_renders(client: AsyncClient):
    response = await client.get("/register/")
    assert response.status_code == 200
    assert "Create your account" in response.text


@pytest.mark.asyncio
async def test_register_page_redirects_authenticated_user(authenticated_staff_client: AsyncClient):
    response = await authenticated_staff_client.get("/register/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/inventory/"


@pytest.mark.asyncio
async def test_register_valid_data(client: AsyncClient, db_session):
    response = await client.post(
        "/register/",
        data={
            "username": "newuser",
            "display_name": "New User",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/inventory/"
    assert SESSION_COOKIE_NAME in response.cookies

    result = await db_session.execute(select(User).where(User.username == "newuser"))
    created_user = result.scalar_one_or_none()
    assert created_user is not None
    assert created_user.display_name == "New User"
    assert created_user.role == "staff"


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, staff_user: User):
    response = await client.post(
        "/register/",
        data={
            "username": "teststaff",
            "display_name": "Another Staff",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "already taken" in response.text


@pytest.mark.asyncio
async def test_register_password_mismatch(client: AsyncClient):
    response = await client.post(
        "/register/",
        data={
            "username": "mismatchuser",
            "display_name": "Mismatch User",
            "password": "securepass123",
            "confirm_password": "differentpass456",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Passwords do not match" in response.text


@pytest.mark.asyncio
async def test_register_short_username(client: AsyncClient):
    response = await client.post(
        "/register/",
        data={
            "username": "ab",
            "display_name": "Short User",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "at least 3 characters" in response.text


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    response = await client.post(
        "/register/",
        data={
            "username": "shortpwduser",
            "display_name": "Short Pwd User",
            "password": "short",
            "confirm_password": "short",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "at least 8 characters" in response.text


@pytest.mark.asyncio
async def test_register_empty_username(client: AsyncClient):
    response = await client.post(
        "/register/",
        data={
            "username": "",
            "display_name": "No Username",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Username is required" in response.text


@pytest.mark.asyncio
async def test_register_empty_display_name(client: AsyncClient):
    response = await client.post(
        "/register/",
        data={
            "username": "nodisplay",
            "display_name": "",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Display name is required" in response.text


@pytest.mark.asyncio
async def test_register_empty_password(client: AsyncClient):
    response = await client.post(
        "/register/",
        data={
            "username": "nopwduser",
            "display_name": "No Password",
            "password": "",
            "confirm_password": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Password is required" in response.text


@pytest.mark.asyncio
async def test_register_empty_confirm_password(client: AsyncClient):
    response = await client.post(
        "/register/",
        data={
            "username": "noconfirm",
            "display_name": "No Confirm",
            "password": "securepass123",
            "confirm_password": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "confirm your password" in response.text


@pytest.mark.asyncio
async def test_register_invalid_username_characters(client: AsyncClient):
    response = await client.post(
        "/register/",
        data={
            "username": "bad user!",
            "display_name": "Bad Username",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "letters, numbers, and underscores" in response.text


@pytest.mark.asyncio
async def test_logout_clears_session_cookie(authenticated_staff_client: AsyncClient):
    response = await authenticated_staff_client.post("/logout/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login/"
    cookie_header = response.headers.get("set-cookie", "")
    assert SESSION_COOKIE_NAME in cookie_header


@pytest.mark.asyncio
async def test_logout_unauthenticated_user(client: AsyncClient):
    response = await client.post("/logout/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login/"


@pytest.mark.asyncio
async def test_login_session_cookie_is_httponly(client: AsyncClient, admin_user: User):
    response = await client.post(
        "/login/",
        data={"username": "testadmin", "password": "adminpass123"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    cookie_header = response.headers.get("set-cookie", "")
    assert "httponly" in cookie_header.lower()


@pytest.mark.asyncio
async def test_register_creates_staff_role_by_default(client: AsyncClient, db_session):
    response = await client.post(
        "/register/",
        data={
            "username": "defaultrole",
            "display_name": "Default Role User",
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    result = await db_session.execute(select(User).where(User.username == "defaultrole"))
    created_user = result.scalar_one_or_none()
    assert created_user is not None
    assert created_user.role == "staff"


@pytest.mark.asyncio
async def test_register_preserves_form_data_on_error(client: AsyncClient):
    response = await client.post(
        "/register/",
        data={
            "username": "preserveuser",
            "display_name": "Preserve User",
            "password": "short",
            "confirm_password": "short",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "preserveuser" in response.text
    assert "Preserve User" in response.text


@pytest.mark.asyncio
async def test_login_preserves_username_on_error(client: AsyncClient):
    response = await client.post(
        "/login/",
        data={"username": "remembereduser", "password": "wrongpass"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "remembereduser" in response.text