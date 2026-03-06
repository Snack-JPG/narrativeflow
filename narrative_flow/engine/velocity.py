"""Mention velocity and influencer weighting calculations."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class MentionEvent:
    """Single mention event with metadata."""
    timestamp: datetime
    narrative: str
    source: str  # reddit, twitter, news, etc.
    weight: float = 1.0  # Influencer weight
    sentiment: float = 0.0  # -1 to 1


@dataclass
class VelocityWindow:
    """Rolling window for velocity calculations."""
    duration: timedelta
    events: deque = field(default_factory=deque)
    current_count: int = 0
    current_weighted_count: float = 0.0


class VelocityCalculator:
    """Calculate mention velocity across different time windows."""

    def __init__(self):
        """Initialize velocity calculator with rolling windows."""
        self.windows = {
            '1h': VelocityWindow(duration=timedelta(hours=1)),
            '4h': VelocityWindow(duration=timedelta(hours=4)),
            '24h': VelocityWindow(duration=timedelta(hours=24)),
            '7d': VelocityWindow(duration=timedelta(days=7))
        }

        # Store events by narrative for detailed analysis
        self.narrative_events = defaultdict(list)

    def add_mention(self, event: MentionEvent):
        """Add a new mention event and update velocities."""
        # Add to narrative-specific storage
        self.narrative_events[event.narrative].append(event)

        # Add to each window
        for window in self.windows.values():
            window.events.append(event)
            window.current_count += 1
            window.current_weighted_count += event.weight

        # Clean old events
        self._clean_old_events()

    def _clean_old_events(self):
        """Remove events outside of window durations."""
        now = datetime.now()

        for window_name, window in self.windows.items():
            # Remove old events from the front of the deque
            while window.events and (now - window.events[0].timestamp) > window.duration:
                old_event = window.events.popleft()
                window.current_count -= 1
                window.current_weighted_count -= old_event.weight

    def get_velocity(self, narrative: str,
                     window: str = '1h') -> Dict[str, float]:
        """
        Get mention velocity for a narrative in specified window.

        Returns:
            Dict with velocity metrics
        """
        if window not in self.windows:
            raise ValueError(f"Invalid window: {window}. Use: {list(self.windows.keys())}")

        self._clean_old_events()
        window_obj = self.windows[window]

        # Filter events for this narrative
        narrative_events = [e for e in window_obj.events if e.narrative == narrative]

        if not narrative_events:
            return {
                'mentions_per_hour': 0.0,
                'weighted_mentions_per_hour': 0.0,
                'acceleration': 0.0,
                'sentiment_weighted': 0.0
            }

        # Calculate base metrics
        hours = window_obj.duration.total_seconds() / 3600
        raw_velocity = len(narrative_events) / hours
        weighted_velocity = sum(e.weight for e in narrative_events) / hours

        # Calculate acceleration (velocity change)
        acceleration = self._calculate_acceleration(narrative, window)

        # Calculate sentiment-weighted velocity
        sentiment_weighted = sum(
            e.weight * (1 + e.sentiment) for e in narrative_events
        ) / hours

        return {
            'mentions_per_hour': raw_velocity,
            'weighted_mentions_per_hour': weighted_velocity,
            'acceleration': acceleration,
            'sentiment_weighted': sentiment_weighted
        }

    def _calculate_acceleration(self, narrative: str, window: str) -> float:
        """Calculate velocity change (acceleration) over time."""
        window_obj = self.windows[window]
        narrative_events = [e for e in window_obj.events if e.narrative == narrative]

        if len(narrative_events) < 2:
            return 0.0

        # Split window in half and compare velocities
        mid_time = datetime.now() - (window_obj.duration / 2)

        first_half = [e for e in narrative_events if e.timestamp < mid_time]
        second_half = [e for e in narrative_events if e.timestamp >= mid_time]

        if not first_half or not second_half:
            return 0.0

        hours = window_obj.duration.total_seconds() / 7200  # Half window in hours

        first_velocity = len(first_half) / hours
        second_velocity = len(second_half) / hours

        # Return percentage change
        if first_velocity > 0:
            return ((second_velocity - first_velocity) / first_velocity) * 100
        else:
            return 100.0 if second_velocity > 0 else 0.0

    def get_all_velocities(self, narrative: str) -> Dict[str, Dict[str, float]]:
        """Get velocities across all time windows."""
        return {
            window: self.get_velocity(narrative, window)
            for window in self.windows.keys()
        }

    def get_trending_narratives(self, window: str = '4h',
                              min_mentions: int = 5) -> List[Dict]:
        """
        Get narratives with highest velocity/acceleration.

        Args:
            window: Time window to analyze
            min_mentions: Minimum mentions required

        Returns:
            List of trending narratives sorted by momentum
        """
        self._clean_old_events()
        window_obj = self.windows[window]

        # Count mentions by narrative
        narrative_counts = defaultdict(lambda: {
            'count': 0,
            'weighted_count': 0.0,
            'sentiment_sum': 0.0
        })

        for event in window_obj.events:
            narrative_counts[event.narrative]['count'] += 1
            narrative_counts[event.narrative]['weighted_count'] += event.weight
            narrative_counts[event.narrative]['sentiment_sum'] += event.sentiment

        # Calculate metrics for each narrative
        trending = []
        hours = window_obj.duration.total_seconds() / 3600

        for narrative, counts in narrative_counts.items():
            if counts['count'] < min_mentions:
                continue

            velocity = counts['count'] / hours
            weighted_velocity = counts['weighted_count'] / hours
            avg_sentiment = counts['sentiment_sum'] / counts['count']
            acceleration = self._calculate_acceleration(narrative, window)

            # Calculate momentum score (combination of velocity and acceleration)
            momentum = weighted_velocity * (1 + acceleration / 100) * (1 + avg_sentiment)

            trending.append({
                'narrative': narrative,
                'velocity': velocity,
                'weighted_velocity': weighted_velocity,
                'acceleration': acceleration,
                'avg_sentiment': avg_sentiment,
                'momentum_score': momentum,
                'mention_count': counts['count']
            })

        # Sort by momentum score
        trending.sort(key=lambda x: x['momentum_score'], reverse=True)

        return trending


class InfluencerWeighting:
    """Calculate influence weights for social media sources."""

    @staticmethod
    def calculate_reddit_weight(karma: int, account_age_days: int,
                              subreddit_karma: Optional[int] = None) -> float:
        """
        Calculate influence weight for Reddit users.

        Args:
            karma: Total karma
            account_age_days: Account age in days
            subreddit_karma: Karma in specific subreddit (optional)

        Returns:
            Weight from 0.1 to 5.0
        """
        # Base weight from karma (logarithmic scale)
        if karma <= 0:
            karma_weight = 0.1
        else:
            # Log scale: 100 karma = 0.5, 1k = 1.0, 10k = 1.5, 100k = 2.0
            karma_weight = min(math.log10(karma) / 2, 2.0)

        # Account age factor (new accounts get lower weight)
        if account_age_days < 30:
            age_factor = 0.3
        elif account_age_days < 90:
            age_factor = 0.5
        elif account_age_days < 365:
            age_factor = 0.8
        else:
            age_factor = 1.0

        # Subreddit-specific karma bonus
        subreddit_bonus = 0.0
        if subreddit_karma and subreddit_karma > 100:
            subreddit_bonus = min(math.log10(subreddit_karma) / 4, 0.5)

        # Calculate final weight
        weight = (karma_weight * age_factor) + subreddit_bonus

        # Ensure minimum weight of 0.1 and maximum of 5.0
        return max(0.1, min(5.0, weight))

    @staticmethod
    def calculate_twitter_weight(followers: int, verified: bool = False,
                                engagement_rate: Optional[float] = None) -> float:
        """
        Calculate influence weight for Twitter users.

        Args:
            followers: Follower count
            verified: Blue checkmark status
            engagement_rate: Average engagement rate (optional)

        Returns:
            Weight from 0.1 to 10.0
        """
        # Base weight from followers (logarithmic scale)
        if followers <= 0:
            follower_weight = 0.1
        else:
            # Log scale: 100 = 0.5, 1k = 1.0, 10k = 2.0, 100k = 3.0, 1M = 4.0
            follower_weight = min(math.log10(followers + 1) / 1.5, 4.0)

        # Verified bonus
        verified_bonus = 1.0 if verified else 0.0

        # Engagement rate bonus (if available)
        engagement_bonus = 0.0
        if engagement_rate:
            # Good engagement (>2%) gets bonus
            if engagement_rate > 0.02:
                engagement_bonus = min(engagement_rate * 10, 1.0)

        # Calculate final weight
        weight = follower_weight + verified_bonus + engagement_bonus

        return max(0.1, min(10.0, weight))

    @staticmethod
    def calculate_news_weight(source_reputation: str,
                            author_reputation: Optional[str] = None) -> float:
        """
        Calculate weight for news sources.

        Args:
            source_reputation: 'high', 'medium', 'low'
            author_reputation: Optional author reputation

        Returns:
            Weight from 0.5 to 5.0
        """
        source_weights = {
            'high': 3.0,    # CoinDesk, CoinTelegraph, The Block
            'medium': 1.5,  # Medium blogs, smaller outlets
            'low': 0.5      # Unknown sources
        }

        weight = source_weights.get(source_reputation.lower(), 1.0)

        # Author reputation bonus
        if author_reputation:
            author_weights = {
                'high': 1.0,
                'medium': 0.5,
                'low': 0.0
            }
            weight += author_weights.get(author_reputation.lower(), 0.0)

        return max(0.5, min(5.0, weight))


class MomentumTracker:
    """Track narrative momentum combining velocity and influence."""

    def __init__(self, velocity_calculator: VelocityCalculator):
        """Initialize momentum tracker."""
        self.velocity_calculator = velocity_calculator
        self.influencer_weighting = InfluencerWeighting()

    def add_reddit_mention(self, narrative: str, content: str,
                          karma: int, account_age_days: int,
                          sentiment: float = 0.0,
                          subreddit_karma: Optional[int] = None):
        """Add weighted Reddit mention."""
        weight = self.influencer_weighting.calculate_reddit_weight(
            karma, account_age_days, subreddit_karma
        )

        event = MentionEvent(
            timestamp=datetime.now(),
            narrative=narrative,
            source='reddit',
            weight=weight,
            sentiment=sentiment
        )

        self.velocity_calculator.add_mention(event)

    def add_twitter_mention(self, narrative: str, content: str,
                           followers: int, verified: bool = False,
                           sentiment: float = 0.0,
                           engagement_rate: Optional[float] = None):
        """Add weighted Twitter mention."""
        weight = self.influencer_weighting.calculate_twitter_weight(
            followers, verified, engagement_rate
        )

        event = MentionEvent(
            timestamp=datetime.now(),
            narrative=narrative,
            source='twitter',
            weight=weight,
            sentiment=sentiment
        )

        self.velocity_calculator.add_mention(event)

    def add_news_mention(self, narrative: str, content: str,
                        source_reputation: str,
                        sentiment: float = 0.0,
                        author_reputation: Optional[str] = None):
        """Add weighted news mention."""
        weight = self.influencer_weighting.calculate_news_weight(
            source_reputation, author_reputation
        )

        event = MentionEvent(
            timestamp=datetime.now(),
            narrative=narrative,
            source='news',
            weight=weight,
            sentiment=sentiment
        )

        self.velocity_calculator.add_mention(event)

    def get_narrative_momentum(self, narrative: str) -> Dict:
        """
        Get comprehensive momentum metrics for a narrative.

        Returns:
            Dict with velocity, influence, and combined momentum scores
        """
        velocities = self.velocity_calculator.get_all_velocities(narrative)

        # Calculate combined momentum score
        # Weight recent activity more heavily
        momentum_score = (
            velocities['1h']['sentiment_weighted'] * 3 +
            velocities['4h']['sentiment_weighted'] * 2 +
            velocities['24h']['sentiment_weighted'] * 1
        ) / 6

        # Apply acceleration bonus/penalty
        acceleration = velocities['4h']['acceleration']
        if acceleration > 0:
            momentum_score *= (1 + acceleration / 200)  # Up to 50% bonus
        else:
            momentum_score *= (1 + acceleration / 400)  # Up to 25% penalty

        return {
            'velocities': velocities,
            'momentum_score': momentum_score,
            'trending': momentum_score > 5.0,  # Threshold for trending
            'acceleration': acceleration
        }