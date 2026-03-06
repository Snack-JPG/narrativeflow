"""Binance market data collector for prices, funding rates, and open interest."""

import httpx
from typing import Dict, List, Any
from datetime import datetime
from .base import BaseCollector
from ..config import settings
from ..models.db_manager import db_manager
from ..models.database import MarketData


class BinanceCollector(BaseCollector):
    """Collector for Binance market data."""

    def __init__(self):
        """Initialize Binance collector."""
        super().__init__("Binance", "market")
        self.base_url = "https://api.binance.com"
        self.futures_url = "https://fapi.binance.com"

    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch data from Binance API.

        Returns:
            List of market data
        """
        all_data = []

        # Get top symbols
        top_symbols = await self.get_top_symbols()

        # Fetch spot prices
        spot_data = await self.fetch_spot_prices(top_symbols)
        all_data.extend(spot_data)

        # Fetch futures data (funding rates and OI)
        futures_data = await self.fetch_futures_data(top_symbols)
        all_data.extend(futures_data)

        return all_data

    async def get_top_symbols(self) -> List[str]:
        """Get top trading symbols by volume.

        Returns:
            List of top symbol pairs
        """
        symbols = []

        try:
            async with httpx.AsyncClient() as client:
                # Get 24hr ticker for all symbols
                response = await client.get(
                    f"{self.base_url}/api/v3/ticker/24hr",
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()

                    # Filter USDT pairs and sort by volume
                    usdt_pairs = [
                        ticker for ticker in data
                        if ticker["symbol"].endswith("USDT")
                    ]

                    # Sort by quote volume (USDT volume)
                    sorted_pairs = sorted(
                        usdt_pairs,
                        key=lambda x: float(x.get("quoteVolume", 0)),
                        reverse=True
                    )

                    # Get top N symbols
                    for ticker in sorted_pairs[:settings.binance_top_symbols]:
                        symbols.append(ticker["symbol"])

        except Exception as e:
            self.logger.error(f"Error fetching top symbols: {e}")
            # Fallback to default symbols
            symbols = [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT"
            ]

        return symbols

    async def fetch_spot_prices(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Fetch spot market data for symbols.

        Args:
            symbols: List of trading pairs

        Returns:
            List of spot market data
        """
        spot_data = []

        try:
            async with httpx.AsyncClient() as client:
                # Get ticker data for specific symbols
                symbols_param = '","'.join(symbols)
                response = await client.get(
                    f"{self.base_url}/api/v3/ticker/24hr",
                    params={"symbols": f'["{symbols_param}"]'},
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()

                    for ticker in data:
                        # Extract base currency
                        symbol = ticker["symbol"].replace("USDT", "")

                        # Guess narrative from symbol
                        narrative = self.guess_narrative_from_symbol(symbol)

                        spot_data.append({
                            "symbol": symbol,
                            "price": float(ticker.get("lastPrice", 0)),
                            "volume_24h": float(ticker.get("quoteVolume", 0)),
                            "price_change_24h": float(ticker.get("priceChangePercent", 0)),
                            "narrative_category": narrative,
                            "timestamp": datetime.utcnow(),
                            "metadata": {
                                "source": "Binance",
                                "type": "spot",
                                "high_24h": float(ticker.get("highPrice", 0)),
                                "low_24h": float(ticker.get("lowPrice", 0)),
                                "count": int(ticker.get("count", 0)),  # Number of trades
                            }
                        })

        except Exception as e:
            self.logger.error(f"Error fetching spot prices: {e}")

        return spot_data

    async def fetch_futures_data(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Fetch futures data including funding rates and open interest.

        Args:
            symbols: List of trading pairs

        Returns:
            List of futures market data
        """
        futures_data = []

        try:
            async with httpx.AsyncClient() as client:
                for symbol in symbols[:20]:  # Limit to avoid rate limits
                    # Get funding rate
                    funding_response = await client.get(
                        f"{self.futures_url}/fapi/v1/fundingRate",
                        params={"symbol": symbol, "limit": 1},
                        timeout=30.0
                    )

                    # Get open interest
                    oi_response = await client.get(
                        f"{self.futures_url}/fapi/v1/openInterest",
                        params={"symbol": symbol},
                        timeout=30.0
                    )

                    funding_rate = 0.0
                    open_interest = 0.0

                    if funding_response.status_code == 200:
                        funding_data = funding_response.json()
                        if funding_data:
                            funding_rate = float(funding_data[0].get("fundingRate", 0))

                    if oi_response.status_code == 200:
                        oi_data = oi_response.json()
                        open_interest = float(oi_data.get("openInterest", 0))

                    if funding_rate != 0 or open_interest != 0:
                        # Extract base currency
                        base_symbol = symbol.replace("USDT", "")
                        narrative = self.guess_narrative_from_symbol(base_symbol)

                        futures_data.append({
                            "symbol": base_symbol,
                            "funding_rate": funding_rate,
                            "open_interest": open_interest,
                            "narrative_category": narrative,
                            "timestamp": datetime.utcnow(),
                            "metadata": {
                                "source": "Binance",
                                "type": "futures",
                                "contract": symbol,
                            }
                        })

        except Exception as e:
            self.logger.error(f"Error fetching futures data: {e}")

        return futures_data

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
            "FET": "AI", "AGIX": "AI", "OCEAN": "AI", "RNDR": "AI", "GRT": "AI",

            # Memecoins
            "DOGE": "Memecoin", "SHIB": "Memecoin", "PEPE": "Memecoin", "FLOKI": "Memecoin",
            "BONK": "Memecoin", "WIF": "Memecoin",

            # L1/L2
            "ETH": "L1/L2", "SOL": "L1/L2", "BNB": "L1/L2", "AVAX": "L1/L2",
            "MATIC": "L1/L2", "ARB": "L1/L2", "OP": "L1/L2", "APT": "L1/L2",
            "SUI": "L1/L2", "SEI": "L1/L2", "TIA": "L1/L2", "ADA": "L1/L2",
            "DOT": "L1/L2", "NEAR": "L1/L2", "ATOM": "L1/L2",

            # DeFi
            "UNI": "DeFi", "AAVE": "DeFi", "CRV": "DeFi", "MKR": "DeFi",
            "COMP": "DeFi", "SNX": "DeFi", "SUSHI": "DeFi", "LDO": "DeFi",
            "1INCH": "DeFi", "CAKE": "DeFi",

            # Infrastructure
            "LINK": "Infrastructure", "API3": "Infrastructure", "BAND": "Infrastructure",

            # Gaming
            "SAND": "Gaming", "MANA": "Gaming", "AXS": "Gaming", "GALA": "Gaming",
            "IMX": "Gaming", "GMT": "Gaming",

            # DePIN
            "FIL": "DePIN", "AR": "DePIN",
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
                # Check if this is spot or futures data
                if "price" in item:
                    # Spot data
                    market_data = MarketData(
                        timestamp=item.get("timestamp", datetime.utcnow()),
                        symbol=item.get("symbol"),
                        price=item.get("price"),
                        volume_24h=item.get("volume_24h"),
                        price_change_24h=item.get("price_change_24h"),
                        narrative_category=item.get("narrative_category"),
                        source="Binance",
                        metadata=item.get("metadata", {})
                    )
                    session.add(market_data)
                    stored_count += 1

                if "funding_rate" in item or "open_interest" in item:
                    # Futures data - update existing or create new
                    # This is a simplified approach - in production you'd merge with existing records
                    market_data = MarketData(
                        timestamp=item.get("timestamp", datetime.utcnow()),
                        symbol=item.get("symbol"),
                        funding_rate=item.get("funding_rate"),
                        open_interest=item.get("open_interest"),
                        narrative_category=item.get("narrative_category"),
                        source="Binance_Futures",
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