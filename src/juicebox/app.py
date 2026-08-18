"""FastAPI application factory."""

from fastapi import FastAPI

from juicebox import __version__
from juicebox.api import health_router


def create_app() -> FastAPI:
    """Build the Juice Box application with its routers attached."""
    app = FastAPI(title="Juice Box", version=__version__)
    app.include_router(health_router)
    return app
