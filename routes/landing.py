import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dependencies import get_current_user
from models.user import User


logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request) -> HTMLResponse:
    user: Optional[User] = await get_current_user(request)

    flash: list[str] = []

    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request,
            "user": user,
            "flash": flash,
        },
    )