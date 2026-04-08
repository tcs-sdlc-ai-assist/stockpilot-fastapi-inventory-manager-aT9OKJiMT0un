import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from models.item import InventoryItem
from models.category import Category
from models.user import User


@pytest.mark.asyncio
async def test_inventory_list_redirects_unauthenticated(client: AsyncClient):
    response = await client.get("/inventory/", follow_redirects=False)
    assert response.status_code == 303
    assert "/login/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_inventory_add_page_redirects_unauthenticated(client: AsyncClient):
    response = await client.get("/inventory/add/", follow_redirects=False)
    assert response.status_code == 303
    assert "/login/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_inventory_list_empty(authenticated_staff_client: AsyncClient):
    response = await authenticated_staff_client.get("/inventory/")
    assert response.status_code == 200
    assert "No inventory items found" in response.text


@pytest.mark.asyncio
async def test_inventory_add_page_loads(authenticated_staff_client: AsyncClient):
    response = await authenticated_staff_client.get("/inventory/add/")
    assert response.status_code == 200
    assert "Add New Inventory Item" in response.text


@pytest.mark.asyncio
async def test_create_item_success(
    authenticated_staff_client: AsyncClient,
    db_session,
    sample_category: Category,
):
    form_data = {
        "name": "Test Widget",
        "sku": "TW-001",
        "description": "A test widget",
        "quantity": "50",
        "unit_price": "9.99",
        "reorder_level": "10",
        "category_id": str(sample_category.id),
    }
    response = await authenticated_staff_client.post(
        "/inventory/add/",
        data=form_data,
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/inventory/"

    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.sku == "TW-001")
    )
    item = result.scalar_one_or_none()
    assert item is not None
    assert item.name == "Test Widget"
    assert item.quantity == 50
    assert item.unit_price == 9.99
    assert item.reorder_level == 10
    assert item.category_id == sample_category.id


@pytest.mark.asyncio
async def test_create_item_missing_name(authenticated_staff_client: AsyncClient):
    form_data = {
        "name": "",
        "sku": "TW-002",
        "description": "",
        "quantity": "10",
        "unit_price": "5.00",
        "reorder_level": "5",
        "category_id": "",
    }
    response = await authenticated_staff_client.post(
        "/inventory/add/",
        data=form_data,
    )
    assert response.status_code == 200
    assert "Name is required" in response.text


@pytest.mark.asyncio
async def test_create_item_invalid_quantity(authenticated_staff_client: AsyncClient):
    form_data = {
        "name": "Bad Quantity Item",
        "sku": "",
        "description": "",
        "quantity": "-5",
        "unit_price": "5.00",
        "reorder_level": "5",
        "category_id": "",
    }
    response = await authenticated_staff_client.post(
        "/inventory/add/",
        data=form_data,
    )
    assert response.status_code == 200
    assert "Quantity must be 0 or greater" in response.text


@pytest.mark.asyncio
async def test_create_item_invalid_unit_price(authenticated_staff_client: AsyncClient):
    form_data = {
        "name": "Bad Price Item",
        "sku": "",
        "description": "",
        "quantity": "10",
        "unit_price": "abc",
        "reorder_level": "5",
        "category_id": "",
    }
    response = await authenticated_staff_client.post(
        "/inventory/add/",
        data=form_data,
    )
    assert response.status_code == 200
    assert "Unit price must be a valid number" in response.text


@pytest.mark.asyncio
async def test_create_item_duplicate_sku(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Existing Item",
        sku="DUP-SKU",
        quantity=10,
        unit_price=5.0,
        reorder_level=5,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()

    form_data = {
        "name": "New Item Same SKU",
        "sku": "DUP-SKU",
        "description": "",
        "quantity": "10",
        "unit_price": "5.00",
        "reorder_level": "5",
        "category_id": "",
    }
    response = await authenticated_staff_client.post(
        "/inventory/add/",
        data=form_data,
    )
    assert response.status_code == 200
    assert "An item with this SKU already exists" in response.text


@pytest.mark.asyncio
async def test_create_item_no_category(
    authenticated_staff_client: AsyncClient,
    db_session,
):
    form_data = {
        "name": "No Category Item",
        "sku": "NC-001",
        "description": "",
        "quantity": "5",
        "unit_price": "1.00",
        "reorder_level": "2",
        "category_id": "",
    }
    response = await authenticated_staff_client.post(
        "/inventory/add/",
        data=form_data,
        follow_redirects=False,
    )
    assert response.status_code == 303

    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.sku == "NC-001")
    )
    item = result.scalar_one_or_none()
    assert item is not None
    assert item.category_id is None


@pytest.mark.asyncio
async def test_inventory_list_shows_items(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Visible Widget",
        sku="VW-001",
        quantity=20,
        unit_price=15.0,
        reorder_level=5,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()

    response = await authenticated_staff_client.get("/inventory/")
    assert response.status_code == 200
    assert "Visible Widget" in response.text
    assert "VW-001" in response.text


@pytest.mark.asyncio
async def test_inventory_list_search(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item1 = InventoryItem(
        name="Alpha Widget",
        sku="AW-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=2,
        created_by_id=staff_user.id,
    )
    item2 = InventoryItem(
        name="Beta Gadget",
        sku="BG-001",
        quantity=20,
        unit_price=10.0,
        reorder_level=5,
        created_by_id=staff_user.id,
    )
    db_session.add_all([item1, item2])
    await db_session.commit()

    response = await authenticated_staff_client.get("/inventory/?search=Alpha")
    assert response.status_code == 200
    assert "Alpha Widget" in response.text
    assert "Beta Gadget" not in response.text


@pytest.mark.asyncio
async def test_inventory_list_search_by_sku(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item1 = InventoryItem(
        name="Item One",
        sku="FINDME-123",
        quantity=10,
        unit_price=5.0,
        reorder_level=2,
        created_by_id=staff_user.id,
    )
    item2 = InventoryItem(
        name="Item Two",
        sku="OTHER-456",
        quantity=20,
        unit_price=10.0,
        reorder_level=5,
        created_by_id=staff_user.id,
    )
    db_session.add_all([item1, item2])
    await db_session.commit()

    response = await authenticated_staff_client.get("/inventory/?search=FINDME")
    assert response.status_code == 200
    assert "Item One" in response.text
    assert "Item Two" not in response.text


@pytest.mark.asyncio
async def test_inventory_list_filter_by_category(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
    sample_category: Category,
):
    cat2 = Category(name="Other Category", color="#ff0000")
    db_session.add(cat2)
    await db_session.commit()
    await db_session.refresh(cat2)

    item1 = InventoryItem(
        name="Cat1 Item",
        sku="C1-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=2,
        category_id=sample_category.id,
        created_by_id=staff_user.id,
    )
    item2 = InventoryItem(
        name="Cat2 Item",
        sku="C2-001",
        quantity=20,
        unit_price=10.0,
        reorder_level=5,
        category_id=cat2.id,
        created_by_id=staff_user.id,
    )
    db_session.add_all([item1, item2])
    await db_session.commit()

    response = await authenticated_staff_client.get(
        f"/inventory/?category={sample_category.id}"
    )
    assert response.status_code == 200
    assert "Cat1 Item" in response.text
    assert "Cat2 Item" not in response.text


@pytest.mark.asyncio
async def test_inventory_list_sort_by_name_asc(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item_a = InventoryItem(
        name="AAA Item",
        quantity=10,
        unit_price=5.0,
        reorder_level=2,
        created_by_id=staff_user.id,
    )
    item_z = InventoryItem(
        name="ZZZ Item",
        quantity=20,
        unit_price=10.0,
        reorder_level=5,
        created_by_id=staff_user.id,
    )
    db_session.add_all([item_z, item_a])
    await db_session.commit()

    response = await authenticated_staff_client.get("/inventory/?sort=name")
    assert response.status_code == 200
    text = response.text
    pos_a = text.find("AAA Item")
    pos_z = text.find("ZZZ Item")
    assert pos_a < pos_z


@pytest.mark.asyncio
async def test_inventory_list_sort_by_name_desc(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item_a = InventoryItem(
        name="AAA Sort Item",
        quantity=10,
        unit_price=5.0,
        reorder_level=2,
        created_by_id=staff_user.id,
    )
    item_z = InventoryItem(
        name="ZZZ Sort Item",
        quantity=20,
        unit_price=10.0,
        reorder_level=5,
        created_by_id=staff_user.id,
    )
    db_session.add_all([item_a, item_z])
    await db_session.commit()

    response = await authenticated_staff_client.get("/inventory/?sort=-name")
    assert response.status_code == 200
    text = response.text
    pos_a = text.find("AAA Sort Item")
    pos_z = text.find("ZZZ Sort Item")
    assert pos_z < pos_a


@pytest.mark.asyncio
async def test_inventory_detail_page(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Detail Item",
        sku="DI-001",
        description="A detailed description",
        quantity=30,
        unit_price=25.50,
        reorder_level=5,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    response = await authenticated_staff_client.get(f"/inventory/{item.id}/")
    assert response.status_code == 200
    assert "Detail Item" in response.text
    assert "DI-001" in response.text
    assert "A detailed description" in response.text
    assert "$25.50" in response.text


@pytest.mark.asyncio
async def test_inventory_detail_not_found(authenticated_staff_client: AsyncClient):
    response = await authenticated_staff_client.get("/inventory/99999/")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_staff_edit_own_item(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Staff Own Item",
        sku="SOI-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=3,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    response = await authenticated_staff_client.get(f"/inventory/{item.id}/edit/")
    assert response.status_code == 200
    assert "Edit Inventory Item" in response.text
    assert "Staff Own Item" in response.text

    form_data = {
        "name": "Staff Own Item Updated",
        "sku": "SOI-001",
        "description": "Updated description",
        "quantity": "20",
        "unit_price": "7.50",
        "reorder_level": "5",
        "category_id": "",
    }
    response = await authenticated_staff_client.post(
        f"/inventory/{item.id}/edit/",
        data=form_data,
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert f"/inventory/{item.id}/" in response.headers.get("location", "")

    await db_session.refresh(item)
    assert item.name == "Staff Own Item Updated"
    assert item.quantity == 20
    assert item.unit_price == 7.50


@pytest.mark.asyncio
async def test_staff_cannot_edit_others_item(
    authenticated_staff_client: AsyncClient,
    db_session,
    admin_user: User,
):
    item = InventoryItem(
        name="Admin Item",
        sku="AI-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=3,
        created_by_id=admin_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    response = await authenticated_staff_client.get(
        f"/inventory/{item.id}/edit/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/inventory/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_staff_cannot_edit_others_item_post(
    authenticated_staff_client: AsyncClient,
    db_session,
    admin_user: User,
):
    item = InventoryItem(
        name="Admin Item Post",
        sku="AIP-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=3,
        created_by_id=admin_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    form_data = {
        "name": "Hacked Name",
        "sku": "AIP-001",
        "description": "",
        "quantity": "999",
        "unit_price": "0.01",
        "reorder_level": "0",
        "category_id": "",
    }
    response = await authenticated_staff_client.post(
        f"/inventory/{item.id}/edit/",
        data=form_data,
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/inventory/" in response.headers.get("location", "")

    await db_session.refresh(item)
    assert item.name == "Admin Item Post"
    assert item.quantity == 10


@pytest.mark.asyncio
async def test_admin_can_edit_any_item(
    authenticated_admin_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Staff Item For Admin Edit",
        sku="SIFAE-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=3,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    response = await authenticated_admin_client.get(f"/inventory/{item.id}/edit/")
    assert response.status_code == 200
    assert "Staff Item For Admin Edit" in response.text

    form_data = {
        "name": "Admin Edited Staff Item",
        "sku": "SIFAE-001",
        "description": "Admin edited this",
        "quantity": "100",
        "unit_price": "50.00",
        "reorder_level": "10",
        "category_id": "",
    }
    response = await authenticated_admin_client.post(
        f"/inventory/{item.id}/edit/",
        data=form_data,
        follow_redirects=False,
    )
    assert response.status_code == 303

    await db_session.refresh(item)
    assert item.name == "Admin Edited Staff Item"
    assert item.quantity == 100


@pytest.mark.asyncio
async def test_staff_delete_own_item(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Staff Delete Item",
        sku="SDI-001",
        quantity=5,
        unit_price=3.0,
        reorder_level=1,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    item_id = item.id

    response = await authenticated_staff_client.post(
        f"/inventory/{item_id}/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/inventory/"

    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    deleted_item = result.scalar_one_or_none()
    assert deleted_item is None


@pytest.mark.asyncio
async def test_staff_cannot_delete_others_item(
    authenticated_staff_client: AsyncClient,
    db_session,
    admin_user: User,
):
    item = InventoryItem(
        name="Admin Item No Delete",
        sku="AIND-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=3,
        created_by_id=admin_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    item_id = item.id

    response = await authenticated_staff_client.post(
        f"/inventory/{item_id}/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/inventory/" in response.headers.get("location", "")

    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    still_exists = result.scalar_one_or_none()
    assert still_exists is not None


@pytest.mark.asyncio
async def test_admin_can_delete_any_item(
    authenticated_admin_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Staff Item Admin Deletes",
        sku="SIAD-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=3,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    item_id = item.id

    response = await authenticated_admin_client.post(
        f"/inventory/{item_id}/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303

    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    deleted_item = result.scalar_one_or_none()
    assert deleted_item is None


@pytest.mark.asyncio
async def test_delete_nonexistent_item(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.post(
        "/inventory/99999/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_edit_nonexistent_item(authenticated_admin_client: AsyncClient):
    response = await authenticated_admin_client.get(
        "/inventory/99999/edit/",
        follow_redirects=False,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_edit_item_validation_errors(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Edit Validation Item",
        sku="EVI-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=3,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    form_data = {
        "name": "",
        "sku": "EVI-001",
        "description": "",
        "quantity": "10",
        "unit_price": "5.00",
        "reorder_level": "3",
        "category_id": "",
    }
    response = await authenticated_staff_client.post(
        f"/inventory/{item.id}/edit/",
        data=form_data,
    )
    assert response.status_code == 200
    assert "Name is required" in response.text


@pytest.mark.asyncio
async def test_edit_item_duplicate_sku(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item1 = InventoryItem(
        name="First Item",
        sku="FIRST-SKU",
        quantity=10,
        unit_price=5.0,
        reorder_level=3,
        created_by_id=staff_user.id,
    )
    item2 = InventoryItem(
        name="Second Item",
        sku="SECOND-SKU",
        quantity=20,
        unit_price=10.0,
        reorder_level=5,
        created_by_id=staff_user.id,
    )
    db_session.add_all([item1, item2])
    await db_session.commit()
    await db_session.refresh(item2)

    form_data = {
        "name": "Second Item",
        "sku": "FIRST-SKU",
        "description": "",
        "quantity": "20",
        "unit_price": "10.00",
        "reorder_level": "5",
        "category_id": "",
    }
    response = await authenticated_staff_client.post(
        f"/inventory/{item2.id}/edit/",
        data=form_data,
    )
    assert response.status_code == 200
    assert "An item with this SKU already exists" in response.text


@pytest.mark.asyncio
async def test_low_stock_indicator_displayed(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Low Stock Widget",
        sku="LSW-001",
        quantity=3,
        unit_price=10.0,
        reorder_level=5,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()

    response = await authenticated_staff_client.get("/inventory/")
    assert response.status_code == 200
    assert "Low Stock" in response.text


@pytest.mark.asyncio
async def test_out_of_stock_indicator_displayed(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Out Of Stock Widget",
        sku="OOS-001",
        quantity=0,
        unit_price=10.0,
        reorder_level=5,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()

    response = await authenticated_staff_client.get("/inventory/")
    assert response.status_code == 200
    assert "Out of Stock" in response.text


@pytest.mark.asyncio
async def test_in_stock_no_low_stock_indicator(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Healthy Stock Widget",
        sku="HSW-001",
        quantity=100,
        unit_price=10.0,
        reorder_level=5,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()

    response = await authenticated_staff_client.get("/inventory/")
    assert response.status_code == 200
    assert "Healthy Stock Widget" in response.text
    text = response.text
    widget_pos = text.find("Healthy Stock Widget")
    next_card_end = text.find("</div>", widget_pos + 500)
    card_section = text[widget_pos:next_card_end] if next_card_end > widget_pos else text[widget_pos:]
    assert "Low Stock" not in card_section
    assert "Out of Stock" not in card_section


@pytest.mark.asyncio
async def test_low_stock_model_property():
    item = InventoryItem()
    item.quantity = 5
    item.reorder_level = 10
    assert item.is_low_stock is True
    assert item.is_out_of_stock is False


@pytest.mark.asyncio
async def test_out_of_stock_model_property():
    item = InventoryItem()
    item.quantity = 0
    item.reorder_level = 10
    assert item.is_out_of_stock is True
    assert item.is_low_stock is False


@pytest.mark.asyncio
async def test_in_stock_model_property():
    item = InventoryItem()
    item.quantity = 50
    item.reorder_level = 10
    assert item.is_low_stock is False
    assert item.is_out_of_stock is False


@pytest.mark.asyncio
async def test_total_value_model_property():
    item = InventoryItem()
    item.quantity = 10
    item.unit_price = 25.50
    assert item.total_value == 255.0


@pytest.mark.asyncio
async def test_inventory_detail_shows_edit_delete_for_owner(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Owner Detail Item",
        sku="ODI-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=3,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    response = await authenticated_staff_client.get(f"/inventory/{item.id}/")
    assert response.status_code == 200
    assert f"/inventory/{item.id}/edit/" in response.text
    assert f"/inventory/{item.id}/delete/" in response.text


@pytest.mark.asyncio
async def test_inventory_detail_hides_edit_delete_for_non_owner_staff(
    authenticated_staff_client: AsyncClient,
    db_session,
    admin_user: User,
):
    item = InventoryItem(
        name="Admin Owned Detail Item",
        sku="AODI-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=3,
        created_by_id=admin_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    response = await authenticated_staff_client.get(f"/inventory/{item.id}/")
    assert response.status_code == 200
    assert "Admin Owned Detail Item" in response.text
    assert f"/inventory/{item.id}/edit/" not in response.text
    assert f"/inventory/{item.id}/delete/" not in response.text


@pytest.mark.asyncio
async def test_admin_sees_edit_delete_on_any_detail(
    authenticated_admin_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item = InventoryItem(
        name="Staff Owned Admin View",
        sku="SOAV-001",
        quantity=10,
        unit_price=5.0,
        reorder_level=3,
        created_by_id=staff_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    response = await authenticated_admin_client.get(f"/inventory/{item.id}/")
    assert response.status_code == 200
    assert f"/inventory/{item.id}/edit/" in response.text
    assert f"/inventory/{item.id}/delete/" in response.text


@pytest.mark.asyncio
async def test_unauthenticated_post_add_redirects(client: AsyncClient):
    form_data = {
        "name": "Sneaky Item",
        "sku": "SNEAK-001",
        "description": "",
        "quantity": "10",
        "unit_price": "5.00",
        "reorder_level": "5",
        "category_id": "",
    }
    response = await client.post(
        "/inventory/add/",
        data=form_data,
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/login/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_unauthenticated_delete_redirects(client: AsyncClient):
    response = await client.post(
        "/inventory/1/delete/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/login/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_unauthenticated_edit_redirects(client: AsyncClient):
    response = await client.get(
        "/inventory/1/edit/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/login/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_unauthenticated_detail_redirects(client: AsyncClient):
    response = await client.get(
        "/inventory/1/",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/login/" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_inventory_list_sort_by_quantity(
    authenticated_staff_client: AsyncClient,
    db_session,
    staff_user: User,
):
    item_low = InventoryItem(
        name="Low Qty Item",
        quantity=2,
        unit_price=5.0,
        reorder_level=1,
        created_by_id=staff_user.id,
    )
    item_high = InventoryItem(
        name="High Qty Item",
        quantity=200,
        unit_price=5.0,
        reorder_level=1,
        created_by_id=staff_user.id,
    )
    db_session.add_all([item_high, item_low])
    await db_session.commit()

    response = await authenticated_staff_client.get("/inventory/?sort=quantity")
    assert response.status_code == 200
    text = response.text
    pos_low = text.find("Low Qty Item")
    pos_high = text.find("High Qty Item")
    assert pos_low < pos_high


@pytest.mark.asyncio
async def test_create_item_with_category(
    authenticated_staff_client: AsyncClient,
    db_session,
    sample_category: Category,
):
    form_data = {
        "name": "Categorized Item",
        "sku": "CI-001",
        "description": "",
        "quantity": "10",
        "unit_price": "5.00",
        "reorder_level": "3",
        "category_id": str(sample_category.id),
    }
    response = await authenticated_staff_client.post(
        "/inventory/add/",
        data=form_data,
        follow_redirects=False,
    )
    assert response.status_code == 303

    result = await db_session.execute(
        select(InventoryItem).where(InventoryItem.sku == "CI-001")
    )
    item = result.scalar_one_or_none()
    assert item is not None
    assert item.category_id == sample_category.id