"""Core routing module for system, authentication, and API metadata endpoints."""

from app.routes.core.system import router as system_router
from app.routes.core.auth import router as auth_router
from app.routes.core.meta import router as meta_router

__all__ = ["system_router", "auth_router", "meta_router"]

