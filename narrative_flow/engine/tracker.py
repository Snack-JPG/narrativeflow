"""Historical Divergence Tracker for NarrativeFlow.

This module tracks and stores divergence signals for historical analysis
and backtesting.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from ..models import DivergenceHistory, MarketData
from .divergence import NarrativeMomentum, DivergenceSignal

logger = logging.getLogger(__name__)


class DivergenceTracker:
    """Tracks and stores historical divergence signals."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.logger = logger

    async def record_divergence(
        self,
        momentum: NarrativeMomentum
    ) -> DivergenceHistory:
        """Record a divergence signal to history."""
        history = DivergenceHistory(
            timestamp=momentum.timestamp,
            narrative=momentum.narrative,
            # Social metrics
            social_velocity=momentum.social_velocity,
            sentiment_strength=momentum.sentiment_strength,
            social_buzz_trend=momentum.social_buzz_trend,
            # On-chain metrics
            onchain_activity=momentum.onchain_activity,
            onchain_delta=momentum.onchain_delta,
            tvl=momentum.tvl,
            tvl_change_24h=momentum.tvl_change_24h,
            # Market metrics
            price=momentum.price,
            price_change_24h=momentum.price_change_24h,
            volume_24h=momentum.volume_24h,
            market_cap=momentum.market_cap,
            # Computed scores
            momentum_score=momentum.momentum_score,
            price_momentum=momentum.price_momentum,
            divergence_score=momentum.divergence_score,
            # Classifications
            divergence_signal=momentum.divergence_signal.value,
            lifecycle_stage=momentum.lifecycle_stage.value,
            confidence=momentum.confidence
        )

        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)

        self.logger.info(
            f"Recorded {momentum.divergence_signal.value} signal for {momentum.narrative} "
            f"with confidence {momentum.confidence:.2f}"
        )

        return history

    async def record_multiple(
        self,
        momentum_list: List[NarrativeMomentum]
    ) -> List[DivergenceHistory]:
        """Record multiple divergence signals."""
        histories = []

        for momentum in momentum_list:
            # Only record significant signals
            if (momentum.divergence_signal != DivergenceSignal.NEUTRAL and
                momentum.confidence >= 0.5):
                history = await self.record_divergence(momentum)
                histories.append(history)

        return histories

    async def update_outcomes(
        self,
        lookback_days: int = 30
    ) -> int:
        """Update historical signals with actual outcomes for backtesting."""
        updated_count = 0

        # Get signals that need outcome updates
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        cutoff_7d = datetime.utcnow() - timedelta(days=7)
        since = datetime.utcnow() - timedelta(days=lookback_days)

        # Query signals without outcomes
        query = select(DivergenceHistory).where(
            and_(
                DivergenceHistory.timestamp >= since,
                DivergenceHistory.price_after_24h.is_(None)
            )
        )

        result = await self.db.execute(query)
        signals = result.scalars().all()

        for signal in signals:
            try:
                # Update 24h outcome if enough time has passed
                if signal.timestamp <= cutoff_24h and signal.price_after_24h is None:
                    price_24h = await self._get_price_at_time(
                        signal.narrative,
                        signal.timestamp + timedelta(hours=24)
                    )
                    if price_24h:
                        signal.price_after_24h = price_24h

                # Update 7d outcome if enough time has passed
                if signal.timestamp <= cutoff_7d and signal.price_after_7d is None:
                    price_7d = await self._get_price_at_time(
                        signal.narrative,
                        signal.timestamp + timedelta(days=7)
                    )
                    if price_7d:
                        signal.price_after_7d = price_7d

                # Calculate success and return
                if signal.price_after_24h and signal.price:
                    return_24h = (signal.price_after_24h - signal.price) / signal.price

                    # Define success based on signal type
                    if signal.divergence_signal == "early_entry":
                        signal.signal_success = return_24h > 0.05  # 5% gain
                        signal.return_pct = return_24h * 100
                    elif signal.divergence_signal == "late_exit":
                        signal.signal_success = return_24h < 0  # Price went down
                        signal.return_pct = -return_24h * 100  # Profit from exit
                    elif signal.divergence_signal == "accumulation":
                        # Check 7d for accumulation signals
                        if signal.price_after_7d:
                            return_7d = (signal.price_after_7d - signal.price) / signal.price
                            signal.signal_success = return_7d > 0.10  # 10% gain in 7d
                            signal.return_pct = return_7d * 100

                    updated_count += 1

            except Exception as e:
                self.logger.error(f"Error updating outcome for signal {signal.id}: {e}")
                continue

        await self.db.commit()
        self.logger.info(f"Updated outcomes for {updated_count} signals")

        return updated_count

    async def _get_price_at_time(
        self,
        narrative: str,
        target_time: datetime
    ) -> Optional[float]:
        """Get the average price for a narrative at a specific time."""
        # Allow 1 hour window
        time_window_start = target_time - timedelta(hours=1)
        time_window_end = target_time + timedelta(hours=1)

        query = select(
            func.avg(MarketData.price)
        ).where(
            and_(
                MarketData.narrative_category == narrative,
                MarketData.timestamp >= time_window_start,
                MarketData.timestamp <= time_window_end
            )
        )

        result = await self.db.execute(query)
        avg_price = result.scalar()

        return avg_price

    async def get_signal_performance(
        self,
        signal_type: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics for historical signals."""
        since = datetime.utcnow() - timedelta(days=days_back)

        query = select(DivergenceHistory).where(
            and_(
                DivergenceHistory.timestamp >= since,
                DivergenceHistory.signal_success.isnot(None)
            )
        )

        if signal_type:
            query = query.where(DivergenceHistory.divergence_signal == signal_type)

        result = await self.db.execute(query)
        signals = result.scalars().all()

        if not signals:
            return {
                "message": "No signals with outcomes available",
                "period_days": days_back
            }

        # Calculate metrics
        total_signals = len(signals)
        successful_signals = sum(1 for s in signals if s.signal_success)
        win_rate = (successful_signals / total_signals) * 100

        avg_return = sum(s.return_pct for s in signals if s.return_pct) / total_signals
        positive_returns = [s.return_pct for s in signals if s.return_pct and s.return_pct > 0]
        negative_returns = [s.return_pct for s in signals if s.return_pct and s.return_pct < 0]

        avg_win = sum(positive_returns) / len(positive_returns) if positive_returns else 0
        avg_loss = sum(negative_returns) / len(negative_returns) if negative_returns else 0

        # Group by signal type
        signal_breakdown = {}
        for signal_type in ["early_entry", "late_exit", "accumulation", "dead"]:
            type_signals = [s for s in signals if s.divergence_signal == signal_type]
            if type_signals:
                type_successful = sum(1 for s in type_signals if s.signal_success)
                signal_breakdown[signal_type] = {
                    "count": len(type_signals),
                    "win_rate": (type_successful / len(type_signals)) * 100,
                    "avg_return": sum(s.return_pct for s in type_signals if s.return_pct) / len(type_signals)
                }

        return {
            "period_days": days_back,
            "total_signals": total_signals,
            "successful_signals": successful_signals,
            "win_rate": win_rate,
            "avg_return": avg_return,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "signal_breakdown": signal_breakdown,
            "best_performing_signal": max(
                signal_breakdown.items(),
                key=lambda x: x[1]["win_rate"]
            )[0] if signal_breakdown else None
        }

    async def get_recent_signals(
        self,
        hours: int = 24,
        signal_type: Optional[str] = None,
        min_confidence: float = 0.6
    ) -> List[Dict[str, Any]]:
        """Get recent divergence signals."""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = select(DivergenceHistory).where(
            and_(
                DivergenceHistory.timestamp >= since,
                DivergenceHistory.confidence >= min_confidence
            )
        )

        if signal_type:
            query = query.where(DivergenceHistory.divergence_signal == signal_type)

        query = query.order_by(desc(DivergenceHistory.timestamp))

        result = await self.db.execute(query)
        signals = result.scalars().all()

        return [
            {
                "id": signal.id,
                "timestamp": signal.timestamp.isoformat(),
                "narrative": signal.narrative,
                "signal": signal.divergence_signal,
                "lifecycle": signal.lifecycle_stage,
                "confidence": signal.confidence,
                "momentum_score": signal.momentum_score,
                "price_momentum": signal.price_momentum,
                "divergence_score": signal.divergence_score,
                "social_velocity": signal.social_velocity,
                "sentiment": signal.sentiment_strength,
                "tvl": signal.tvl,
                "price": signal.price,
                "price_change_24h": signal.price_change_24h
            }
            for signal in signals
        ]