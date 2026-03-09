"""FastAPI routes for AI briefing system."""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
import logging
from sqlalchemy import select, desc

from ..ai import (
    ClaudeClient,
    BriefingGenerator,
    ChangeDetector,
    CatalystIdentifier,
    MarketRegimeAnalyzer,
    BriefingStorage
)
from ..models import RawData, MarketData, OnChainData, DivergenceHistory, DataSource
from ..models.db_manager import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/briefing", tags=["briefing"])


class BriefingRequest(BaseModel):
    """Request model for generating briefing."""
    time_window: int = Field(default=24, description="Hours of data to analyze")
    force_regenerate: bool = Field(default=False, description="Force regeneration even if recent briefing exists")
    include_history: bool = Field(default=True, description="Include historical comparison")


class BriefingResponse(BaseModel):
    """Response model for briefing."""
    id: int
    timestamp: datetime
    executive_summary: str
    emerging_narratives: List[Dict[str, Any]]
    overheated_narratives: List[Dict[str, Any]]
    key_catalysts: List[Dict[str, Any]]
    divergences: List[Dict[str, Any]]
    market_regime: Dict[str, str]
    recommendations: List[Dict[str, Any]]
    changes_from_previous: Optional[Dict[str, Any]]
    markdown_output: str
    json_output: Dict[str, Any]


class BriefingHistoryResponse(BaseModel):
    """Response model for briefing history."""
    briefings: List[BriefingResponse]
    total_count: int
    page: int
    page_size: int


# Initialize components
storage = BriefingStorage()
claude: Optional[ClaudeClient] = None
briefing_gen: Optional[BriefingGenerator] = None
change_detector = ChangeDetector()
catalyst_identifier = CatalystIdentifier()
regime_analyzer = MarketRegimeAnalyzer()


def _get_briefing_generator() -> BriefingGenerator:
    """Lazily initialize Claude-backed briefing generator."""
    global claude, briefing_gen

    if briefing_gen is not None:
        return briefing_gen

    try:
        claude = ClaudeClient()
        briefing_gen = BriefingGenerator(claude)
        return briefing_gen
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI briefing unavailable: ANTHROPIC_API_KEY is not configured. "
                "Set the environment variable and retry."
            )
        ) from exc


@router.on_event("startup")
async def startup():
    """Initialize storage on startup."""
    await storage.initialize()


@router.get("/latest", response_model=BriefingResponse)
async def get_latest_briefing():
    """Get the most recent briefing.

    Returns:
        Latest briefing or 404 if none exists
    """
    try:
        briefing = await storage.get_latest_briefing()
        if not briefing:
            raise HTTPException(status_code=404, detail="No briefings found")
        return BriefingResponse(**briefing)
    except Exception as e:
        logger.error(f"Error fetching latest briefing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=BriefingHistoryResponse)
async def get_briefing_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date")
):
    """Get briefing history with pagination.

    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        start_date: Optional filter by start date
        end_date: Optional filter by end date

    Returns:
        Paginated briefing history
    """
    try:
        offset = (page - 1) * page_size
        briefings = await storage.get_briefing_history(
            limit=page_size,
            offset=offset,
            start_date=start_date,
            end_date=end_date
        )

        # Get total count (simplified - would need proper count query)
        stats = await storage.get_stats()
        total_count = stats.get("total_briefings", 0)

        return BriefingHistoryResponse(
            briefings=[BriefingResponse(**b) for b in briefings],
            total_count=total_count,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error fetching briefing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=BriefingResponse)
async def generate_briefing(
    request: BriefingRequest,
    background_tasks: BackgroundTasks
):
    """Generate a new narrative briefing.

    Args:
        request: Briefing generation parameters
        background_tasks: FastAPI background tasks

    Returns:
        Generated briefing
    """
    try:
        # Check if recent briefing exists (unless forced)
        if not request.force_regenerate:
            latest = await storage.get_latest_briefing()
            if latest:
                latest_time = datetime.fromisoformat(latest["timestamp"])
                if datetime.utcnow() - latest_time < timedelta(hours=1):
                    logger.info("Recent briefing exists, returning cached")
                    return BriefingResponse(**latest)

        # Gather data for analysis
        async with get_db_session() as session:
            # Get social data
            social_data = await _get_social_data(session, request.time_window)

            # Get on-chain data
            onchain_data = await _get_onchain_data(session, request.time_window)

            # Get price data
            price_data = await _get_price_data(session, request.time_window)

            # Detect divergences
            divergence_signals = await _get_divergences(
                session, social_data, onchain_data, price_data
            )

        # Get previous briefing for comparison
        previous_briefing = None
        if request.include_history:
            previous_briefing = await storage.get_latest_briefing()

        # Generate briefing
        generator = _get_briefing_generator()
        briefing = await generator.generate_briefing(
            social_data=social_data,
            onchain_data=onchain_data,
            price_data=price_data,
            divergence_signals=divergence_signals,
            previous_briefing=previous_briefing,
            time_window=request.time_window
        )

        # Save to storage
        briefing_dict = {
            "timestamp": briefing.timestamp,
            "executive_summary": briefing.executive_summary,
            "emerging_narratives": briefing.emerging_narratives,
            "overheated_narratives": briefing.overheated_narratives,
            "key_catalysts": briefing.key_catalysts,
            "divergences": briefing.divergences,
            "market_regime": briefing.market_regime,
            "recommendations": briefing.recommendations,
            "changes_from_previous": briefing.changes_from_previous,
            "markdown_output": briefing.markdown_output,
            "json_output": briefing.json_output
        }
        briefing_id = await storage.save_briefing(briefing_dict)
        briefing_dict["id"] = briefing_id

        # Save additional data in background
        background_tasks.add_task(
            _save_analysis_data,
            social_data, onchain_data, divergence_signals
        )

        return BriefingResponse(**briefing_dict)

    except Exception as e:
        logger.error(f"Error generating briefing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime/{narrative}")
async def get_narrative_regime(
    narrative: str,
    hours: int = Query(168, description="Hours of history to analyze")
):
    """Get regime analysis for a specific narrative.

    Args:
        narrative: Narrative name
        hours: Hours of historical data to analyze

    Returns:
        Regime analysis and history
    """
    try:
        # Get historical data
        history = await storage.get_narrative_history(narrative, hours)

        if not history:
            raise HTTPException(status_code=404, detail=f"No data for narrative: {narrative}")

        # Get current metrics
        current_metrics = history[0] if history else {}

        # Analyze regime
        analysis = await regime_analyzer.analyze_regime(
            narrative=narrative,
            metrics=current_metrics,
            historical_data=history
        )

        # Get regime history
        regime_history = await storage.get_regime_history(narrative, hours)

        return {
            "narrative": narrative,
            "current_analysis": {
                "stage": analysis.current_stage.value,
                "confidence": analysis.stage_confidence,
                "time_in_stage": analysis.time_in_stage,
                "next_likely_stage": analysis.next_likely_stage.value if analysis.next_likely_stage else None,
                "transition_probability": analysis.transition_probability,
                "risk_level": analysis.risk_level,
                "opportunity_score": analysis.opportunity_score,
                "recommendation": analysis.recommendation
            },
            "history": regime_history,
            "metrics_history": history
        }

    except Exception as e:
        logger.error(f"Error analyzing regime for {narrative}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalysts")
async def get_recent_catalysts(
    hours: int = Query(24, description="Hours of history")
):
    """Get recent market catalysts.

    Args:
        hours: Hours of history to retrieve

    Returns:
        List of catalyst events
    """
    try:
        catalysts = await storage.get_recent_catalysts(hours)
        return {
            "catalysts": catalysts,
            "count": len(catalysts),
            "time_window": f"{hours} hours"
        }
    except Exception as e:
        logger.error(f"Error fetching catalysts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/changes")
async def detect_narrative_changes(
    hours: int = Query(24, description="Hours to compare")
):
    """Detect narrative changes over time window.

    Args:
        hours: Hours to look back for comparison

    Returns:
        Detected changes and shifts
    """
    try:
        # Get current and historical data
        async with get_db_session() as session:
            current_data = await _get_current_narrative_data(session)
            historical_data = await _get_historical_narrative_data(session, hours)

        # Detect changes
        changes = await change_detector.detect_changes(
            current_data=current_data,
            historical_data=historical_data,
            lookback_hours=hours
        )

        return {
            "changes": [
                {
                    "narrative": c.narrative,
                    "change_type": c.change_type,
                    "previous_state": c.previous_state,
                    "current_state": c.current_state,
                    "change_magnitude": c.change_magnitude,
                    "confidence": c.confidence,
                    "description": c.description
                }
                for c in changes
            ],
            "count": len(changes),
            "time_window": f"{hours} hours"
        }

    except Exception as e:
        logger.error(f"Error detecting changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_briefing_stats():
    """Get statistics about briefing system.

    Returns:
        System statistics
    """
    try:
        stats = await storage.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
async def _get_social_data(session, time_window: int) -> List[Dict[str, Any]]:
    """Get social data from database."""
    since = datetime.utcnow() - timedelta(hours=time_window)
    query = (
        select(RawData, DataSource.name)
        .join(DataSource, RawData.source_id == DataSource.id)
        .where(RawData.timestamp >= since)
        .order_by(desc(RawData.timestamp))
        .limit(500)
    )
    result = await session.execute(query)

    social_data: List[Dict[str, Any]] = []
    for raw_item, source_name in result.all():
        source_metadata = raw_item.source_metadata or {}
        narratives = raw_item.narrative_tags or []
        if isinstance(narratives, str):
            narratives = [narratives]

        author_influence = (
            source_metadata.get("author_followers")
            or source_metadata.get("followers")
            or source_metadata.get("author_karma")
            or 0
        )
        engagement = (
            source_metadata.get("engagement")
            or source_metadata.get("interactions")
            or source_metadata.get("upvotes")
            or source_metadata.get("score")
            or 0
        )

        text_content = " ".join(
            part for part in [raw_item.title, raw_item.content] if part
        ).strip()

        social_data.append({
            "id": raw_item.id,
            "timestamp": raw_item.timestamp.isoformat(),
            "title": raw_item.title,
            "content": raw_item.content,
            "text": text_content,
            "url": raw_item.url,
            "author": raw_item.author,
            "source": source_name,
            "narratives": narratives,
            "sentiment": {
                "label": raw_item.sentiment or "neutral",
                "score": raw_item.sentiment_score if raw_item.sentiment_score is not None else 0.0,
            },
            "author_influence": float(author_influence) if isinstance(author_influence, (int, float)) else 0.0,
            "engagement": float(engagement) if isinstance(engagement, (int, float)) else 0.0,
            "metadata": source_metadata,
        })

    return social_data


async def _get_onchain_data(session, time_window: int) -> Dict[str, Any]:
    """Get on-chain data from database."""
    since = datetime.utcnow() - timedelta(hours=time_window)
    query = (
        select(OnChainData)
        .where(OnChainData.timestamp >= since)
        .order_by(desc(OnChainData.timestamp))
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    onchain_data: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        narrative = row.narrative_category or "Uncategorized"
        if narrative not in onchain_data:
            onchain_data[narrative] = {
                "tvl": 0.0,
                "tvl_change": 0.0,
                "active_protocols": set(),
                "chains": set(),
                "_tvl_change_count": 0,
            }

        bucket = onchain_data[narrative]
        bucket["tvl"] += float(row.tvl or 0.0)
        if row.tvl_change_24h is not None:
            bucket["tvl_change"] += float(row.tvl_change_24h)
            bucket["_tvl_change_count"] += 1
        if row.protocol:
            bucket["active_protocols"].add(row.protocol)
        if row.chain:
            bucket["chains"].add(row.chain)

    for narrative, bucket in onchain_data.items():
        count = bucket.pop("_tvl_change_count")
        bucket["tvl_change"] = (bucket["tvl_change"] / count) if count else 0.0
        bucket["active_protocols"] = len(bucket["active_protocols"])
        bucket["chains"] = sorted(bucket["chains"])

    return onchain_data


async def _get_price_data(session, time_window: int) -> Dict[str, Any]:
    """Get price data from database."""
    since = datetime.utcnow() - timedelta(hours=time_window)
    query = (
        select(MarketData)
        .where(MarketData.timestamp >= since)
        .order_by(desc(MarketData.timestamp))
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    price_data: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        narrative = row.narrative_category or "Uncategorized"
        if narrative not in price_data:
            price_data[narrative] = {
                "price": None,
                "change_24h": 0.0,
                "total_volume_24h": 0.0,
                "total_market_cap": 0.0,
                "symbols": set(),
                "_price_change_count": 0,
            }

        bucket = price_data[narrative]

        # Keep the most recent non-null price as representative snapshot.
        if bucket["price"] is None and row.price is not None:
            bucket["price"] = float(row.price)

        if row.price_change_24h is not None:
            bucket["change_24h"] += float(row.price_change_24h)
            bucket["_price_change_count"] += 1

        bucket["total_volume_24h"] += float(row.volume_24h or 0.0)
        bucket["total_market_cap"] += float(row.market_cap or 0.0)
        if row.symbol:
            bucket["symbols"].add(row.symbol)

    for narrative, bucket in price_data.items():
        count = bucket.pop("_price_change_count")
        bucket["change_24h"] = (bucket["change_24h"] / count) if count else 0.0
        bucket["price"] = bucket["price"] if bucket["price"] is not None else 0.0
        bucket["symbols"] = sorted(bucket["symbols"])

    return price_data


async def _get_divergences(
    session,
    social_data: List[Dict[str, Any]],
    onchain_data: Dict[str, Any],
    price_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Detect divergence signals."""
    # Derive a lookback window from gathered social data; fallback to 24h.
    since = datetime.utcnow() - timedelta(hours=24)
    timestamps = [
        item.get("timestamp") for item in social_data
        if item.get("timestamp")
    ]
    if timestamps:
        parsed_times = []
        for timestamp in timestamps:
            try:
                parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
                parsed_times.append(parsed)
            except (TypeError, ValueError):
                continue
        if parsed_times:
            since = min(parsed_times)

    query = (
        select(DivergenceHistory)
        .where(DivergenceHistory.timestamp >= since)
        .order_by(desc(DivergenceHistory.timestamp))
        .limit(50)
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    signals: List[Dict[str, Any]] = []
    for row in rows:
        signals.append({
            "narrative": row.narrative,
            "signal": row.divergence_signal,
            "signal_type": row.divergence_signal,
            "lifecycle": row.lifecycle_stage,
            "confidence": float(row.confidence or 0.0),
            "strength": float(row.divergence_score or row.momentum_score or 0.0),
            "momentum_score": float(row.momentum_score or 0.0),
            "divergence_score": float(row.divergence_score or 0.0),
            "social_velocity": float(row.social_velocity or 0.0),
            "tvl": float(row.tvl or 0.0),
            "price": float(row.price or 0.0),
            "price_change_24h": float(row.price_change_24h or 0.0),
            "timestamp": row.timestamp.isoformat(),
        })

    return signals


async def _get_current_narrative_data(session) -> Dict[str, Any]:
    """Get current narrative metrics."""
    # Simplified - would query actual database
    return {"narratives": {}}


async def _get_historical_narrative_data(session, hours: int) -> List[Dict[str, Any]]:
    """Get historical narrative data."""
    # Simplified - would query actual database
    return []


async def _save_analysis_data(
    social_data: List[Dict[str, Any]],
    onchain_data: Dict[str, Any],
    divergence_signals: List[Dict[str, Any]]
):
    """Save analysis data in background."""
    try:
        # Save narrative snapshots
        for narrative, metrics in onchain_data.items():
            await storage.save_narrative_snapshot(narrative, metrics)

        # Save catalyst events
        # (would extract from social_data)

        logger.info("Background data saved successfully")
    except Exception as e:
        logger.error(f"Error saving background data: {e}")
