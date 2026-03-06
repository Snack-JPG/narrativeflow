"""WebSocket endpoints for real-time divergence alerts."""

import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from ..engine import DivergenceDetector, DivergenceTracker, DivergenceSignal
from ..models import get_db
from ..config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriber_preferences: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        self.subscriber_preferences.pop(websocket, None)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """Broadcast a message to all connected WebSockets."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.add(connection)

        # Clean up disconnected sockets
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_filtered(self, data: Dict, message_type: str):
        """Broadcast to connections based on their preferences."""
        message = json.dumps({
            "type": message_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })

        disconnected = set()
        for connection, prefs in self.subscriber_preferences.items():
            try:
                # Check if this message matches preferences
                if self._matches_preferences(data, prefs, message_type):
                    await connection.send_text(message)
            except:
                disconnected.add(connection)

        # Clean up disconnected sockets
        for conn in disconnected:
            self.disconnect(conn)

    def _matches_preferences(self, data: Dict, prefs: Dict, message_type: str) -> bool:
        """Check if data matches subscriber preferences."""
        if not prefs:
            return True  # No filters, send everything

        # Check signal type filter
        if "signal_types" in prefs:
            signal = data.get("signal")
            if signal and signal not in prefs["signal_types"]:
                return False

        # Check minimum confidence
        if "min_confidence" in prefs:
            confidence = data.get("confidence", 0)
            if confidence < prefs["min_confidence"]:
                return False

        # Check narrative filter
        if "narratives" in prefs:
            narrative = data.get("narrative")
            if narrative and narrative not in prefs["narratives"]:
                return False

        # Check message type filter
        if "message_types" in prefs:
            if message_type not in prefs["message_types"]:
                return False

        return True

    def set_preferences(self, websocket: WebSocket, preferences: Dict):
        """Set filtering preferences for a connection."""
        self.subscriber_preferences[websocket] = preferences
        logger.info(f"Updated preferences for WebSocket: {preferences}")


# Global connection manager
manager = ConnectionManager()


class DivergenceMonitor:
    """Monitors for divergence signals and sends alerts."""

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.running = False
        self.check_interval = 60  # Check every minute
        self.last_signals: Dict[str, datetime] = {}

    async def start(self):
        """Start monitoring for divergences."""
        self.running = True
        logger.info("Starting divergence monitor...")

        while self.running:
            try:
                async with self.db_session_factory() as db:
                    await self._check_divergences(db)
            except Exception as e:
                logger.error(f"Error in divergence monitor: {e}")

            await asyncio.sleep(self.check_interval)

    async def stop(self):
        """Stop monitoring."""
        self.running = False
        logger.info("Stopping divergence monitor...")

    async def _check_divergences(self, db: AsyncSession):
        """Check for new divergence signals."""
        detector = DivergenceDetector(db)
        tracker = DivergenceTracker(db)

        # Get top divergences
        signals = await detector.get_top_divergences(
            min_confidence=0.6,
            limit=10
        )

        for signal in signals:
            # Create unique key for this signal
            signal_key = f"{signal.narrative}_{signal.divergence_signal.value}"

            # Check if we've already alerted on this recently (within 1 hour)
            if signal_key in self.last_signals:
                last_alert = self.last_signals[signal_key]
                if datetime.utcnow() - last_alert < timedelta(hours=1):
                    continue

            # Record signal to history
            await tracker.record_divergence(signal)

            # Prepare alert data
            alert_data = {
                "narrative": signal.narrative,
                "signal": signal.divergence_signal.value,
                "lifecycle": signal.lifecycle_stage.value,
                "confidence": signal.confidence,
                "momentum_score": signal.momentum_score,
                "divergence_score": signal.divergence_score,
                "sentiment": signal.sentiment_strength,
                "social_velocity": signal.social_velocity,
                "tvl": signal.tvl,
                "price": signal.price,
                "price_change_24h": signal.price_change_24h,
                "alert_level": self._get_alert_level(signal)
            }

            # Broadcast alert
            await manager.broadcast_filtered(alert_data, "divergence_alert")

            # Update last signal time
            self.last_signals[signal_key] = datetime.utcnow()

            logger.info(
                f"Divergence alert: {signal.narrative} - "
                f"{signal.divergence_signal.value} "
                f"(confidence: {signal.confidence:.2f})"
            )

    def _get_alert_level(self, signal) -> str:
        """Determine alert level based on signal characteristics."""
        if signal.divergence_signal == DivergenceSignal.EARLY_ENTRY and signal.confidence > 0.8:
            return "high"
        elif signal.divergence_signal == DivergenceSignal.ACCUMULATION and signal.confidence > 0.7:
            return "medium"
        elif signal.divergence_signal == DivergenceSignal.LATE_EXIT and signal.confidence > 0.8:
            return "high"
        else:
            return "low"


# Global divergence monitor
monitor: Optional[DivergenceMonitor] = None


async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time divergence alerts."""
    await manager.connect(websocket)

    try:
        # Send initial connection message
        await manager.send_personal_message(
            json.dumps({
                "type": "connection",
                "message": "Connected to NarrativeFlow divergence alerts",
                "timestamp": datetime.utcnow().isoformat()
            }),
            websocket
        )

        # Listen for client messages (preferences, commands)
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "subscribe":
                # Set subscription preferences
                preferences = message.get("preferences", {})
                manager.set_preferences(websocket, preferences)

                await manager.send_personal_message(
                    json.dumps({
                        "type": "subscription",
                        "message": "Preferences updated",
                        "preferences": preferences,
                        "timestamp": datetime.utcnow().isoformat()
                    }),
                    websocket
                )

            elif message.get("type") == "ping":
                # Respond to ping
                await manager.send_personal_message(
                    json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }),
                    websocket
                )

            elif message.get("type") == "request_current":
                # Send current top divergences
                async with get_db() as db:
                    detector = DivergenceDetector(db)
                    signals = await detector.get_top_divergences(
                        min_confidence=0.5,
                        limit=5
                    )

                    for signal in signals:
                        alert_data = {
                            "narrative": signal.narrative,
                            "signal": signal.divergence_signal.value,
                            "lifecycle": signal.lifecycle_stage.value,
                            "confidence": signal.confidence,
                            "momentum_score": signal.momentum_score,
                            "divergence_score": signal.divergence_score
                        }

                        await manager.send_personal_message(
                            json.dumps({
                                "type": "current_signal",
                                "data": alert_data,
                                "timestamp": datetime.utcnow().isoformat()
                            }),
                            websocket
                        )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


def start_monitor(db_session_factory):
    """Start the divergence monitor in the background."""
    global monitor
    if monitor is None:
        monitor = DivergenceMonitor(db_session_factory)
        asyncio.create_task(monitor.start())
        logger.info("Divergence monitor started")


def stop_monitor():
    """Stop the divergence monitor."""
    global monitor
    if monitor:
        asyncio.create_task(monitor.stop())
        monitor = None
        logger.info("Divergence monitor stopped")