"""Integration between WebSocket divergence alerts and Telegram bot."""

import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime

from narrative_flow.api.websocket import manager as ws_manager
from narrative_flow.telegram.alerts import AlertManager, AlertSeverity, Alert
from narrative_flow.telegram.bot import TelegramBot

logger = logging.getLogger(__name__)


class TelegramWebSocketBridge:
    """Bridges WebSocket divergence alerts to Telegram notifications."""

    def __init__(self, telegram_bot: TelegramBot, alert_manager: AlertManager):
        self.telegram_bot = telegram_bot
        self.alert_manager = alert_manager
        self.running = False
        self.connected_to_ws = False

    async def start(self):
        """Start listening to WebSocket events."""
        self.running = True
        logger.info("Starting Telegram-WebSocket bridge...")

        # Register a custom handler for WebSocket broadcasts
        asyncio.create_task(self._listen_for_alerts())

    async def stop(self):
        """Stop listening to WebSocket events."""
        self.running = False
        logger.info("Stopping Telegram-WebSocket bridge...")

    async def _listen_for_alerts(self):
        """Listen for WebSocket divergence alerts and forward to Telegram."""
        while self.running:
            try:
                # This is a simplified approach - in production, you'd implement
                # a proper message queue or pub/sub system between the WebSocket
                # and Telegram components
                await asyncio.sleep(1)  # Check for new alerts every second

                # The actual implementation would receive alerts from the WebSocket manager
                # For now, we'll integrate directly with the divergence monitor

            except Exception as e:
                logger.error(f"Error in WebSocket bridge: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def handle_divergence_alert(self, alert_data: Dict):
        """Process a divergence alert from WebSocket."""
        try:
            narrative = alert_data.get("narrative", "Unknown")
            signal = alert_data.get("signal", "")
            confidence = alert_data.get("confidence", 0)
            alert_level = alert_data.get("alert_level", "low")

            # Determine severity based on alert level
            if alert_level == "high":
                severity = AlertSeverity.CRITICAL
            elif alert_level == "medium":
                severity = AlertSeverity.WARNING
            else:
                severity = AlertSeverity.INFO

            # Create alert message
            message = self._format_divergence_message(alert_data)

            # Create alert object
            alert = Alert(
                narrative=narrative,
                message=message,
                severity=severity,
                timestamp=datetime.utcnow(),
                data={
                    "signal": signal,
                    "confidence": f"{confidence:.0%}",
                    "momentum_score": alert_data.get("momentum_score", 0),
                    "price_change_24h": f"{alert_data.get('price_change_24h', 0):+.1f}%"
                }
            )

            # Queue alert for sending
            await self.alert_manager.queue_alert(alert)

            logger.info(f"Forwarded divergence alert to Telegram: {narrative} - {signal}")

        except Exception as e:
            logger.error(f"Error handling divergence alert: {e}")

    def _format_divergence_message(self, alert_data: Dict) -> str:
        """Format divergence alert data into a Telegram message."""
        narrative = alert_data.get("narrative", "Unknown")
        signal = alert_data.get("signal", "")
        confidence = alert_data.get("confidence", 0)
        lifecycle = alert_data.get("lifecycle", "")
        momentum_score = alert_data.get("momentum_score", 0)
        price_change = alert_data.get("price_change_24h", 0)

        # Signal-specific messages
        if signal == "EARLY_ENTRY":
            title = f"📈 Early Entry Opportunity: {narrative}"
            description = (
                f"Strong social and on-chain momentum detected with limited price movement.\n"
                f"This could be an early entry opportunity."
            )
        elif signal == "LATE_EXIT":
            title = f"📉 Exit Signal: {narrative}"
            description = (
                f"Price has moved significantly while momentum is declining.\n"
                f"Consider taking profits or reducing exposure."
            )
        elif signal == "ACCUMULATION":
            title = f"🐋 Smart Money Accumulation: {narrative}"
            description = (
                f"On-chain activity increasing despite low social buzz.\n"
                f"Smart money may be quietly accumulating."
            )
        elif signal == "DEAD":
            title = f"💀 Dead Narrative: {narrative}"
            description = (
                f"Both social and on-chain momentum declining significantly.\n"
                f"This narrative appears to be losing steam."
            )
        else:
            title = f"📊 Signal Detected: {narrative}"
            description = f"A {signal} signal has been detected."

        # Build complete message
        message = (
            f"**{title}**\n\n"
            f"{description}\n\n"
            f"**Metrics:**\n"
            f"• Confidence: {confidence:.0%}\n"
            f"• Lifecycle Stage: {lifecycle}\n"
            f"• Momentum Score: {momentum_score:.1f}\n"
            f"• Price Change (24h): {price_change:+.1f}%"
        )

        return message

    async def handle_lifecycle_transition(self, transition_data: Dict):
        """Process a lifecycle transition alert."""
        try:
            narrative = transition_data.get("narrative", "Unknown")
            old_stage = transition_data.get("old_stage", "")
            new_stage = transition_data.get("new_stage", "")

            # Create lifecycle alert
            alert = self.alert_manager.create_lifecycle_alert(
                narrative=narrative,
                old_stage=old_stage,
                new_stage=new_stage
            )

            # Queue alert for sending
            await self.alert_manager.queue_alert(alert)

            logger.info(f"Forwarded lifecycle transition to Telegram: {narrative} -> {new_stage}")

        except Exception as e:
            logger.error(f"Error handling lifecycle transition: {e}")

    async def handle_momentum_shift(self, momentum_data: Dict):
        """Process a momentum shift alert."""
        try:
            narrative = momentum_data.get("narrative", "Unknown")
            momentum_score = momentum_data.get("momentum_score", 0)
            change_24h = momentum_data.get("change_24h", 0)

            # Only alert on significant momentum shifts
            if abs(change_24h) < 30:
                return

            # Create momentum alert
            alert = self.alert_manager.create_momentum_alert(
                narrative=narrative,
                momentum_score=momentum_score,
                change_24h=change_24h
            )

            # Queue alert for sending
            await self.alert_manager.queue_alert(alert)

            logger.info(f"Forwarded momentum shift to Telegram: {narrative} {change_24h:+.1f}%")

        except Exception as e:
            logger.error(f"Error handling momentum shift: {e}")


# Enhanced WebSocket manager integration
class EnhancedDivergenceMonitor:
    """Enhanced divergence monitor that sends alerts to both WebSocket and Telegram."""

    def __init__(self, telegram_bridge: Optional[TelegramWebSocketBridge] = None):
        self.telegram_bridge = telegram_bridge
        self.last_lifecycle_stages: Dict[str, str] = {}
        self.last_momentum_scores: Dict[str, float] = {}

    async def process_signal(self, signal_data: Dict):
        """Process a divergence signal and send appropriate alerts."""
        # Send to WebSocket clients
        await ws_manager.broadcast_filtered(signal_data, "divergence_alert")

        # Send to Telegram if bridge is available
        if self.telegram_bridge:
            await self.telegram_bridge.handle_divergence_alert(signal_data)

        # Check for lifecycle transitions
        narrative = signal_data.get("narrative")
        lifecycle = signal_data.get("lifecycle")

        if narrative and lifecycle:
            old_stage = self.last_lifecycle_stages.get(narrative)
            if old_stage and old_stage != lifecycle:
                transition_data = {
                    "narrative": narrative,
                    "old_stage": old_stage,
                    "new_stage": lifecycle
                }

                if self.telegram_bridge:
                    await self.telegram_bridge.handle_lifecycle_transition(transition_data)

            self.last_lifecycle_stages[narrative] = lifecycle

        # Check for major momentum shifts
        momentum_score = signal_data.get("momentum_score", 0)

        if narrative and momentum_score:
            last_score = self.last_momentum_scores.get(narrative, momentum_score)
            change = ((momentum_score - last_score) / max(last_score, 0.1)) * 100

            if abs(change) > 30:  # 30% change threshold
                momentum_data = {
                    "narrative": narrative,
                    "momentum_score": momentum_score,
                    "change_24h": change
                }

                if self.telegram_bridge:
                    await self.telegram_bridge.handle_momentum_shift(momentum_data)

            self.last_momentum_scores[narrative] = momentum_score