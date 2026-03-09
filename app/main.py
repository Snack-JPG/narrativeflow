"""Compatibility entrypoint for Docker and legacy `app.main` imports."""

import uvicorn

from narrative_flow.api.main import app


def main() -> None:
    """Run the FastAPI server."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
