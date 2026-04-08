from sqlalchemy import select
from passlib.context import CryptContext

from database import async_session, engine, Base
from models.user import User
from models.category import Category
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_CATEGORIES = [
    {"name": "Electronics", "color": "#3b82f6"},
    {"name": "Clothing", "color": "#8b5cf6"},
    {"name": "Food & Beverage", "color": "#f59e0b"},
    {"name": "Office Supplies", "color": "#6366f1"},
    {"name": "Tools", "color": "#64748b"},
    {"name": "Health & Beauty", "color": "#ec4899"},
]


async def seed_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        try:
            await _seed_admin_user(session)
            await _seed_categories(session)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _seed_admin_user(session) -> None:
    result = await session.execute(
        select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME)
    )
    existing_admin = result.scalars().first()

    if existing_admin is not None:
        return

    hashed_password = pwd_context.hash(settings.DEFAULT_ADMIN_PASSWORD)
    admin_user = User(
        username=settings.DEFAULT_ADMIN_USERNAME,
        display_name="Administrator",
        hashed_password=hashed_password,
        role="admin",
    )
    session.add(admin_user)


async def _seed_categories(session) -> None:
    for cat_data in DEFAULT_CATEGORIES:
        result = await session.execute(
            select(Category).where(Category.name == cat_data["name"])
        )
        existing_category = result.scalars().first()

        if existing_category is not None:
            continue

        category = Category(
            name=cat_data["name"],
            color=cat_data["color"],
        )
        session.add(category)