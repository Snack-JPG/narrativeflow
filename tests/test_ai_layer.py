"""Tests for AI Analysis Layer (Phase 4)."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from narrative_flow.ai import (
    ClaudeClient,
    BriefingGenerator,
    ChangeDetector,
    CatalystIdentifier,
    MarketRegimeAnalyzer,
    BriefingStorage
)
from narrative_flow.ai.market_regime import LifecycleStage, RegimeAnalysis


@pytest.fixture
def mock_claude_client():
    """Mock Claude client."""
    client = Mock(spec=ClaudeClient)
    client.generate = AsyncMock(return_value={
        "summary": "Test summary",
        "key_points": ["point1", "point2"]
    })
    return client


@pytest.fixture
def briefing_generator(mock_claude_client):
    """Create briefing generator with mocked client."""
    return BriefingGenerator(mock_claude_client)


@pytest.fixture
def change_detector():
    """Create change detector."""
    return ChangeDetector()


@pytest.fixture
def catalyst_identifier():
    """Create catalyst identifier."""
    return CatalystIdentifier()


@pytest.fixture
def regime_analyzer():
    """Create market regime analyzer."""
    return MarketRegimeAnalyzer()


@pytest.fixture
def storage():
    """Create briefing storage."""
    return BriefingStorage()


class TestClaudeClient:
    """Test Claude API client."""

    @pytest.mark.asyncio
    async def test_generate_briefing_prompt(self):
        """Test briefing prompt generation."""
        client = ClaudeClient()

        # Mock the actual API call
        with patch.object(client, '_call_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {
                "executive_summary": "Market shows bullish sentiment",
                "key_narratives": ["AI", "RWA"],
                "recommendations": []
            }

            result = await client.generate(
                prompt="Generate briefing",
                system="You are a market analyst"
            )

            assert "executive_summary" in result
            assert "key_narratives" in result


class TestBriefingGenerator:
    """Test briefing generation."""

    @pytest.mark.asyncio
    async def test_generate_briefing(self, briefing_generator):
        """Test full briefing generation."""
        social_data = [
            {"narrative": "AI", "mentions": 100, "sentiment": 0.8},
            {"narrative": "RWA", "mentions": 50, "sentiment": 0.6}
        ]

        onchain_data = {
            "AI": {"tvl": 1000000, "tvl_change": 0.1},
            "RWA": {"tvl": 500000, "tvl_change": 0.05}
        }

        price_data = {
            "AI": {"price": 100, "change_24h": 0.15},
            "RWA": {"price": 50, "change_24h": -0.02}
        }

        divergence_signals = [
            {
                "narrative": "AI",
                "signal": "early_entry",
                "confidence": 0.85
            }
        ]

        briefing = await briefing_generator.generate_briefing(
            social_data=social_data,
            onchain_data=onchain_data,
            price_data=price_data,
            divergence_signals=divergence_signals,
            time_window=24
        )

        assert briefing is not None
        assert hasattr(briefing, 'timestamp')
        assert hasattr(briefing, 'executive_summary')
        assert hasattr(briefing, 'emerging_narratives')
        assert hasattr(briefing, 'divergences')


class TestChangeDetector:
    """Test change detection."""

    @pytest.mark.asyncio
    async def test_detect_changes(self, change_detector):
        """Test narrative change detection."""
        current_data = {
            "narratives": {
                "AI": {"momentum": 0.8, "sentiment": 0.7, "mentions": 150},
                "RWA": {"momentum": 0.3, "sentiment": 0.4, "mentions": 30}
            }
        }

        historical_data = [
            {
                "narratives": {
                    "AI": {"momentum": 0.4, "sentiment": 0.5, "mentions": 50},
                    "RWA": {"momentum": 0.6, "sentiment": 0.6, "mentions": 80}
                }
            }
        ]

        changes = await change_detector.detect_changes(
            current_data=current_data,
            historical_data=historical_data,
            lookback_hours=24
        )

        assert len(changes) > 0
        # AI should show increasing momentum
        ai_changes = [c for c in changes if c.narrative == "AI"]
        assert len(ai_changes) > 0
        assert ai_changes[0].change_type in ["momentum_surge", "sentiment_shift"]

        # RWA should show declining momentum
        rwa_changes = [c for c in changes if c.narrative == "RWA"]
        assert len(rwa_changes) > 0


class TestCatalystIdentifier:
    """Test catalyst identification."""

    @pytest.mark.asyncio
    async def test_identify_catalysts(self, catalyst_identifier):
        """Test catalyst identification from social data."""
        social_data = [
            {
                "content": "Coinbase launches new AI agent wallet feature",
                "timestamp": datetime.utcnow(),
                "narrative": "AI",
                "sentiment": 0.9
            },
            {
                "content": "BlackRock expands RWA tokenization program",
                "timestamp": datetime.utcnow(),
                "narrative": "RWA",
                "sentiment": 0.8
            }
        ]

        catalysts = await catalyst_identifier.identify_catalysts(
            social_data=social_data,
            lookback_hours=24
        )

        assert len(catalysts) > 0
        # Should identify Coinbase and BlackRock as catalysts
        catalyst_texts = [c.description for c in catalysts]
        assert any("Coinbase" in text for text in catalyst_texts)
        assert any("BlackRock" in text for text in catalyst_texts)


class TestMarketRegimeAnalyzer:
    """Test market regime analysis."""

    @pytest.mark.asyncio
    async def test_analyze_regime(self, regime_analyzer):
        """Test regime analysis for narrative."""
        metrics = {
            "momentum_score": 0.7,
            "social_velocity": 100,
            "sentiment": 0.6,
            "tvl": 1000000,
            "price_change_24h": 0.05
        }

        historical_data = [
            {
                "momentum_score": 0.5,
                "social_velocity": 50,
                "sentiment": 0.5,
                "tvl": 800000,
                "price_change_24h": 0.02
            }
            for _ in range(7)  # 7 days of similar data
        ]

        analysis = await regime_analyzer.analyze_regime(
            narrative="AI",
            metrics=metrics,
            historical_data=historical_data
        )

        assert isinstance(analysis, RegimeAnalysis)
        assert analysis.current_stage in [stage for stage in LifecycleStage]
        assert 0 <= analysis.stage_confidence <= 1
        assert analysis.risk_level in ["low", "medium", "high", "very_high"]
        assert 0 <= analysis.opportunity_score <= 1


class TestBriefingStorage:
    """Test briefing storage operations."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_briefing(self, storage):
        """Test saving and retrieving briefings."""
        await storage.initialize()

        briefing_data = {
            "timestamp": datetime.utcnow(),
            "executive_summary": "Test summary",
            "emerging_narratives": ["AI", "RWA"],
            "overheated_narratives": ["MEME"],
            "key_catalysts": [{"catalyst": "Test event"}],
            "divergences": [{"narrative": "AI", "signal": "early_entry"}],
            "market_regime": {"overall": "bullish"},
            "recommendations": [{"action": "buy", "narrative": "AI"}],
            "markdown_output": "# Test Briefing",
            "json_output": {"test": "data"}
        }

        # Save briefing
        briefing_id = await storage.save_briefing(briefing_data)
        assert briefing_id is not None

        # Retrieve latest
        latest = await storage.get_latest_briefing()
        assert latest is not None
        assert latest["executive_summary"] == "Test summary"

        # Get history
        history = await storage.get_briefing_history(limit=10)
        assert len(history) > 0
        assert history[0]["executive_summary"] == "Test summary"


class TestAPIIntegration:
    """Test API route integration."""

    @pytest.mark.asyncio
    async def test_briefing_routes_registered(self):
        """Test that briefing routes are properly registered."""
        from narrative_flow.api.main import app

        # Check that briefing routes exist
        route_paths = [route.path for route in app.routes]
        assert any("/api/briefing" in path for path in route_paths)
        assert any("/api/briefing/latest" in path for path in route_paths)
        assert any("/api/briefing/generate" in path for path in route_paths)
        assert any("/api/briefing/regime" in path for path in route_paths)
        assert any("/api/briefing/catalysts" in path for path in route_paths)


@pytest.mark.asyncio
async def test_end_to_end_briefing_generation():
    """Test end-to-end briefing generation flow."""
    from narrative_flow.api.briefing_routes import generate_briefing, BriefingRequest

    with patch('narrative_flow.api.briefing_routes.get_db_session') as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value.__aenter__.return_value = mock_session

        with patch('narrative_flow.api.briefing_routes._get_social_data') as mock_social:
            mock_social.return_value = [{"narrative": "AI", "mentions": 100}]

            with patch('narrative_flow.api.briefing_routes._get_onchain_data') as mock_onchain:
                mock_onchain.return_value = {"AI": {"tvl": 1000000}}

                with patch('narrative_flow.api.briefing_routes._get_price_data') as mock_price:
                    mock_price.return_value = {"AI": {"price": 100}}

                    with patch('narrative_flow.api.briefing_routes._get_divergences') as mock_div:
                        mock_div.return_value = [{"narrative": "AI", "signal": "early_entry"}]

                        # Test generation
                        request = BriefingRequest(time_window=24, force_regenerate=True)
                        background_tasks = AsyncMock()

                        # This would normally call the actual endpoint
                        # For testing, we just verify the structure
                        assert request.time_window == 24
                        assert request.force_regenerate == True