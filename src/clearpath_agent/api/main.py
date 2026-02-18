"""FastAPI application for ClearPath Agent."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import generate, health


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = FastAPI(
        title="ClearPath Agent API",
        description=(
            "Converts StructuredIntent JSON from the Relational Agent "
            "into FieldPulse ClearPath import template Excel files."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS - allow n8n to call from any origin (MVP)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(health.router, tags=["health"])
    app.include_router(generate.router, tags=["generation"])

    return app


app = create_app()


def run_server():
    """Entry point for clearpath-api command."""
    import uvicorn

    uvicorn.run(
        "clearpath_agent.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
