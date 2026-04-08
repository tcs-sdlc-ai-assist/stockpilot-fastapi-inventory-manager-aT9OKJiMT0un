import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from models.category import Category
from models.item import InventoryItem


@pytest.mark.asyncio
async def test_list_categories_as_admin(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.get("/categories/", follow_redirects=False)
    assert response.status_code == 200
    assert "Categories" in response.text


@pytest.mark.asyncio
async def test_list_categories_as_staff_redirects(authenticated_staff_client: AsyncClient):
    response = await authenticated_staff_client.get("/categories/", follow_redirects=False)
    assert response.status_code == 303
    assert "/inventory/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_list_categories_unauthenticated_redirects(client: AsyncClient):
    response = await client.get("/categories/", follow_redirects=False)
    assert response.status_code == 303
    assert "/login/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_create_category_as_admin(authenticated_admin_client: AsyncClient, db_session):
    response = await authenticated_admin_client.post(
        "/categories/",
        data={"name": "New Test Category", "color": "#ff5733"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/categories/" in response.headers.get("location", "")

    result = await db_session.execute(
        select(Category).where(Category.name == "New Test Category")
    )
    category = result.scalar_one_or_none()
    assert category is not None
    assert category.color == "#ff5733"


@pytest.mark.asyncio
async def test_create_category_missing_name(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/categories/",
        data={"name": "", "color": "#ff5733"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Category name is required" in response.text


@pytest.mark.asyncio
async def test_create_category_name_too_short(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/categories/",
        data={"name": "A", "color": "#ff5733"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "at least 2 characters" in response.text


@pytest.mark.asyncio
async def test_create_category_name_too_long(authenticated_admin_client: AsyncClient):
    long_name = "A" * 51
    response = await authenticated_admin_client.post(
        "/categories/",
        data={"name": long_name, "color": "#ff5733"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "at most 50 characters" in response.text


@pytest.mark.asyncio
async def test_create_category_invalid_color(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/categories/",
        data={"name": "Valid Name", "color": "notacolor"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "valid hex color" in response.text


@pytest.mark.asyncio
async def test_create_duplicate_category(authenticated_admin_client: AsyncClient, sample_category):
    response = await authenticated_admin_client.post(
        "/categories/",
        data={"name": sample_category.name, "color": "#123456"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "already exists" in response.text


@pytest.mark.asyncio
async def test_create_category_as_staff_denied(authenticated_staff_client: AsyncClient):
    response = await authenticated_staff_client.post(
        "/categories/",
        data={"name": "Staff Category", "color": "#aabbcc"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/inventory/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_delete_empty_category_as_admin(authenticated_admin_client: AsyncClient, db_session):
    category = Category(name="Deletable Category", color="#abcdef")
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)

    response = await authenticated_admin_client.post(
        f"/categories/{category.id}/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/categories/" in response.headers.get("location", "")

    result = await db_session.execute(
        select(Category).where(Category.id == category.id)
    )
    deleted = result.scalar_one_or_none()
    assert deleted is None


@pytest.mark.asyncio
async def test_delete_category_with_items_blocked(
    authenticated_admin_client: AsyncClient,
    db_session,
    sample_category,
    admin_user,
):
    item = InventoryItem(
        name="Test Item In Category",
        quantity=10,
        unit_price=5.0,
        reorder_level=2,
        category_id=sample_category.id,
        created_by_id=admin_user.id,
    )
    db_session.add(item)
    await db_session.commit()

    response = await authenticated_admin_client.post(
        f"/categories/{sample_category.id}/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303

    result = await db_session.execute(
        select(Category).where(Category.id == sample_category.id)
    )
    still_exists = result.scalar_one_or_none()
    assert still_exists is not None


@pytest.mark.asyncio
async def test_delete_nonexistent_category(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/categories/99999/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/categories/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_delete_category_as_staff_denied(
    authenticated_staff_client: AsyncClient,
    sample_category,
):
    response = await authenticated_staff_client.post(
        f"/categories/{sample_category.id}/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/inventory/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_categories_page_shows_category(
    authenticated_admin_client: AsyncClient,
    sample_category,
):
    response = await authenticated_admin_client.get("/categories/", follow_redirects=False)
    assert response.status_code == 200
    assert sample_category.name in response.text


@pytest.mark.asyncio
async def test_create_category_with_three_char_hex_color(
    authenticated_admin_client: AsyncClient,
    db_session,
):
    response = await authenticated_admin_client.post(
        "/categories/",
        data={"name": "Short Color Cat", "color": "#abc"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    result = await db_session.execute(
        select(Category).where(Category.name == "Short Color Cat")
    )
    category = result.scalar_one_or_none()
    assert category is not None
    assert category.color == "#abc"


@pytest.mark.asyncio
async def test_create_category_default_color(
    authenticated_admin_client: AsyncClient,
    db_session,
):
    response = await authenticated_admin_client.post(
        "/categories/",
        data={"name": "Default Color Cat"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    result = await db_session.execute(
        select(Category).where(Category.name == "Default Color Cat")
    )
    category = result.scalar_one_or_none()
    assert category is not None
    assert category.color == "#0d9488"