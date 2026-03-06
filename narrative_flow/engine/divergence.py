"""Divergence Detection Engine for NarrativeFlow.

This module implements the core divergence detection logic to identify
when narrative momentum diverges from price momentum, signaling potential
trading opportunities.

Core Signals:
1. EARLY ENTRY: Social buzz ↑ + On-chain activity ↑ + Price flat/down
2. LATE/EXIT: Price already pumped + social buzz declining or on-chain flat
3. SMART MONEY ACCUMULATION: Low social buzz + high on-chain activity
4. DEAD NARRATIVE: Everything declining
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
import asyncio

from ..models import (
    NarrativeMetrics,
    MarketData,
    OnChainData,
    EnrichedData,
    VelocitySnapshot
)

logger = logging.getLogger(__name__)


class DivergenceSignal(Enum):
    """Types of divergence signals."""
    EARLY_ENTRY = "early_entry"
    LATE_EXIT = "late_exit"
    ACCUMULATION = "accumulation"
    DEAD = "dead"
    NEUTRAL = "neutral"


class LifecycleStage(Enum):
    """Narrative lifecycle stages."""
    WHISPER = "whisper"
    EMERGING = "emerging"
    MAINSTREAM = "mainstream"
    PEAK = "peak"
    DECLINING = "declining"
    DEAD = "dead"


@dataclass
class NarrativeMomentum:
    """Container for narrative momentum data."""
    narrative: str
    timestamp: datetime

    # Social metrics
    social_velocity: float  # Mentions per hour
    sentiment_strength: float  # Average sentiment score (-1 to 1)
    social_buzz_trend: float  # % change in velocity

    # On-chain metrics
    onchain_activity: float  # TVL + active addresses normalized
    onchain_delta: float  # % change in on-chain activity
    tvl: float
    tvl_change_24h: float

    # Market metrics
    price: float
    price_change_24h: float
    volume_24h: float
    market_cap: float

    # Computed scores
    momentum_score: float  # Composite narrative momentum
    price_momentum: float
    divergence_score: float  # Strength of divergence

    # Classification
    divergence_signal: DivergenceSignal
    lifecycle_stage: LifecycleStage
    confidence: float  # 0-1 confidence in signal


class DivergenceDetector:
    """Main divergence detection engine."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.logger = logger

        # Thresholds for signal detection
        self.SOCIAL_BUZZ_HIGH = 0.3  # 30% increase
        self.SOCIAL_BUZZ_LOW = -0.2  # 20% decrease
        self.ONCHAIN_HIGH = 0.2  # 20% increase
        self.ONCHAIN_LOW = -0.15  # 15% decrease
        self.PRICE_PUMP = 0.5  # 50% price increase
        self.PRICE_FLAT = 0.1  # 10% price movement threshold

    async def analyze_narrative(
        self,
        narrative: str,
        lookback_hours: int = 24
    ) -> Optional[NarrativeMomentum]:
        """Analyze a single narrative for divergence."""
        try:
            now = datetime.utcnow()
            since = now - timedelta(hours=lookback_hours)

            # Gather all data components
            social_data = await self._get_social_metrics(narrative, since)
            onchain_data = await self._get_onchain_metrics(narrative, since)
            market_data = await self._get_market_metrics(narrative, since)

            if not all([social_data, onchain_data, market_data]):
                self.logger.warning(f"Insufficient data for narrative {narrative}")
                return None

            # Calculate momentum scores
            narrative_momentum = self._calculate_narrative_momentum(
                social_data, onchain_data
            )

            price_momentum = self._calculate_price_momentum(market_data)

            # Detect divergence
            divergence_score = narrative_momentum - price_momentum
            divergence_signal = self._classify_divergence(
                social_data, onchain_data, market_data, divergence_score
            )

            # Classify lifecycle stage
            lifecycle_stage = self._classify_lifecycle(
                social_data, onchain_data, market_data
            )

            # Calculate confidence
            confidence = self._calculate_confidence(
                social_data, onchain_data, market_data, divergence_signal
            )

            return NarrativeMomentum(
                narrative=narrative,
                timestamp=now,
                social_velocity=social_data['velocity'],
                sentiment_strength=social_data['sentiment'],
                social_buzz_trend=social_data['trend'],
                onchain_activity=onchain_data['activity'],
                onchain_delta=onchain_data['delta'],
                tvl=onchain_data['tvl'],
                tvl_change_24h=onchain_data['tvl_change'],
                price=market_data['price'],
                price_change_24h=market_data['price_change'],
                volume_24h=market_data['volume'],
                market_cap=market_data['market_cap'],
                momentum_score=narrative_momentum,
                price_momentum=price_momentum,
                divergence_score=divergence_score,
                divergence_signal=divergence_signal,
                lifecycle_stage=lifecycle_stage,
                confidence=confidence
            )

        except Exception as e:
            self.logger.error(f"Error analyzing narrative {narrative}: {e}")
            return None

    async def _get_social_metrics(
        self,
        narrative: str,
        since: datetime
    ) -> Optional[Dict[str, float]]:
        """Get social metrics for a narrative."""
        # Get velocity snapshot
        velocity_query = select(VelocitySnapshot).where(
            and_(
                VelocitySnapshot.narrative_category == narrative,
                VelocitySnapshot.timestamp >= since,
                VelocitySnapshot.time_window == "4h"
            )
        ).order_by(desc(VelocitySnapshot.timestamp)).limit(2)

        result = await self.db.execute(velocity_query)
        snapshots = result.scalars().all()

        if not snapshots:
            return None

        latest = snapshots[0]
        velocity = latest.sentiment_weighted_velocity or latest.mentions_per_hour or 0

        # Calculate trend
        trend = 0
        if len(snapshots) > 1 and snapshots[1].mentions_per_hour > 0:
            trend = (
                (latest.mentions_per_hour - snapshots[1].mentions_per_hour) /
                snapshots[1].mentions_per_hour
            )

        # Get sentiment
        sentiment_query = select(
            func.avg(EnrichedData.sentiment_score)
        ).where(
            and_(
                EnrichedData.primary_narrative == narrative,
                EnrichedData.timestamp >= since
            )
        )

        sentiment_result = await self.db.execute(sentiment_query)
        avg_sentiment = sentiment_result.scalar() or 0

        return {
            'velocity': velocity,
            'sentiment': avg_sentiment,
            'trend': trend,
            'acceleration': latest.acceleration or 0
        }

    async def _get_onchain_metrics(
        self,
        narrative: str,
        since: datetime
    ) -> Optional[Dict[str, float]]:
        """Get on-chain metrics for a narrative."""
        # Get latest TVL data
        tvl_query = select(
            func.sum(OnChainData.tvl).label('total_tvl'),
            func.sum(OnChainData.tvl_change_24h).label('tvl_change'),
            func.avg(OnChainData.active_addresses).label('avg_addresses')
        ).where(
            and_(
                OnChainData.narrative_category == narrative,
                OnChainData.timestamp >= since
            )
        )

        result = await self.db.execute(tvl_query)
        row = result.first()

        if not row or not row.total_tvl:
            return None

        # Normalize activity (TVL in millions + active addresses in thousands)
        activity = (row.total_tvl / 1_000_000) + ((row.avg_addresses or 0) / 1_000)

        # Calculate delta (TVL change as a percentage)
        delta = 0
        if row.total_tvl > 0:
            delta = (row.tvl_change or 0) / row.total_tvl

        return {
            'tvl': row.total_tvl or 0,
            'tvl_change': row.tvl_change or 0,
            'activity': activity,
            'delta': delta,
            'active_addresses': row.avg_addresses or 0
        }

    async def _get_market_metrics(
        self,
        narrative: str,
        since: datetime
    ) -> Optional[Dict[str, float]]:
        """Get market metrics for a narrative."""
        # Get aggregated market data
        market_query = select(
            func.avg(MarketData.price).label('avg_price'),
            func.avg(MarketData.price_change_24h).label('avg_price_change'),
            func.sum(MarketData.volume_24h).label('total_volume'),
            func.sum(MarketData.market_cap).label('total_market_cap')
        ).where(
            and_(
                MarketData.narrative_category == narrative,
                MarketData.timestamp >= since
            )
        )

        result = await self.db.execute(market_query)
        row = result.first()

        if not row or not row.avg_price:
            return None

        return {
            'price': row.avg_price or 0,
            'price_change': row.avg_price_change or 0,
            'volume': row.total_volume or 0,
            'market_cap': row.total_market_cap or 0
        }

    def _calculate_narrative_momentum(
        self,
        social_data: Dict[str, float],
        onchain_data: Dict[str, float]
    ) -> float:
        """Calculate composite narrative momentum score.

        Formula: social_velocity × sentiment_strength × on_chain_delta
        Normalized to 0-100 scale.
        """
        # Normalize components
        velocity_normalized = min(social_data['velocity'] / 100, 2.0)  # Cap at 2x
        sentiment_normalized = (social_data['sentiment'] + 1) / 2  # Convert -1,1 to 0,1
        onchain_normalized = (onchain_data['delta'] + 1) / 2  # Convert -1,1 to 0,1

        # Weight social signals more heavily in early stages
        social_weight = 0.5
        onchain_weight = 0.3
        sentiment_weight = 0.2

        momentum = (
            velocity_normalized * social_weight +
            onchain_normalized * onchain_weight +
            sentiment_normalized * sentiment_weight
        ) * 100

        # Apply acceleration boost
        if social_data['acceleration'] > 50:  # Accelerating rapidly
            momentum *= 1.2

        return min(momentum, 100)  # Cap at 100

    def _calculate_price_momentum(
        self,
        market_data: Dict[str, float]
    ) -> float:
        """Calculate price momentum score.

        Based on price change and volume.
        """
        price_change_pct = market_data['price_change'] / 100  # Convert to decimal

        # Volume-weighted price momentum
        volume_normalized = min(market_data['volume'] / 10_000_000, 1.0)  # $10M cap

        # Price momentum (0-100 scale)
        momentum = (price_change_pct + 1) * 50  # Convert -1,1 to 0,100

        # Boost for high volume
        if volume_normalized > 0.5:
            momentum *= (1 + volume_normalized * 0.2)

        return min(max(momentum, 0), 100)  # Clamp 0-100

    def _classify_divergence(
        self,
        social_data: Dict[str, float],
        onchain_data: Dict[str, float],
        market_data: Dict[str, float],
        divergence_score: float
    ) -> DivergenceSignal:
        """Classify the type of divergence signal."""
        social_trend = social_data['trend']
        onchain_delta = onchain_data['delta']
        price_change = market_data['price_change'] / 100  # Convert to decimal

        # EARLY ENTRY: Social buzz rising + on-chain rising + price flat/down
        if (social_trend > self.SOCIAL_BUZZ_HIGH and
            onchain_delta > self.ONCHAIN_HIGH and
            price_change < self.PRICE_FLAT):
            return DivergenceSignal.EARLY_ENTRY

        # LATE/EXIT: Price pumped + social declining or on-chain flat
        elif (price_change > self.PRICE_PUMP and
              (social_trend < 0 or onchain_delta < self.ONCHAIN_LOW)):
            return DivergenceSignal.LATE_EXIT

        # SMART MONEY ACCUMULATION: Low social + high on-chain
        elif (social_trend < 0 and onchain_delta > self.ONCHAIN_HIGH):
            return DivergenceSignal.ACCUMULATION

        # DEAD NARRATIVE: Everything declining
        elif (social_trend < self.SOCIAL_BUZZ_LOW and
              onchain_delta < self.ONCHAIN_LOW and
              price_change < -self.PRICE_FLAT):
            return DivergenceSignal.DEAD

        # NEUTRAL: No clear signal
        else:
            return DivergenceSignal.NEUTRAL

    def _classify_lifecycle(
        self,
        social_data: Dict[str, float],
        onchain_data: Dict[str, float],
        market_data: Dict[str, float]
    ) -> LifecycleStage:
        """Classify narrative lifecycle stage."""
        velocity = social_data['velocity']
        sentiment = social_data['sentiment']
        tvl = onchain_data['tvl']
        price_change = market_data['price_change'] / 100

        # Whisper: Very low activity, but positive sentiment
        if velocity < 10 and sentiment > 0:
            return LifecycleStage.WHISPER

        # Emerging: Growing activity, positive sentiment, low price movement
        elif velocity < 50 and social_data['trend'] > 0 and price_change < 0.2:
            return LifecycleStage.EMERGING

        # Mainstream: High activity, mixed sentiment, moderate price movement
        elif velocity > 50 and velocity < 200:
            return LifecycleStage.MAINSTREAM

        # Peak: Very high activity, high price movement
        elif velocity > 200 or price_change > 0.5:
            return LifecycleStage.PEAK

        # Declining: Decreasing activity, negative sentiment
        elif social_data['trend'] < -0.2 and sentiment < 0:
            return LifecycleStage.DECLINING

        # Dead: Very low activity, negative sentiment, price declining
        elif velocity < 5 and sentiment < -0.3 and price_change < -0.2:
            return LifecycleStage.DEAD

        # Default to mainstream
        return LifecycleStage.MAINSTREAM

    def _calculate_confidence(
        self,
        social_data: Dict[str, float],
        onchain_data: Dict[str, float],
        market_data: Dict[str, float],
        signal: DivergenceSignal
    ) -> float:
        """Calculate confidence score for the divergence signal (0-1)."""
        confidence = 0.5  # Base confidence

        # Increase confidence for strong signals
        if signal == DivergenceSignal.EARLY_ENTRY:
            # Strong social trend increases confidence
            if social_data['trend'] > 0.5:
                confidence += 0.2
            # Strong on-chain growth increases confidence
            if onchain_data['delta'] > 0.3:
                confidence += 0.15
            # Low price movement increases confidence
            if abs(market_data['price_change']) < 10:
                confidence += 0.15

        elif signal == DivergenceSignal.LATE_EXIT:
            # High price pump increases confidence
            if market_data['price_change'] > 100:
                confidence += 0.25
            # Declining social increases confidence
            if social_data['trend'] < -0.3:
                confidence += 0.25

        elif signal == DivergenceSignal.ACCUMULATION:
            # Strong on-chain activity increases confidence
            if onchain_data['delta'] > 0.4:
                confidence += 0.3
            # Very low social activity increases confidence
            if social_data['velocity'] < 5:
                confidence += 0.2

        elif signal == DivergenceSignal.DEAD:
            # Everything strongly negative increases confidence
            if (social_data['trend'] < -0.5 and
                onchain_data['delta'] < -0.3 and
                market_data['price_change'] < -30):
                confidence += 0.4

        return min(confidence, 1.0)

    async def scan_all_narratives(
        self,
        narratives: List[str],
        lookback_hours: int = 24
    ) -> List[NarrativeMomentum]:
        """Scan all narratives for divergence signals."""
        results = []

        tasks = [
            self.analyze_narrative(narrative, lookback_hours)
            for narrative in narratives
        ]

        momentum_list = await asyncio.gather(*tasks)

        for momentum in momentum_list:
            if momentum:
                results.append(momentum)

        # Sort by divergence score (strongest signals first)
        results.sort(key=lambda x: abs(x.divergence_score), reverse=True)

        return results

    async def get_top_divergences(
        self,
        signal_type: Optional[DivergenceSignal] = None,
        min_confidence: float = 0.6,
        limit: int = 10
    ) -> List[NarrativeMomentum]:
        """Get top divergence signals."""
        from ..config import settings

        # Scan all narratives
        all_signals = await self.scan_all_narratives(
            settings.narrative_categories,
            lookback_hours=24
        )

        # Filter by signal type and confidence
        filtered = []
        for signal in all_signals:
            if signal.confidence >= min_confidence:
                if signal_type is None or signal.divergence_signal == signal_type:
                    filtered.append(signal)

        # Return top results
        return filtered[:limit]