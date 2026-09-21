from __future__ import annotations

import os
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Form,
    Request,
    Response,
    status
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse
)
from fastapi.templating import Jinja2Templates


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEMPLATE_DIRECTORY = (
    PROJECT_ROOT
    / "code"
    / "templates"
)

templates = Jinja2Templates(
    directory=TEMPLATE_DIRECTORY
)

router = APIRouter()

SESSION_IDLE_SECONDS = int(
    os.getenv(
        "SESSION_IDLE_SECONDS",
        "120"
    )
)

DEMO_USERNAME = os.getenv(
    "HW3_USERNAME",
    "sanjana"
)

DEMO_PASSWORD = os.getenv(
    "HW3_PASSWORD",
    "Data260!7801"
)

DEMO_DISPLAY_NAME = (
    "Sanjana Thummalapalli"
)


def current_timestamp() -> int:
    """Return the current Unix timestamp."""

    return int(time.time())


def session_user(
    request: Request
) -> dict[str, Any] | None:
    """
    Return the logged-in user when the session is active.

    Expired sessions are cleared and cannot be reused.
    """

    user = request.session.get("user")

    last_activity = request.session.get(
        "last_activity"
    )

    if not user or not last_activity:
        return None

    idle_seconds = (
        current_timestamp()
        - int(last_activity)
    )

    if idle_seconds > SESSION_IDLE_SECONDS:
        request.session.clear()
        return None

    # Refresh the activity time after a valid request.
    request.session["last_activity"] = (
        current_timestamp()
    )

    return user


def credentials_are_valid(
    username: str,
    password: str
) -> bool:
    """Safely compare the submitted credentials."""

    username_matches = secrets.compare_digest(
        username,
        DEMO_USERNAME
    )

    password_matches = secrets.compare_digest(
        password,
        DEMO_PASSWORD
    )

    return (
        username_matches
        and password_matches
    )


@router.get(
    "/",
    response_class=HTMLResponse
)
async def home_page(
    request: Request
) -> HTMLResponse:
    """Display the application home page."""

    user = session_user(request)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "user": user,
            "idle_timeout": SESSION_IDLE_SECONDS
        }
    )


@router.get(
    "/login",
    response_class=HTMLResponse
)
async def login_page(
    request: Request,
    expired: int = 0
) -> Response:
    """Display the login form."""

    if session_user(request):
        return RedirectResponse(
            url="/dashboard",
            status_code=(
                status.HTTP_303_SEE_OTHER
            )
        )

    message = None

    if expired:
        message = (
            "Your session expired because of "
            "inactivity. Please log in again."
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "user": None,
            "error": None,
            "message": message,
            "username": ""
        }
    )


@router.post(
    "/login",
    response_class=HTMLResponse
)
async def process_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
) -> Response:
    """Validate credentials and create a session."""

    cleaned_username = username.strip()

    if not credentials_are_valid(
        cleaned_username,
        password
    ):
        request.session.clear()

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "user": None,
                "error": (
                    "Invalid username or password."
                ),
                "message": None,
                "username": cleaned_username
            },
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            )
        )

    request.session.clear()

    request.session["user"] = {
        "username": DEMO_USERNAME,
        "display_name": DEMO_DISPLAY_NAME
    }

    request.session["last_activity"] = (
        current_timestamp()
    )

    return RedirectResponse(
        url="/dashboard",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.get(
    "/dashboard",
    response_class=HTMLResponse
)
async def dashboard_page(
    request: Request
) -> Response:
    """Display the protected dashboard."""

    # Check whether a session existed before session_user()
    # potentially clears it because it expired.
    had_session = bool(
        request.session.get("user")
    )

    user = session_user(request)

    if user is None:
        request.session.clear()

        redirect_url = (
            "/login?expired=1"
            if had_session
            else "/login"
        )

        return RedirectResponse(
            url=redirect_url,
            status_code=(
                status.HTTP_303_SEE_OTHER
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "idle_timeout": SESSION_IDLE_SECONDS
        }
    )


@router.get("/logout")
async def logout(
    request: Request
) -> RedirectResponse:
    """Destroy the session and redirect home."""

    request.session.clear()

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER
    )