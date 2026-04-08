from typing import Optional
import logging

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignedExpired
from sqlalchemy import select

from config import settings
from database import async_session
from models.user import User


logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds

_signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="stockpilot-session")


def encode_session(user: User) -> str:
    data = {
        "user_id": user.id,
        "role": user.role,
        "username": user.username,
    }
    return _signer.dumps(data)


def decode_session(cookie: str) -> Optional[dict]:
    try:
        data = _signer.loads(cookie, max_age=SESSION_MAX_AGE)
        if not isinstance(data, dict):
            return None
        if "user_id" not in data:
            return None
        return data
    except (BadSignature, SignedExpired) as exc:
        logger.warning("Invalid or expired session cookie: %s", exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error decoding session cookie: %s", exc)
        return None


async def get_current_user(request: Request) -> Optional[User]:
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        return None

    session_data = decode_session(cookie)
    if not session_data:
        return None

    user_id = session_data.get("user_id")
    if user_id is None:
        return None

    try:
        async with async_session() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            return user
    except Exception as exc:
        logger.error("Error fetching user from session: %s", exc)
        return None


async def require_auth(request: Request) -> User:
    user = await get_current_user(request)
    if user is None:
        raise HTTPException(
            status_code=303,
            detail="Authentication required",
            headers={"Location": "/login/"},
        )
    return user


async def require_admin(request: Request) -> User:
    user = await require_auth(request)
    if user.role != "admin":
        raise HTTPException(
            status_code=303,
            detail="Admin access required",
            headers={"Location": "/inventory/"},
        )
    return user


def set_session_cookie(response: RedirectResponse, user: User) -> None:
    token = encode_session(user)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: RedirectResponse) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )