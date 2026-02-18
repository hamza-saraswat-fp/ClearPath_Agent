"""Health check endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Health check for n8n and monitoring."""
    return {
        "status": "healthy",
        "service": "clearpath-agent",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
