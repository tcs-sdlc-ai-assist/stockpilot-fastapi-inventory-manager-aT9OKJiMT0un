import logging
import re
from typing import Optional

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import select, func

from config import settings
from database import async_session
from dependencies import require_admin
from models.user import User
from models.item import InventoryItem

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/users/", response_class=HTMLResponse)
async def list_users(request: Request):
    user = await require_admin(request)

    async with async_session() as db:
        result = await db.execute(
            select(User).order_by(User.created_at.desc())
        )
        users = list(result.scalars().all())

    flash = request.session.pop("flash", []) if hasattr(request, "session") else []

    return templates.TemplateResponse(
        "users/list.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "default_admin_username": settings.DEFAULT_ADMIN_USERNAME,
            "flash": flash,
            "form_data": None,
            "form_errors": None,
        },
    )


@router.post("/users/", response_class=HTMLResponse)
async def create_user(
    request: Request,
    username: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    role: str = Form("staff"),
):
    user = await require_admin(request)

    form_data = {
        "username": username,
        "display_name": display_name,
        "role": role,
    }
    form_errors: dict[str, str] = {}

    username_stripped = username.strip()
    display_name_stripped = display_name.strip()

    if not username_stripped or len(username_stripped) < 3:
        form_errors["username"] = "Username must be at least 3 characters."
    elif len(username_stripped) > 50:
        form_errors["username"] = "Username must be at most 50 characters."
    elif not re.match(r"^[a-zA-Z0-9_]+$", username_stripped):
        form_errors["username"] = "Username can only contain letters, numbers, and underscores."

    if not display_name_stripped or len(display_name_stripped) < 3:
        form_errors["display_name"] = "Display name must be at least 3 characters."
    elif len(display_name_stripped) > 100:
        form_errors["display_name"] = "Display name must be at most 100 characters."

    if not password or len(password) < 8:
        form_errors["password"] = "Password must be at least 8 characters."
    elif len(password) > 128:
        form_errors["password"] = "Password must be at most 128 characters."

    if role not in ("admin", "staff"):
        form_errors["role"] = "Role must be either 'admin' or 'staff'."

    if not form_errors:
        async with async_session() as db:
            result = await db.execute(
                select(User).where(User.username == username_stripped)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user is not None:
                form_errors["username"] = "A user with this username already exists."

    if form_errors:
        async with async_session() as db:
            result = await db.execute(
                select(User).order_by(User.created_at.desc())
            )
            users = list(result.scalars().all())

        return templates.TemplateResponse(
            "users/list.html",
            {
                "request": request,
                "user": user,
                "users": users,
                "default_admin_username": settings.DEFAULT_ADMIN_USERNAME,
                "flash": [],
                "form_data": form_data,
                "form_errors": form_errors,
            },
        )

    async with async_session() as db:
        hashed_password = pwd_context.hash(password)
        new_user = User(
            username=username_stripped,
            display_name=display_name_stripped,
            hashed_password=hashed_password,
            role=role,
        )
        db.add(new_user)
        await db.commit()

    logger.info(
        "Admin '%s' created new user '%s' with role '%s'",
        user.username,
        username_stripped,
        role,
    )

    response = RedirectResponse(url="/users/", status_code=303)
    return response


@router.post("/users/{user_id}/delete/", response_class=HTMLResponse)
async def delete_user(request: Request, user_id: int):
    current_user = await require_admin(request)

    if user_id == current_user.id:
        logger.warning(
            "Admin '%s' attempted to delete their own account.",
            current_user.username,
        )
        response = RedirectResponse(url="/users/", status_code=303)
        return response

    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        target_user = result.scalar_one_or_none()

        if target_user is None:
            logger.warning(
                "Admin '%s' attempted to delete non-existent user id=%d.",
                current_user.username,
                user_id,
            )
            response = RedirectResponse(url="/users/", status_code=303)
            return response

        if target_user.username == settings.DEFAULT_ADMIN_USERNAME:
            logger.warning(
                "Admin '%s' attempted to delete the default admin account.",
                current_user.username,
            )
            response = RedirectResponse(url="/users/", status_code=303)
            return response

        await db.execute(
            select(InventoryItem).where(InventoryItem.created_by_id == target_user.id)
        )
        items_result = await db.execute(
            select(InventoryItem).where(InventoryItem.created_by_id == target_user.id)
        )
        items = list(items_result.scalars().all())
        for item in items:
            await db.delete(item)

        deleted_username = target_user.username
        await db.delete(target_user)
        await db.commit()

    logger.info(
        "Admin '%s' deleted user '%s' (id=%d).",
        current_user.username,
        deleted_username,
        user_id,
    )

    response = RedirectResponse(url="/users/", status_code=303)
    return response