"""Health check route."""

from fastapi import APIRouter

from juicebox import __version__

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Report that the service is running and which version is serving."""
    return {"status": "ok", "version": __version__}
