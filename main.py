import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import engine, Base
from seed import seed_database
from dependencies import get_current_user

from routes.auth import router as auth_router
from routes.inventory import router as inventory_router
from routes.categories import router as categories_router
from routes.dashboard import router as dashboard_router
from routes.users import router as users_router
from routes.landing import router as landing_router


logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up StockPilot application...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully.")
    except Exception as exc:
        logger.error("Error creating database tables: %s", exc)
        raise

    try:
        await seed_database()
        logger.info("Database seeding completed successfully.")
    except Exception as exc:
        logger.error("Error seeding database: %s", exc)
        raise

    yield

    logger.info("Shutting down StockPilot application...")


app = FastAPI(
    title="StockPilot",
    description="Intelligent Inventory Management System",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(landing_router)
app.include_router(auth_router)
app.include_router(inventory_router)
app.include_router(categories_router)
app.include_router(dashboard_router)
app.include_router(users_router)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc) -> HTMLResponse:
    user = await get_current_user(request)
    return templates.TemplateResponse(
        "errors/404.html",
        {
            "request": request,
            "user": user,
            "flash": [],
        },
        status_code=404,
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}