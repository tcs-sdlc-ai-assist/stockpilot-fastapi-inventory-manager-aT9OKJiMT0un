import logging
import re

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import select

from database import async_session
from dependencies import (
    get_current_user,
    set_session_cookie,
    clear_session_cookie,
)
from models.user import User


logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


@router.get("/login/", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    user = await get_current_user(request)
    if user is not None:
        if user.role == "admin":
            return RedirectResponse(url="/dashboard/", status_code=303)
        return RedirectResponse(url="/inventory/", status_code=303)

    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "user": None,
            "form_data": None,
            "form_errors": None,
            "flash": None,
        },
    )


@router.post("/login/", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
) -> HTMLResponse:
    form_data = {"username": username}
    form_errors: dict[str, str] = {}

    username = username.strip()
    password = password.strip()

    if not username:
        form_errors["username"] = "Username is required."
    if not password:
        form_errors["password"] = "Password is required."

    if form_errors:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "user": None,
                "form_data": form_data,
                "form_errors": form_errors,
                "flash": None,
            },
        )

    try:
        async with async_session() as db:
            result = await db.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
    except Exception as exc:
        logger.error("Database error during login: %s", exc)
        form_errors["general"] = "An unexpected error occurred. Please try again."
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "user": None,
                "form_data": form_data,
                "form_errors": form_errors,
                "flash": None,
            },
        )

    if user is None or not pwd_context.verify(password, user.hashed_password):
        form_errors["general"] = "Invalid username or password."
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "user": None,
                "form_data": form_data,
                "form_errors": form_errors,
                "flash": None,
            },
        )

    logger.info("User '%s' logged in successfully.", user.username)

    if user.role == "admin":
        redirect_url = "/dashboard/"
    else:
        redirect_url = "/inventory/"

    response = RedirectResponse(url=redirect_url, status_code=303)
    set_session_cookie(response, user)
    return response


@router.get("/register/", response_class=HTMLResponse)
async def register_page(request: Request) -> HTMLResponse:
    user = await get_current_user(request)
    if user is not None:
        return RedirectResponse(url="/inventory/", status_code=303)

    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "user": None,
            "form_data": None,
            "form_errors": None,
            "flash": None,
        },
    )


@router.post("/register/", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    username: str = Form(""),
    display_name: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
) -> HTMLResponse:
    form_data = {
        "username": username,
        "display_name": display_name,
    }
    form_errors: dict[str, str] = {}

    username = username.strip()
    display_name = display_name.strip()

    if not username:
        form_errors["username"] = "Username is required."
    elif len(username) < 3:
        form_errors["username"] = "Username must be at least 3 characters."
    elif len(username) > 50:
        form_errors["username"] = "Username must be at most 50 characters."
    elif not USERNAME_PATTERN.match(username):
        form_errors["username"] = "Username may only contain letters, numbers, and underscores."

    if not display_name:
        form_errors["display_name"] = "Display name is required."
    elif len(display_name) < 3:
        form_errors["display_name"] = "Display name must be at least 3 characters."
    elif len(display_name) > 100:
        form_errors["display_name"] = "Display name must be at most 100 characters."

    if not password:
        form_errors["password"] = "Password is required."
    elif len(password) < 8:
        form_errors["password"] = "Password must be at least 8 characters."
    elif len(password) > 128:
        form_errors["password"] = "Password must be at most 128 characters."

    if not confirm_password:
        form_errors["confirm_password"] = "Please confirm your password."
    elif password and confirm_password != password:
        form_errors["confirm_password"] = "Passwords do not match."

    if form_errors:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "user": None,
                "form_data": form_data,
                "form_errors": form_errors,
                "flash": None,
            },
        )

    try:
        async with async_session() as db:
            result = await db.execute(
                select(User).where(User.username == username)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user is not None:
                form_errors["username"] = "This username is already taken."
                return templates.TemplateResponse(
                    "auth/register.html",
                    {
                        "request": request,
                        "user": None,
                        "form_data": form_data,
                        "form_errors": form_errors,
                        "flash": None,
                    },
                )

            hashed_password = pwd_context.hash(password)
            new_user = User(
                username=username,
                display_name=display_name,
                hashed_password=hashed_password,
                role="staff",
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
    except Exception as exc:
        logger.error("Database error during registration: %s", exc)
        form_errors["general"] = "An unexpected error occurred. Please try again."
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "user": None,
                "form_data": form_data,
                "form_errors": form_errors,
                "flash": None,
            },
        )

    logger.info("New user '%s' registered successfully.", new_user.username)

    response = RedirectResponse(url="/inventory/", status_code=303)
    set_session_cookie(response, new_user)
    return response


@router.post("/logout/", response_class=HTMLResponse)
async def logout(request: Request) -> RedirectResponse:
    user = await get_current_user(request)
    if user is not None:
        logger.info("User '%s' logged out.", user.username)

    response = RedirectResponse(url="/login/", status_code=303)
    clear_session_cookie(response)
    return response