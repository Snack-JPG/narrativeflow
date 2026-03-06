"""Analyze and classify market regime for each narrative."""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger(__name__)


class NarrativeStage(Enum):
    """Narrative lifecycle stages."""
    WHISPER = "whisper"           # Early mentions, low volume
    EMERGING = "emerging"         # Growing interest, early adopters
    MAINSTREAM = "mainstream"     # Wide adoption, media coverage
    PEAK = "peak"                # Maximum hype, FOMO stage
    DECLINING = "declining"       # Interest waning, sellers emerging
    DEAD = "dead"                # Minimal activity, narrative over


@dataclass
class RegimeAnalysis:
    """Market regime analysis for a narrative."""
    narrative: str
    current_stage: NarrativeStage
    stage_confidence: float  # 0-1
    time_in_stage: int  # hours
    next_likely_stage: Optional[NarrativeStage]
    transition_probability: float  # 0-1
    stage_indicators: Dict[str, float]
    risk_level: str  # low, medium, high, extreme
    opportunity_score: float  # 0-10
    recommendation: str


class MarketRegimeAnalyzer:
    """Analyze market regime and lifecycle stage for narratives."""

    def __init__(self):
        """Initialize market regime analyzer."""
        self.stage_thresholds = self._initialize_thresholds()
        self.stage_transitions = self._initialize_transitions()

    def _initialize_thresholds(self) -> Dict[str, Dict[str, Tuple[float, float]]]:
        """Initialize thresholds for stage classification."""
        return {
            NarrativeStage.WHISPER: {
                "mention_velocity": (0, 0.2),
                "sentiment": (0, 0.7),
                "on_chain_activity": (0, 0.1),
                "price_momentum": (-0.1, 0.1),
                "influencer_ratio": (0, 0.1)
            },
            NarrativeStage.EMERGING: {
                "mention_velocity": (0.2, 0.5),
                "sentiment": (0.5, 0.8),
                "on_chain_activity": (0.1, 0.3),
                "price_momentum": (0, 0.3),
                "influencer_ratio": (0.1, 0.3)
            },
            NarrativeStage.MAINSTREAM: {
                "mention_velocity": (0.5, 0.8),
                "sentiment": (0.6, 0.9),
                "on_chain_activity": (0.3, 0.6),
                "price_momentum": (0.2, 0.5),
                "influencer_ratio": (0.3, 0.6)
            },
            NarrativeStage.PEAK: {
                "mention_velocity": (0.8, 1.0),
                "sentiment": (0.7, 1.0),
                "on_chain_activity": (0.5, 1.0),
                "price_momentum": (0.4, 1.0),
                "influencer_ratio": (0.5, 1.0)
            },
            NarrativeStage.DECLINING: {
                "mention_velocity": (0.3, 0.7),
                "sentiment": (0.3, 0.6),
                "on_chain_activity": (0.2, 0.5),
                "price_momentum": (-0.2, 0.2),
                "influencer_ratio": (0.2, 0.5)
            },
            NarrativeStage.DEAD: {
                "mention_velocity": (0, 0.3),
                "sentiment": (0, 0.5),
                "on_chain_activity": (0, 0.2),
                "price_momentum": (-1.0, 0),
                "influencer_ratio": (0, 0.2)
            }
        }

    def _initialize_transitions(self) -> Dict[NarrativeStage, List[NarrativeStage]]:
        """Initialize valid stage transitions."""
        return {
            NarrativeStage.WHISPER: [NarrativeStage.EMERGING, NarrativeStage.DEAD],
            NarrativeStage.EMERGING: [NarrativeStage.MAINSTREAM, NarrativeStage.WHISPER, NarrativeStage.DEAD],
            NarrativeStage.MAINSTREAM: [NarrativeStage.PEAK, NarrativeStage.DECLINING, NarrativeStage.EMERGING],
            NarrativeStage.PEAK: [NarrativeStage.DECLINING, NarrativeStage.MAINSTREAM],
            NarrativeStage.DECLINING: [NarrativeStage.DEAD, NarrativeStage.EMERGING, NarrativeStage.MAINSTREAM],
            NarrativeStage.DEAD: [NarrativeStage.WHISPER, NarrativeStage.EMERGING]
        }

    async def analyze_regime(
        self,
        narrative: str,
        metrics: Dict[str, float],
        historical_data: Optional[List[Dict[str, Any]]] = None
    ) -> RegimeAnalysis:
        """Analyze the market regime for a narrative.

        Args:
            narrative: Narrative name
            metrics: Current metrics (mention_velocity, sentiment, etc.)
            historical_data: Historical data for trend analysis

        Returns:
            Complete regime analysis
        """
        # Normalize metrics to 0-1 scale
        normalized_metrics = self._normalize_metrics(metrics)

        # Classify current stage
        stage, confidence = self._classify_stage(normalized_metrics)

        # Calculate time in stage
        time_in_stage = self._calculate_time_in_stage(
            narrative, stage, historical_data
        )

        # Predict next stage transition
        next_stage, transition_prob = self._predict_transition(
            stage, normalized_metrics, time_in_stage
        )

        # Calculate risk and opportunity
        risk_level = self._assess_risk(stage, normalized_metrics)
        opportunity_score = self._calculate_opportunity(
            stage, normalized_metrics, transition_prob
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            stage, risk_level, opportunity_score, normalized_metrics
        )

        return RegimeAnalysis(
            narrative=narrative,
            current_stage=stage,
            stage_confidence=confidence,
            time_in_stage=time_in_stage,
            next_likely_stage=next_stage,
            transition_probability=transition_prob,
            stage_indicators=normalized_metrics,
            risk_level=risk_level,
            opportunity_score=opportunity_score,
            recommendation=recommendation
        )

    async def analyze_all_narratives(
        self,
        narrative_metrics: Dict[str, Dict[str, float]],
        historical_data: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> Dict[str, RegimeAnalysis]:
        """Analyze regime for all narratives.

        Args:
            narrative_metrics: Metrics for each narrative
            historical_data: Historical data by narrative

        Returns:
            Regime analysis for each narrative
        """
        analyses = {}

        for narrative, metrics in narrative_metrics.items():
            hist_data = historical_data.get(narrative) if historical_data else None
            analysis = await self.analyze_regime(narrative, metrics, hist_data)
            analyses[narrative] = analysis

        return analyses

    def _normalize_metrics(self, metrics: Dict[str, float]) -> Dict[str, float]:
        """Normalize metrics to 0-1 scale."""
        normalized = {}

        # Define normalization ranges
        ranges = {
            "mention_velocity": (0, 1000),    # mentions per hour
            "sentiment": (-1, 1),              # -1 to 1 scale
            "on_chain_activity": (0, 1000000), # volume in USD
            "price_momentum": (-0.5, 0.5),     # percentage change
            "influencer_ratio": (0, 1),        # already 0-1
            "novelty_score": (0, 1),           # already 0-1
            "engagement_rate": (0, 0.1)        # engagement ratio
        }

        for metric, value in metrics.items():
            if metric in ranges:
                min_val, max_val = ranges[metric]
                # Handle sentiment specially (convert from -1,1 to 0,1)
                if metric == "sentiment":
                    normalized[metric] = (value + 1) / 2
                else:
                    normalized[metric] = max(0, min(1, (value - min_val) / (max_val - min_val)))
            else:
                # Pass through unknown metrics
                normalized[metric] = value

        return normalized

    def _classify_stage(
        self,
        metrics: Dict[str, float]
    ) -> Tuple[NarrativeStage, float]:
        """Classify narrative stage based on metrics."""
        stage_scores = {}

        for stage, thresholds in self.stage_thresholds.items():
            score = 0
            count = 0

            for metric, (min_val, max_val) in thresholds.items():
                if metric in metrics:
                    value = metrics[metric]
                    # Check if value falls within threshold
                    if min_val <= value <= max_val:
                        score += 1
                    else:
                        # Partial score based on distance
                        if value < min_val:
                            distance = min_val - value
                        else:
                            distance = value - max_val
                        score += max(0, 1 - distance * 2)
                    count += 1

            if count > 0:
                stage_scores[stage] = score / count
            else:
                stage_scores[stage] = 0

        # Find best matching stage
        best_stage = max(stage_scores, key=stage_scores.get)
        confidence = stage_scores[best_stage]

        # Apply heuristic adjustments
        best_stage, confidence = self._apply_heuristics(
            best_stage, confidence, metrics
        )

        return best_stage, confidence

    def _apply_heuristics(
        self,
        stage: NarrativeStage,
        confidence: float,
        metrics: Dict[str, float]
    ) -> Tuple[NarrativeStage, float]:
        """Apply heuristic rules to refine stage classification."""

        # High sentiment + high velocity + high price = likely PEAK
        if (metrics.get("sentiment", 0) > 0.8 and
            metrics.get("mention_velocity", 0) > 0.7 and
            metrics.get("price_momentum", 0) > 0.4):
            if stage != NarrativeStage.PEAK:
                return NarrativeStage.PEAK, confidence * 0.8

        # Very low activity = likely DEAD
        if (metrics.get("mention_velocity", 0) < 0.1 and
            metrics.get("on_chain_activity", 0) < 0.1):
            if stage != NarrativeStage.DEAD:
                return NarrativeStage.DEAD, confidence * 0.9

        # Growing metrics from low base = EMERGING
        if (metrics.get("mention_velocity", 0) > 0.2 and
            metrics.get("sentiment", 0) > 0.6 and
            metrics.get("price_momentum", 0) < 0.2):
            if stage not in [NarrativeStage.EMERGING, NarrativeStage.WHISPER]:
                return NarrativeStage.EMERGING, confidence * 0.85

        return stage, confidence

    def _calculate_time_in_stage(
        self,
        narrative: str,
        current_stage: NarrativeStage,
        historical_data: Optional[List[Dict[str, Any]]]
    ) -> int:
        """Calculate hours narrative has been in current stage."""
        if not historical_data:
            return 0

        hours_in_stage = 0
        for data_point in reversed(historical_data):
            hist_stage = data_point.get("stage")
            if hist_stage == current_stage.value:
                hours_in_stage += 1
            else:
                break

        return hours_in_stage

    def _predict_transition(
        self,
        current_stage: NarrativeStage,
        metrics: Dict[str, float],
        time_in_stage: int
    ) -> Tuple[Optional[NarrativeStage], float]:
        """Predict next stage transition."""
        valid_transitions = self.stage_transitions.get(current_stage, [])
        if not valid_transitions:
            return None, 0

        transition_scores = {}

        for next_stage in valid_transitions:
            # Calculate transition probability
            score = self._calculate_transition_probability(
                current_stage, next_stage, metrics, time_in_stage
            )
            transition_scores[next_stage] = score

        # Get most likely transition
        if transition_scores:
            best_transition = max(transition_scores, key=transition_scores.get)
            probability = transition_scores[best_transition]
            return best_transition, probability

        return None, 0

    def _calculate_transition_probability(
        self,
        current: NarrativeStage,
        next_stage: NarrativeStage,
        metrics: Dict[str, float],
        time_in_stage: int
    ) -> float:
        """Calculate probability of specific stage transition."""
        base_prob = 0.3  # Base transition probability

        # Time factor - longer in stage = higher transition probability
        time_factor = min(1.0, time_in_stage / 168)  # 168 hours = 1 week

        # Metric alignment factor
        next_thresholds = self.stage_thresholds[next_stage]
        alignment_score = 0
        count = 0

        for metric, (min_val, max_val) in next_thresholds.items():
            if metric in metrics:
                value = metrics[metric]
                if min_val <= value <= max_val:
                    alignment_score += 1
                count += 1

        metric_factor = alignment_score / count if count > 0 else 0

        # Combine factors
        probability = base_prob + (time_factor * 0.3) + (metric_factor * 0.4)

        # Apply transition-specific adjustments
        if current == NarrativeStage.PEAK and next_stage == NarrativeStage.DECLINING:
            # Peak to declining is common
            probability *= 1.2
        elif current == NarrativeStage.WHISPER and next_stage == NarrativeStage.EMERGING:
            # Whisper to emerging requires strong signals
            if metrics.get("mention_velocity", 0) > 0.3:
                probability *= 1.3

        return min(1.0, probability)

    def _assess_risk(
        self,
        stage: NarrativeStage,
        metrics: Dict[str, float]
    ) -> str:
        """Assess risk level for current regime."""
        risk_score = 0

        # Stage-based risk
        stage_risks = {
            NarrativeStage.WHISPER: 0.3,
            NarrativeStage.EMERGING: 0.4,
            NarrativeStage.MAINSTREAM: 0.5,
            NarrativeStage.PEAK: 0.9,
            NarrativeStage.DECLINING: 0.8,
            NarrativeStage.DEAD: 0.2
        }
        risk_score = stage_risks.get(stage, 0.5)

        # Adjust for metrics
        if metrics.get("price_momentum", 0) > 0.5:
            risk_score += 0.2  # High price momentum = higher risk
        if metrics.get("sentiment", 0) < 0.3:
            risk_score += 0.1  # Low sentiment = higher risk
        if metrics.get("on_chain_activity", 0) < 0.2:
            risk_score += 0.1  # Low on-chain = higher risk

        # Classify risk level
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.5:
            return "medium"
        elif risk_score < 0.7:
            return "high"
        else:
            return "extreme"

    def _calculate_opportunity(
        self,
        stage: NarrativeStage,
        metrics: Dict[str, float],
        transition_prob: float
    ) -> float:
        """Calculate opportunity score (0-10)."""
        opportunity = 5.0  # Base score

        # Stage-based opportunity
        if stage == NarrativeStage.EMERGING:
            opportunity += 3
        elif stage == NarrativeStage.WHISPER:
            opportunity += 2
        elif stage == NarrativeStage.MAINSTREAM:
            opportunity += 1
        elif stage == NarrativeStage.PEAK:
            opportunity -= 2
        elif stage == NarrativeStage.DECLINING:
            opportunity -= 1

        # Metric-based adjustments
        if metrics.get("sentiment", 0) > 0.7:
            opportunity += 1
        if metrics.get("on_chain_activity", 0) > 0.5:
            opportunity += 1
        if metrics.get("price_momentum", 0) < 0.1:
            opportunity += 1  # Low price with good metrics = opportunity

        # Transition opportunity
        if transition_prob > 0.6 and stage in [NarrativeStage.WHISPER, NarrativeStage.EMERGING]:
            opportunity += 1

        return max(0, min(10, opportunity))

    def _generate_recommendation(
        self,
        stage: NarrativeStage,
        risk: str,
        opportunity: float,
        metrics: Dict[str, float]
    ) -> str:
        """Generate actionable recommendation based on regime."""

        if stage == NarrativeStage.WHISPER:
            if opportunity > 6:
                return "🔍 Early opportunity detected. Start researching tokens. Small positions only."
            else:
                return "👀 Monitor closely. Too early to enter, but watch for emergence signals."

        elif stage == NarrativeStage.EMERGING:
            if risk == "low" and opportunity > 7:
                return "🟢 Strong entry signal. Narrative gaining traction with low risk. Scale in positions."
            elif opportunity > 5:
                return "🟡 Cautious entry. Good opportunity but monitor risk factors closely."
            else:
                return "⏸️ Wait for better entry. Metrics not aligned yet."

        elif stage == NarrativeStage.MAINSTREAM:
            if metrics.get("price_momentum", 0) < 0.3:
                return "✅ Still room to enter. Narrative mainstream but price hasn't fully caught up."
            else:
                return "⚠️ Late entry. Only for short-term trades with strict stops."

        elif stage == NarrativeStage.PEAK:
            if risk == "extreme":
                return "🔴 EXIT SIGNAL. Take profits immediately. Narrative at peak with extreme risk."
            else:
                return "⚡ Consider taking partial profits. Monitor for declining momentum."

        elif stage == NarrativeStage.DECLINING:
            return "📉 Exit remaining positions. Narrative losing steam. Look for new opportunities."

        elif stage == NarrativeStage.DEAD:
            if metrics.get("on_chain_activity", 0) > 0.3:
                return "🔄 Possible revival signs in on-chain data. Watch for resurrection."
            else:
                return "💀 Avoid completely. Narrative is dead with no revival signs."

        return "📊 Continue monitoring. No clear action signal."

    def get_stage_summary(self) -> Dict[str, List[str]]:
        """Get summary of narratives by stage."""
        # This would be populated from actual data
        return {
            "whisper": [],
            "emerging": [],
            "mainstream": [],
            "peak": [],
            "declining": [],
            "dead": []
        }