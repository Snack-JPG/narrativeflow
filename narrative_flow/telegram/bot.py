"""Telegram bot implementation using python-telegram-bot (similar to grammY)."""

import asyncio
from datetime import datetime, time
from typing import Optional, List, Dict

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    JobQueue
)
from telegram.constants import ParseMode

from narrative_flow.config.settings import settings
from narrative_flow.models.database import NarrativeMetrics, DivergenceHistory
from narrative_flow.models.db_manager import db_manager
from narrative_flow.ai.briefing_generator import BriefingGenerator
from narrative_flow.telegram.alerts import AlertManager, Alert, AlertSeverity
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession


class TelegramBot:
    """Telegram bot for NarrativeFlow alerts and commands."""

    def __init__(self):
        self.bot: Optional[Bot] = None
        self.app: Optional[Application] = None
        self.alert_manager = AlertManager()
        self.briefing_generator = BriefingGenerator()
        self.chat_id = settings.telegram_chat_id
        self.running = False

    async def initialize(self):
        """Initialize the bot with token."""
        if not settings.telegram_bot_token:
            print("⚠️ No Telegram bot token configured")
            return False

        if not settings.telegram_chat_id:
            print("⚠️ No Telegram chat ID configured")
            return False

        try:
            # Create bot application
            self.app = Application.builder().token(settings.telegram_bot_token).build()

            # Add command handlers
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("help", self.cmd_help))
            self.app.add_handler(CommandHandler("narrative", self.cmd_narrative))
            self.app.add_handler(CommandHandler("divergence", self.cmd_divergence))
            self.app.add_handler(CommandHandler("briefing", self.cmd_briefing))
            self.app.add_handler(CommandHandler("top", self.cmd_top))
            self.app.add_handler(CommandHandler("lifecycle", self.cmd_lifecycle))

            # Initialize alert manager
            await self.alert_manager.connect()

            # Schedule daily briefing
            self.schedule_daily_briefing()

            print(f"✅ Telegram bot initialized")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize Telegram bot: {e}")
            return False

    def schedule_daily_briefing(self):
        """Schedule daily morning briefing."""
        if not self.app or not self.app.job_queue:
            return

        # Create time for daily briefing
        briefing_time = time(
            hour=settings.telegram_daily_briefing_hour,
            minute=settings.telegram_daily_briefing_minute
        )

        # Schedule daily job
        self.app.job_queue.run_daily(
            self.send_daily_briefing,
            briefing_time,
            name="daily_briefing"
        )

        print(f"📅 Daily briefing scheduled for {briefing_time}")

    async def start(self):
        """Start the bot."""
        if not self.app:
            if not await self.initialize():
                return

        self.running = True

        # Start alert processor
        asyncio.create_task(self.process_alerts())

        # Start polling
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        print("🤖 Telegram bot started")

    async def stop(self):
        """Stop the bot."""
        self.running = False

        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

        await self.alert_manager.disconnect()
        print("🛑 Telegram bot stopped")

    async def process_alerts(self):
        """Process queued alerts."""
        while self.running:
            try:
                # Get alert from queue (with timeout to allow checking running status)
                alert = await asyncio.wait_for(
                    self.alert_manager.alert_queue.get(),
                    timeout=1.0
                )

                # Send alert
                await self.send_alert(alert)

                # Store in history
                await self.alert_manager.store_alert(alert)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error processing alert: {e}")
                await asyncio.sleep(1)

    async def send_alert(self, alert: Alert):
        """Send an alert to Telegram."""
        if not self.app or not self.chat_id:
            return

        try:
            message = alert.format_telegram()
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Error sending Telegram alert: {e}")

    async def send_daily_briefing(self, context: ContextTypes.DEFAULT_TYPE):
        """Send daily morning briefing."""
        try:
            # Generate briefing
            async with db_manager.get_session() as session:
                briefing = await self.briefing_generator.generate_daily_briefing(session)

            if briefing:
                # Format for Telegram
                message = f"☀️ **Good Morning! Here's your NarrativeFlow Daily Briefing**\n\n{briefing}"

                await context.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            print(f"Error sending daily briefing: {e}")

    # Command Handlers

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_message = (
            "🚀 **Welcome to NarrativeFlow Bot!**\n\n"
            "I track crypto narrative rotations and send alerts on:\n"
            "• 📈 Early entry signals\n"
            "• 📉 Exit signals\n"
            "• 🐋 Smart money accumulation\n"
            "• 🔄 Narrative lifecycle transitions\n"
            "• ⚡ Major momentum shifts\n\n"
            "Use /help to see available commands."
        )
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = (
            "📖 **Available Commands:**\n\n"
            "/narrative <name> - Get status of a specific narrative\n"
            "/divergence - Show current divergence signals\n"
            "/briefing - Get latest AI analysis briefing\n"
            "/top - Show top narratives by momentum\n"
            "/lifecycle - Show all narratives with lifecycle stages\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)

    async def cmd_narrative(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /narrative command."""
        if not context.args:
            await update.message.reply_text(
                "Please specify a narrative. Example: /narrative AI",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        narrative = " ".join(context.args).upper()

        async with db_manager.get_session() as session:
            # Get latest metrics for narrative
            result = await session.execute(
                select(NarrativeMetrics)
                .where(NarrativeMetrics.narrative_category == narrative)
                .order_by(desc(NarrativeMetrics.timestamp))
                .limit(1)
            )
            metrics = result.scalar_one_or_none()

            if not metrics:
                await update.message.reply_text(
                    f"No data found for narrative: {narrative}",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Format response
            message = (
                f"📊 **{narrative} Narrative Status**\n\n"
                f"**Lifecycle Stage:** {metrics.lifecycle_stage or 'N/A'}\n"
                f"**Momentum Score:** {metrics.momentum_score or 0:.2f}\n\n"
                f"**24h Changes:**\n"
                f"• Social Buzz: {metrics.acceleration or 0:+.1f}%\n"
                f"• On-chain Activity: {metrics.tvl_change_24h or 0:+.1f}%\n"
                f"• Price Movement: {metrics.avg_price_change_24h or 0:+.1f}%\n\n"
                f"**Current Metrics:**\n"
                f"• Mention Velocity: {metrics.mention_velocity or 0:.0f}/hour\n"
                f"• Sentiment: {metrics.sentiment_avg or 0:.2f}\n"
                f"• TVL: ${(metrics.total_tvl or 0) / 1e9:.2f}B\n"
                f"• Volume (24h): ${(metrics.total_volume_24h or 0) / 1e9:.2f}B\n\n"
                f"_Last updated: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}_"
            )

            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    async def cmd_divergence(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /divergence command."""
        async with db_manager.get_session() as session:
            # Get recent divergence signals
            result = await session.execute(
                select(DivergenceHistory)
                .where(DivergenceHistory.confidence > 0.7)
                .order_by(desc(DivergenceHistory.timestamp))
                .limit(10)
            )
            signals = result.scalars().all()

            if not signals:
                await update.message.reply_text(
                    "No significant divergence signals detected currently.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Format response
            lines = ["🔍 **Current Divergence Signals:**\n"]

            for signal in signals:
                emoji = {
                    "early_entry": "📈",
                    "late_exit": "📉",
                    "accumulation": "🐋",
                    "dead": "💀"
                }.get(signal.divergence_signal, "📊")

                lines.append(
                    f"{emoji} **{signal.narrative}** - {signal.divergence_signal.upper()}\n"
                    f"   Confidence: {signal.confidence:.0%}\n"
                    f"   Social/On-chain/Price: "
                    f"{signal.social_velocity or 0:.1f}/{signal.onchain_activity or 0:.1f}/{signal.price_momentum or 0:.1f}\n"
                )

            message = "\n".join(lines)
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    async def cmd_briefing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /briefing command."""
        try:
            async with db_manager.get_session() as session:
                briefing = await self.briefing_generator.generate_daily_briefing(session)

            if briefing:
                message = f"📰 **Latest Market Briefing**\n\n{briefing}"
            else:
                message = "Unable to generate briefing at this time."

            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(
                "Error generating briefing. Please try again later.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /top command."""
        async with db_manager.get_session() as session:
            # Get top narratives by momentum
            result = await session.execute(
                select(NarrativeMetrics)
                .order_by(desc(NarrativeMetrics.momentum_score))
                .limit(10)
            )
            top_narratives = result.scalars().all()

            if not top_narratives:
                await update.message.reply_text(
                    "No narrative data available.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Format response
            lines = ["🏆 **Top Narratives by Momentum:**\n"]

            for i, metrics in enumerate(top_narratives, 1):
                trend = "📈" if (metrics.avg_price_change_24h or 0) > 0 else "📉"
                lines.append(
                    f"{i}. **{metrics.narrative_category}** - Score: {metrics.momentum_score or 0:.1f}\n"
                    f"    {trend} Price 24h: {metrics.avg_price_change_24h or 0:+.1f}%\n"
                    f"    Social: {metrics.acceleration or 0:+.1f}% | "
                    f"On-chain: {metrics.tvl_change_24h or 0:+.1f}%\n"
                )

            message = "\n".join(lines)
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    async def cmd_lifecycle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /lifecycle command."""
        async with db_manager.get_session() as session:
            # Get all narratives with their lifecycle stages
            result = await session.execute(
                select(NarrativeMetrics)
                .order_by(NarrativeMetrics.narrative)
            )
            all_narratives = result.scalars().all()

            if not all_narratives:
                await update.message.reply_text(
                    "No narrative data available.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Group by lifecycle stage
            stages = {}
            for metrics in all_narratives:
                stage = metrics.lifecycle_stage
                if stage not in stages:
                    stages[stage] = []
                stages[stage].append(metrics.narrative_category)

            # Format response
            lines = ["🔄 **Narrative Lifecycle Stages:**\n"]

            stage_order = ["WHISPER", "EMERGING", "MAINSTREAM", "PEAK_FOMO", "DECLINING", "DEAD"]
            stage_emojis = {
                "WHISPER": "🤫",
                "EMERGING": "🌱",
                "MAINSTREAM": "🚀",
                "PEAK_FOMO": "🔥",
                "DECLINING": "📉",
                "DEAD": "💀"
            }

            for stage in stage_order:
                if stage in stages:
                    emoji = stage_emojis.get(stage, "📊")
                    lines.append(f"\n{emoji} **{stage}:**")
                    for narrative in sorted(stages[stage]):
                        lines.append(f"  • {narrative}")

            message = "\n".join(lines)
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    async def send_custom_message(self, message: str):
        """Send a custom message to the configured chat."""
        if not self.app or not self.chat_id:
            return

        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Error sending custom message: {e}")