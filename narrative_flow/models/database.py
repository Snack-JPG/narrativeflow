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
    source_metadata = Column(JSON)  # Flexible field for source-specific data

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
    source_metadata = Column(JSON)


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
    source_metadata = Column(JSON)


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

    # New Phase 2 metrics
    weighted_velocity = Column(Float)  # Influencer-weighted velocity
    acceleration = Column(Float)  # Velocity change percentage
    novelty_score = Column(Float)  # Average novelty (0-1)
    innovation_rate = Column(Float)  # % of novel content


class EnrichedData(Base):
    """Enriched data with narrative classification and sentiment."""
    __tablename__ = "enriched_data"
    __table_args__ = (
        Index("idx_enriched_timestamp", "timestamp"),
        Index("idx_enriched_narrative", "primary_narrative"),
        Index("idx_enriched_sentiment", "sentiment_label"),
        Index("idx_enriched_novelty", "novelty_score"),
    )

    id = Column(Integer, primary_key=True)
    raw_data_id = Column(Integer, ForeignKey("raw_data.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Classification
    primary_narrative = Column(String(50))
    all_narratives = Column(JSON)  # List of all applicable narratives
    classification_confidence = Column(Float)
    classification_method = Column(String(20))  # 'fast', 'ai', 'hybrid'

    # Sentiment
    sentiment_label = Column(String(20))  # bullish, bearish, neutral
    sentiment_score = Column(Float)  # -1.0 to 1.0
    sentiment_confidence = Column(Float)  # 0.0 to 1.0
    sentiment_method = Column(String(20))  # 'cryptopanic', 'keywords', 'hybrid'

    # Influence
    influencer_weight = Column(Float, default=1.0)
    source_reputation = Column(String(20))  # high, medium, low

    # Novelty
    novelty_score = Column(Float)  # 0.0 to 1.0
    is_novel = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    new_terms = Column(JSON)  # List of new/trending terms

    # Tokens
    extracted_tokens = Column(JSON)  # Crypto tokens mentioned

    # Reddit specific
    reddit_karma = Column(Integer)
    reddit_account_age = Column(Integer)  # days
    reddit_subreddit = Column(String(100))

    # Twitter specific
    twitter_followers = Column(Integer)
    twitter_verified = Column(Boolean)
    twitter_engagement = Column(Float)  # engagement rate

    # Processing metadata
    processed_at = Column(DateTime, default=datetime.utcnow)
    processing_time_ms = Column(Integer)  # Time taken to process

    # Relationships
    raw_data = relationship("RawData", backref="enriched")


class VelocitySnapshot(Base):
    """Snapshot of narrative velocity metrics."""
    __tablename__ = "velocity_snapshots"
    __table_args__ = (
        Index("idx_velocity_timestamp", "timestamp"),
        Index("idx_velocity_narrative", "narrative_category"),
        Index("idx_velocity_window", "time_window"),
    )

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    narrative_category = Column(String(50), nullable=False)
    time_window = Column(String(10), nullable=False)  # 1h, 4h, 24h, 7d

    # Velocity metrics
    mentions_per_hour = Column(Float)
    weighted_mentions_per_hour = Column(Float)
    acceleration = Column(Float)  # % change in velocity
    sentiment_weighted_velocity = Column(Float)

    # Supporting metrics
    total_mentions = Column(Integer)
    unique_sources = Column(Integer)
    avg_influencer_weight = Column(Float)


class DivergenceHistory(Base):
    """Historical divergence signals for backtesting."""
    __tablename__ = "divergence_history"
    __table_args__ = (
        Index("idx_divergence_timestamp", "timestamp"),
        Index("idx_divergence_narrative", "narrative"),
        Index("idx_divergence_signal", "divergence_signal"),
        Index("idx_divergence_confidence", "confidence"),
    )

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    narrative = Column(String(50), nullable=False)

    # Social metrics at signal time
    social_velocity = Column(Float)
    sentiment_strength = Column(Float)
    social_buzz_trend = Column(Float)

    # On-chain metrics at signal time
    onchain_activity = Column(Float)
    onchain_delta = Column(Float)
    tvl = Column(Float)
    tvl_change_24h = Column(Float)

    # Market metrics at signal time
    price = Column(Float)
    price_change_24h = Column(Float)
    volume_24h = Column(Float)
    market_cap = Column(Float)

    # Computed scores
    momentum_score = Column(Float)
    price_momentum = Column(Float)
    divergence_score = Column(Float)

    # Classifications
    divergence_signal = Column(String(20))  # early_entry, late_exit, accumulation, dead, neutral
    lifecycle_stage = Column(String(20))  # whisper, emerging, mainstream, peak, declining, dead
    confidence = Column(Float)  # 0-1 confidence score

    # Outcome tracking (for backtesting)
    price_after_24h = Column(Float)  # Price 24h after signal
    price_after_7d = Column(Float)  # Price 7d after signal
    signal_success = Column(Boolean)  # Whether the signal was profitable
    return_pct = Column(Float)  # Actual return if acted on signal