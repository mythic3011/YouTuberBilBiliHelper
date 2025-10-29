"""Core routing module for system and authentication endpoints."""

from app.routes.core.system import router as system_router
from app.routes.core.auth import router as auth_router

__all__ = ["system_router", "auth_router"]

