"""RSS feed collector for news sources."""

import feedparser
import httpx
from typing import Dict, List, Any
from datetime import datetime
from .base import BaseCollector
from ..config import settings


class RSSCollector(BaseCollector):
    """Collector for RSS feeds from crypto news sources."""

    def __init__(self):
        """Initialize RSS collector."""
        super().__init__("RSS", "social")
        self.feeds = settings.rss_feeds

    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch data from RSS feeds.

        Returns:
            List of news articles
        """
        all_articles = []

        for source_name, feed_url in self.feeds.items():
            try:
                # Fetch RSS feed
                async with httpx.AsyncClient() as client:
                    response = await client.get(feed_url, timeout=30.0)

                if response.status_code == 200:
                    # Parse feed
                    feed = feedparser.parse(response.text)
                    articles = self.parse_feed(feed, source_name)
                    all_articles.extend(articles)
                else:
                    self.logger.error(f"Error fetching {source_name} RSS: {response.status_code}")

            except Exception as e:
                self.logger.error(f"Error fetching {source_name} RSS feed: {e}")

        return all_articles

    def parse_feed(self, feed: feedparser.FeedParserDict, source_name: str) -> List[Dict[str, Any]]:
        """Parse RSS feed into standardized format.

        Args:
            feed: Parsed RSS feed
            source_name: Name of the news source

        Returns:
            List of parsed articles
        """
        articles = []

        for entry in feed.entries[:20]:  # Limit to 20 most recent articles per feed
            # Parse publication date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])
            else:
                published = datetime.utcnow()

            # Extract content
            content = ""
            if hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description

            # Clean HTML tags from content
            if content:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text()[:2000]  # Limit content length

            # Extract categories/tags
            tags = []
            if hasattr(entry, 'tags'):
                tags = [tag.term for tag in entry.tags]

            article = {
                "title": entry.get('title', ''),
                "content": content,
                "url": entry.get('link', ''),
                "author": entry.get('author', source_name),
                "timestamp": published,
                "metadata": {
                    "source": source_name,
                    "feed": "RSS",
                    "tags": tags,
                    "categories": entry.get('categories', []),
                }
            }

            articles.append(article)

        return articles

    def parse_data(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Parse raw data (already parsed in fetch_data).

        Args:
            raw_data: Pre-parsed data

        Returns:
            List of parsed items
        """
        return raw_data