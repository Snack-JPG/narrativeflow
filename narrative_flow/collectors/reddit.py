"""Reddit collector using PRAW."""

import asyncio
from typing import Dict, List, Any
from datetime import datetime
import praw
from .base import BaseCollector
from ..config import settings


class RedditCollector(BaseCollector):
    """Collector for Reddit data using PRAW."""

    def __init__(self):
        """Initialize Reddit collector."""
        super().__init__("Reddit", "social")
        self.reddit = None
        self.subreddits = settings.reddit_subreddits
        self.post_limit = settings.reddit_post_limit

    def _initialize_praw(self):
        """Initialize PRAW Reddit instance."""
        if not self.reddit:
            if settings.reddit_client_id and settings.reddit_client_secret:
                self.reddit = praw.Reddit(
                    client_id=settings.reddit_client_id,
                    client_secret=settings.reddit_client_secret,
                    user_agent=settings.reddit_user_agent
                )
            else:
                # Use read-only mode without credentials
                self.reddit = praw.Reddit(
                    client_id="dummy",
                    client_secret="dummy",
                    user_agent=settings.reddit_user_agent,
                    redirect_uri="http://localhost:8080",
                    refresh_token="dummy"
                )
                self.reddit.read_only = True

    async def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch data from Reddit.

        Returns:
            List of Reddit posts and comments
        """
        # PRAW is synchronous, so we run it in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_sync)

    def _fetch_sync(self) -> List[Dict[str, Any]]:
        """Synchronous fetch method for PRAW.

        Returns:
            List of Reddit posts
        """
        self._initialize_praw()
        all_posts = []

        for subreddit_name in self.subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)

                # Get hot posts
                for post in subreddit.hot(limit=self.post_limit // 2):
                    all_posts.append(self._parse_post(post, subreddit_name))

                # Get new posts
                for post in subreddit.new(limit=self.post_limit // 2):
                    all_posts.append(self._parse_post(post, subreddit_name))

            except Exception as e:
                self.logger.error(f"Error fetching from r/{subreddit_name}: {e}")

        return all_posts

    def _parse_post(self, post, subreddit_name: str) -> Dict[str, Any]:
        """Parse Reddit post into standardized format.

        Args:
            post: PRAW submission object
            subreddit_name: Name of subreddit

        Returns:
            Parsed post data
        """
        # Calculate engagement metrics
        total_engagement = post.score + post.num_comments
        engagement_ratio = post.upvote_ratio if hasattr(post, 'upvote_ratio') else 0.5

        # Determine sentiment from upvote ratio and comments
        if engagement_ratio > 0.7:
            sentiment = "bullish"
            sentiment_score = (engagement_ratio - 0.5) * 2
        elif engagement_ratio < 0.3:
            sentiment = "bearish"
            sentiment_score = (engagement_ratio - 0.5) * 2
        else:
            sentiment = "neutral"
            sentiment_score = 0.0

        return {
            "title": post.title,
            "content": post.selftext[:2000] if post.selftext else "",
            "url": f"https://reddit.com{post.permalink}",
            "author": str(post.author) if post.author else "deleted",
            "timestamp": datetime.utcfromtimestamp(post.created_utc),
            "metadata": {
                "source": "Reddit",
                "subreddit": subreddit_name,
                "post_id": post.id,
                "score": post.score,
                "num_comments": post.num_comments,
                "upvote_ratio": engagement_ratio,
                "total_engagement": total_engagement,
                "flair": post.link_flair_text if post.link_flair_text else None,
                "is_stickied": post.stickied,
                "sentiment_score": sentiment_score,
            }
        }

    def parse_data(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Parse raw data (already parsed in _fetch_sync).

        Args:
            raw_data: Pre-parsed data

        Returns:
            List of parsed items
        """
        return raw_data