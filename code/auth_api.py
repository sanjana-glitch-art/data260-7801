from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from code.database import get_db
from code.models import ServerSession, User
from code.schemas import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    UserResponse,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
)


password_hash = PasswordHash.recommended()


SESSION_COOKIE_NAME = os.getenv(
    "SESSION_COOKIE_NAME",
    "s7801_session",
)

SESSION_HOURS = int(
    os.getenv(
        "SESSION_HOURS",
        "8",
    )
)

COOKIE_SECURE = (
    os.getenv(
        "COOKIE_SECURE",
        "false",
    ).strip().lower()
    == "true"
)


def utc_now() -> datetime:
    """Return the current UTC time without timezone metadata."""

    return datetime.now(
        timezone.utc
    ).replace(
        tzinfo=None
    )


def session_expiration() -> datetime:
    """Return the expiration time for a new session."""

    return utc_now() + timedelta(
        hours=SESSION_HOURS
    )


def hash_password(
    password: str,
) -> str:
    """Hash a plaintext password."""

    return password_hash.hash(
        password
    )


def verify_password(
    password: str,
    stored_password_hash: str,
) -> bool:
    """Verify a plaintext password against a saved hash."""

    try:
        return password_hash.verify(
            password,
            stored_password_hash,
        )
    except Exception:
        return False


def read_session_token(
    request: Request,
) -> str | None:
    """Read the opaque session token from the browser cookie."""

    return request.cookies.get(
        SESSION_COOKIE_NAME
    )


def require_user(
    request: Request,
    database: Annotated[
        Session,
        Depends(get_db),
    ],
) -> User:
    """Return the authenticated user or raise HTTP 401."""

    token = read_session_token(
        request
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    server_session = database.scalar(
        select(ServerSession).where(
            ServerSession.token == token
        )
    )

    if server_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session.",
        )

    now = utc_now()

    if server_session.expires_at <= now:
        database.delete(
            server_session
        )
        database.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired.",
        )

    user = database.get(
        User,
        server_session.user_id,
    )

    if user is None or not user.is_active:
        database.delete(
            server_session
        )
        database.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable.",
        )

    server_session.last_activity_at = now
    server_session.expires_at = (
        session_expiration()
    )

    database.commit()

    return user


CurrentUser = Annotated[
    User,
    Depends(require_user),
]


@router.post(
    "/login",
    response_model=AuthResponse,
)
def login(
    login_data: LoginRequest,
    response: Response,
    database: Annotated[
        Session,
        Depends(get_db),
    ],
) -> AuthResponse:
    """Validate credentials and create a server-side session."""

    normalized_email = (
        login_data.email
        .strip()
        .casefold()
    )

    user = database.scalar(
        select(User).where(
            User.email == normalized_email
        )
    )

    if (
        user is None
        or not user.is_active
        or not verify_password(
            login_data.password,
            user.password_hash,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Remove expired sessions before creating a new one.
    database.execute(
        delete(ServerSession).where(
            ServerSession.expires_at
            <= utc_now()
        )
    )

    token = secrets.token_urlsafe(
        48
    )

    server_session = ServerSession(
        token=token,
        user_id=user.id,
        created_at=utc_now(),
        last_activity_at=utc_now(),
        expires_at=session_expiration(),
    )

    database.add(
        server_session
    )

    database.commit()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_HOURS * 60 * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )

    return AuthResponse(
        user=UserResponse.model_validate(
            user
        )
    )


@router.get(
    "/me",
    response_model=AuthResponse,
)
def get_current_user(
    user: CurrentUser,
) -> AuthResponse:
    """Return the user associated with the current session."""

    return AuthResponse(
        user=UserResponse.model_validate(
            user
        )
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
)
def logout(
    request: Request,
    response: Response,
    database: Annotated[
        Session,
        Depends(get_db),
    ],
) -> MessageResponse:
    """Delete the server-side session and browser cookie."""

    token = read_session_token(
        request
    )

    if token:
        database.execute(
            delete(ServerSession).where(
                ServerSession.token == token
            )
        )

        database.commit()

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )

    return MessageResponse(
        message="Logged out successfully."
    )