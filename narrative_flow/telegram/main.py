"""Main Telegram bot runner with all integrations."""

import asyncio
import logging
import signal
import sys
from typing import Optional

from narrative_flow.config.settings import settings
from narrative_flow.telegram.bot import TelegramBot
from narrative_flow.telegram.alerts import AlertManager
from narrative_flow.telegram.websocket_integration import TelegramWebSocketBridge
from narrative_flow.models.db_manager import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramBotRunner:
    """Main runner for the Telegram bot with all integrations."""

    def __init__(self):
        self.bot: Optional[TelegramBot] = None
        self.bridge: Optional[TelegramWebSocketBridge] = None
        self.running = False

    async def initialize(self):
        """Initialize all components."""
        try:
            # Initialize database
            await db_manager.create_all()
            logger.info("✅ Database initialized")

            # Initialize Telegram bot
            self.bot = TelegramBot()
            success = await self.bot.initialize()

            if not success:
                logger.error("Failed to initialize Telegram bot")
                return False

            # Initialize WebSocket bridge
            self.bridge = TelegramWebSocketBridge(
                telegram_bot=self.bot,
                alert_manager=self.bot.alert_manager
            )

            logger.info("✅ All components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def start(self):
        """Start the bot and all integrations."""
        if not await self.initialize():
            logger.error("Cannot start due to initialization failure")
            return

        self.running = True

        try:
            # Start the Telegram bot
            await self.bot.start()

            # Start the WebSocket bridge
            await self.bridge.start()

            logger.info("🚀 NarrativeFlow Telegram Bot is running!")
            logger.info(f"📱 Bot username: @{settings.telegram_bot_token.split(':')[0] if settings.telegram_bot_token else 'not_configured'}")
            logger.info(f"💬 Sending alerts to chat: {settings.telegram_chat_id}")

            # Send startup message
            if self.bot:
                await self.bot.send_custom_message(
                    "🚀 **NarrativeFlow Bot Started**\n\n"
                    "I'm now monitoring narrative rotations and will send alerts for:\n"
                    "• Divergence signals\n"
                    "• Lifecycle transitions\n"
                    "• Major momentum shifts\n\n"
                    "Use /help to see available commands."
                )

            # Keep running until stopped
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error during bot operation: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the bot and all integrations."""
        logger.info("Shutting down NarrativeFlow Telegram Bot...")
        self.running = False

        # Send shutdown message
        if self.bot:
            try:
                await self.bot.send_custom_message(
                    "🛑 **NarrativeFlow Bot Stopping**\n\n"
                    "The bot is shutting down for maintenance.\n"
                    "Alerts will resume when the bot restarts."
                )
            except:
                pass  # Ignore errors during shutdown

        # Stop components
        if self.bridge:
            await self.bridge.stop()

        if self.bot:
            await self.bot.stop()

        logger.info("✅ Shutdown complete")

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.stop())
        sys.exit(0)


def main():
    """Main entry point for the Telegram bot."""
    runner = TelegramBotRunner()

    # Set up signal handlers
    signal.signal(signal.SIGINT, runner.handle_shutdown)
    signal.signal(signal.SIGTERM, runner.handle_shutdown)

    # Run the bot
    try:
        asyncio.run(runner.start())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        logger.info("Bot terminated")


if __name__ == "__main__":
    main()