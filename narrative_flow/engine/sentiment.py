"""Sentiment scoring engine for crypto narrative analysis."""

import re
from typing import Dict, Tuple, Optional, List
from datetime import datetime
from dataclasses import dataclass
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class SentimentLabel(Enum):
    """Sentiment categories."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class SentimentScore:
    """Detailed sentiment scoring result."""
    label: SentimentLabel
    score: float  # -1.0 (bearish) to 1.0 (bullish)
    confidence: float  # 0.0 to 1.0
    method: str  # 'cryptopanic', 'keywords', 'hybrid'
    reasoning: Optional[str] = None


class SentimentAnalyzer:
    """Fast sentiment scoring for crypto content."""

    def __init__(self):
        """Initialize sentiment analyzer with crypto-specific patterns."""
        self.bullish_keywords = self._init_bullish_keywords()
        self.bearish_keywords = self._init_bearish_keywords()
        self.amplifiers = self._init_amplifiers()
        self.negations = {'not', 'no', 'never', 'neither', 'nor', "n't", 'none'}

    def _init_bullish_keywords(self) -> Dict[str, float]:
        """Initialize bullish sentiment keywords with weights."""
        return {
            # Strong bullish (0.8-1.0)
            'moon': 0.9,
            'moonshot': 1.0,
            'parabolic': 0.9,
            'breakout': 0.8,
            'bullish': 0.8,
            'pump': 0.8,
            'rally': 0.8,
            'surge': 0.8,
            'explode': 0.9,
            'exploding': 0.9,
            'skyrocket': 0.9,

            # Moderate bullish (0.5-0.7)
            'buy': 0.6,
            'buying': 0.6,
            'accumulate': 0.7,
            'accumulating': 0.7,
            'hodl': 0.6,
            'hold': 0.5,
            'long': 0.6,
            'uptrend': 0.7,
            'recovery': 0.6,
            'bounce': 0.6,
            'support': 0.5,
            'bottom': 0.5,

            # Mild bullish (0.3-0.5)
            'good': 0.4,
            'great': 0.5,
            'excellent': 0.5,
            'amazing': 0.5,
            'positive': 0.4,
            'optimistic': 0.5,
            'promising': 0.5,
            'potential': 0.4,
            'opportunity': 0.4,
            'undervalued': 0.5,
            'cheap': 0.4,
            'discount': 0.4,

            # Technical bullish
            'golden cross': 0.8,
            'ascending': 0.6,
            'higher high': 0.6,
            'higher low': 0.6,
            'macd bullish': 0.7,
            'rsi oversold': 0.6,
            'cup and handle': 0.7,

            # Fundamental bullish
            'adoption': 0.6,
            'partnership': 0.6,
            'integration': 0.5,
            'mainnet': 0.6,
            'launch': 0.5,
            'upgrade': 0.5,
            'innovation': 0.5,
            'breakthrough': 0.7,

            # Emojis/symbols
            '🚀': 0.9,
            '📈': 0.7,
            '💎': 0.6,
            '🔥': 0.7,
            '⬆️': 0.6,
            '🟢': 0.6,
            '💚': 0.5,
            '🐂': 0.8,
            'LFG': 0.8,
            'WAGMI': 0.7,
        }

    def _init_bearish_keywords(self) -> Dict[str, float]:
        """Initialize bearish sentiment keywords with weights."""
        return {
            # Strong bearish (-0.8 to -1.0)
            'crash': -0.9,
            'dump': -0.8,
            'dumping': -0.8,
            'plunge': -0.8,
            'collapse': -0.9,
            'rekt': -0.9,
            'scam': -1.0,
            'rug': -1.0,
            'rugpull': -1.0,
            'ponzi': -1.0,
            'fraud': -1.0,

            # Moderate bearish (-0.5 to -0.7)
            'sell': -0.6,
            'selling': -0.6,
            'short': -0.6,
            'shorting': -0.6,
            'bearish': -0.7,
            'downtrend': -0.7,
            'decline': -0.6,
            'falling': -0.6,
            'drop': -0.6,
            'sink': -0.6,
            'resistance': -0.5,
            'overbought': -0.5,

            # Mild bearish (-0.3 to -0.5)
            'bad': -0.4,
            'terrible': -0.5,
            'awful': -0.5,
            'negative': -0.4,
            'pessimistic': -0.5,
            'concern': -0.4,
            'worried': -0.4,
            'overvalued': -0.5,
            'expensive': -0.4,
            'bubble': -0.5,

            # Technical bearish
            'death cross': -0.8,
            'descending': -0.6,
            'lower high': -0.6,
            'lower low': -0.6,
            'macd bearish': -0.7,
            'rsi overbought': -0.6,
            'head and shoulders': -0.7,

            # Fundamental bearish
            'hack': -0.8,
            'exploit': -0.8,
            'vulnerability': -0.6,
            'delay': -0.5,
            'lawsuit': -0.6,
            'regulation': -0.5,
            'ban': -0.7,
            'shutdown': -0.8,
            'bankruptcy': -0.9,

            # Emojis/symbols
            '📉': -0.7,
            '🔴': -0.6,
            '❌': -0.6,
            '⬇️': -0.6,
            '💔': -0.5,
            '😱': -0.5,
            '🐻': -0.8,
            'NGMI': -0.7,
            'GG': -0.6,
        }

    def _init_amplifiers(self) -> Dict[str, float]:
        """Initialize amplifier words that strengthen sentiment."""
        return {
            'very': 1.3,
            'extremely': 1.5,
            'absolutely': 1.4,
            'totally': 1.3,
            'completely': 1.3,
            'really': 1.2,
            'so': 1.2,
            'super': 1.3,
            'ultra': 1.4,
            'mega': 1.4,
            'huge': 1.3,
            'massive': 1.4,
            'insane': 1.5,
            'incredible': 1.3,
            'definitely': 1.2,
            'certainly': 1.2,
        }

    def analyze(self, text: str, title: str = "",
               cryptopanic_sentiment: Optional[str] = None) -> SentimentScore:
        """
        Analyze sentiment of crypto content.

        Args:
            text: Content to analyze
            title: Optional title (given higher weight)
            cryptopanic_sentiment: Pre-existing sentiment from CryptoPanic

        Returns:
            SentimentScore with label, score, and confidence
        """
        # Use CryptoPanic sentiment if available and high confidence
        if cryptopanic_sentiment:
            return self._process_cryptopanic_sentiment(cryptopanic_sentiment, text, title)

        # Otherwise, perform our own analysis
        return self._analyze_text(text, title)

    def _process_cryptopanic_sentiment(self, cp_sentiment: str,
                                      text: str, title: str) -> SentimentScore:
        """Process CryptoPanic sentiment and validate with our analysis."""
        # Map CryptoPanic sentiment to our scale
        cp_mapping = {
            'extremely-bullish': (SentimentLabel.BULLISH, 1.0),
            'bullish': (SentimentLabel.BULLISH, 0.7),
            'positive': (SentimentLabel.BULLISH, 0.5),
            'neutral': (SentimentLabel.NEUTRAL, 0.0),
            'negative': (SentimentLabel.BEARISH, -0.5),
            'bearish': (SentimentLabel.BEARISH, -0.7),
            'extremely-bearish': (SentimentLabel.BEARISH, -1.0),
        }

        if cp_sentiment.lower() in cp_mapping:
            label, base_score = cp_mapping[cp_sentiment.lower()]

            # Validate with quick keyword check
            our_score = self._calculate_raw_score(f"{title} {text}")

            # If our analysis strongly disagrees, reduce confidence
            if abs(our_score - base_score) > 0.5:
                confidence = 0.6
                # Average the scores
                final_score = (base_score + our_score) / 2
            else:
                confidence = 0.9
                final_score = base_score

            return SentimentScore(
                label=label,
                score=final_score,
                confidence=confidence,
                method='cryptopanic',
                reasoning=f"CryptoPanic: {cp_sentiment}"
            )

        # Fallback to our analysis if CryptoPanic sentiment is unknown
        return self._analyze_text(text, title)

    def _analyze_text(self, text: str, title: str = "") -> SentimentScore:
        """Perform keyword-based sentiment analysis."""
        # Combine and preprocess text
        full_text = f"{title} {title} {text}".lower()  # Title counted twice

        # Calculate raw sentiment score
        raw_score = self._calculate_raw_score(full_text)

        # Determine label and confidence
        if raw_score > 0.2:
            label = SentimentLabel.BULLISH
            confidence = min(abs(raw_score), 1.0)
        elif raw_score < -0.2:
            label = SentimentLabel.BEARISH
            confidence = min(abs(raw_score), 1.0)
        else:
            label = SentimentLabel.NEUTRAL
            confidence = 1.0 - abs(raw_score) * 2  # Higher confidence for clear neutral

        return SentimentScore(
            label=label,
            score=raw_score,
            confidence=confidence,
            method='keywords'
        )

    def _calculate_raw_score(self, text: str) -> float:
        """Calculate raw sentiment score from text."""
        words = text.split()
        total_score = 0.0
        word_count = 0

        i = 0
        while i < len(words):
            word = words[i]

            # Check for negation
            is_negated = False
            if i > 0 and words[i-1] in self.negations:
                is_negated = True

            # Check for amplifier
            amplifier = 1.0
            if i > 0 and words[i-1] in self.amplifiers:
                amplifier = self.amplifiers[words[i-1]]

            # Calculate word sentiment
            word_score = 0.0

            # Check bullish keywords
            for keyword, score in self.bullish_keywords.items():
                if keyword in word or word in keyword.split():
                    word_score = score
                    break

            # Check bearish keywords if not bullish
            if word_score == 0:
                for keyword, score in self.bearish_keywords.items():
                    if keyword in word or word in keyword.split():
                        word_score = score
                        break

            # Apply negation and amplification
            if is_negated:
                word_score = -word_score * 0.5  # Negation weakens sentiment
            word_score *= amplifier

            if word_score != 0:
                total_score += word_score
                word_count += 1

            i += 1

        # Calculate average score
        if word_count > 0:
            avg_score = total_score / word_count

            # Apply sigmoid-like transformation to keep in [-1, 1] range
            import math
            return math.tanh(avg_score)
        else:
            return 0.0

    def batch_analyze(self, items: List[Dict]) -> List[SentimentScore]:
        """
        Analyze sentiment for multiple items.

        Args:
            items: List of dicts with 'text', 'title', and optional 'cryptopanic_sentiment'

        Returns:
            List of SentimentScore objects
        """
        results = []
        for item in items:
            score = self.analyze(
                text=item.get('text', ''),
                title=item.get('title', ''),
                cryptopanic_sentiment=item.get('cryptopanic_sentiment')
            )
            results.append(score)

        return results

    def get_aggregate_sentiment(self, scores: List[SentimentScore]) -> Dict:
        """
        Calculate aggregate sentiment metrics from multiple scores.

        Returns:
            Dict with overall metrics
        """
        if not scores:
            return {
                'average_score': 0.0,
                'bullish_pct': 0.0,
                'bearish_pct': 0.0,
                'neutral_pct': 0.0,
                'average_confidence': 0.0
            }

        total_score = sum(s.score for s in scores)
        bullish_count = sum(1 for s in scores if s.label == SentimentLabel.BULLISH)
        bearish_count = sum(1 for s in scores if s.label == SentimentLabel.BEARISH)
        neutral_count = sum(1 for s in scores if s.label == SentimentLabel.NEUTRAL)
        total_confidence = sum(s.confidence for s in scores)

        total = len(scores)

        return {
            'average_score': total_score / total,
            'bullish_pct': (bullish_count / total) * 100,
            'bearish_pct': (bearish_count / total) * 100,
            'neutral_pct': (neutral_count / total) * 100,
            'average_confidence': total_confidence / total,
            'total_items': total
        }