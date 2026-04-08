import logging
from typing import List

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func

from database import async_session
from dependencies import require_admin
from models.user import User
from models.item import InventoryItem
from models.category import Category

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard/", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(require_admin)):
    try:
        async with async_session() as db:
            # Total items count
            result = await db.execute(select(func.count(InventoryItem.id)))
            total_items = result.scalar_one_or_none() or 0

            # Total inventory value
            result = await db.execute(
                select(func.coalesce(func.sum(InventoryItem.quantity * InventoryItem.unit_price), 0.0))
            )
            total_value = result.scalar_one_or_none() or 0.0

            # Total users count
            result = await db.execute(select(func.count(User.id)))
            total_users = result.scalar_one_or_none() or 0

            # Low stock count (quantity > 0 and quantity <= reorder_level)
            result = await db.execute(
                select(func.count(InventoryItem.id)).where(
                    InventoryItem.quantity > 0,
                    InventoryItem.quantity <= InventoryItem.reorder_level,
                )
            )
            low_stock_count = result.scalar_one_or_none() or 0

            # Out of stock count (quantity <= 0)
            result = await db.execute(
                select(func.count(InventoryItem.id)).where(
                    InventoryItem.quantity <= 0,
                )
            )
            out_of_stock_count = result.scalar_one_or_none() or 0

            # Low stock items (quantity <= reorder_level), includes both low and out of stock
            result = await db.execute(
                select(InventoryItem)
                .where(InventoryItem.quantity <= InventoryItem.reorder_level)
                .order_by(InventoryItem.quantity.asc())
                .limit(20)
            )
            low_stock_items: List[InventoryItem] = list(result.scalars().all())

            # Recent items (last 10 by created_at)
            result = await db.execute(
                select(InventoryItem)
                .order_by(InventoryItem.created_at.desc())
                .limit(10)
            )
            recent_items: List[InventoryItem] = list(result.scalars().all())

        stats = {
            "total_items": total_items,
            "total_value": float(total_value),
            "total_users": total_users,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
        }

        flash = request.session.pop("flash", []) if hasattr(request, "session") else []

        return templates.TemplateResponse(
            "dashboard/index.html",
            {
                "request": request,
                "user": user,
                "stats": stats,
                "low_stock_items": low_stock_items,
                "recent_items": recent_items,
                "flash": flash,
            },
        )
    except Exception as exc:
        logger.error("Error loading dashboard: %s", exc)
        return templates.TemplateResponse(
            "dashboard/index.html",
            {
                "request": request,
                "user": user,
                "stats": {
                    "total_items": 0,
                    "total_value": 0.0,
                    "total_users": 0,
                    "low_stock_count": 0,
                    "out_of_stock_count": 0,
                },
                "low_stock_items": [],
                "recent_items": [],
                "flash": ["Error loading dashboard data. Please try again."],
            },
        )