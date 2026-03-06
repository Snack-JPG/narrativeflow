"""DeFiLlama on-chain data collector."""

import httpx
from typing import Dict, List, Any
from datetime import datetime
from .base import BaseCollector
from ..models.db_manager import db_manager
from ..models.database import OnChainData


class DeFiLlamaCollector(BaseCollector):
    """Collector for DeFiLlama TVL and protocol data."""

    def __init__(self):
        """Initialize DeFiLlama collector."""
        super().__init__("DeFiLlama", "onchain")
        self.base_url = "https://api.llama.fi"

    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch data from DeFiLlama API.

        Returns:
            List of protocol data
        """
        all_data = []

        # Fetch TVL data
        tvl_data = await self.fetch_tvl_data()
        all_data.extend(tvl_data)

        # Fetch protocol details for top protocols
        protocol_data = await self.fetch_protocol_details()
        all_data.extend(protocol_data)

        return all_data

    async def fetch_tvl_data(self) -> List[Dict[str, Any]]:
        """Fetch TVL data by protocol and chain.

        Returns:
            List of TVL data
        """
        protocols = []

        try:
            async with httpx.AsyncClient() as client:
                # Get all protocols
                response = await client.get(
                    f"{self.base_url}/protocols",
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()

                    # Process top 100 protocols by TVL
                    for protocol in data[:100]:
                        parsed = self.parse_protocol_tvl(protocol)
                        if parsed:
                            protocols.append(parsed)
                else:
                    self.logger.error(f"DeFiLlama API error: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Error fetching DeFiLlama TVL data: {e}")

        return protocols

    async def fetch_protocol_details(self) -> List[Dict[str, Any]]:
        """Fetch detailed protocol data for top protocols.

        Returns:
            List of detailed protocol data
        """
        details = []

        # Get list of top protocol slugs
        top_protocols = ["aave", "uniswap", "compound", "curve", "makerdao", "lido", "eigenlayer"]

        try:
            async with httpx.AsyncClient() as client:
                for protocol_slug in top_protocols:
                    response = await client.get(
                        f"{self.base_url}/protocol/{protocol_slug}",
                        timeout=30.0
                    )

                    if response.status_code == 200:
                        data = response.json()
                        parsed = self.parse_protocol_detail(data)
                        if parsed:
                            details.append(parsed)

        except Exception as e:
            self.logger.error(f"Error fetching protocol details: {e}")

        return details

    def parse_protocol_tvl(self, protocol: Dict[str, Any]) -> Dict[str, Any]:
        """Parse protocol TVL data.

        Args:
            protocol: Protocol data from API

        Returns:
            Parsed protocol data
        """
        # Map protocol category to narrative
        category = protocol.get("category", "").lower()
        narrative = self.map_category_to_narrative(category)

        tvl = protocol.get("tvl", 0)
        tvl_change = protocol.get("change_1d", 0) if protocol.get("change_1d") else 0

        return {
            "protocol": protocol.get("name", "Unknown"),
            "chain": protocol.get("chain", "Multi-Chain"),
            "tvl": tvl,
            "tvl_change_24h": tvl_change,
            "narrative_category": narrative,
            "timestamp": datetime.utcnow(),
            "metadata": {
                "source": "DeFiLlama",
                "category": category,
                "symbol": protocol.get("symbol"),
                "chains": protocol.get("chains", []),
                "mcap": protocol.get("mcap", 0),
            }
        }

    def parse_protocol_detail(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse detailed protocol data.

        Args:
            data: Detailed protocol data

        Returns:
            Parsed protocol details
        """
        # Extract current TVL
        current_tvl = data.get("tvl", [{}])[-1] if data.get("tvl") else {}
        tvl = current_tvl.get("totalLiquidityUSD", 0)

        # Calculate 24h change
        tvl_24h_ago = 0
        if len(data.get("tvl", [])) > 1:
            tvl_24h_ago = data["tvl"][-2].get("totalLiquidityUSD", 0)
        tvl_change = ((tvl - tvl_24h_ago) / tvl_24h_ago * 100) if tvl_24h_ago > 0 else 0

        category = data.get("category", "").lower()
        narrative = self.map_category_to_narrative(category)

        return {
            "protocol": data.get("name", "Unknown"),
            "chain": data.get("chain", "Multi-Chain"),
            "tvl": tvl,
            "tvl_change_24h": tvl_change,
            "narrative_category": narrative,
            "timestamp": datetime.utcnow(),
            "metadata": {
                "source": "DeFiLlama",
                "category": category,
                "description": data.get("description", ""),
                "twitter": data.get("twitter"),
                "website": data.get("url"),
                "token_symbol": data.get("symbol"),
                "gecko_id": data.get("gecko_id"),
            }
        }

    def map_category_to_narrative(self, category: str) -> str:
        """Map DeFiLlama category to our narrative taxonomy.

        Args:
            category: DeFiLlama category

        Returns:
            Narrative category
        """
        mapping = {
            "dexes": "DeFi",
            "lending": "DeFi",
            "yield": "DeFi",
            "liquid staking": "DeFi",
            "derivatives": "Derivatives",
            "bridge": "Infrastructure",
            "oracle": "Infrastructure",
            "gaming": "Gaming",
            "nft": "NFT",
            "privacy": "Privacy",
            "rwa": "RWA",
            "ai": "AI",
            "social": "Social",
        }

        for key, narrative in mapping.items():
            if key in category.lower():
                return narrative

        return "DeFi"  # Default to DeFi for unmatched categories

    async def store_data(self, data_items: List[Dict[str, Any]]) -> int:
        """Store on-chain data in database.

        Args:
            data_items: List of data items to store

        Returns:
            Number of items stored
        """
        stored_count = 0

        async with db_manager.get_session() as session:
            for item in data_items:
                # Create on-chain data entry
                onchain_data = OnChainData(
                    timestamp=item.get("timestamp", datetime.utcnow()),
                    protocol=item.get("protocol"),
                    chain=item.get("chain"),
                    tvl=item.get("tvl"),
                    tvl_change_24h=item.get("tvl_change_24h"),
                    narrative_category=item.get("narrative_category"),
                    source="DeFiLlama",
                    metadata=item.get("metadata", {})
                )
                session.add(onchain_data)
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