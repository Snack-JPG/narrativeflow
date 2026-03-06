"""Main entry point for NarrativeFlow."""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from narrative_flow.api.main import app
from narrative_flow.models.db_manager import db_manager
from narrative_flow.scheduler import scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting NarrativeFlow...")

    # Create database tables
    await db_manager.create_all()
    logger.info("Database initialized")

    # Run initial data collection
    await scheduler.run_initial_collection()

    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down NarrativeFlow...")
    scheduler.stop()
    await db_manager.close()
    logger.info("Shutdown complete")


# Set lifespan for the app
app.router.lifespan_context = lifespan


def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal")
    sys.exit(0)


def main():
    """Main entry point."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()