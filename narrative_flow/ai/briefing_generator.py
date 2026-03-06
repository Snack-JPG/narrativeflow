"""Narrative briefing generator using Claude AI."""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import asyncio

from .claude_client import ClaudeClient
from ..models.database import NarrativeMetrics, MarketData, OnChainData, DivergenceHistory

logger = logging.getLogger(__name__)


@dataclass
class NarrativeBriefing:
    """Structured narrative briefing."""
    timestamp: datetime
    executive_summary: str
    emerging_narratives: List[Dict[str, Any]]
    overheated_narratives: List[Dict[str, Any]]
    key_catalysts: List[Dict[str, Any]]
    divergences: List[Dict[str, Any]]
    market_regime: Dict[str, str]
    recommendations: List[Dict[str, Any]]
    changes_from_previous: Optional[Dict[str, Any]] = None
    markdown_output: Optional[str] = None
    json_output: Optional[Dict[str, Any]] = None


class BriefingGenerator:
    """Generate AI-powered narrative briefings."""

    def __init__(self, claude_client: Optional[ClaudeClient] = None):
        """Initialize briefing generator.

        Args:
            claude_client: Claude API client instance
        """
        self.claude = claude_client or ClaudeClient()

    async def generate_briefing(
        self,
        social_data: List[Dict[str, Any]],
        onchain_data: Dict[str, Any],
        price_data: Dict[str, Any],
        divergence_signals: List[Dict[str, Any]],
        previous_briefing: Optional[NarrativeBriefing] = None,
        time_window: int = 24
    ) -> NarrativeBriefing:
        """Generate comprehensive narrative briefing.

        Args:
            social_data: Recent social mentions with sentiment
            onchain_data: On-chain metrics by narrative
            price_data: Price movements by narrative
            divergence_signals: Detected divergence opportunities
            previous_briefing: Previous briefing for comparison
            time_window: Hours of data to analyze

        Returns:
            Structured narrative briefing
        """
        logger.info(f"Generating briefing for {time_window}h window")

        # Prepare enriched data for Claude
        enriched_data = await self._enrich_data(
            social_data, onchain_data, price_data, divergence_signals
        )

        # Generate main analysis
        analysis = await self.claude.analyze_narrative_data(
            enriched_data["social"],
            enriched_data["onchain"],
            enriched_data["price"],
            context=self._generate_context(time_window, divergence_signals)
        )

        # Generate change detection if we have previous briefing
        changes = None
        if previous_briefing:
            changes = await self._detect_changes(analysis, previous_briefing)

        # Generate formatted outputs
        formatted = await self._generate_formatted_outputs(
            analysis, changes, enriched_data
        )

        # Create briefing object
        briefing = NarrativeBriefing(
            timestamp=datetime.utcnow(),
            executive_summary=analysis.get("summary", ""),
            emerging_narratives=analysis.get("emerging_narratives", []),
            overheated_narratives=analysis.get("overheated_narratives", []),
            key_catalysts=analysis.get("catalysts", []),
            divergences=analysis.get("divergences", []),
            market_regime=analysis.get("market_regime", {}),
            recommendations=analysis.get("recommendations", []),
            changes_from_previous=changes,
            markdown_output=formatted["markdown"],
            json_output=formatted["json"]
        )

        logger.info("Briefing generated successfully")
        return briefing

    async def _enrich_data(
        self,
        social_data: List[Dict[str, Any]],
        onchain_data: Dict[str, Any],
        price_data: Dict[str, Any],
        divergence_signals: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Enrich and structure data for analysis."""
        # Calculate social metrics by narrative
        narrative_social = {}
        for mention in social_data:
            narratives = mention.get("narratives", [])
            for narrative in narratives:
                if narrative not in narrative_social:
                    narrative_social[narrative] = {
                        "mentions": 0,
                        "positive": 0,
                        "negative": 0,
                        "influencer_mentions": 0,
                        "avg_engagement": 0,
                        "top_mentions": []
                    }

                stats = narrative_social[narrative]
                stats["mentions"] += 1

                sentiment = mention.get("sentiment", {})
                if sentiment.get("label") == "positive":
                    stats["positive"] += 1
                elif sentiment.get("label") == "negative":
                    stats["negative"] += 1

                if mention.get("author_influence", 0) > 1000:
                    stats["influencer_mentions"] += 1

                # Keep top mentions
                if len(stats["top_mentions"]) < 5:
                    stats["top_mentions"].append({
                        "text": mention.get("text", "")[:200],
                        "author": mention.get("author", ""),
                        "engagement": mention.get("engagement", 0),
                        "source": mention.get("source", "")
                    })

        # Calculate sentiment ratios
        for narrative, stats in narrative_social.items():
            total = stats["mentions"]
            if total > 0:
                stats["positive_ratio"] = stats["positive"] / total
                stats["negative_ratio"] = stats["negative"] / total
                stats["influencer_ratio"] = stats["influencer_mentions"] / total

        # Add divergence signals to enriched data
        enriched_divergences = []
        for signal in divergence_signals[:10]:  # Top 10 divergences
            enriched_divergences.append({
                "narrative": signal.get("narrative", ""),
                "type": signal.get("signal_type", ""),
                "strength": signal.get("strength", 0),
                "tokens": signal.get("top_tokens", []),
                "description": self._describe_divergence(signal)
            })

        return {
            "social": narrative_social,
            "onchain": onchain_data,
            "price": price_data,
            "divergences": enriched_divergences
        }

    def _generate_context(
        self,
        time_window: int,
        divergence_signals: List[Dict[str, Any]]
    ) -> str:
        """Generate additional context for analysis."""
        context = f"""
Time Window: Last {time_window} hours
Analysis Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Divergence Signals Detected: {len(divergence_signals)}
- Early Entry Signals: {len([s for s in divergence_signals if s.get('signal_type') == 'early_entry'])}
- Exit Signals: {len([s for s in divergence_signals if s.get('signal_type') == 'exit'])}
- Accumulation Signals: {len([s for s in divergence_signals if s.get('signal_type') == 'accumulation'])}

Market Conditions:
- Overall crypto market sentiment trending
- Major news events in last 24h
- Regulatory developments
- Technical market structure
"""
        return context

    async def _detect_changes(
        self,
        current_analysis: Dict[str, Any],
        previous_briefing: NarrativeBriefing
    ) -> Dict[str, Any]:
        """Detect changes from previous briefing."""
        changes = {
            "new_narratives": [],
            "momentum_shifts": [],
            "regime_changes": [],
            "new_catalysts": [],
            "signal_changes": []
        }

        # Compare emerging narratives
        prev_emerging = {n.get("narrative") for n in previous_briefing.emerging_narratives}
        curr_emerging = {n.get("narrative") for n in current_analysis.get("emerging_narratives", [])}

        changes["new_narratives"] = list(curr_emerging - prev_emerging)

        # Compare market regimes
        prev_regime = previous_briefing.market_regime
        curr_regime = current_analysis.get("market_regime", {})

        for narrative, stage in curr_regime.items():
            if narrative in prev_regime and prev_regime[narrative] != stage:
                changes["regime_changes"].append({
                    "narrative": narrative,
                    "from": prev_regime[narrative],
                    "to": stage
                })

        # Identify new catalysts
        prev_catalysts = {c.get("event") for c in previous_briefing.key_catalysts}
        curr_catalysts = {c.get("event") for c in current_analysis.get("catalysts", [])}

        for catalyst in curr_catalysts - prev_catalysts:
            changes["new_catalysts"].append(catalyst)

        return changes

    async def _generate_formatted_outputs(
        self,
        analysis: Dict[str, Any],
        changes: Optional[Dict[str, Any]],
        enriched_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate markdown and JSON formatted outputs."""
        # Generate markdown briefing
        markdown = self._generate_markdown_briefing(analysis, changes, enriched_data)

        # Generate JSON output
        json_output = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": analysis.get("summary", ""),
            "narratives": {
                "emerging": analysis.get("emerging_narratives", []),
                "overheated": analysis.get("overheated_narratives", [])
            },
            "catalysts": analysis.get("catalysts", []),
            "divergences": enriched_data.get("divergences", []),
            "market_regime": analysis.get("market_regime", {}),
            "recommendations": analysis.get("recommendations", []),
            "changes": changes,
            "metrics": {
                "total_mentions": sum(s["mentions"] for s in enriched_data["social"].values()),
                "narratives_tracked": len(enriched_data["social"]),
                "divergence_signals": len(enriched_data.get("divergences", []))
            }
        }

        return {
            "markdown": markdown,
            "json": json_output
        }

    def _generate_markdown_briefing(
        self,
        analysis: Dict[str, Any],
        changes: Optional[Dict[str, Any]],
        enriched_data: Dict[str, Any]
    ) -> str:
        """Generate markdown-formatted briefing."""
        time_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

        md = f"""# 📊 NarrativeFlow Daily Briefing
*{time_str}*

## 📝 Executive Summary
{analysis.get('summary', 'No summary available')}

"""

        # Add changes section if available
        if changes and any(changes.values()):
            md += "## 🔄 What's New Since Last Briefing\n"
            if changes.get("new_narratives"):
                md += f"- **New Emerging Narratives:** {', '.join(changes['new_narratives'])}\n"
            if changes.get("regime_changes"):
                for change in changes["regime_changes"]:
                    md += f"- **{change['narrative']}:** {change['from']} → {change['to']}\n"
            if changes.get("new_catalysts"):
                md += f"- **New Catalysts:** {', '.join(changes['new_catalysts'][:3])}\n"
            md += "\n"

        # Emerging narratives
        md += "## 🚀 Emerging Narratives (Entry Signals)\n"
        for narrative in analysis.get("emerging_narratives", [])[:3]:
            md += f"""
### {narrative.get('narrative', 'Unknown')}
- **Signal Strength:** {narrative.get('strength', 'N/A')}/10
- **Social Buzz:** {narrative.get('social_momentum', 'N/A')}
- **Price Action:** {narrative.get('price_status', 'N/A')}
- **Top Tokens:** {', '.join(narrative.get('tokens', [])[:5])}
- **Why Now:** {narrative.get('reason', 'N/A')}
"""

        # Overheated narratives
        md += "\n## 🔥 Overheated Narratives (Exit Signals)\n"
        for narrative in analysis.get("overheated_narratives", [])[:3]:
            md += f"""
### {narrative.get('narrative', 'Unknown')}
- **Risk Level:** {narrative.get('risk_level', 'N/A')}/10
- **Price vs Fundamentals:** {narrative.get('divergence', 'N/A')}
- **Sentiment Shift:** {narrative.get('sentiment_change', 'N/A')}
- **Tokens to Watch:** {', '.join(narrative.get('tokens', [])[:5])}
- **Warning:** {narrative.get('warning', 'N/A')}
"""

        # Key catalysts
        md += "\n## ⚡ Key Market Catalysts\n"
        for catalyst in analysis.get("catalysts", [])[:5]:
            md += f"- **{catalyst.get('event', 'Unknown')}**: {catalyst.get('impact', 'N/A')} → Affects: {catalyst.get('narratives', 'N/A')}\n"

        # Divergences
        if enriched_data.get("divergences"):
            md += "\n## 🎯 Top Divergence Opportunities\n"
            for div in enriched_data["divergences"][:5]:
                md += f"""
**{div['narrative']} - {div['type']}**
- Strength: {div['strength']}/10
- Tokens: {', '.join(t['symbol'] for t in div.get('tokens', [])[:3])}
- {div['description']}
"""

        # Market regime
        md += "\n## 📈 Market Regime by Narrative\n"
        regime_emojis = {
            "whisper": "🤫",
            "emerging": "🌱",
            "mainstream": "📢",
            "peak": "🎯",
            "declining": "📉",
            "dead": "💀"
        }
        for narrative, stage in analysis.get("market_regime", {}).items():
            emoji = regime_emojis.get(stage.lower(), "❓")
            md += f"- **{narrative}**: {emoji} {stage}\n"

        # Recommendations
        md += "\n## 💡 Actionable Recommendations\n"
        for i, rec in enumerate(analysis.get("recommendations", [])[:5], 1):
            md += f"{i}. {rec.get('action', 'N/A')}: {rec.get('details', 'N/A')}\n"

        # Footer
        md += f"\n---\n*Generated by NarrativeFlow AI Analysis Layer*\n*Next update in 6 hours*"

        return md

    def _describe_divergence(self, signal: Dict[str, Any]) -> str:
        """Generate human-readable divergence description."""
        signal_type = signal.get("signal_type", "")
        narrative = signal.get("narrative", "")
        strength = signal.get("strength", 0)

        descriptions = {
            "early_entry": f"Social buzz increasing rapidly but price hasn't moved yet. Strength: {strength}/10",
            "exit": f"Price already pumped but social momentum declining. Exit signal strength: {strength}/10",
            "accumulation": f"Low social activity but strong on-chain accumulation detected. Smart money moving in.",
            "dead": f"Both social and on-chain activity declining. Avoid this narrative."
        }

        return descriptions.get(signal_type, f"Divergence detected with strength {strength}/10")