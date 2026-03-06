"""Scheduler for periodic data collection."""

import asyncio
import logging
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .collectors import (
    CryptoPanicCollector,
    RedditCollector,
    RSSCollector,
    DeFiLlamaCollector,
    CoinGeckoCollector,
    BinanceCollector
)
from .config import settings
from .models.db_manager import db_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataCollectionScheduler:
    """Manages scheduled data collection tasks."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.collectors = {
            "cryptopanic": CryptoPanicCollector(),
            "reddit": RedditCollector(),
            "rss": RSSCollector(),
            "defi_llama": DeFiLlamaCollector(),
            "coingecko": CoinGeckoCollector(),
            "binance": BinanceCollector(),
        }

    async def collect_cryptopanic(self):
        """Collect CryptoPanic data."""
        try:
            logger.info("Starting CryptoPanic collection")
            collector = self.collectors["cryptopanic"]
            items = await collector.collect()
            logger.info(f"Collected {items} items from CryptoPanic")
        except Exception as e:
            logger.error(f"CryptoPanic collection failed: {e}")

    async def collect_reddit(self):
        """Collect Reddit data."""
        try:
            logger.info("Starting Reddit collection")
            collector = self.collectors["reddit"]
            items = await collector.collect()
            logger.info(f"Collected {items} items from Reddit")
        except Exception as e:
            logger.error(f"Reddit collection failed: {e}")

    async def collect_rss(self):
        """Collect RSS feed data."""
        try:
            logger.info("Starting RSS collection")
            collector = self.collectors["rss"]
            items = await collector.collect()
            logger.info(f"Collected {items} items from RSS feeds")
        except Exception as e:
            logger.error(f"RSS collection failed: {e}")

    async def collect_defi_llama(self):
        """Collect DeFiLlama data."""
        try:
            logger.info("Starting DeFiLlama collection")
            collector = self.collectors["defi_llama"]
            items = await collector.collect()
            logger.info(f"Collected {items} items from DeFiLlama")
        except Exception as e:
            logger.error(f"DeFiLlama collection failed: {e}")

    async def collect_coingecko(self):
        """Collect CoinGecko data."""
        try:
            logger.info("Starting CoinGecko collection")
            collector = self.collectors["coingecko"]
            items = await collector.collect()
            logger.info(f"Collected {items} items from CoinGecko")
        except Exception as e:
            logger.error(f"CoinGecko collection failed: {e}")

    async def collect_binance(self):
        """Collect Binance data."""
        try:
            logger.info("Starting Binance collection")
            collector = self.collectors["binance"]
            items = await collector.collect()
            logger.info(f"Collected {items} items from Binance")
        except Exception as e:
            logger.error(f"Binance collection failed: {e}")

    def setup_jobs(self):
        """Set up scheduled jobs."""
        # CryptoPanic - every 5 minutes
        self.scheduler.add_job(
            self.collect_cryptopanic,
            IntervalTrigger(seconds=settings.cryptopanic_interval),
            id="cryptopanic",
            name="CryptoPanic Collection",
            replace_existing=True
        )

        # Reddit - every 10 minutes
        self.scheduler.add_job(
            self.collect_reddit,
            IntervalTrigger(seconds=settings.reddit_interval),
            id="reddit",
            name="Reddit Collection",
            replace_existing=True
        )

        # RSS - every 15 minutes
        self.scheduler.add_job(
            self.collect_rss,
            IntervalTrigger(seconds=settings.rss_interval),
            id="rss",
            name="RSS Collection",
            replace_existing=True
        )

        # DeFiLlama - every 30 minutes
        self.scheduler.add_job(
            self.collect_defi_llama,
            IntervalTrigger(seconds=settings.defi_llama_interval),
            id="defi_llama",
            name="DeFiLlama Collection",
            replace_existing=True
        )

        # CoinGecko - every 10 minutes
        self.scheduler.add_job(
            self.collect_coingecko,
            IntervalTrigger(seconds=settings.coingecko_interval),
            id="coingecko",
            name="CoinGecko Collection",
            replace_existing=True
        )

        # Binance - every minute
        self.scheduler.add_job(
            self.collect_binance,
            IntervalTrigger(seconds=settings.binance_interval),
            id="binance",
            name="Binance Collection",
            replace_existing=True
        )

    async def run_initial_collection(self):
        """Run initial data collection for all sources."""
        logger.info("Running initial data collection...")

        tasks = [
            self.collect_cryptopanic(),
            self.collect_reddit(),
            self.collect_rss(),
            self.collect_defi_llama(),
            self.collect_coingecko(),
            self.collect_binance(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Initial collection failed for task {i}: {result}")

        logger.info("Initial data collection complete")

    def start(self):
        """Start the scheduler."""
        self.setup_jobs()
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")


# Global scheduler instance
scheduler = DataCollectionScheduler()