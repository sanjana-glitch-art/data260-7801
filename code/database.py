from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    sessionmaker,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    PROJECT_ROOT / ".env.hw4"
)


MYSQL_HOST = os.getenv(
    "MYSQL_HOST",
    "127.0.0.1",
)

MYSQL_PORT = int(
    os.getenv(
        "MYSQL_PORT",
        "3307",
    )
)

MYSQL_DATABASE = os.getenv(
    "MYSQL_DATABASE",
    "s7801_rel",
)

MYSQL_USER = os.getenv(
    "MYSQL_USER",
    "s7801_app",
)

MYSQL_PASSWORD = os.getenv(
    "MYSQL_PASSWORD",
    "s7801_app_7801",
)


DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    database=MYSQL_DATABASE,
    query={
        "charset": "utf8mb4",
    },
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy database models."""


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)


# Required Homework 4 database-session variable.
db_session_basede26 = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """Provide one database session for a FastAPI request."""

    database = db_session_basede26()

    try:
        yield database
    finally:
        database.close()