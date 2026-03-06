#!/usr/bin/env python3
"""Test script for NarrativeFlow Phase 2 - Narrative Classification + Sentiment Engine."""

import asyncio
import os
from datetime import datetime
import logging
from typing import List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_classification():
    """Test narrative classification system."""
    from narrative_flow.engine import NarrativeClassifier

    logger.info("\n=== Testing Narrative Classification ===")

    classifier = NarrativeClassifier()

    test_cases = [
        {
            'title': 'TAO Price Surges as AI Agents Gain Traction',
            'content': 'Bittensor (TAO) price rallied 30% as autonomous AI agents and machine learning protocols see increased adoption.',
            'expected': ['AI']
        },
        {
            'title': 'BlackRock Launches New RWA Token Fund',
            'content': 'BlackRock expands its tokenized treasury fund with real world assets backing, bringing institutional adoption.',
            'expected': ['RWA']
        },
        {
            'title': 'Render Network Powers GPU Computing for AI',
            'content': 'RNDR token gains as decentralized GPU network sees surge in AI rendering and compute demand.',
            'expected': ['AI', 'DePIN']
        },
        {
            'title': 'BONK and WIF Lead Memecoin Rally',
            'content': 'Solana memecoins BONK and dogwifhat see massive gains as community driven tokens pump.',
            'expected': ['Memecoin']
        },
        {
            'title': 'Arbitrum TVL Hits New High in DeFi',
            'content': 'Layer 2 solution Arbitrum sees record TVL as DeFi protocols like GMX and Uniswap expand.',
            'expected': ['L1/L2', 'DeFi']
        }
    ]

    for test in test_cases:
        # Extract tokens
        tokens = classifier.extract_tokens(f"{test['title']} {test['content']}")
        logger.info(f"\nTokens found: {tokens}")

        # Classify
        categories, confidence = classifier.classify_fast(
            test['content'],
            test['title'],
            tokens
        )

        logger.info(f"Title: {test['title'][:50]}...")
        logger.info(f"Expected: {test['expected']}")
        logger.info(f"Got: {[cat.value for cat in categories]}")
        logger.info(f"Confidence: {confidence:.2f}")

        # Check if classification is correct
        got_categories = [cat.value for cat in categories]
        match = all(exp in got_categories for exp in test['expected'])
        logger.info(f"✅ PASS" if match else f"❌ FAIL")

    return True


async def test_sentiment():
    """Test sentiment analysis."""
    from narrative_flow.engine import SentimentAnalyzer

    logger.info("\n=== Testing Sentiment Analysis ===")

    analyzer = SentimentAnalyzer()

    test_cases = [
        {
            'text': 'Bitcoin is going to the moon! Bullish on BTC, this is the breakout we\'ve been waiting for! 🚀',
            'expected': 'bullish'
        },
        {
            'text': 'Market crash incoming. Sell everything. This ponzi is collapsing.',
            'expected': 'bearish'
        },
        {
            'text': 'Bitcoin trading sideways around 45k. Volume remains steady.',
            'expected': 'neutral'
        },
        {
            'text': 'HUGE pump incoming!!! 100x guaranteed moonshot 🚀🚀🚀 LFG WAGMI',
            'expected': 'bullish'
        },
        {
            'text': 'Project got rugged. Team exit scammed. Complete fraud.',
            'expected': 'bearish'
        }
    ]

    for test in test_cases:
        result = analyzer.analyze(test['text'])

        logger.info(f"\nText: {test['text'][:80]}...")
        logger.info(f"Expected: {test['expected']}")
        logger.info(f"Got: {result.label.value}")
        logger.info(f"Score: {result.score:.2f}")
        logger.info(f"Confidence: {result.confidence:.2f}")

        match = result.label.value == test['expected']
        logger.info(f"✅ PASS" if match else f"❌ FAIL")

    return True


async def test_velocity():
    """Test mention velocity calculation."""
    from narrative_flow.engine import VelocityCalculator, MentionEvent
    from datetime import timedelta

    logger.info("\n=== Testing Velocity Calculation ===")

    calculator = VelocityCalculator()

    # Simulate mentions over time
    now = datetime.now()
    narratives = ['AI', 'DeFi', 'Memecoin']

    # Add mentions with different patterns
    for i in range(50):
        # AI: steady increase
        calculator.add_mention(MentionEvent(
            timestamp=now - timedelta(hours=2) + timedelta(minutes=i*2),
            narrative='AI',
            source='twitter',
            weight=1.5,
            sentiment=0.5
        ))

        # DeFi: burst then decline
        if i < 20:
            calculator.add_mention(MentionEvent(
                timestamp=now - timedelta(hours=1) + timedelta(minutes=i),
                narrative='DeFi',
                source='reddit',
                weight=1.0,
                sentiment=0.2
            ))

        # Memecoin: recent spike
        if i > 30:
            calculator.add_mention(MentionEvent(
                timestamp=now - timedelta(minutes=20-i+30),
                narrative='Memecoin',
                source='twitter',
                weight=2.0,
                sentiment=0.8
            ))

    # Check velocities
    for narrative in narratives:
        logger.info(f"\n{narrative} Velocity:")
        for window in ['1h', '4h', '24h']:
            velocity = calculator.get_velocity(narrative, window)
            logger.info(f"  {window}: {velocity['mentions_per_hour']:.1f} mentions/hr, "
                       f"acceleration: {velocity['acceleration']:.1f}%")

    # Get trending narratives
    trending = calculator.get_trending_narratives(window='4h', min_mentions=5)
    logger.info("\nTrending Narratives (4h):")
    for item in trending[:5]:
        logger.info(f"  {item['narrative']}: momentum={item['momentum_score']:.2f}, "
                   f"velocity={item['velocity']:.1f}/hr")

    return True


async def test_novelty():
    """Test novelty scoring."""
    from narrative_flow.engine import NoveltyScorer

    logger.info("\n=== Testing Novelty Scoring ===")

    scorer = NoveltyScorer()

    # Add some baseline documents
    baseline_docs = [
        "Bitcoin price reaches new all time high as institutional adoption grows",
        "Ethereum scaling solutions see increased TVL in DeFi protocols",
        "New AI agent framework launches on Solana blockchain",
        "Memecoin rally continues with BONK and WIF leading gains"
    ]

    for doc in baseline_docs:
        scorer.add_document(doc, narrative="General")

    # Test novelty detection
    test_cases = [
        {
            'content': 'Bitcoin hits another ATH with institutions buying',
            'expected_novel': False,  # Similar to baseline
            'description': 'Recycled Bitcoin ATH news'
        },
        {
            'content': 'Revolutionary quantum computing breakthrough threatens blockchain security',
            'expected_novel': True,  # New topic
            'description': 'Novel quantum computing topic'
        },
        {
            'content': 'AI agents now autonomously managing DeFi portfolios worth millions',
            'expected_novel': True,  # New angle on AI
            'description': 'Fresh AI narrative angle'
        },
        {
            'content': 'Memecoins BONK and WIF continue rally with massive gains',
            'expected_novel': False,  # Very similar to baseline
            'description': 'Duplicate memecoin content'
        }
    ]

    for test in test_cases:
        result = scorer.calculate_novelty_score(test['content'])

        logger.info(f"\nContent: {test['content'][:80]}...")
        logger.info(f"Description: {test['description']}")
        logger.info(f"Novelty Score: {result['novelty_score']:.2f}")
        logger.info(f"Is Novel: {result['is_novel']}")
        logger.info(f"Is Duplicate: {result['is_duplicate']}")
        logger.info(f"Reasoning: {result['reasoning']}")

        match = result['is_novel'] == test['expected_novel']
        logger.info(f"✅ PASS" if match else f"❌ FAIL")

    return True


async def test_influencer_weighting():
    """Test influencer weight calculations."""
    from narrative_flow.engine import InfluencerWeighting

    logger.info("\n=== Testing Influencer Weighting ===")

    weighting = InfluencerWeighting()

    # Test Reddit weights
    logger.info("\nReddit User Weights:")
    reddit_tests = [
        {'karma': 100, 'age_days': 30, 'expected_range': (0.1, 0.5)},
        {'karma': 10000, 'age_days': 365, 'expected_range': (1.0, 2.0)},
        {'karma': 100000, 'age_days': 1000, 'expected_range': (1.5, 3.0)},
    ]

    for test in reddit_tests:
        weight = weighting.calculate_reddit_weight(
            karma=test['karma'],
            account_age_days=test['age_days']
        )
        logger.info(f"  Karma: {test['karma']}, Age: {test['age_days']}d -> Weight: {weight:.2f}")

        in_range = test['expected_range'][0] <= weight <= test['expected_range'][1]
        logger.info(f"  Expected range: {test['expected_range']} - {'✅ PASS' if in_range else '❌ FAIL'}")

    # Test Twitter weights
    logger.info("\nTwitter User Weights:")
    twitter_tests = [
        {'followers': 100, 'verified': False, 'expected_range': (0.1, 1.0)},
        {'followers': 10000, 'verified': False, 'expected_range': (1.5, 2.5)},
        {'followers': 100000, 'verified': True, 'expected_range': (3.0, 5.0)},
    ]

    for test in twitter_tests:
        weight = weighting.calculate_twitter_weight(
            followers=test['followers'],
            verified=test['verified']
        )
        logger.info(f"  Followers: {test['followers']}, Verified: {test['verified']} -> Weight: {weight:.2f}")

        in_range = test['expected_range'][0] <= weight <= test['expected_range'][1]
        logger.info(f"  Expected range: {test['expected_range']} - {'✅ PASS' if in_range else '❌ FAIL'}")

    return True


async def test_ai_classification():
    """Test AI classification (requires API key)."""
    logger.info("\n=== Testing AI Classification ===")

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        logger.warning("Skipping AI classification test - no API key found")
        return True

    from narrative_flow.engine import AIClassifier, ClassificationRequest

    ai_classifier = AIClassifier(api_key=api_key)

    # Create test requests
    requests = [
        ClassificationRequest(
            id='1',
            title='Agentic wallets enable autonomous DeFi trading',
            content='New smart wallets can execute trades based on AI decisions',
            timestamp=datetime.now(),
            metadata={}
        ),
        ClassificationRequest(
            id='2',
            title='Mysterious whale accumulates ONDO tokens',
            content='Large wallet quietly building position in RWA protocol',
            timestamp=datetime.now(),
            metadata={}
        )
    ]

    # Classify batch
    results = await ai_classifier.classify_batch(requests)

    for req, result in zip(requests, results):
        logger.info(f"\nTitle: {req.title}")
        logger.info(f"Narratives: {result.narratives}")
        logger.info(f"Confidence: {result.confidence:.2f}")
        logger.info(f"Reasoning: {result.reasoning}")

    return True


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("NarrativeFlow Phase 2 Test Suite")
    logger.info("=" * 60)

    tests = [
        ("Classification", test_classification),
        ("Sentiment", test_sentiment),
        ("Velocity", test_velocity),
        ("Novelty", test_novelty),
        ("Influencer Weighting", test_influencer_weighting),
        ("AI Classification", test_ai_classification)
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            logger.info(f"\nRunning {name} tests...")
            result = await test_func()
            if result:
                logger.info(f"✅ {name} tests passed")
                passed += 1
            else:
                logger.info(f"❌ {name} tests failed")
                failed += 1
        except Exception as e:
            logger.error(f"❌ {name} tests failed with error: {e}")
            failed += 1

    logger.info("\n" + "=" * 60)
    logger.info(f"Test Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)