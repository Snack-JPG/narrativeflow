"""Database models for NarrativeFlow."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, JSON, Boolean, Index, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class DataSource(Base):
    """Data source information."""
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    type = Column(String(50), nullable=False)  # social, onchain, market
    last_fetch = Column(DateTime)
    is_active = Column(Boolean, default=True)
    config = Column(JSON)  # Store source-specific config

    # Relationships
    raw_data = relationship("RawData", back_populates="source")


class RawData(Base):
    """Raw collected data from various sources."""
    __tablename__ = "raw_data"
    __table_args__ = (
        Index("idx_raw_data_timestamp", "timestamp"),
        Index("idx_raw_data_source", "source_id"),
        Index("idx_raw_data_narrative", "narrative_tags"),
    )

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Content
    title = Column(String(500))
    content = Column(Text)
    url = Column(String(500))
    author = Column(String(200))

    # Metadata
    narrative_tags = Column(JSON)  # List of narrative categories
    sentiment = Column(String(20))  # bullish, bearish, neutral
    sentiment_score = Column(Float)  # -1 to 1

    # Source-specific data
    metadata = Column(JSON)  # Flexible field for source-specific data

    # Relationships
    source = relationship("DataSource", back_populates="raw_data")


class MarketData(Base):
    """Market data for tokens."""
    __tablename__ = "market_data"
    __table_args__ = (
        Index("idx_market_data_timestamp", "timestamp"),
        Index("idx_market_data_symbol", "symbol"),
    )

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    symbol = Column(String(20), nullable=False)

    # Price data
    price = Column(Float)
    volume_24h = Column(Float)
    market_cap = Column(Float)
    price_change_24h = Column(Float)

    # Advanced metrics
    funding_rate = Column(Float)  # For perpetuals
    open_interest = Column(Float)  # For derivatives

    # Narrative association
    narrative_category = Column(String(50))

    # Source
    source = Column(String(50))  # binance, coingecko, etc.
    metadata = Column(JSON)


class OnChainData(Base):
    """On-chain metrics data."""
    __tablename__ = "onchain_data"
    __table_args__ = (
        Index("idx_onchain_data_timestamp", "timestamp"),
        Index("idx_onchain_data_protocol", "protocol"),
    )

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Protocol info
    protocol = Column(String(100), nullable=False)
    chain = Column(String(50))

    # Metrics
    tvl = Column(Float)  # Total Value Locked
    tvl_change_24h = Column(Float)
    active_addresses = Column(Integer)
    transactions = Column(Integer)
    fees_24h = Column(Float)
    revenue_24h = Column(Float)

    # Narrative association
    narrative_category = Column(String(50))

    # Source
    source = Column(String(50))  # defi_llama, dune, etc.
    metadata = Column(JSON)


class NarrativeMetrics(Base):
    """Aggregated narrative metrics."""
    __tablename__ = "narrative_metrics"
    __table_args__ = (
        Index("idx_narrative_metrics_timestamp", "timestamp"),
        Index("idx_narrative_metrics_category", "narrative_category"),
    )

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    narrative_category = Column(String(50), nullable=False)

    # Social metrics
    mention_count = Column(Integer, default=0)
    mention_velocity = Column(Float)  # mentions/hour
    sentiment_avg = Column(Float)  # Average sentiment score
    sentiment_bullish_pct = Column(Float)  # % of bullish mentions

    # On-chain metrics
    total_tvl = Column(Float)
    tvl_change_24h = Column(Float)
    active_protocols = Column(Integer)

    # Market metrics
    total_market_cap = Column(Float)
    avg_price_change_24h = Column(Float)
    total_volume_24h = Column(Float)

    # Derived metrics
    momentum_score = Column(Float)  # Calculated narrative momentum
    divergence_signal = Column(String(50))  # early, late, accumulation, dead
    lifecycle_stage = Column(String(50))  # whisper, emerging, mainstream, peak, declining, dead