"""FastAPI application factory."""

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from juicebox import __version__
from juicebox.api import agents_router, health_router
from juicebox.api.errors import validation_error_detail


def create_app() -> FastAPI:
    """Build the Juice Box application with its routers and handlers attached."""
    app = FastAPI(title="Juice Box", version=__version__)
    app.include_router(health_router)
    app.include_router(agents_router)

    @app.exception_handler(ValidationError)
    async def _validation_error(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": validation_error_detail(exc)})

    @app.exception_handler(yaml.YAMLError)
    async def _yaml_error(request: Request, exc: yaml.YAMLError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": validation_error_detail(exc)})

    return app
