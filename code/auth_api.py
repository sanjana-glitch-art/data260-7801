from __future__ import annotations

import os
import secrets
from code.database import get_db
from code.models import User
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pwdlib import PasswordHash
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/auth",
    tags=["Homework 7 JWT authentication"],
)

password_hash = (
    PasswordHash.recommended()
)

bearer_scheme = HTTPBearer(
    auto_error=False
)

JWT_SECRET = os.getenv(
    "HW7_JWT_SECRET",
    "",
)

JWT_MINUTES = int(
    os.getenv(
        "HW7_JWT_MINUTES",
        "60",
    )
)

JWT_ALGORITHM = "HS256"

VALID_ROLES = {
    "reader",
    "writer",
    "moderator",
}

Role = Literal[
    "reader",
    "writer",
    "moderator",
]


class LoginRequest(BaseModel):
    """Credentials accepted by the JWT login route."""

    username: str = Field(
        min_length=1,
        max_length=80,
    )

    password: str = Field(
        min_length=1,
        max_length=255,
    )


class UserIdentity(BaseModel):
    """Safe authenticated-user information."""

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    username: str
    display_name: str
    email: str
    role: Role


class TokenResponse(BaseModel):
    """JWT access-token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserIdentity


class IdentityResponse(BaseModel):
    """Authenticated identity response."""

    user: UserIdentity


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
    """Verify a password against its stored hash."""

    try:
        return password_hash.verify(
            password,
            stored_password_hash,
        )
    except (
        TypeError,
        ValueError,
    ):
        return False


def require_jwt_secret() -> str:
    """Return the configured secret or fail safely."""

    if len(JWT_SECRET) < 32:
        raise RuntimeError(
            "HW7_JWT_SECRET must contain "
            "at least 32 characters."
        )

    return JWT_SECRET


def create_access_token(
    user: User,
) -> tuple[str, int]:
    """Create a signed, expiring JWT."""

    now = datetime.now(
        UTC
    )

    expiration = now + timedelta(
        minutes=JWT_MINUTES
    )

    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": expiration,
        "jti": secrets.token_hex(16),
    }

    token = jwt.encode(
        payload,
        require_jwt_secret(),
        algorithm=JWT_ALGORITHM,
    )

    return (
        token,
        JWT_MINUTES * 60,
    )


def unauthorized(
    detail: str = (
        "Missing or invalid access token."
    ),
) -> HTTPException:
    """Create a consistent 401 response."""

    return HTTPException(
        status_code=(
            status.HTTP_401_UNAUTHORIZED
        ),
        detail=detail,
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def decode_access_token(
    token: str,
) -> dict[str, object]:
    """Decode and validate a JWT."""

    try:
        payload = jwt.decode(
            token,
            require_jwt_secret(),
            algorithms=[
                JWT_ALGORITHM
            ],
            options={
                "require": [
                    "sub",
                    "username",
                    "role",
                    "iat",
                    "exp",
                    "jti",
                ],
            },
        )
    except jwt.ExpiredSignatureError as error:
        raise unauthorized(
            "Access token has expired."
        ) from error
    except jwt.InvalidTokenError as error:
        raise unauthorized() from error

    return payload


def require_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    database: Annotated[
        Session,
        Depends(get_db),
    ],
) -> User:
    """Return the user authenticated by a Bearer token."""

    if (
        credentials is None
        or credentials.scheme.casefold()
        != "bearer"
    ):
        raise unauthorized()

    payload = decode_access_token(
        credentials.credentials
    )

    raw_user_id = payload.get(
        "sub"
    )

    try:
        user_id = int(
            str(raw_user_id)
        )
    except (
        TypeError,
        ValueError,
    ) as error:
        raise unauthorized() from error

    user = database.scalar(
        select(User).where(
            User.id == user_id
        )
    )

    if (
        user is None
        or not user.is_active
    ):
        raise unauthorized()

    token_username = str(
        payload.get(
            "username",
            "",
        )
    )

    token_role = str(
        payload.get(
            "role",
            "",
        )
    )

    if (
        token_username
        != user.username
        or token_role
        != user.role
        or user.role
        not in VALID_ROLES
    ):
        raise unauthorized()

    return user


CurrentUser = Annotated[
    User,
    Depends(require_user),
]


def require_writer(
    user: CurrentUser,
) -> User:
    """Allow writer or moderator roles."""

    if user.role not in {
        "writer",
        "moderator",
    }:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Writer or moderator role required."
            ),
        )

    return user


WriterUser = Annotated[
    User,
    Depends(require_writer),
]


def require_moderator(
    user: CurrentUser,
) -> User:
    """Allow only the moderator role."""

    if user.role != "moderator":
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Moderator role required."
            ),
        )

    return user


ModeratorUser = Annotated[
    User,
    Depends(require_moderator),
]


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    login_data: LoginRequest,
    database: Annotated[
        Session,
        Depends(get_db),
    ],
) -> TokenResponse:
    """Validate credentials and issue a JWT."""

    cleaned_username = (
        login_data.username.strip()
    )

    user = database.scalar(
        select(User).where(
            User.username
            == cleaned_username
        )
    )

    credentials_valid = (
        user is not None
        and user.is_active
        and verify_password(
            login_data.password,
            user.password_hash,
        )
    )

    if not credentials_valid:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid username or password."
            ),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if user.role not in VALID_ROLES:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "User has an invalid role."
            ),
        )

    token, expires_in = (
        create_access_token(
            user
        )
    )

    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserIdentity.model_validate(
            user
        ),
    )


@router.get(
    "/me",
    response_model=IdentityResponse,
)
def get_current_user(
    user: CurrentUser,
) -> IdentityResponse:
    """Return the JWT-authenticated user."""

    return IdentityResponse(
        user=UserIdentity.model_validate(
            user
        )
    )