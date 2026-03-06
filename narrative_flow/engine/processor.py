"""Main processing engine for narrative classification and enrichment."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from sqlalchemy.orm import Session

from narrative_flow.models.database import (
    RawData, EnrichedData, NarrativeMetrics,
    VelocitySnapshot
)
from narrative_flow.engine.classifier import NarrativeClassifier
from narrative_flow.engine.ai_classifier import HybridClassifier, AIClassifier
from narrative_flow.engine.sentiment import SentimentAnalyzer
from narrative_flow.engine.velocity import VelocityCalculator, MomentumTracker
from narrative_flow.engine.novelty import NoveltyScorer

logger = logging.getLogger(__name__)


class NarrativeProcessor:
    """Main processor for enriching raw data with narrative analysis."""

    def __init__(self, db_session: Session,
                 enable_ai: bool = True,
                 anthropic_api_key: Optional[str] = None):
        """
        Initialize the narrative processor.

        Args:
            db_session: SQLAlchemy database session
            enable_ai: Enable Claude API for classification
            anthropic_api_key: Optional Anthropic API key
        """
        self.db_session = db_session

        # Initialize components
        self.classifier = NarrativeClassifier()

        # AI classifier (optional)
        self.ai_classifier = None
        if enable_ai:
            self.ai_classifier = AIClassifier(api_key=anthropic_api_key)

        self.hybrid_classifier = HybridClassifier(
            classifier=self.classifier,
            ai_classifier=self.ai_classifier
        )

        self.sentiment_analyzer = SentimentAnalyzer()
        self.velocity_calculator = VelocityCalculator()
        self.momentum_tracker = MomentumTracker(self.velocity_calculator)
        self.novelty_scorer = NoveltyScorer()

        # Processing stats
        self.stats = {
            'items_processed': 0,
            'total_processing_time': 0,
            'errors': 0
        }

    async def process_item(self, raw_data: RawData) -> EnrichedData:
        """
        Process a single raw data item.

        Args:
            raw_data: Raw data item from database

        Returns:
            Enriched data with narrative classification and sentiment
        """
        start_time = datetime.now()

        try:
            # Extract text content
            title = raw_data.title or ""
            content = raw_data.content or ""
            full_text = f"{title} {content}"

            # 1. Classify narrative (< 1ms target)
            classification = await self.hybrid_classifier.classify(
                item_id=str(raw_data.id),
                title=title,
                content=content,
                metadata=raw_data.source_metadata
            )

            # 2. Analyze sentiment
            cryptopanic_sentiment = None
            if raw_data.source_metadata and 'sentiment' in raw_data.source_metadata:
                cryptopanic_sentiment = raw_data.source_metadata['sentiment']

            sentiment = self.sentiment_analyzer.analyze(
                text=content,
                title=title,
                cryptopanic_sentiment=cryptopanic_sentiment
            )

            # 3. Calculate novelty
            novelty = self.novelty_scorer.calculate_novelty_score(
                content=full_text,
                narrative=classification['narratives'][0] if classification['narratives'] else "",
                timestamp=raw_data.timestamp
            )

            # 4. Extract influencer metrics (if available)
            influencer_weight = 1.0
            reddit_karma = None
            reddit_age = None
            twitter_followers = None
            twitter_verified = False

            if raw_data.source_metadata:
                # Reddit metrics
                if raw_data.source.name == 'reddit':
                    reddit_karma = raw_data.source_metadata.get('author_karma')
                    reddit_age = raw_data.source_metadata.get('author_age_days')
                    reddit_subreddit = raw_data.source_metadata.get('subreddit')

                    if reddit_karma and reddit_age:
                        influencer_weight = self.momentum_tracker.influencer_weighting.calculate_reddit_weight(
                            karma=reddit_karma,
                            account_age_days=reddit_age
                        )

                # Twitter metrics (if implemented)
                elif raw_data.source.name == 'twitter':
                    twitter_followers = raw_data.source_metadata.get('author_followers')
                    twitter_verified = raw_data.source_metadata.get('author_verified', False)

                    if twitter_followers:
                        influencer_weight = self.momentum_tracker.influencer_weighting.calculate_twitter_weight(
                            followers=twitter_followers,
                            verified=twitter_verified
                        )

            # 5. Add to velocity tracking
            for narrative in classification['narratives']:
                self.velocity_calculator.add_mention(
                    event={
                        'timestamp': raw_data.timestamp,
                        'narrative': narrative,
                        'source': raw_data.source.name,
                        'weight': influencer_weight,
                        'sentiment': sentiment.score
                    }
                )

            # 6. Create enriched data record
            enriched = EnrichedData(
                raw_data_id=raw_data.id,
                timestamp=raw_data.timestamp,

                # Classification
                primary_narrative=classification['narratives'][0] if classification['narratives'] else None,
                all_narratives=classification['narratives'],
                classification_confidence=classification['confidence'],
                classification_method=classification['method'],

                # Sentiment
                sentiment_label=sentiment.label.value,
                sentiment_score=sentiment.score,
                sentiment_confidence=sentiment.confidence,
                sentiment_method=sentiment.method,

                # Influence
                influencer_weight=influencer_weight,
                source_reputation=self._get_source_reputation(raw_data.source.name),

                # Novelty
                novelty_score=novelty['novelty_score'],
                is_novel=novelty['is_novel'],
                is_duplicate=novelty['is_duplicate'],
                new_terms=novelty['new_terms'][:10] if novelty['new_terms'] else [],

                # Tokens
                extracted_tokens=classification.get('tokens', []),

                # Reddit specific
                reddit_karma=reddit_karma,
                reddit_account_age=reddit_age,

                # Twitter specific
                twitter_followers=twitter_followers,
                twitter_verified=twitter_verified,

                # Processing metadata
                processed_at=datetime.now(),
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )

            # Save to database
            self.db_session.add(enriched)

            # Update stats
            self.stats['items_processed'] += 1
            self.stats['total_processing_time'] += enriched.processing_time_ms

            # Log if processing took too long
            if enriched.processing_time_ms > 10:
                logger.warning(f"Processing took {enriched.processing_time_ms}ms for item {raw_data.id}")

            return enriched

        except Exception as e:
            logger.error(f"Error processing item {raw_data.id}: {e}")
            self.stats['errors'] += 1
            raise

    def _get_source_reputation(self, source_name: str) -> str:
        """Determine source reputation."""
        high_reputation = {
            'cryptopanic', 'coingecko', 'coindesk',
            'cointelegraph', 'theblock', 'decrypt'
        }
        medium_reputation = {
            'reddit', 'twitter', 'medium'
        }

        source_lower = source_name.lower()
        if source_lower in high_reputation:
            return 'high'
        elif source_lower in medium_reputation:
            return 'medium'
        else:
            return 'low'

    async def process_batch(self, raw_items: List[RawData]) -> List[EnrichedData]:
        """
        Process a batch of raw data items.

        Args:
            raw_items: List of raw data items

        Returns:
            List of enriched data items
        """
        logger.info(f"Processing batch of {len(raw_items)} items")

        # Process items concurrently (but with controlled concurrency)
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

        async def process_with_semaphore(item):
            async with semaphore:
                return await self.process_item(item)

        tasks = [process_with_semaphore(item) for item in raw_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out errors
        enriched_items = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing error: {result}")
            else:
                enriched_items.append(result)

        # Process any pending AI classifications
        if self.ai_classifier:
            ai_results = await self.ai_classifier.flush()
            logger.info(f"Processed {len(ai_results)} AI classifications")

        # Commit all changes
        self.db_session.commit()

        logger.info(f"Successfully processed {len(enriched_items)} items")
        return enriched_items

    def update_narrative_metrics(self, narrative: str):
        """
        Update aggregate metrics for a narrative.

        Args:
            narrative: Narrative category to update
        """
        # Get velocity metrics
        velocities = self.velocity_calculator.get_all_velocities(narrative)

        # Get recent enriched data for this narrative
        recent_enriched = self.db_session.query(EnrichedData).filter(
            EnrichedData.primary_narrative == narrative,
            EnrichedData.timestamp > datetime.now() - timedelta(hours=24)
        ).all()

        if not recent_enriched:
            return

        # Calculate aggregate sentiment
        sentiment_scores = [e.sentiment_score for e in recent_enriched]
        bullish_count = sum(1 for e in recent_enriched if e.sentiment_label == 'bullish')

        # Calculate average novelty
        novelty_scores = [e.novelty_score for e in recent_enriched if e.novelty_score]
        innovation_rate = sum(1 for e in recent_enriched if e.is_novel) / len(recent_enriched)

        # Create or update metrics record
        metrics = NarrativeMetrics(
            timestamp=datetime.now(),
            narrative_category=narrative,

            # Social metrics
            mention_count=len(recent_enriched),
            mention_velocity=velocities['1h']['mentions_per_hour'],
            sentiment_avg=sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0,
            sentiment_bullish_pct=(bullish_count / len(recent_enriched)) * 100,

            # New Phase 2 metrics
            weighted_velocity=velocities['1h']['weighted_mentions_per_hour'],
            acceleration=velocities['4h']['acceleration'],
            novelty_score=sum(novelty_scores) / len(novelty_scores) if novelty_scores else 0,
            innovation_rate=innovation_rate * 100,

            # Calculate momentum score
            momentum_score=self._calculate_momentum_score(
                velocities, sentiment_scores, novelty_scores
            )
        )

        self.db_session.add(metrics)

        # Create velocity snapshots for different windows
        for window, velocity_data in velocities.items():
            snapshot = VelocitySnapshot(
                timestamp=datetime.now(),
                narrative_category=narrative,
                time_window=window,
                mentions_per_hour=velocity_data['mentions_per_hour'],
                weighted_mentions_per_hour=velocity_data['weighted_mentions_per_hour'],
                acceleration=velocity_data['acceleration'],
                sentiment_weighted_velocity=velocity_data['sentiment_weighted']
            )
            self.db_session.add(snapshot)

        self.db_session.commit()

    def _calculate_momentum_score(self, velocities: Dict,
                                 sentiment_scores: List[float],
                                 novelty_scores: List[float]) -> float:
        """Calculate combined momentum score."""
        # Weight recent activity more heavily
        velocity_score = (
            velocities['1h']['weighted_mentions_per_hour'] * 3 +
            velocities['4h']['weighted_mentions_per_hour'] * 2 +
            velocities['24h']['weighted_mentions_per_hour'] * 1
        ) / 6

        # Apply sentiment modifier
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        sentiment_modifier = 1 + avg_sentiment  # Range: 0 to 2

        # Apply novelty modifier
        avg_novelty = sum(novelty_scores) / len(novelty_scores) if novelty_scores else 0.5
        novelty_modifier = 0.8 + (avg_novelty * 0.4)  # Range: 0.8 to 1.2

        # Apply acceleration bonus/penalty
        acceleration = velocities['4h']['acceleration']
        if acceleration > 0:
            acceleration_modifier = 1 + (acceleration / 200)  # Up to 50% bonus
        else:
            acceleration_modifier = 1 + (acceleration / 400)  # Up to 25% penalty

        # Calculate final momentum
        momentum = velocity_score * sentiment_modifier * novelty_modifier * acceleration_modifier

        return round(momentum, 2)

    def get_stats(self) -> Dict:
        """Get processing statistics."""
        avg_time = (
            self.stats['total_processing_time'] / self.stats['items_processed']
            if self.stats['items_processed'] > 0 else 0
        )

        return {
            **self.stats,
            'avg_processing_time_ms': avg_time,
            'classifier_stats': self.hybrid_classifier.get_stats() if self.hybrid_classifier else {}
        }