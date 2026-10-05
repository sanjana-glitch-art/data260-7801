from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from code.auth_api import (
    router as auth_router,
)
from code.performance_api import (
    router as performance_router,
)
from code.sponsors_api import (
    router as sponsors_router,
)
from code.trials_api import (
    router as trials_router,
)


PORT_BASE = 8601


app = FastAPI(
    title="Clinical Trial Listing API",
    description=(
        "DATA-260 Clinical Trial Listing service "
        "with React, Redux Toolkit, FastAPI, "
        "MySQL, MCP tools, and server-side sessions."
    ),
    version="5.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=["*"],
)


app.include_router(
    auth_router
)

app.include_router(
    sponsors_router
)

app.include_router(
    trials_router
)

# Retained from Homework 4 for reproducibility.
app.include_router(
    performance_router
)


@app.get("/")
def read_root() -> dict[str, str]:
    """Return basic application information."""

    return {
        "application": (
            "Clinical Trial Listing API"
        ),
        "assignment": (
            "DATA 260 Homework 5"
        ),
        "student": (
            "Sanjana Thummalapalli"
        ),
        "sid4": "7801",
        "version": "5.0.0",
        "documentation": "/docs",
        "frontend": (
            "http://127.0.0.1:5173"
        ),
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return a basic application health response."""

    return {
        "status": "ok",
        "database": "s7801_rel",
        "assignment": "hw5",
    }


if __name__ == "__main__":
    uvicorn.run(
        "code.main:app",
        host="127.0.0.1",
        port=PORT_BASE,
        reload=True,
    )