"""CryptoPanic news aggregator collector."""

import httpx
from typing import Dict, List, Any
from datetime import datetime
from .base import BaseCollector
from ..config import settings


class CryptoPanicCollector(BaseCollector):
    """Collector for CryptoPanic news aggregator."""

    def __init__(self):
        """Initialize CryptoPanic collector."""
        super().__init__("CryptoPanic", "social")
        self.base_url = "https://cryptopanic.com/api/v1/posts/"
        self.api_key = settings.cryptopanic_api_key

    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch data from CryptoPanic API.

        Returns:
            List of news items
        """
        params = {
            "auth_token": self.api_key,
            "public": "true",
            "filter": "hot",  # Get hot/trending news
            "currencies": "BTC,ETH,SOL",  # Focus on major currencies
        }

        # Remove auth_token if not provided (free tier)
        if not self.api_key:
            params.pop("auth_token")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return self.parse_data(data)
                else:
                    self.logger.error(f"CryptoPanic API error: {response.status_code}")
                    return []

        except Exception as e:
            self.logger.error(f"Error fetching CryptoPanic data: {e}")
            return []

    def parse_data(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse CryptoPanic data into standardized format.

        Args:
            raw_data: Raw API response

        Returns:
            List of parsed news items
        """
        parsed_items = []

        if "results" not in raw_data:
            return parsed_items

        for item in raw_data["results"]:
            # Extract votes for sentiment
            votes = item.get("votes", {})
            bullish_votes = votes.get("positive", 0)
            bearish_votes = votes.get("negative", 0)
            total_votes = votes.get("total", 1)

            # Calculate sentiment from votes
            if total_votes > 0:
                sentiment_score = (bullish_votes - bearish_votes) / total_votes
                if sentiment_score > 0.1:
                    sentiment = "bullish"
                elif sentiment_score < -0.1:
                    sentiment = "bearish"
                else:
                    sentiment = "neutral"
            else:
                sentiment = "neutral"
                sentiment_score = 0.0

            # Extract currencies mentioned
            currencies = [c["code"] for c in item.get("currencies", [])]

            parsed_item = {
                "title": item.get("title", ""),
                "content": item.get("body", ""),
                "url": item.get("url", ""),
                "author": item.get("source", {}).get("title", "Unknown"),
                "timestamp": datetime.fromisoformat(
                    item.get("created_at", datetime.utcnow().isoformat()).replace("Z", "+00:00")
                ),
                "metadata": {
                    "source": "CryptoPanic",
                    "kind": item.get("kind", "news"),  # news, media, blog
                    "currencies": currencies,
                    "votes": votes,
                    "comments": item.get("comments", 0),
                    "sentiment_label": sentiment,
                    "sentiment_score": sentiment_score,
                }
            }

            parsed_items.append(parsed_item)

        return parsed_items