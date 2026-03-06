"""Identify market catalysts driving narrative movements."""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import re
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Catalyst:
    """Represents a market catalyst event."""
    event_type: str  # listing, partnership, upgrade, hack, regulation, launch
    event_description: str
    affected_narratives: List[str]
    affected_tokens: List[str]
    impact_score: float  # 0-10 scale
    confidence: float  # 0-1 scale
    timestamp: datetime
    source: str
    metadata: Dict[str, Any]


class CatalystIdentifier:
    """Identify and analyze market catalysts from social and news data."""

    def __init__(self):
        """Initialize catalyst identifier with pattern matchers."""
        self.catalyst_patterns = self._initialize_patterns()
        self.narrative_keywords = self._initialize_narrative_keywords()

    def _initialize_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Initialize regex patterns for catalyst detection."""
        return {
            "listing": [
                re.compile(r"(coinbase|binance|kraken|okx|bybit).*(list|add|launch)", re.IGNORECASE),
                re.compile(r"listed on\s+(\w+)", re.IGNORECASE),
                re.compile(r"(\w+)\s+listing", re.IGNORECASE)
            ],
            "partnership": [
                re.compile(r"(partner|collaborate|team up|integrate).*(with|between)", re.IGNORECASE),
                re.compile(r"(\w+)\s+x\s+(\w+)", re.IGNORECASE),
                re.compile(r"strategic (partnership|alliance|collaboration)", re.IGNORECASE)
            ],
            "launch": [
                re.compile(r"(launch|release|deploy|introduce|unveil).*(mainnet|testnet|beta|v\d+)", re.IGNORECASE),
                re.compile(r"(mainnet|testnet) (launch|live|deployed)", re.IGNORECASE),
                re.compile(r"new (protocol|platform|feature) launch", re.IGNORECASE)
            ],
            "upgrade": [
                re.compile(r"(upgrade|update|v\d+\.\d+|version).*(release|deploy|live)", re.IGNORECASE),
                re.compile(r"(fork|halving|merge)", re.IGNORECASE),
                re.compile(r"network upgrade", re.IGNORECASE)
            ],
            "hack": [
                re.compile(r"(hack|exploit|drain|attack|breach)", re.IGNORECASE),
                re.compile(r"\$\d+[MmKk]?.*(stolen|hacked|drained)", re.IGNORECASE),
                re.compile(r"security (incident|breach|vulnerability)", re.IGNORECASE)
            ],
            "regulation": [
                re.compile(r"(SEC|CFTC|regulatory|regulation|compliance)", re.IGNORECASE),
                re.compile(r"(approve|reject|sue|lawsuit|settlement)", re.IGNORECASE),
                re.compile(r"(ETF|spot|futures).*(approve|reject)", re.IGNORECASE)
            ],
            "funding": [
                re.compile(r"(raise|funding|investment|series [A-E])", re.IGNORECASE),
                re.compile(r"\$\d+[MmBb]?.*(funding|raise|investment)", re.IGNORECASE),
                re.compile(r"(VC|venture|investor).*(invest|fund|back)", re.IGNORECASE)
            ],
            "adoption": [
                re.compile(r"(adopt|implement|use|integrate).*(crypto|blockchain|web3)", re.IGNORECASE),
                re.compile(r"(payment|accept).*(bitcoin|ethereum|crypto)", re.IGNORECASE),
                re.compile(r"(institutional|enterprise|government).*(adopt|use)", re.IGNORECASE)
            ]
        }

    def _initialize_narrative_keywords(self) -> Dict[str, List[str]]:
        """Initialize keywords for narrative association."""
        return {
            "AI": ["artificial intelligence", "machine learning", "neural", "agent", "AGI",
                   "LLM", "generative", "TAO", "FET", "AGIX", "RNDR", "inference"],
            "RWA": ["real world asset", "tokenized", "treasury", "bond", "commodity",
                    "real estate", "ONDO", "MPL", "GFI", "CFG", "tokenization"],
            "DePIN": ["decentralized physical", "infrastructure", "hardware", "network",
                      "helium", "HNT", "FIL", "RNDR", "compute", "storage", "wireless"],
            "Memecoin": ["meme", "doge", "shiba", "pepe", "wojak", "community coin",
                         "DOGE", "SHIB", "PEPE", "FLOKI", "viral"],
            "L1/L2": ["layer 1", "layer 2", "scaling", "rollup", "sidechain", "ethereum",
                      "solana", "avalanche", "polygon", "arbitrum", "optimism", "base"],
            "DeFi": ["decentralized finance", "yield", "lending", "borrowing", "AMM",
                     "DEX", "liquidity", "AAVE", "UNI", "COMP", "MKR", "farming"],
            "Gaming": ["gamefi", "play to earn", "P2E", "metaverse", "virtual world",
                       "AXS", "SAND", "MANA", "IMX", "GALA", "gaming"],
            "NFT": ["non-fungible", "NFT", "digital art", "collectible", "PFP",
                    "opensea", "blur", "BAYC", "punks", "ordinals"],
            "Privacy": ["privacy", "anonymous", "zero knowledge", "ZK", "mixer",
                        "tornado", "monero", "zcash", "XMR", "ZEC", "secret"]
        }

    async def identify_catalysts(
        self,
        social_data: List[Dict[str, Any]],
        news_data: List[Dict[str, Any]],
        price_movements: Dict[str, float],
        time_window: int = 24
    ) -> List[Catalyst]:
        """Identify market catalysts from data.

        Args:
            social_data: Recent social media posts
            news_data: Recent news articles
            price_movements: Price changes by token
            time_window: Hours to analyze

        Returns:
            List of identified catalysts
        """
        catalysts = []

        # Extract catalysts from social data
        social_catalysts = await self._extract_from_social(social_data)
        catalysts.extend(social_catalysts)

        # Extract catalysts from news
        news_catalysts = await self._extract_from_news(news_data)
        catalysts.extend(news_catalysts)

        # Correlate with price movements
        catalysts = await self._correlate_with_prices(catalysts, price_movements)

        # Deduplicate and rank
        catalysts = self._deduplicate_and_rank(catalysts)

        logger.info(f"Identified {len(catalysts)} catalysts in {time_window}h window")
        return catalysts

    async def _extract_from_social(
        self,
        social_data: List[Dict[str, Any]]
    ) -> List[Catalyst]:
        """Extract catalysts from social media data."""
        catalysts = []
        event_mentions = defaultdict(list)

        for post in social_data:
            text = post.get("text", "")
            timestamp = post.get("timestamp", datetime.utcnow())
            source = post.get("source", "unknown")

            # Check for catalyst patterns
            for event_type, patterns in self.catalyst_patterns.items():
                for pattern in patterns:
                    if pattern.search(text):
                        # Extract affected narratives
                        affected_narratives = self._extract_narratives(text)
                        affected_tokens = self._extract_tokens(text)

                        # Calculate impact based on engagement
                        impact_score = self._calculate_impact(
                            post.get("engagement", 0),
                            post.get("author_influence", 0)
                        )

                        event_key = f"{event_type}:{':'.join(affected_narratives)}"
                        event_mentions[event_key].append({
                            "text": text[:500],
                            "impact": impact_score,
                            "timestamp": timestamp,
                            "source": source,
                            "tokens": affected_tokens
                        })
                        break

        # Create catalyst objects from aggregated mentions
        for event_key, mentions in event_mentions.items():
            event_type, narratives_str = event_key.split(":", 1)
            affected_narratives = narratives_str.split(":") if narratives_str else []

            # Aggregate information
            total_impact = sum(m["impact"] for m in mentions)
            avg_impact = total_impact / len(mentions)
            all_tokens = list(set(token for m in mentions for token in m["tokens"]))

            # Create catalyst if significant enough
            if avg_impact > 3 or len(mentions) > 5:  # Thresholds
                catalyst = Catalyst(
                    event_type=event_type,
                    event_description=self._generate_description(event_type, mentions[0]["text"]),
                    affected_narratives=affected_narratives,
                    affected_tokens=all_tokens[:10],  # Top 10 tokens
                    impact_score=min(avg_impact, 10),
                    confidence=min(0.3 + len(mentions) * 0.1, 1.0),
                    timestamp=mentions[0]["timestamp"],
                    source="social_aggregate",
                    metadata={
                        "mention_count": len(mentions),
                        "sources": list(set(m["source"] for m in mentions)),
                        "sample_text": mentions[0]["text"]
                    }
                )
                catalysts.append(catalyst)

        return catalysts

    async def _extract_from_news(
        self,
        news_data: List[Dict[str, Any]]
    ) -> List[Catalyst]:
        """Extract catalysts from news articles."""
        catalysts = []

        for article in news_data:
            title = article.get("title", "")
            content = article.get("content", article.get("summary", ""))
            full_text = f"{title} {content}"
            timestamp = article.get("timestamp", datetime.utcnow())
            source = article.get("source", "news")

            # Check for catalyst patterns
            for event_type, patterns in self.catalyst_patterns.items():
                for pattern in patterns:
                    if pattern.search(full_text):
                        affected_narratives = self._extract_narratives(full_text)
                        affected_tokens = self._extract_tokens(full_text)

                        # News articles have higher base impact
                        impact_score = 5.0 + self._calculate_news_impact(article)

                        catalyst = Catalyst(
                            event_type=event_type,
                            event_description=title[:200],
                            affected_narratives=affected_narratives,
                            affected_tokens=affected_tokens[:10],
                            impact_score=min(impact_score, 10),
                            confidence=0.8,  # Higher confidence for news
                            timestamp=timestamp,
                            source=f"news:{source}",
                            metadata={
                                "headline": title,
                                "url": article.get("url", ""),
                                "author": article.get("author", "")
                            }
                        )
                        catalysts.append(catalyst)
                        break

        return catalysts

    async def _correlate_with_prices(
        self,
        catalysts: List[Catalyst],
        price_movements: Dict[str, float]
    ) -> List[Catalyst]:
        """Correlate catalysts with price movements to validate impact."""
        for catalyst in catalysts:
            # Check if affected tokens showed price movement
            token_movements = []
            for token in catalyst.affected_tokens:
                if token in price_movements:
                    token_movements.append(abs(price_movements[token]))

            if token_movements:
                avg_movement = sum(token_movements) / len(token_movements)
                # Adjust impact score based on actual price movement
                catalyst.impact_score = min(
                    catalyst.impact_score * (1 + avg_movement / 10),
                    10
                )
                catalyst.metadata["avg_price_movement"] = avg_movement

        return catalysts

    def _extract_narratives(self, text: str) -> List[str]:
        """Extract narrative categories from text."""
        narratives = []
        text_lower = text.lower()

        for narrative, keywords in self.narrative_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    narratives.append(narrative)
                    break

        return list(set(narratives))

    def _extract_tokens(self, text: str) -> List[str]:
        """Extract token symbols from text."""
        # Pattern for token symbols (2-5 uppercase letters, often preceded by $)
        token_pattern = re.compile(r'\$?([A-Z]{2,5})\b')
        tokens = token_pattern.findall(text)

        # Filter out common words that match pattern but aren't tokens
        exclude = {"CEO", "USA", "USD", "EUR", "API", "THE", "AND", "FOR"}
        tokens = [t for t in tokens if t not in exclude]

        return list(set(tokens))

    def _calculate_impact(self, engagement: int, author_influence: int) -> float:
        """Calculate impact score from social metrics."""
        # Logarithmic scaling for engagement
        engagement_score = min(5, 1 + (engagement ** 0.5) / 100)

        # Influence bonus
        influence_bonus = min(3, author_influence / 10000)

        return engagement_score + influence_bonus

    def _calculate_news_impact(self, article: Dict[str, Any]) -> float:
        """Calculate additional impact from news article properties."""
        impact = 0

        # Source credibility
        credible_sources = ["coindesk", "theblock", "decrypt", "bloomberg", "reuters"]
        source = article.get("source", "").lower()
        if any(cs in source for cs in credible_sources):
            impact += 2

        # Headline keywords indicating importance
        headline = article.get("title", "").lower()
        important_words = ["breaking", "exclusive", "confirmed", "official", "major"]
        if any(word in headline for word in important_words):
            impact += 1

        return impact

    def _generate_description(self, event_type: str, sample_text: str) -> str:
        """Generate catalyst description from event type and sample."""
        descriptions = {
            "listing": "Exchange listing announcement",
            "partnership": "Strategic partnership formed",
            "launch": "Protocol or feature launch",
            "upgrade": "Network upgrade or improvement",
            "hack": "Security incident reported",
            "regulation": "Regulatory development",
            "funding": "Funding round announced",
            "adoption": "Institutional adoption news"
        }

        base_description = descriptions.get(event_type, "Market event")

        # Try to extract specific details
        if "$" in sample_text:
            amounts = re.findall(r'\$[\d,]+[MBK]?', sample_text)
            if amounts:
                base_description += f" ({amounts[0]})"

        return base_description

    def _deduplicate_and_rank(self, catalysts: List[Catalyst]) -> List[Catalyst]:
        """Deduplicate similar catalysts and rank by importance."""
        # Group similar catalysts
        unique_catalysts = {}

        for catalyst in catalysts:
            # Create key for grouping
            key = f"{catalyst.event_type}:{':'.join(sorted(catalyst.affected_narratives))}"

            if key not in unique_catalysts:
                unique_catalysts[key] = catalyst
            else:
                # Merge with existing catalyst
                existing = unique_catalysts[key]
                # Keep the one with higher impact
                if catalyst.impact_score > existing.impact_score:
                    unique_catalysts[key] = catalyst
                # Merge metadata
                existing.metadata["mention_count"] = existing.metadata.get("mention_count", 1) + 1
                existing.confidence = min(1.0, existing.confidence + 0.1)

        # Sort by impact score
        ranked_catalysts = sorted(
            unique_catalysts.values(),
            key=lambda c: c.impact_score,
            reverse=True
        )

        return ranked_catalysts

    async def link_catalyst_to_movement(
        self,
        catalyst: Catalyst,
        narrative_movements: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Link a catalyst to observed narrative movements.

        Args:
            catalyst: Identified catalyst
            narrative_movements: Narrative metrics changes

        Returns:
            Analysis linking catalyst to movements
        """
        links = []

        for narrative in catalyst.affected_narratives:
            if narrative in narrative_movements:
                movement = narrative_movements[narrative]

                # Check if movement aligns with catalyst timing
                correlation = self._calculate_correlation(
                    catalyst.timestamp,
                    movement.get("change_timestamp"),
                    movement.get("magnitude", 0)
                )

                if correlation > 0.5:
                    links.append({
                        "narrative": narrative,
                        "movement_magnitude": movement.get("magnitude", 0),
                        "correlation_strength": correlation,
                        "lag_hours": self._calculate_lag(
                            catalyst.timestamp,
                            movement.get("change_timestamp")
                        )
                    })

        return {
            "catalyst": catalyst.event_description,
            "timestamp": catalyst.timestamp.isoformat(),
            "linked_movements": links,
            "total_impact": sum(l["movement_magnitude"] for l in links),
            "confidence": catalyst.confidence * (len(links) / max(1, len(catalyst.affected_narratives)))
        }

    def _calculate_correlation(
        self,
        catalyst_time: datetime,
        movement_time: Optional[datetime],
        magnitude: float
    ) -> float:
        """Calculate correlation between catalyst and movement."""
        if not movement_time:
            return 0.0

        # Time difference in hours
        time_diff = abs((movement_time - catalyst_time).total_seconds() / 3600)

        # Correlation decreases with time lag
        if time_diff < 1:
            correlation = 1.0
        elif time_diff < 6:
            correlation = 0.8
        elif time_diff < 24:
            correlation = 0.5
        elif time_diff < 48:
            correlation = 0.3
        else:
            correlation = 0.1

        # Adjust for magnitude
        correlation *= min(1.0, magnitude / 5)

        return correlation

    def _calculate_lag(
        self,
        catalyst_time: datetime,
        movement_time: Optional[datetime]
    ) -> float:
        """Calculate time lag in hours between catalyst and movement."""
        if not movement_time:
            return 0.0
        return (movement_time - catalyst_time).total_seconds() / 3600