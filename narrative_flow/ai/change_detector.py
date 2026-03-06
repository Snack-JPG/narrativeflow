"""Detect changes in narrative momentum and market conditions."""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class NarrativeChange:
    """Represents a change in narrative state."""
    narrative: str
    change_type: str  # momentum_shift, regime_change, new_emergence, sentiment_flip
    previous_state: Any
    current_state: Any
    change_magnitude: float  # 0-1 scale
    confidence: float  # 0-1 scale
    timestamp: datetime
    description: str


class ChangeDetector:
    """Detect and analyze changes in narrative dynamics."""

    def __init__(self, sensitivity: float = 0.3):
        """Initialize change detector.

        Args:
            sensitivity: Threshold for detecting changes (0-1).
                        Lower = more sensitive to small changes
        """
        self.sensitivity = sensitivity

    async def detect_changes(
        self,
        current_data: Dict[str, Any],
        historical_data: List[Dict[str, Any]],
        lookback_hours: int = 24
    ) -> List[NarrativeChange]:
        """Detect all narrative changes from historical comparison.

        Args:
            current_data: Current narrative metrics
            historical_data: List of historical data points
            lookback_hours: Hours to look back for comparison

        Returns:
            List of detected narrative changes
        """
        changes = []

        # Get comparison period data
        comparison_data = self._get_comparison_data(historical_data, lookback_hours)
        if not comparison_data:
            logger.warning("No historical data available for comparison")
            return changes

        # Detect momentum shifts
        momentum_changes = await self._detect_momentum_shifts(
            current_data, comparison_data
        )
        changes.extend(momentum_changes)

        # Detect regime changes
        regime_changes = await self._detect_regime_changes(
            current_data, comparison_data
        )
        changes.extend(regime_changes)

        # Detect new narrative emergences
        new_narratives = await self._detect_new_narratives(
            current_data, comparison_data
        )
        changes.extend(new_narratives)

        # Detect sentiment flips
        sentiment_changes = await self._detect_sentiment_flips(
            current_data, comparison_data
        )
        changes.extend(sentiment_changes)

        # Sort by change magnitude
        changes.sort(key=lambda x: x.change_magnitude, reverse=True)

        logger.info(f"Detected {len(changes)} narrative changes")
        return changes

    async def detect_daily_changes(
        self,
        today_data: Dict[str, Any],
        yesterday_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect what's new today vs yesterday.

        Args:
            today_data: Today's narrative data
            yesterday_data: Yesterday's narrative data

        Returns:
            Structured daily changes report
        """
        changes = {
            "new_narratives": [],
            "momentum_gainers": [],
            "momentum_losers": [],
            "sentiment_flips": [],
            "volume_spikes": [],
            "new_catalysts": [],
            "regime_transitions": []
        }

        # Compare narrative presence
        today_narratives = set(today_data.get("narratives", {}).keys())
        yesterday_narratives = set(yesterday_data.get("narratives", {}).keys())

        # New narratives that appeared today
        changes["new_narratives"] = list(today_narratives - yesterday_narratives)

        # Analyze each narrative
        for narrative in today_narratives & yesterday_narratives:
            today_metrics = today_data["narratives"].get(narrative, {})
            yesterday_metrics = yesterday_data["narratives"].get(narrative, {})

            # Calculate momentum change
            momentum_change = self._calculate_momentum_change(
                today_metrics, yesterday_metrics
            )

            if momentum_change > self.sensitivity:
                changes["momentum_gainers"].append({
                    "narrative": narrative,
                    "change": momentum_change,
                    "current_momentum": today_metrics.get("momentum", 0),
                    "description": self._describe_momentum_change(
                        narrative, momentum_change, "gain"
                    )
                })
            elif momentum_change < -self.sensitivity:
                changes["momentum_losers"].append({
                    "narrative": narrative,
                    "change": abs(momentum_change),
                    "current_momentum": today_metrics.get("momentum", 0),
                    "description": self._describe_momentum_change(
                        narrative, abs(momentum_change), "loss"
                    )
                })

            # Check sentiment flip
            sentiment_flip = self._check_sentiment_flip(
                today_metrics, yesterday_metrics
            )
            if sentiment_flip:
                changes["sentiment_flips"].append(sentiment_flip)

            # Check volume spike
            volume_spike = self._check_volume_spike(
                today_metrics, yesterday_metrics
            )
            if volume_spike:
                changes["volume_spikes"].append(volume_spike)

            # Check regime transition
            regime_transition = self._check_regime_transition(
                narrative, today_metrics, yesterday_metrics
            )
            if regime_transition:
                changes["regime_transitions"].append(regime_transition)

        # Detect new catalysts
        changes["new_catalysts"] = self._detect_catalyst_changes(
            today_data, yesterday_data
        )

        return changes

    async def _detect_momentum_shifts(
        self,
        current_data: Dict[str, Any],
        historical_data: List[Dict[str, Any]]
    ) -> List[NarrativeChange]:
        """Detect significant momentum shifts."""
        changes = []

        for narrative, current_metrics in current_data.get("narratives", {}).items():
            # Get historical momentum
            historical_momentum = self._extract_historical_metric(
                historical_data, narrative, "momentum"
            )

            if not historical_momentum:
                continue

            current_momentum = current_metrics.get("momentum", 0)
            avg_historical = np.mean(historical_momentum)
            std_historical = np.std(historical_momentum) if len(historical_momentum) > 1 else 0

            # Check if current momentum is significantly different
            if std_historical > 0:
                z_score = (current_momentum - avg_historical) / std_historical

                if abs(z_score) > 2:  # 2 standard deviations
                    change_type = "momentum_surge" if z_score > 0 else "momentum_collapse"
                    changes.append(NarrativeChange(
                        narrative=narrative,
                        change_type=change_type,
                        previous_state=avg_historical,
                        current_state=current_momentum,
                        change_magnitude=min(abs(z_score) / 4, 1.0),  # Normalize to 0-1
                        confidence=min(0.5 + abs(z_score) * 0.1, 1.0),
                        timestamp=datetime.utcnow(),
                        description=f"{narrative} momentum {'surged' if z_score > 0 else 'collapsed'} "
                                  f"by {abs(z_score):.1f} standard deviations"
                    ))

        return changes

    async def _detect_regime_changes(
        self,
        current_data: Dict[str, Any],
        historical_data: List[Dict[str, Any]]
    ) -> List[NarrativeChange]:
        """Detect narrative lifecycle regime changes."""
        changes = []
        regime_sequence = [
            "whisper", "emerging", "mainstream", "peak", "declining", "dead"
        ]

        for narrative, current_metrics in current_data.get("narratives", {}).items():
            current_regime = current_metrics.get("regime", "unknown")

            # Get most recent historical regime
            for hist_point in reversed(historical_data):
                hist_regime = hist_point.get("narratives", {}).get(narrative, {}).get("regime")
                if hist_regime and hist_regime != current_regime:
                    # Regime has changed
                    try:
                        prev_idx = regime_sequence.index(hist_regime)
                        curr_idx = regime_sequence.index(current_regime)
                        progression = curr_idx - prev_idx

                        change_magnitude = abs(progression) / len(regime_sequence)
                        change_type = "regime_progression" if progression > 0 else "regime_regression"

                        changes.append(NarrativeChange(
                            narrative=narrative,
                            change_type=change_type,
                            previous_state=hist_regime,
                            current_state=current_regime,
                            change_magnitude=change_magnitude,
                            confidence=0.8,
                            timestamp=datetime.utcnow(),
                            description=f"{narrative} moved from {hist_regime} to {current_regime} phase"
                        ))
                    except ValueError:
                        # Unknown regime in sequence
                        pass
                    break

        return changes

    async def _detect_new_narratives(
        self,
        current_data: Dict[str, Any],
        historical_data: List[Dict[str, Any]]
    ) -> List[NarrativeChange]:
        """Detect newly emerging narratives."""
        changes = []

        # Get all historical narratives
        historical_narratives = set()
        for hist_point in historical_data:
            historical_narratives.update(hist_point.get("narratives", {}).keys())

        # Check for new narratives
        current_narratives = set(current_data.get("narratives", {}).keys())
        new_narratives = current_narratives - historical_narratives

        for narrative in new_narratives:
            metrics = current_data["narratives"][narrative]
            changes.append(NarrativeChange(
                narrative=narrative,
                change_type="new_emergence",
                previous_state=None,
                current_state=metrics,
                change_magnitude=metrics.get("momentum", 0.5),
                confidence=0.9,
                timestamp=datetime.utcnow(),
                description=f"New narrative detected: {narrative} with momentum {metrics.get('momentum', 0):.2f}"
            ))

        return changes

    async def _detect_sentiment_flips(
        self,
        current_data: Dict[str, Any],
        historical_data: List[Dict[str, Any]]
    ) -> List[NarrativeChange]:
        """Detect sentiment polarity flips."""
        changes = []

        for narrative, current_metrics in current_data.get("narratives", {}).items():
            current_sentiment = current_metrics.get("sentiment", 0)

            # Get historical sentiment
            historical_sentiment = self._extract_historical_metric(
                historical_data, narrative, "sentiment"
            )

            if historical_sentiment:
                avg_historical = np.mean(historical_sentiment)

                # Check for polarity flip
                if (current_sentiment > 0 > avg_historical) or (current_sentiment < 0 < avg_historical):
                    change_magnitude = abs(current_sentiment - avg_historical)
                    changes.append(NarrativeChange(
                        narrative=narrative,
                        change_type="sentiment_flip",
                        previous_state=avg_historical,
                        current_state=current_sentiment,
                        change_magnitude=min(change_magnitude, 1.0),
                        confidence=0.7,
                        timestamp=datetime.utcnow(),
                        description=f"{narrative} sentiment flipped from "
                                  f"{'positive' if avg_historical > 0 else 'negative'} to "
                                  f"{'positive' if current_sentiment > 0 else 'negative'}"
                    ))

        return changes

    def _get_comparison_data(
        self,
        historical_data: List[Dict[str, Any]],
        lookback_hours: int
    ) -> List[Dict[str, Any]]:
        """Get historical data within lookback window."""
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        comparison_data = []

        for data_point in historical_data:
            timestamp = data_point.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)

            if timestamp and timestamp >= cutoff_time:
                comparison_data.append(data_point)

        return comparison_data

    def _extract_historical_metric(
        self,
        historical_data: List[Dict[str, Any]],
        narrative: str,
        metric: str
    ) -> List[float]:
        """Extract historical values for a specific metric."""
        values = []
        for data_point in historical_data:
            narrative_data = data_point.get("narratives", {}).get(narrative, {})
            if metric in narrative_data:
                values.append(narrative_data[metric])
        return values

    def _calculate_momentum_change(
        self,
        today_metrics: Dict[str, Any],
        yesterday_metrics: Dict[str, Any]
    ) -> float:
        """Calculate momentum change between two periods."""
        today_momentum = today_metrics.get("momentum", 0)
        yesterday_momentum = yesterday_metrics.get("momentum", 0)

        if yesterday_momentum == 0:
            return today_momentum
        else:
            return (today_momentum - yesterday_momentum) / abs(yesterday_momentum)

    def _check_sentiment_flip(
        self,
        today_metrics: Dict[str, Any],
        yesterday_metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if sentiment has flipped polarity."""
        today_sentiment = today_metrics.get("sentiment", 0)
        yesterday_sentiment = yesterday_metrics.get("sentiment", 0)

        if (today_sentiment > 0 > yesterday_sentiment) or (today_sentiment < 0 < yesterday_sentiment):
            return {
                "from": "positive" if yesterday_sentiment > 0 else "negative",
                "to": "positive" if today_sentiment > 0 else "negative",
                "magnitude": abs(today_sentiment - yesterday_sentiment)
            }
        return None

    def _check_volume_spike(
        self,
        today_metrics: Dict[str, Any],
        yesterday_metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for volume spikes."""
        today_volume = today_metrics.get("volume", 0)
        yesterday_volume = yesterday_metrics.get("volume", 0)

        if yesterday_volume > 0:
            spike_ratio = today_volume / yesterday_volume
            if spike_ratio > 2:  # 2x volume spike
                return {
                    "ratio": spike_ratio,
                    "current_volume": today_volume,
                    "description": f"Volume spiked {spike_ratio:.1f}x"
                }
        return None

    def _check_regime_transition(
        self,
        narrative: str,
        today_metrics: Dict[str, Any],
        yesterday_metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for lifecycle regime transitions."""
        today_regime = today_metrics.get("regime")
        yesterday_regime = yesterday_metrics.get("regime")

        if today_regime and yesterday_regime and today_regime != yesterday_regime:
            return {
                "narrative": narrative,
                "from": yesterday_regime,
                "to": today_regime,
                "timestamp": datetime.utcnow().isoformat()
            }
        return None

    def _detect_catalyst_changes(
        self,
        today_data: Dict[str, Any],
        yesterday_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect new catalysts between periods."""
        today_catalysts = set(today_data.get("catalysts", []))
        yesterday_catalysts = set(yesterday_data.get("catalysts", []))

        new_catalysts = []
        for catalyst in today_catalysts - yesterday_catalysts:
            new_catalysts.append({
                "event": catalyst,
                "timestamp": datetime.utcnow().isoformat(),
                "is_new": True
            })

        return new_catalysts

    def _describe_momentum_change(
        self,
        narrative: str,
        change_magnitude: float,
        direction: str
    ) -> str:
        """Generate human-readable momentum change description."""
        intensity = "slightly" if change_magnitude < 0.5 else "significantly" if change_magnitude < 1 else "dramatically"
        action = "gained" if direction == "gain" else "lost"
        return f"{narrative} {intensity} {action} momentum ({change_magnitude:.1%} change)"