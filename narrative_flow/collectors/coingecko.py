"""CoinGecko market data and categories collector."""

import httpx
from typing import Dict, List, Any
from datetime import datetime
from .base import BaseCollector
from ..config import settings
from ..models.db_manager import db_manager
from ..models.database import MarketData


class CoinGeckoCollector(BaseCollector):
    """Collector for CoinGecko market data and narrative categories."""

    def __init__(self):
        """Initialize CoinGecko collector."""
        super().__init__("CoinGecko", "market")
        self.base_url = "https://api.coingecko.com/api/v3"
        self.api_key = settings.coingecko_api_key

    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch data from CoinGecko API.

        Returns:
            List of market data
        """
        all_data = []

        # Fetch categories data
        categories_data = await self.fetch_categories()
        all_data.extend(categories_data)

        # Fetch top coins data
        coins_data = await self.fetch_top_coins()
        all_data.extend(coins_data)

        return all_data

    async def fetch_categories(self) -> List[Dict[str, Any]]:
        """Fetch market data by category (narrative baskets).

        Returns:
            List of category market data
        """
        categories = []

        try:
            headers = {}
            if self.api_key:
                headers["x-cg-demo-api-key"] = self.api_key

            async with httpx.AsyncClient() as client:
                # Get all categories
                response = await client.get(
                    f"{self.base_url}/coins/categories",
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()

                    for category in data:
                        # Map CoinGecko category to our narratives
                        narrative = self.map_category_to_narrative(category.get("id", ""))

                        if narrative != "Uncategorized":
                            categories.append({
                                "category_id": category.get("id"),
                                "name": category.get("name"),
                                "narrative_category": narrative,
                                "market_cap": category.get("market_cap", 0),
                                "market_cap_change_24h": category.get("market_cap_change_24h", 0),
                                "volume_24h": category.get("volume_24h", 0),
                                "top_coins": category.get("top_3_coins", []),
                                "timestamp": datetime.utcnow(),
                                "metadata": {
                                    "source": "CoinGecko",
                                    "type": "category"
                                }
                            })
                else:
                    self.logger.error(f"CoinGecko categories API error: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Error fetching CoinGecko categories: {e}")

        return categories

    async def fetch_top_coins(self) -> List[Dict[str, Any]]:
        """Fetch top coins by market cap.

        Returns:
            List of top coins market data
        """
        coins = []

        try:
            headers = {}
            if self.api_key:
                headers["x-cg-demo-api-key"] = self.api_key

            async with httpx.AsyncClient() as client:
                # Get top 100 coins
                params = {
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 100,
                    "page": 1,
                    "sparkline": False,
                    "price_change_percentage": "24h"
                }

                response = await client.get(
                    f"{self.base_url}/coins/markets",
                    params=params,
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()

                    for coin in data:
                        # Try to determine narrative from coin categories
                        # (would need additional API call per coin for full categories)
                        narrative = self.guess_narrative_from_symbol(coin.get("symbol", "").upper())

                        coins.append({
                            "symbol": coin.get("symbol", "").upper(),
                            "name": coin.get("name"),
                            "price": coin.get("current_price", 0),
                            "market_cap": coin.get("market_cap", 0),
                            "volume_24h": coin.get("total_volume", 0),
                            "price_change_24h": coin.get("price_change_percentage_24h", 0),
                            "narrative_category": narrative,
                            "timestamp": datetime.utcnow(),
                            "metadata": {
                                "source": "CoinGecko",
                                "type": "coin",
                                "rank": coin.get("market_cap_rank"),
                                "circulating_supply": coin.get("circulating_supply"),
                                "total_supply": coin.get("total_supply"),
                                "ath": coin.get("ath"),
                                "ath_change_percentage": coin.get("ath_change_percentage"),
                            }
                        })
                else:
                    self.logger.error(f"CoinGecko markets API error: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Error fetching CoinGecko top coins: {e}")

        return coins

    def map_category_to_narrative(self, category_id: str) -> str:
        """Map CoinGecko category to our narrative taxonomy.

        Args:
            category_id: CoinGecko category ID

        Returns:
            Narrative category
        """
        # Use the mapping from settings
        mapping = settings.coingecko_category_mapping

        for gecko_cat, narrative in mapping.items():
            if gecko_cat in category_id.lower():
                return narrative

        return "Uncategorized"

    def guess_narrative_from_symbol(self, symbol: str) -> str:
        """Guess narrative category from token symbol.

        Args:
            symbol: Token symbol

        Returns:
            Guessed narrative category
        """
        # Map well-known tokens to narratives
        token_narratives = {
            # AI
            "TAO": "AI", "FET": "AI", "AGIX": "AI", "OCEAN": "AI", "RNDR": "AI",
            "NMR": "AI", "GRT": "AI",

            # RWA
            "ONDO": "RWA", "MPL": "RWA", "RWA": "RWA", "CPOOL": "RWA",

            # DePIN
            "HNT": "DePIN", "MOBILE": "DePIN", "IOT": "DePIN", "FIL": "DePIN",
            "AR": "DePIN",

            # Memecoins
            "DOGE": "Memecoin", "SHIB": "Memecoin", "PEPE": "Memecoin", "BONK": "Memecoin",
            "WIF": "Memecoin", "FLOKI": "Memecoin",

            # L1/L2
            "ETH": "L1/L2", "SOL": "L1/L2", "AVAX": "L1/L2", "MATIC": "L1/L2",
            "ARB": "L1/L2", "OP": "L1/L2", "SUI": "L1/L2", "APT": "L1/L2",
            "SEI": "L1/L2", "TIA": "L1/L2",

            # DeFi
            "UNI": "DeFi", "AAVE": "DeFi", "CRV": "DeFi", "MKR": "DeFi",
            "COMP": "DeFi", "SNX": "DeFi", "SUSHI": "DeFi", "LDO": "DeFi",

            # Infrastructure
            "LINK": "Infrastructure", "API3": "Infrastructure", "BAND": "Infrastructure",
        }

        return token_narratives.get(symbol, "Uncategorized")

    async def store_data(self, data_items: List[Dict[str, Any]]) -> int:
        """Store market data in database.

        Args:
            data_items: List of data items to store

        Returns:
            Number of items stored
        """
        stored_count = 0

        async with db_manager.get_session() as session:
            for item in data_items:
                # Skip category aggregates, only store individual tokens
                if item.get("metadata", {}).get("type") == "coin":
                    market_data = MarketData(
                        timestamp=item.get("timestamp", datetime.utcnow()),
                        symbol=item.get("symbol"),
                        price=item.get("price"),
                        volume_24h=item.get("volume_24h"),
                        market_cap=item.get("market_cap"),
                        price_change_24h=item.get("price_change_24h"),
                        narrative_category=item.get("narrative_category"),
                        source="CoinGecko",
                        metadata=item.get("metadata", {})
                    )
                    session.add(market_data)
                    stored_count += 1

        return stored_count

    def parse_data(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Parse raw data (already parsed in fetch methods).

        Args:
            raw_data: Pre-parsed data

        Returns:
            List of parsed items
        """
        return raw_data