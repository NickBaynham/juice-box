"""HTTP routers for the Juice Box API."""

from juicebox.api.agents import router as agents_router
from juicebox.api.health import router as health_router

__all__ = ["agents_router", "health_router"]
