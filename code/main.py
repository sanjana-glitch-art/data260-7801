from __future__ import annotations

from code.auth_api import (
    router as auth_router,
)
from code.bikeshare_api import (
    router as bikeshare_router,
)
from code.memory_api import (
    router as memory_router,
)
from code.mongo_database import (
    MONGODB_DATABASE,
    ping_mongodb,
)
from code.mongo_trials_api import (
    router as mongo_trials_router,
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

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

PORT_BASE = 8601


app = FastAPI(
    title="Clinical Trial Listing API",
    description=(
        "DATA-260 Clinical Trial Listing service "
        "with React, Redux Toolkit, FastAPI, "
        "MySQL, MongoDB, MCP tools, memory, "
        "and local Ollama integration."
    ),
    version="6.0.0",
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

app.include_router(
    mongo_trials_router
)

app.include_router(
    memory_router
)

# Retained from Homework 4 for reproducibility.
app.include_router(
    performance_router
)

app.include_router(
    bikeshare_router
)

@app.get("/")
def read_root() -> dict[str, str]:
    """Return basic application information."""

    return {
        "application": (
            "Clinical Trial Listing API"
        ),
        "assignment": (
            "DATA 260 Homework 6"
        ),
        "student": (
            "Sanjana Thummalapalli"
        ),
        "sid4": "7801",
        "version": "6.0.0",
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
        "assignment": "hw6",
    }

@app.get("/health/mongodb")
def mongodb_health_check() -> dict[str, str]:
    """Check the Homework 6 MongoDB connection."""

    try:
        connected = ping_mongodb()
    except Exception as error: # noqa: BLE001
        return {
            "status": "error",
            "database": MONGODB_DATABASE,
            "detail": (
                f"{type(error).__name__}: "
                f"{error}"
            ),
        }

    return {
        "status": (
            "ok"
            if connected
            else "error"
        ),
        "database": MONGODB_DATABASE,
    }

if __name__ == "__main__":
    uvicorn.run(
        "code.main:app",
        host="127.0.0.1",
        port=PORT_BASE,
        reload=True,
    )