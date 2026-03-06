"""FastAPI application for NarrativeFlow."""

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
import logging

from ..models import get_db, RawData, MarketData, OnChainData, NarrativeMetrics, DataSource
from ..config import settings

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
            "metadata": item.metadata,
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
            "metadata": item.metadata,
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