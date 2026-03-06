"""AI-powered narrative classification using Claude API."""

import os
import json
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from collections import deque
import anthropic
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


@dataclass
class ClassificationRequest:
    """Request for AI classification."""
    id: str
    title: str
    content: str
    timestamp: datetime
    source_metadata: Dict[str, Any]


@dataclass
class ClassificationResult:
    """Result from AI classification."""
    id: str
    narratives: List[str]
    confidence: float
    reasoning: Optional[str] = None


class AIClassifier:
    """Claude API integration for nuanced classification of ambiguous items."""

    def __init__(self, api_key: Optional[str] = None,
                 rate_limit: int = 10,
                 batch_size: int = 5):
        """
        Initialize AI classifier with rate limiting.

        Args:
            api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
            rate_limit: Max requests per minute
            batch_size: Items to process in one API call
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            logger.warning("No Anthropic API key found. AI classification disabled.")
            self.client = None
        else:
            self.client = AsyncAnthropic(api_key=self.api_key)

        self.rate_limit = rate_limit
        self.batch_size = batch_size

        # Rate limiting
        self.request_times = deque(maxlen=rate_limit)
        self.pending_items = []
        self.processing_lock = asyncio.Lock()

    def _get_classification_prompt(self, items: List[ClassificationRequest]) -> str:
        """Generate prompt for Claude to classify items."""
        items_text = ""
        for i, item in enumerate(items, 1):
            items_text += f"""
Item {i}:
Title: {item.title[:200] if item.title else 'N/A'}
Content: {item.content[:500] if item.content else 'N/A'}
---
"""

        return f"""You are a crypto narrative classifier. Classify each item into one or more of these narrative categories:
- AI: Artificial intelligence, machine learning, autonomous agents
- RWA: Real World Assets, tokenized assets, institutional adoption
- DePIN: Decentralized Physical Infrastructure Networks
- Memecoin: Meme-based cryptocurrencies, community coins
- L1/L2: Layer 1 and Layer 2 blockchains, scaling solutions
- NFT: Non-fungible tokens, digital collectibles, art
- DeFi: Decentralized finance protocols, yield, lending
- Gaming: GameFi, play-to-earn, metaverse
- Privacy: Privacy coins, zero-knowledge proofs, mixers
- Derivatives: Perpetuals, options, synthetic assets
- Social: Social tokens, decentralized social networks
- Infrastructure: Oracles, indexers, developer tools

For each item, provide:
1. The most relevant narrative categories (1-3 max)
2. A confidence score (0.0-1.0)
3. Brief reasoning (one sentence)

Items to classify:
{items_text}

Return your response as a JSON array with this structure:
[
  {{
    "item_id": 1,
    "narratives": ["AI", "Infrastructure"],
    "confidence": 0.85,
    "reasoning": "Discusses AI agents using oracle infrastructure"
  }},
  ...
]

Focus on the primary narrative theme. Be selective - not everything needs multiple categories."""

    async def _check_rate_limit(self):
        """Check if we can make another API request."""
        now = datetime.now()

        # Remove requests older than 1 minute
        while self.request_times and (now - self.request_times[0]) > timedelta(minutes=1):
            self.request_times.popleft()

        # Check if we can make another request
        if len(self.request_times) >= self.rate_limit:
            # Wait until oldest request is 1 minute old
            wait_time = 60 - (now - self.request_times[0]).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached. Waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                return await self._check_rate_limit()

        self.request_times.append(now)
        return True

    async def classify_batch(self, items: List[ClassificationRequest]) -> List[ClassificationResult]:
        """
        Classify a batch of items using Claude API.

        Args:
            items: List of items to classify

        Returns:
            List of classification results
        """
        if not self.client:
            logger.warning("AI classification unavailable (no API key)")
            return [
                ClassificationResult(
                    id=item.id,
                    narratives=[],
                    confidence=0.0
                ) for item in items
            ]

        async with self.processing_lock:
            await self._check_rate_limit()

            try:
                # Build prompt
                prompt = self._get_classification_prompt(items)

                # Call Claude API
                message = await self.client.messages.create(
                    model="claude-3-haiku-20240307",  # Fast, cheap model for classification
                    max_tokens=1000,
                    temperature=0.3,  # Lower temperature for consistent classification
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                # Parse response
                response_text = message.content[0].text

                # Extract JSON from response
                try:
                    # Find JSON array in response
                    start_idx = response_text.find('[')
                    end_idx = response_text.rfind(']') + 1
                    json_str = response_text[start_idx:end_idx]
                    classifications = json.loads(json_str)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Failed to parse Claude response: {e}")
                    logger.debug(f"Response was: {response_text}")
                    return self._fallback_results(items)

                # Map results back to items
                results = []
                result_map = {c['item_id']: c for c in classifications}

                for i, item in enumerate(items, 1):
                    if i in result_map:
                        classification = result_map[i]
                        results.append(ClassificationResult(
                            id=item.id,
                            narratives=classification.get('narratives', []),
                            confidence=classification.get('confidence', 0.5),
                            reasoning=classification.get('reasoning')
                        ))
                    else:
                        results.append(ClassificationResult(
                            id=item.id,
                            narratives=[],
                            confidence=0.0
                        ))

                logger.info(f"Successfully classified {len(results)} items via AI")
                return results

            except Exception as e:
                logger.error(f"AI classification failed: {e}")
                return self._fallback_results(items)

    def _fallback_results(self, items: List[ClassificationRequest]) -> List[ClassificationResult]:
        """Generate fallback results when AI classification fails."""
        return [
            ClassificationResult(
                id=item.id,
                narratives=[],
                confidence=0.0,
                reasoning="AI classification unavailable"
            ) for item in items
        ]

    async def add_item(self, item: ClassificationRequest):
        """Add item to pending queue for batch processing."""
        self.pending_items.append(item)

        # Process if batch is full
        if len(self.pending_items) >= self.batch_size:
            await self.process_pending()

    async def process_pending(self) -> List[ClassificationResult]:
        """Process all pending items."""
        if not self.pending_items:
            return []

        # Take items to process
        items_to_process = self.pending_items[:self.batch_size]
        self.pending_items = self.pending_items[self.batch_size:]

        # Classify batch
        results = await self.classify_batch(items_to_process)

        return results

    async def flush(self) -> List[ClassificationResult]:
        """Process all remaining pending items."""
        all_results = []

        while self.pending_items:
            results = await self.process_pending()
            all_results.extend(results)

        return all_results


class HybridClassifier:
    """Combines fast keyword matching with AI classification."""

    def __init__(self, classifier, ai_classifier: Optional[AIClassifier] = None):
        """
        Initialize hybrid classifier.

        Args:
            classifier: Fast keyword-based classifier
            ai_classifier: Optional AI classifier for ambiguous items
        """
        self.classifier = classifier
        self.ai_classifier = ai_classifier
        self.stats = {
            'fast_classifications': 0,
            'ai_classifications': 0,
            'total_items': 0
        }

    async def classify(self, item_id: str, title: str, content: str,
                       metadata: Optional[Dict] = None) -> Dict:
        """
        Classify an item using hybrid approach.

        Returns:
            Dict with narratives, confidence, and method used
        """
        self.stats['total_items'] += 1

        # Extract tokens for better classification
        tokens = self.classifier.extract_tokens(f"{title} {content}")

        # Try fast classification first
        fast_categories, confidence = self.classifier.classify_fast(
            content, title, tokens
        )

        # Check if we need AI help
        if self.classifier.needs_ai_classification(fast_categories, confidence):
            if self.ai_classifier:
                # Queue for AI classification
                request = ClassificationRequest(
                    id=item_id,
                    title=title,
                    content=content,
                    timestamp=datetime.now(),
                    metadata=metadata or {}
                )

                await self.ai_classifier.add_item(request)
                self.stats['ai_classifications'] += 1

                # For now, return fast results (AI results will be processed async)
                return {
                    'narratives': [cat.value for cat in fast_categories],
                    'confidence': confidence,
                    'method': 'fast_pending_ai',
                    'tokens': tokens
                }

        self.stats['fast_classifications'] += 1

        return {
            'narratives': [cat.value for cat in fast_categories],
            'confidence': confidence,
            'method': 'fast',
            'tokens': tokens
        }

    def get_stats(self) -> Dict:
        """Get classification statistics."""
        return {
            **self.stats,
            'ai_percentage': (
                self.stats['ai_classifications'] / max(self.stats['total_items'], 1) * 100
            )
        }