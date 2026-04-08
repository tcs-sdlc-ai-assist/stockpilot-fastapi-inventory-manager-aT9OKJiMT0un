import logging
from typing import Optional

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from database import async_session
from dependencies import require_auth
from models.user import User
from models.item import InventoryItem
from models.category import Category

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/inventory/", response_class=HTMLResponse)
async def inventory_list(
    request: Request,
    search: Optional[str] = None,
    category: Optional[str] = None,
    sort: Optional[str] = None,
):
    user = await require_auth(request)

    filters = {
        "search": search or "",
        "category": category or "",
        "sort": sort or "name",
    }

    async with async_session() as db:
        stmt = select(InventoryItem).options(
            selectinload(InventoryItem.category),
            selectinload(InventoryItem.owner),
        )

        if filters["search"]:
            search_term = f"%{filters['search']}%"
            stmt = stmt.where(
                or_(
                    InventoryItem.name.ilike(search_term),
                    InventoryItem.sku.ilike(search_term),
                )
            )

        if filters["category"]:
            try:
                cat_id = int(filters["category"])
                stmt = stmt.where(InventoryItem.category_id == cat_id)
            except (ValueError, TypeError):
                pass

        sort_field = filters["sort"]
        descending = False
        if sort_field.startswith("-"):
            descending = True
            sort_field = sort_field[1:]

        sort_column_map = {
            "name": InventoryItem.name,
            "quantity": InventoryItem.quantity,
            "unit_price": InventoryItem.unit_price,
            "created_at": InventoryItem.created_at,
        }
        sort_column = sort_column_map.get(sort_field, InventoryItem.name)
        if descending:
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        result = await db.execute(stmt)
        items = result.scalars().all()

        cat_result = await db.execute(select(Category).order_by(Category.name))
        categories = cat_result.scalars().all()

    flash = request.session.pop("flash", []) if hasattr(request, "session") else []
    flash = request.cookies.get("flash_messages", None)
    flash_messages: list[str] = []

    return templates.TemplateResponse(
        "inventory/list.html",
        {
            "request": request,
            "user": user,
            "items": items,
            "categories": categories,
            "filters": filters,
            "flash": flash_messages,
        },
    )


@router.get("/inventory/add/", response_class=HTMLResponse)
async def inventory_add_form(request: Request):
    user = await require_auth(request)

    async with async_session() as db:
        cat_result = await db.execute(select(Category).order_by(Category.name))
        categories = cat_result.scalars().all()

    return templates.TemplateResponse(
        "inventory/form.html",
        {
            "request": request,
            "user": user,
            "item": None,
            "categories": categories,
            "form_errors": None,
        },
    )


@router.post("/inventory/add/", response_class=HTMLResponse)
async def inventory_add_submit(
    request: Request,
    name: str = Form(""),
    sku: str = Form(""),
    description: str = Form(""),
    quantity: str = Form("0"),
    unit_price: str = Form("0.00"),
    reorder_level: str = Form("10"),
    category_id: str = Form(""),
):
    user = await require_auth(request)

    form_errors: dict[str, str] = {}

    name = name.strip()
    sku = sku.strip()
    description = description.strip()

    if not name:
        form_errors["name"] = "Name is required."
    elif len(name) > 200:
        form_errors["name"] = "Name must be 200 characters or fewer."

    if sku and len(sku) > 50:
        form_errors["sku"] = "SKU must be 50 characters or fewer."

    try:
        quantity_int = int(quantity)
        if quantity_int < 0:
            form_errors["quantity"] = "Quantity must be 0 or greater."
    except (ValueError, TypeError):
        form_errors["quantity"] = "Quantity must be a valid integer."
        quantity_int = 0

    try:
        unit_price_float = float(unit_price)
        if unit_price_float < 0:
            form_errors["unit_price"] = "Unit price must be 0 or greater."
    except (ValueError, TypeError):
        form_errors["unit_price"] = "Unit price must be a valid number."
        unit_price_float = 0.0

    try:
        reorder_level_int = int(reorder_level)
        if reorder_level_int < 0:
            form_errors["reorder_level"] = "Reorder level must be 0 or greater."
    except (ValueError, TypeError):
        form_errors["reorder_level"] = "Reorder level must be a valid integer."
        reorder_level_int = 10

    category_id_int: Optional[int] = None
    if category_id and category_id.strip():
        try:
            category_id_int = int(category_id)
        except (ValueError, TypeError):
            form_errors["category_id"] = "Invalid category."

    if form_errors:
        async with async_session() as db:
            cat_result = await db.execute(select(Category).order_by(Category.name))
            categories = cat_result.scalars().all()

        item_data = type("ItemData", (), {
            "name": name,
            "sku": sku,
            "description": description,
            "quantity": quantity_int,
            "unit_price": unit_price_float,
            "reorder_level": reorder_level_int,
            "category_id": category_id_int,
        })()

        return templates.TemplateResponse(
            "inventory/form.html",
            {
                "request": request,
                "user": user,
                "item": item_data,
                "categories": categories,
                "form_errors": form_errors,
            },
        )

    async with async_session() as db:
        try:
            if sku:
                existing_sku = await db.execute(
                    select(InventoryItem).where(InventoryItem.sku == sku)
                )
                if existing_sku.scalar_one_or_none() is not None:
                    form_errors["sku"] = "An item with this SKU already exists."
                    cat_result = await db.execute(select(Category).order_by(Category.name))
                    categories = cat_result.scalars().all()

                    item_data = type("ItemData", (), {
                        "name": name,
                        "sku": sku,
                        "description": description,
                        "quantity": quantity_int,
                        "unit_price": unit_price_float,
                        "reorder_level": reorder_level_int,
                        "category_id": category_id_int,
                    })()

                    return templates.TemplateResponse(
                        "inventory/form.html",
                        {
                            "request": request,
                            "user": user,
                            "item": item_data,
                            "categories": categories,
                            "form_errors": form_errors,
                        },
                    )

            if category_id_int is not None:
                cat_check = await db.execute(
                    select(Category).where(Category.id == category_id_int)
                )
                if cat_check.scalar_one_or_none() is None:
                    category_id_int = None

            new_item = InventoryItem(
                name=name,
                sku=sku if sku else None,
                description=description if description else None,
                quantity=quantity_int,
                unit_price=unit_price_float,
                reorder_level=reorder_level_int,
                category_id=category_id_int,
                created_by_id=user.id,
            )
            db.add(new_item)
            await db.commit()

            return RedirectResponse(url="/inventory/", status_code=303)

        except Exception as exc:
            await db.rollback()
            logger.error("Error creating inventory item: %s", exc)

            cat_result_err = await db.execute(select(Category).order_by(Category.name))
            categories = cat_result_err.scalars().all()

            item_data = type("ItemData", (), {
                "name": name,
                "sku": sku,
                "description": description,
                "quantity": quantity_int,
                "unit_price": unit_price_float,
                "reorder_level": reorder_level_int,
                "category_id": category_id_int,
            })()

            form_errors["general"] = "An unexpected error occurred. Please try again."
            return templates.TemplateResponse(
                "inventory/form.html",
                {
                    "request": request,
                    "user": user,
                    "item": item_data,
                    "categories": categories,
                    "form_errors": form_errors,
                },
            )


@router.get("/inventory/{item_id}/", response_class=HTMLResponse)
async def inventory_detail(request: Request, item_id: int):
    user = await require_auth(request)

    async with async_session() as db:
        result = await db.execute(
            select(InventoryItem)
            .options(
                selectinload(InventoryItem.category),
                selectinload(InventoryItem.owner),
            )
            .where(InventoryItem.id == item_id)
        )
        item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    can_edit = user.role == "admin" or item.created_by_id == user.id
    can_delete = user.role == "admin" or item.created_by_id == user.id

    return templates.TemplateResponse(
        "inventory/detail.html",
        {
            "request": request,
            "user": user,
            "item": item,
            "can_edit": can_edit,
            "can_delete": can_delete,
        },
    )


@router.get("/inventory/{item_id}/edit/", response_class=HTMLResponse)
async def inventory_edit_form(request: Request, item_id: int):
    user = await require_auth(request)

    async with async_session() as db:
        result = await db.execute(
            select(InventoryItem)
            .options(
                selectinload(InventoryItem.category),
                selectinload(InventoryItem.owner),
            )
            .where(InventoryItem.id == item_id)
        )
        item = result.scalar_one_or_none()

        if item is None:
            raise HTTPException(status_code=404, detail="Item not found")

        if user.role != "admin" and item.created_by_id != user.id:
            raise HTTPException(
                status_code=303,
                detail="You do not have permission to edit this item.",
                headers={"Location": "/inventory/"},
            )

        cat_result = await db.execute(select(Category).order_by(Category.name))
        categories = cat_result.scalars().all()

    return templates.TemplateResponse(
        "inventory/form.html",
        {
            "request": request,
            "user": user,
            "item": item,
            "categories": categories,
            "form_errors": None,
        },
    )


@router.post("/inventory/{item_id}/edit/", response_class=HTMLResponse)
async def inventory_edit_submit(
    request: Request,
    item_id: int,
    name: str = Form(""),
    sku: str = Form(""),
    description: str = Form(""),
    quantity: str = Form("0"),
    unit_price: str = Form("0.00"),
    reorder_level: str = Form("10"),
    category_id: str = Form(""),
):
    user = await require_auth(request)

    form_errors: dict[str, str] = {}

    name = name.strip()
    sku = sku.strip()
    description = description.strip()

    if not name:
        form_errors["name"] = "Name is required."
    elif len(name) > 200:
        form_errors["name"] = "Name must be 200 characters or fewer."

    if sku and len(sku) > 50:
        form_errors["sku"] = "SKU must be 50 characters or fewer."

    try:
        quantity_int = int(quantity)
        if quantity_int < 0:
            form_errors["quantity"] = "Quantity must be 0 or greater."
    except (ValueError, TypeError):
        form_errors["quantity"] = "Quantity must be a valid integer."
        quantity_int = 0

    try:
        unit_price_float = float(unit_price)
        if unit_price_float < 0:
            form_errors["unit_price"] = "Unit price must be 0 or greater."
    except (ValueError, TypeError):
        form_errors["unit_price"] = "Unit price must be a valid number."
        unit_price_float = 0.0

    try:
        reorder_level_int = int(reorder_level)
        if reorder_level_int < 0:
            form_errors["reorder_level"] = "Reorder level must be 0 or greater."
    except (ValueError, TypeError):
        form_errors["reorder_level"] = "Reorder level must be a valid integer."
        reorder_level_int = 10

    category_id_int: Optional[int] = None
    if category_id and category_id.strip():
        try:
            category_id_int = int(category_id)
        except (ValueError, TypeError):
            form_errors["category_id"] = "Invalid category."

    async with async_session() as db:
        result = await db.execute(
            select(InventoryItem)
            .options(
                selectinload(InventoryItem.category),
                selectinload(InventoryItem.owner),
            )
            .where(InventoryItem.id == item_id)
        )
        item = result.scalar_one_or_none()

        if item is None:
            raise HTTPException(status_code=404, detail="Item not found")

        if user.role != "admin" and item.created_by_id != user.id:
            raise HTTPException(
                status_code=303,
                detail="You do not have permission to edit this item.",
                headers={"Location": "/inventory/"},
            )

        if form_errors:
            cat_result = await db.execute(select(Category).order_by(Category.name))
            categories = cat_result.scalars().all()

            item_data = type("ItemData", (), {
                "name": name,
                "sku": sku,
                "description": description,
                "quantity": quantity_int,
                "unit_price": unit_price_float,
                "reorder_level": reorder_level_int,
                "category_id": category_id_int,
                "id": item_id,
            })()

            return templates.TemplateResponse(
                "inventory/form.html",
                {
                    "request": request,
                    "user": user,
                    "item": item_data,
                    "categories": categories,
                    "form_errors": form_errors,
                },
            )

        try:
            if sku:
                existing_sku = await db.execute(
                    select(InventoryItem).where(
                        InventoryItem.sku == sku,
                        InventoryItem.id != item_id,
                    )
                )
                if existing_sku.scalar_one_or_none() is not None:
                    form_errors["sku"] = "An item with this SKU already exists."
                    cat_result = await db.execute(select(Category).order_by(Category.name))
                    categories = cat_result.scalars().all()

                    item_data = type("ItemData", (), {
                        "name": name,
                        "sku": sku,
                        "description": description,
                        "quantity": quantity_int,
                        "unit_price": unit_price_float,
                        "reorder_level": reorder_level_int,
                        "category_id": category_id_int,
                        "id": item_id,
                    })()

                    return templates.TemplateResponse(
                        "inventory/form.html",
                        {
                            "request": request,
                            "user": user,
                            "item": item_data,
                            "categories": categories,
                            "form_errors": form_errors,
                        },
                    )

            if category_id_int is not None:
                cat_check = await db.execute(
                    select(Category).where(Category.id == category_id_int)
                )
                if cat_check.scalar_one_or_none() is None:
                    category_id_int = None

            item.name = name
            item.sku = sku if sku else None
            item.description = description if description else None
            item.quantity = quantity_int
            item.unit_price = unit_price_float
            item.reorder_level = reorder_level_int
            item.category_id = category_id_int

            await db.commit()

            return RedirectResponse(url=f"/inventory/{item_id}/", status_code=303)

        except Exception as exc:
            await db.rollback()
            logger.error("Error updating inventory item %d: %s", item_id, exc)

            cat_result_err = await db.execute(select(Category).order_by(Category.name))
            categories = cat_result_err.scalars().all()

            item_data = type("ItemData", (), {
                "name": name,
                "sku": sku,
                "description": description,
                "quantity": quantity_int,
                "unit_price": unit_price_float,
                "reorder_level": reorder_level_int,
                "category_id": category_id_int,
                "id": item_id,
            })()

            form_errors["general"] = "An unexpected error occurred. Please try again."
            return templates.TemplateResponse(
                "inventory/form.html",
                {
                    "request": request,
                    "user": user,
                    "item": item_data,
                    "categories": categories,
                    "form_errors": form_errors,
                },
            )


@router.post("/inventory/{item_id}/delete/")
async def inventory_delete(request: Request, item_id: int):
    user = await require_auth(request)

    async with async_session() as db:
        result = await db.execute(
            select(InventoryItem).where(InventoryItem.id == item_id)
        )
        item = result.scalar_one_or_none()

        if item is None:
            raise HTTPException(status_code=404, detail="Item not found")

        if user.role != "admin" and item.created_by_id != user.id:
            raise HTTPException(
                status_code=303,
                detail="You do not have permission to delete this item.",
                headers={"Location": "/inventory/"},
            )

        try:
            await db.delete(item)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("Error deleting inventory item %d: %s", item_id, exc)

    return RedirectResponse(url="/inventory/", status_code=303)