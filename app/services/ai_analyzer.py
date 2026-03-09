"""Background AI analysis worker for Docker Compose."""

import asyncio
import logging
import os

from narrative_flow.ai import BriefingStorage, BriefingGenerator, ClaudeClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AIAnalyzerService:
    """Runs periodic AI analysis tasks for narrative briefings."""

    def __init__(self, interval_seconds: int = 3600):
        self.interval_seconds = interval_seconds
        self.storage = BriefingStorage()
        self.generator = None

    async def initialize(self) -> None:
        """Initialize storage and optional Claude client."""
        await self.storage.initialize()
        logger.info("Briefing storage initialized")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not configured; AI analyzer running in idle mode")
            return

        self.generator = BriefingGenerator(ClaudeClient())
        logger.info("AI briefing generator initialized")

    async def run_forever(self) -> None:
        """Run the worker loop."""
        await self.initialize()

        while True:
            try:
                if self.generator:
                    # Placeholder for scheduled analysis generation.
                    logger.info("AI analyzer heartbeat: ready for scheduled briefing jobs")
                else:
                    logger.info("AI analyzer heartbeat: idle (no API key)")
            except Exception as exc:
                logger.exception("AI analyzer loop error: %s", exc)

            await asyncio.sleep(self.interval_seconds)


def main() -> None:
    """Service entrypoint."""
    asyncio.run(AIAnalyzerService().run_forever())


if __name__ == "__main__":
    main()
