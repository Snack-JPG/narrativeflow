"""Base collector class for all data sources."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from ..models.db_manager import db_manager
from ..models.database import DataSource, RawData
from sqlalchemy import select


class BaseCollector(ABC):
    """Abstract base class for data collectors."""

    def __init__(self, source_name: str, source_type: str):
        """Initialize collector.

        Args:
            source_name: Name of the data source
            source_type: Type of data source (social, onchain, market)
        """
        self.source_name = source_name
        self.source_type = source_type
        self.logger = logging.getLogger(f"collector.{source_name}")
        self.is_running = False

    @abstractmethod
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch data from the source.

        Returns:
            List of raw data dictionaries
        """
        pass

    @abstractmethod
    def parse_data(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Parse raw data into standardized format.

        Args:
            raw_data: Raw data from source

        Returns:
            List of parsed data dictionaries
        """
        pass

    def classify_narrative(self, text: str) -> List[str]:
        """Classify text into narrative categories.

        Args:
            text: Text to classify

        Returns:
            List of narrative categories
        """
        # Simple keyword-based classification for Phase 1
        # Will be replaced with AI classification in later phases
        narratives = []
        text_lower = text.lower()

        narrative_keywords = {
            "AI": ["ai", "artificial intelligence", "machine learning", "gpt", "claude", "agent", "llm"],
            "RWA": ["rwa", "real world asset", "tokenized", "treasury", "bond"],
            "DePIN": ["depin", "decentralized physical", "helium", "hivemapper", "render"],
            "Memecoin": ["meme", "doge", "shiba", "pepe", "wojak", "bonk"],
            "L1/L2": ["layer 1", "layer 2", "l1", "l2", "ethereum", "solana", "avalanche", "polygon", "arbitrum", "optimism"],
            "NFT": ["nft", "non-fungible", "ordinals", "inscription", "jpeg"],
            "DeFi": ["defi", "yield", "lending", "amm", "dex", "liquidity", "stake", "farm", "aave", "compound", "uniswap"],
            "Gaming": ["gaming", "gamefi", "play to earn", "p2e", "metaverse"],
            "Privacy": ["privacy", "zero knowledge", "zk", "monero", "zcash", "tornado"],
            "Derivatives": ["derivatives", "perpetual", "futures", "options", "leverage"],
            "Social": ["social", "lens", "farcaster", "friend.tech"],
            "Infrastructure": ["infrastructure", "oracle", "bridge", "interoperability", "chainlink"]
        }

        for narrative, keywords in narrative_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                narratives.append(narrative)

        return narratives if narratives else ["Uncategorized"]

    def analyze_sentiment(self, text: str) -> tuple[str, float]:
        """Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (sentiment label, sentiment score)
        """
        # Simple keyword-based sentiment for Phase 1
        text_lower = text.lower()

        bullish_words = ["bullish", "moon", "pump", "buy", "long", "breakout", "rally", "surge", "soar", "ath"]
        bearish_words = ["bearish", "dump", "sell", "short", "crash", "drop", "plunge", "rekt", "scam", "rug"]

        bullish_count = sum(1 for word in bullish_words if word in text_lower)
        bearish_count = sum(1 for word in bearish_words if word in text_lower)

        if bullish_count > bearish_count:
            score = min(1.0, bullish_count * 0.2)
            return "bullish", score
        elif bearish_count > bullish_count:
            score = max(-1.0, -bearish_count * 0.2)
            return "bearish", score
        else:
            return "neutral", 0.0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def collect(self) -> int:
        """Main collection method with retry logic.

        Returns:
            Number of items collected
        """
        try:
            self.logger.info(f"Starting collection from {self.source_name}")

            # Fetch data
            raw_data = await self.fetch_data()

            # Parse and store data
            items_stored = await self.store_data(raw_data)

            # Update last fetch time
            await self.update_source_status()

            self.logger.info(f"Collected {items_stored} items from {self.source_name}")
            return items_stored

        except Exception as e:
            self.logger.error(f"Error collecting from {self.source_name}: {e}")
            raise

    async def store_data(self, data_items: List[Dict[str, Any]]) -> int:
        """Store collected data in database.

        Args:
            data_items: List of data items to store

        Returns:
            Number of items stored
        """
        stored_count = 0

        async with db_manager.get_session() as session:
            # Get or create data source
            result = await session.execute(
                select(DataSource).where(DataSource.name == self.source_name)
            )
            source = result.scalar_one_or_none()

            if not source:
                source = DataSource(
                    name=self.source_name,
                    type=self.source_type,
                    last_fetch=datetime.utcnow()
                )
                session.add(source)
                await session.flush()

            # Store each data item
            for item in data_items:
                # Extract text for classification
                text = f"{item.get('title', '')} {item.get('content', '')}"

                # Classify narrative and sentiment
                narratives = self.classify_narrative(text)
                sentiment, sentiment_score = self.analyze_sentiment(text)

                # Create raw data entry
                raw_data = RawData(
                    source_id=source.id,
                    timestamp=item.get("timestamp", datetime.utcnow()),
                    title=item.get("title"),
                    content=item.get("content"),
                    url=item.get("url"),
                    author=item.get("author"),
                    narrative_tags=narratives,
                    sentiment=sentiment,
                    sentiment_score=sentiment_score,
                    metadata=item.get("metadata", {})
                )
                session.add(raw_data)
                stored_count += 1

        return stored_count

    async def update_source_status(self):
        """Update source last fetch time."""
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(DataSource).where(DataSource.name == self.source_name)
            )
            source = result.scalar_one_or_none()
            if source:
                source.last_fetch = datetime.utcnow()

    async def run_periodic(self, interval_seconds: int):
        """Run collector periodically.

        Args:
            interval_seconds: Collection interval in seconds
        """
        self.is_running = True
        while self.is_running:
            try:
                await self.collect()
            except Exception as e:
                self.logger.error(f"Collection failed: {e}")

            await asyncio.sleep(interval_seconds)

    def stop(self):
        """Stop periodic collection."""
        self.is_running = False