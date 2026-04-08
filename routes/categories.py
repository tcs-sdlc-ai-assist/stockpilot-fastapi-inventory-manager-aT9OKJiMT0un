import logging
from typing import Optional

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func

from database import async_session
from dependencies import require_admin
from models.user import User
from models.category import Category
from models.item import InventoryItem

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/categories/", response_class=HTMLResponse)
async def list_categories(request: Request, user: User = Depends(require_admin)):
    flash = request.session.pop("flash", []) if hasattr(request, "session") else []
    flash_messages = request.cookies.get("flash", None)

    categories_with_counts = []

    try:
        async with async_session() as db:
            stmt = (
                select(
                    Category,
                    func.count(InventoryItem.id).label("item_count"),
                )
                .outerjoin(InventoryItem, InventoryItem.category_id == Category.id)
                .group_by(Category.id)
                .order_by(Category.name)
            )
            result = await db.execute(stmt)
            rows = result.all()

            for category, item_count in rows:
                category.item_count = item_count
                categories_with_counts.append(category)
    except Exception as exc:
        logger.error("Error fetching categories: %s", exc)

    flash = []
    raw_flash = request.cookies.get("flash")
    if raw_flash:
        flash = [raw_flash]

    response = templates.TemplateResponse(
        "categories/list.html",
        {
            "request": request,
            "user": user,
            "categories": categories_with_counts,
            "flash": flash,
            "form_data": {},
            "form_errors": {},
        },
    )

    if raw_flash:
        response.delete_cookie("flash", path="/")

    return response


@router.post("/categories/", response_class=HTMLResponse)
async def create_category(
    request: Request,
    name: str = Form(""),
    color: str = Form("#0d9488"),
    user: User = Depends(require_admin),
):
    form_data = {"name": name.strip(), "color": color.strip()}
    form_errors: dict[str, str] = {}

    name_clean = name.strip()
    color_clean = color.strip()

    if not name_clean:
        form_errors["name"] = "Category name is required."
    elif len(name_clean) < 2:
        form_errors["name"] = "Category name must be at least 2 characters."
    elif len(name_clean) > 50:
        form_errors["name"] = "Category name must be at most 50 characters."

    if not color_clean:
        form_errors["color"] = "Color is required."
    elif not _is_valid_hex_color(color_clean):
        form_errors["color"] = "Color must be a valid hex color (e.g. #0d9488)."

    if not form_errors:
        try:
            async with async_session() as db:
                existing_stmt = select(Category).where(Category.name == name_clean)
                existing_result = await db.execute(existing_stmt)
                existing = existing_result.scalar_one_or_none()

                if existing is not None:
                    form_errors["name"] = "A category with this name already exists."
                else:
                    new_category = Category(
                        name=name_clean,
                        color=color_clean,
                    )
                    db.add(new_category)
                    await db.commit()

                    response = RedirectResponse(url="/categories/", status_code=303)
                    response.set_cookie(
                        key="flash",
                        value=f"Category '{name_clean}' created successfully.",
                        max_age=10,
                        httponly=True,
                        samesite="lax",
                        path="/",
                    )
                    return response
        except Exception as exc:
            logger.error("Error creating category: %s", exc)
            form_errors["general"] = "An unexpected error occurred. Please try again."

    categories_with_counts = []
    try:
        async with async_session() as db:
            stmt = (
                select(
                    Category,
                    func.count(InventoryItem.id).label("item_count"),
                )
                .outerjoin(InventoryItem, InventoryItem.category_id == Category.id)
                .group_by(Category.id)
                .order_by(Category.name)
            )
            result = await db.execute(stmt)
            rows = result.all()

            for category, item_count in rows:
                category.item_count = item_count
                categories_with_counts.append(category)
    except Exception as exc:
        logger.error("Error fetching categories: %s", exc)

    return templates.TemplateResponse(
        "categories/list.html",
        {
            "request": request,
            "user": user,
            "categories": categories_with_counts,
            "flash": [],
            "form_data": form_data,
            "form_errors": form_errors,
        },
    )


@router.post("/categories/{category_id}/delete/", response_class=HTMLResponse)
async def delete_category(
    request: Request,
    category_id: int,
    user: User = Depends(require_admin),
):
    try:
        async with async_session() as db:
            stmt = select(Category).where(Category.id == category_id)
            result = await db.execute(stmt)
            category = result.scalar_one_or_none()

            if category is None:
                response = RedirectResponse(url="/categories/", status_code=303)
                response.set_cookie(
                    key="flash",
                    value="Error: Category not found.",
                    max_age=10,
                    httponly=True,
                    samesite="lax",
                    path="/",
                )
                return response

            item_count_stmt = (
                select(func.count(InventoryItem.id))
                .where(InventoryItem.category_id == category_id)
            )
            item_count_result = await db.execute(item_count_stmt)
            item_count = item_count_result.scalar() or 0

            if item_count > 0:
                response = RedirectResponse(url="/categories/", status_code=303)
                response.set_cookie(
                    key="flash",
                    value=f"Error: Cannot delete category '{category.name}' because it has {item_count} item{'s' if item_count != 1 else ''} assigned to it.",
                    max_age=10,
                    httponly=True,
                    samesite="lax",
                    path="/",
                )
                return response

            category_name = category.name
            await db.delete(category)
            await db.commit()

            response = RedirectResponse(url="/categories/", status_code=303)
            response.set_cookie(
                key="flash",
                value=f"Category '{category_name}' deleted successfully.",
                max_age=10,
                httponly=True,
                samesite="lax",
                path="/",
            )
            return response
    except Exception as exc:
        logger.error("Error deleting category %s: %s", category_id, exc)
        response = RedirectResponse(url="/categories/", status_code=303)
        response.set_cookie(
            key="flash",
            value="Error: An unexpected error occurred while deleting the category.",
            max_age=10,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return response


def _is_valid_hex_color(value: str) -> bool:
    if not value.startswith("#"):
        return False
    hex_part = value[1:]
    if len(hex_part) not in (3, 6):
        return False
    try:
        int(hex_part, 16)
        return True
    except ValueError:
        return False