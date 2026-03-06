"""Alert management system with severity levels and rate limiting."""

import asyncio
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, List
import redis.asyncio as aioredis
from dataclasses import dataclass

from narrative_flow.config.settings import settings


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure."""
    narrative: str
    message: str
    severity: AlertSeverity
    timestamp: datetime
    data: Optional[Dict] = None

    def format_telegram(self) -> str:
        """Format alert for Telegram message."""
        # Emoji based on severity
        emoji_map = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨"
        }

        emoji = emoji_map[self.severity]

        # Format message
        lines = [
            f"{emoji} **{self.severity.value.upper()} ALERT**",
            f"**Narrative:** {self.narrative}",
            f"**Time:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            self.message
        ]

        # Add data if present
        if self.data:
            lines.append("\n**Details:**")
            for key, value in self.data.items():
                if isinstance(value, float):
                    lines.append(f"• {key}: {value:.2f}")
                else:
                    lines.append(f"• {key}: {value}")

        return "\n".join(lines)


class AlertManager:
    """Manages alert rate limiting and queueing."""

    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.alert_queue: asyncio.Queue = asyncio.Queue()
        self.running = False

    async def connect(self):
        """Connect to Redis for rate limiting."""
        try:
            self.redis_client = await aioredis.from_url(
                settings.redis_url,
                decode_responses=True
            )
            await self.redis_client.ping()
            print("✅ Connected to Redis for alert rate limiting")
        except Exception as e:
            print(f"⚠️ Redis connection failed, rate limiting disabled: {e}")
            self.redis_client = None

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()

    async def can_send_alert(self, narrative: str, severity: AlertSeverity) -> bool:
        """Check if an alert can be sent based on rate limiting."""
        # Critical alerts bypass rate limiting if configured
        if severity == AlertSeverity.CRITICAL and settings.alert_critical_bypass_limit:
            return True

        if not self.redis_client:
            # No Redis, allow all alerts
            return True

        # Create rate limit key
        current_hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
        key = f"alert_limit:{narrative}:{current_hour}"

        try:
            # Get current count
            count = await self.redis_client.get(key)
            if count is None:
                count = 0
            else:
                count = int(count)

            # Check limit
            if count >= settings.alert_max_per_narrative_per_hour:
                return False

            # Increment counter with TTL of 1 hour
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, 3600)  # 1 hour TTL
            await pipe.execute()

            return True

        except Exception as e:
            print(f"Rate limiting error: {e}")
            # On error, allow the alert
            return True

    async def queue_alert(self, alert: Alert) -> bool:
        """Queue an alert for sending."""
        # Check rate limiting
        if not await self.can_send_alert(alert.narrative, alert.severity):
            print(f"Rate limited: {alert.narrative} - {alert.message[:50]}...")
            return False

        # Add to queue
        await self.alert_queue.put(alert)
        return True

    async def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get recent alerts from Redis."""
        if not self.redis_client:
            return []

        alerts = []
        try:
            # Get alerts from the last N hours
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            key_pattern = "alert_history:*"

            # Scan for alert history keys
            cursor = "0"
            while cursor != 0:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor,
                    match=key_pattern,
                    count=100
                )

                for key in keys:
                    alert_data = await self.redis_client.get(key)
                    if alert_data:
                        alert_dict = json.loads(alert_data)
                        timestamp = datetime.fromisoformat(alert_dict["timestamp"])

                        if timestamp > cutoff:
                            alerts.append(Alert(
                                narrative=alert_dict["narrative"],
                                message=alert_dict["message"],
                                severity=AlertSeverity(alert_dict["severity"]),
                                timestamp=timestamp,
                                data=alert_dict.get("data")
                            ))

            # Sort by timestamp
            alerts.sort(key=lambda x: x.timestamp, reverse=True)

        except Exception as e:
            print(f"Error fetching recent alerts: {e}")

        return alerts

    async def store_alert(self, alert: Alert):
        """Store alert in history."""
        if not self.redis_client:
            return

        try:
            # Create unique key with timestamp
            key = f"alert_history:{alert.narrative}:{alert.timestamp.isoformat()}"

            # Store alert data
            alert_data = {
                "narrative": alert.narrative,
                "message": alert.message,
                "severity": alert.severity.value,
                "timestamp": alert.timestamp.isoformat(),
                "data": alert.data
            }

            # Store with 7 day TTL
            await self.redis_client.setex(
                key,
                604800,  # 7 days in seconds
                json.dumps(alert_data)
            )

        except Exception as e:
            print(f"Error storing alert: {e}")

    def create_divergence_alert(
        self,
        narrative: str,
        social_change: float,
        onchain_change: float,
        price_change: float,
        signal_type: str
    ) -> Alert:
        """Create a divergence signal alert."""
        severity = AlertSeverity.INFO

        if signal_type == "EARLY_ENTRY":
            message = f"📈 **Early Entry Signal Detected!**\n{narrative} showing strong momentum with limited price movement"
            severity = AlertSeverity.WARNING
        elif signal_type == "EXIT":
            message = f"📉 **Exit Signal Detected!**\n{narrative} momentum declining while price remains elevated"
            severity = AlertSeverity.WARNING
        elif signal_type == "ACCUMULATION":
            message = f"🐋 **Smart Money Accumulation Detected!**\n{narrative} showing on-chain activity despite low social buzz"
            severity = AlertSeverity.INFO
        else:
            message = f"Signal detected for {narrative}"

        return Alert(
            narrative=narrative,
            message=message,
            severity=severity,
            timestamp=datetime.utcnow(),
            data={
                "social_change_24h": f"{social_change:.1f}%",
                "onchain_change_24h": f"{onchain_change:.1f}%",
                "price_change_24h": f"{price_change:.1f}%",
                "signal_type": signal_type
            }
        )

    def create_lifecycle_alert(
        self,
        narrative: str,
        old_stage: str,
        new_stage: str
    ) -> Alert:
        """Create a lifecycle transition alert."""
        # Determine severity based on transition
        severity = AlertSeverity.INFO

        if new_stage == "EMERGING":
            message = f"🌱 {narrative} narrative entering **Emerging** phase"
            severity = AlertSeverity.WARNING
        elif new_stage == "MAINSTREAM":
            message = f"🚀 {narrative} narrative reaching **Mainstream** adoption"
            severity = AlertSeverity.WARNING
        elif new_stage == "PEAK_FOMO":
            message = f"🔥 {narrative} narrative at **Peak FOMO** - consider exits"
            severity = AlertSeverity.CRITICAL
        elif new_stage == "DECLINING":
            message = f"📉 {narrative} narrative entering **Decline** phase"
            severity = AlertSeverity.WARNING
        else:
            message = f"{narrative} transitioned from {old_stage} to {new_stage}"

        return Alert(
            narrative=narrative,
            message=message,
            severity=severity,
            timestamp=datetime.utcnow(),
            data={
                "previous_stage": old_stage,
                "current_stage": new_stage
            }
        )

    def create_momentum_alert(
        self,
        narrative: str,
        momentum_score: float,
        change_24h: float
    ) -> Alert:
        """Create a major momentum shift alert."""
        severity = AlertSeverity.INFO

        if abs(change_24h) > 100:
            severity = AlertSeverity.CRITICAL
            emoji = "🚨"
        elif abs(change_24h) > 50:
            severity = AlertSeverity.WARNING
            emoji = "⚡"
        else:
            emoji = "📊"

        direction = "surge" if change_24h > 0 else "drop"

        message = f"{emoji} Major momentum {direction} in {narrative} narrative"

        return Alert(
            narrative=narrative,
            message=message,
            severity=severity,
            timestamp=datetime.utcnow(),
            data={
                "momentum_score": momentum_score,
                "change_24h": f"{change_24h:+.1f}%"
            }
        )