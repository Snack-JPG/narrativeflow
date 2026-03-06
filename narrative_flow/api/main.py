"""FastAPI application for NarrativeFlow."""

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
import logging

from ..models import get_db, RawData, MarketData, OnChainData, NarrativeMetrics, DataSource, EnrichedData, VelocitySnapshot
from ..config import settings
from ..engine import NarrativeProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="NarrativeFlow API",
    description="Crypto Narrative Rotation Tracker - Data Collection Layer",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "NarrativeFlow",
        "version": "1.0.0",
        "description": "Crypto Narrative Rotation Tracker - Data Collection Layer"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/sources")
async def get_sources(
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get all data sources and their status."""
    result = await db.execute(select(DataSource))
    sources = result.scalars().all()

    return [
        {
            "id": source.id,
            "name": source.name,
            "type": source.type,
            "last_fetch": source.last_fetch.isoformat() if source.last_fetch else None,
            "is_active": source.is_active,
        }
        for source in sources
    ]


@app.get("/narratives")
async def get_narratives() -> List[str]:
    """Get all narrative categories."""
    return settings.narrative_categories


@app.get("/social/recent")
async def get_recent_social(
    source: Optional[str] = Query(None, description="Filter by source (Reddit, CryptoPanic, RSS)"),
    narrative: Optional[str] = Query(None, description="Filter by narrative category"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment (bullish, bearish, neutral)"),
    hours: int = Query(24, description="Number of hours to look back"),
    limit: int = Query(100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get recent social data."""
    # Build query
    query = select(RawData).join(DataSource)

    # Add filters
    conditions = []
    if source:
        conditions.append(DataSource.name == source)
    if narrative:
        conditions.append(RawData.narrative_tags.contains(narrative))
    if sentiment:
        conditions.append(RawData.sentiment == sentiment)

    # Time filter
    since = datetime.utcnow() - timedelta(hours=hours)
    conditions.append(RawData.timestamp >= since)

    if conditions:
        query = query.where(and_(*conditions))

    # Order and limit
    query = query.order_by(desc(RawData.timestamp)).limit(limit)

    # Execute query
    result = await db.execute(query)
    items = result.scalars().all()

    return [
        {
            "id": item.id,
            "timestamp": item.timestamp.isoformat(),
            "source": item.source.name,
            "title": item.title,
            "content": item.content[:500] if item.content else None,
            "url": item.url,
            "author": item.author,
            "narratives": item.narrative_tags,
            "sentiment": item.sentiment,
            "sentiment_score": item.sentiment_score,
            "metadata": item.source_metadata,
        }
        for item in items
    ]


@app.get("/market/prices")
async def get_market_prices(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    narrative: Optional[str] = Query(None, description="Filter by narrative category"),
    hours: int = Query(24, description="Number of hours to look back"),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get market price data."""
    query = select(MarketData)

    # Add filters
    conditions = []
    if symbol:
        conditions.append(MarketData.symbol == symbol.upper())
    if narrative:
        conditions.append(MarketData.narrative_category == narrative)

    # Time filter
    since = datetime.utcnow() - timedelta(hours=hours)
    conditions.append(MarketData.timestamp >= since)

    if conditions:
        query = query.where(and_(*conditions))

    # Order by timestamp
    query = query.order_by(desc(MarketData.timestamp))

    # Execute query
    result = await db.execute(query)
    items = result.scalars().all()

    return [
        {
            "timestamp": item.timestamp.isoformat(),
            "symbol": item.symbol,
            "price": item.price,
            "volume_24h": item.volume_24h,
            "market_cap": item.market_cap,
            "price_change_24h": item.price_change_24h,
            "funding_rate": item.funding_rate,
            "open_interest": item.open_interest,
            "narrative": item.narrative_category,
            "source": item.source,
        }
        for item in items
    ]


@app.get("/onchain/tvl")
async def get_onchain_tvl(
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    chain: Optional[str] = Query(None, description="Filter by chain"),
    narrative: Optional[str] = Query(None, description="Filter by narrative category"),
    hours: int = Query(24, description="Number of hours to look back"),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get on-chain TVL data."""
    query = select(OnChainData)

    # Add filters
    conditions = []
    if protocol:
        conditions.append(OnChainData.protocol == protocol)
    if chain:
        conditions.append(OnChainData.chain == chain)
    if narrative:
        conditions.append(OnChainData.narrative_category == narrative)

    # Time filter
    since = datetime.utcnow() - timedelta(hours=hours)
    conditions.append(OnChainData.timestamp >= since)

    if conditions:
        query = query.where(and_(*conditions))

    # Order by TVL
    query = query.order_by(desc(OnChainData.tvl))

    # Execute query
    result = await db.execute(query)
    items = result.scalars().all()

    return [
        {
            "timestamp": item.timestamp.isoformat(),
            "protocol": item.protocol,
            "chain": item.chain,
            "tvl": item.tvl,
            "tvl_change_24h": item.tvl_change_24h,
            "narrative": item.narrative_category,
            "source": item.source,
            "metadata": item.source_metadata,
        }
        for item in items
    ]


@app.get("/narratives/stats")
async def get_narrative_stats(
    hours: int = Query(24, description="Number of hours to look back"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get aggregate statistics by narrative."""
    since = datetime.utcnow() - timedelta(hours=hours)

    stats = {}

    for narrative in settings.narrative_categories:
        # Count social mentions
        social_query = select(func.count(RawData.id)).where(
            and_(
                RawData.narrative_tags.contains(narrative),
                RawData.timestamp >= since
            )
        )
        social_result = await db.execute(social_query)
        social_count = social_result.scalar() or 0

        # Get sentiment distribution
        sentiment_query = select(
            RawData.sentiment,
            func.count(RawData.id)
        ).where(
            and_(
                RawData.narrative_tags.contains(narrative),
                RawData.timestamp >= since
            )
        ).group_by(RawData.sentiment)

        sentiment_result = await db.execute(sentiment_query)
        sentiment_dist = {row[0]: row[1] for row in sentiment_result}

        # Get total TVL for narrative
        tvl_query = select(func.sum(OnChainData.tvl)).where(
            and_(
                OnChainData.narrative_category == narrative,
                OnChainData.timestamp >= since
            )
        )
        tvl_result = await db.execute(tvl_query)
        total_tvl = tvl_result.scalar() or 0

        # Get market cap for narrative
        mcap_query = select(func.sum(MarketData.market_cap)).where(
            and_(
                MarketData.narrative_category == narrative,
                MarketData.timestamp >= since
            )
        )
        mcap_result = await db.execute(mcap_query)
        total_mcap = mcap_result.scalar() or 0

        stats[narrative] = {
            "social_mentions": social_count,
            "sentiment": sentiment_dist,
            "total_tvl": total_tvl,
            "total_market_cap": total_mcap,
        }

    return {
        "period_hours": hours,
        "narratives": stats
    }


@app.get("/narratives/sentiment")
async def get_narrative_sentiment(
    narrative: Optional[str] = Query(None, description="Filter by specific narrative"),
    hours: int = Query(24, description="Number of hours to look back"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get sentiment analysis for narratives."""
    since = datetime.utcnow() - timedelta(hours=hours)

    # Query enriched data for sentiment
    query = select(EnrichedData)
    conditions = [EnrichedData.timestamp >= since]

    if narrative:
        conditions.append(EnrichedData.primary_narrative == narrative)

    query = query.where(and_(*conditions))
    result = await db.execute(query)
    items = result.scalars().all()

    if not items:
        return {"message": "No data available for the specified period"}

    # Aggregate by narrative
    narrative_sentiments = {}

    for item in items:
        if not item.primary_narrative:
            continue

        if item.primary_narrative not in narrative_sentiments:
            narrative_sentiments[item.primary_narrative] = {
                'bullish_count': 0,
                'bearish_count': 0,
                'neutral_count': 0,
                'total_score': 0,
                'total_count': 0,
                'avg_confidence': 0,
                'weighted_score': 0
            }

        ns = narrative_sentiments[item.primary_narrative]

        # Count by sentiment label
        if item.sentiment_label == 'bullish':
            ns['bullish_count'] += 1
        elif item.sentiment_label == 'bearish':
            ns['bearish_count'] += 1
        else:
            ns['neutral_count'] += 1

        # Accumulate scores
        ns['total_score'] += item.sentiment_score
        ns['total_count'] += 1
        ns['avg_confidence'] += item.sentiment_confidence
        ns['weighted_score'] += item.sentiment_score * item.influencer_weight

    # Calculate averages
    for narrative, data in narrative_sentiments.items():
        if data['total_count'] > 0:
            data['avg_score'] = data['total_score'] / data['total_count']
            data['avg_confidence'] = data['avg_confidence'] / data['total_count']
            data['weighted_avg_score'] = data['weighted_score'] / data['total_count']
            data['bullish_pct'] = (data['bullish_count'] / data['total_count']) * 100
            data['bearish_pct'] = (data['bearish_count'] / data['total_count']) * 100
            data['neutral_pct'] = (data['neutral_count'] / data['total_count']) * 100

        # Remove intermediate calculations
        del data['total_score']
        del data['weighted_score']

    return {
        "period_hours": hours,
        "since": since.isoformat(),
        "narratives": narrative_sentiments
    }


@app.get("/narratives/velocity")
async def get_narrative_velocity(
    narrative: Optional[str] = Query(None, description="Filter by specific narrative"),
    window: str = Query("4h", description="Time window: 1h, 4h, 24h, 7d"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get mention velocity metrics for narratives."""
    # Validate window
    valid_windows = ['1h', '4h', '24h', '7d']
    if window not in valid_windows:
        raise HTTPException(400, f"Invalid window. Must be one of: {valid_windows}")

    # Query velocity snapshots
    query = select(VelocitySnapshot).where(
        VelocitySnapshot.time_window == window
    )

    if narrative:
        query = query.where(VelocitySnapshot.narrative_category == narrative)

    # Get most recent snapshots
    query = query.order_by(desc(VelocitySnapshot.timestamp)).limit(100)

    result = await db.execute(query)
    snapshots = result.scalars().all()

    if not snapshots:
        return {"message": "No velocity data available"}

    # Group by narrative and get latest
    narrative_velocities = {}

    for snapshot in snapshots:
        if snapshot.narrative_category not in narrative_velocities:
            narrative_velocities[snapshot.narrative_category] = {
                'timestamp': snapshot.timestamp.isoformat(),
                'mentions_per_hour': snapshot.mentions_per_hour,
                'weighted_mentions_per_hour': snapshot.weighted_mentions_per_hour,
                'acceleration': snapshot.acceleration,
                'sentiment_weighted_velocity': snapshot.sentiment_weighted_velocity,
                'momentum_score': snapshot.sentiment_weighted_velocity * (1 + snapshot.acceleration/100)
            }

    # Sort by momentum score
    sorted_narratives = sorted(
        narrative_velocities.items(),
        key=lambda x: x[1]['momentum_score'],
        reverse=True
    )

    return {
        "window": window,
        "narratives": dict(sorted_narratives),
        "top_trending": [n for n, _ in sorted_narratives[:5]]
    }


@app.get("/narratives/trending")
async def get_trending_narratives(
    min_mentions: int = Query(5, description="Minimum mentions required"),
    hours: int = Query(4, description="Hours to analyze"),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get trending narratives based on momentum."""
    since = datetime.utcnow() - timedelta(hours=hours)

    # Query recent narrative metrics
    query = select(NarrativeMetrics).where(
        NarrativeMetrics.timestamp >= since
    ).order_by(desc(NarrativeMetrics.momentum_score))

    result = await db.execute(query)
    metrics = result.scalars().all()

    # Group by narrative and get latest
    narrative_latest = {}
    for metric in metrics:
        if metric.narrative_category not in narrative_latest:
            narrative_latest[metric.narrative_category] = metric

    # Filter and sort
    trending = []
    for narrative, metric in narrative_latest.items():
        if metric.mention_count >= min_mentions:
            trending.append({
                'narrative': narrative,
                'momentum_score': metric.momentum_score,
                'velocity': metric.weighted_velocity,
                'acceleration': metric.acceleration,
                'sentiment_avg': metric.sentiment_avg,
                'bullish_pct': metric.sentiment_bullish_pct,
                'novelty_score': metric.novelty_score,
                'innovation_rate': metric.innovation_rate,
                'mention_count': metric.mention_count,
                'lifecycle_stage': metric.lifecycle_stage,
                'divergence_signal': metric.divergence_signal
            })

    # Sort by momentum
    trending.sort(key=lambda x: x['momentum_score'], reverse=True)

    return trending[:20]  # Top 20


@app.get("/narratives/novelty")
async def get_narrative_novelty(
    narrative: Optional[str] = Query(None, description="Filter by specific narrative"),
    hours: int = Query(24, description="Number of hours to look back"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get novelty metrics for narratives."""
    since = datetime.utcnow() - timedelta(hours=hours)

    # Query enriched data for novelty
    query = select(EnrichedData)
    conditions = [EnrichedData.timestamp >= since]

    if narrative:
        conditions.append(EnrichedData.primary_narrative == narrative)

    query = query.where(and_(*conditions))
    result = await db.execute(query)
    items = result.scalars().all()

    if not items:
        return {"message": "No data available for the specified period"}

    # Aggregate by narrative
    narrative_novelty = {}

    for item in items:
        if not item.primary_narrative:
            continue

        if item.primary_narrative not in narrative_novelty:
            narrative_novelty[item.primary_narrative] = {
                'novel_count': 0,
                'duplicate_count': 0,
                'total_count': 0,
                'avg_novelty_score': 0,
                'new_terms': []
            }

        nn = narrative_novelty[item.primary_narrative]

        # Count novel vs duplicate
        if item.is_novel:
            nn['novel_count'] += 1
        if item.is_duplicate:
            nn['duplicate_count'] += 1

        nn['total_count'] += 1
        nn['avg_novelty_score'] += item.novelty_score or 0

        # Collect new terms
        if item.new_terms:
            nn['new_terms'].extend(item.new_terms)

    # Calculate averages and dedupe terms
    for narrative, data in narrative_novelty.items():
        if data['total_count'] > 0:
            data['avg_novelty_score'] = data['avg_novelty_score'] / data['total_count']
            data['innovation_rate'] = (data['novel_count'] / data['total_count']) * 100
            data['duplication_rate'] = (data['duplicate_count'] / data['total_count']) * 100

            # Get top new terms
            from collections import Counter
            term_counts = Counter(data['new_terms'])
            data['top_new_terms'] = [term for term, _ in term_counts.most_common(10)]
            del data['new_terms']

    return {
        "period_hours": hours,
        "since": since.isoformat(),
        "narratives": narrative_novelty
    }


@app.get("/search")
async def search_data(
    q: str = Query(..., description="Search query"),
    source_type: Optional[str] = Query(None, description="Filter by source type (social, onchain, market)"),
    limit: int = Query(50, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Search across all data sources."""
    # Search in raw data (social)
    query = select(RawData).join(DataSource)

    # Add search conditions
    search_conditions = [
        RawData.title.contains(q) if RawData.title else False,
        RawData.content.contains(q) if RawData.content else False,
    ]
    query = query.where(func.or_(*search_conditions))

    if source_type:
        query = query.where(DataSource.type == source_type)

    query = query.order_by(desc(RawData.timestamp)).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    return [
        {
            "type": "social",
            "timestamp": item.timestamp.isoformat(),
            "source": item.source.name,
            "title": item.title,
            "content": item.content[:500] if item.content else None,
            "url": item.url,
            "narratives": item.narrative_tags,
            "sentiment": item.sentiment,
        }
        for item in items
    ]