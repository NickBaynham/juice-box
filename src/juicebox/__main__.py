"""Uvicorn entrypoint for running the Juice Box API."""

import uvicorn

from juicebox.config.settings import Settings


def main() -> None:
    """Run the API with uvicorn using settings read from the environment."""
    settings = Settings()
    uvicorn.run(
        "juicebox.app:create_app",
        host=settings.api_host,
        port=settings.api_port,
        factory=True,
    )


if __name__ == "__main__":
    main()
