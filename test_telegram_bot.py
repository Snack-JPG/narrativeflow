"""Test script for the Telegram bot."""

import asyncio
import os
from datetime import datetime
from narrative_flow.config.settings import settings
from narrative_flow.telegram.alerts import AlertManager, AlertSeverity, Alert
from narrative_flow.models.db_manager import db_manager
from narrative_flow.models.database import NarrativeMetrics, DivergenceHistory
from sqlalchemy import select


async def test_database_setup():
    """Test database setup and add sample data."""
    print("Testing database setup...")

    # Create tables
    await db_manager.create_all()
    print("✅ Database tables created")

    # Add sample narrative metrics
    async with db_manager.get_session() as session:
        # Add sample metrics for AI narrative
        ai_metrics = NarrativeMetrics(
            timestamp=datetime.utcnow(),
            narrative_category="AI",
            mention_count=1500,
            mention_velocity=125.5,
            sentiment_avg=0.75,
            sentiment_bullish_pct=0.82,
            total_tvl=5_000_000_000,
            tvl_change_24h=15.3,
            active_protocols=25,
            total_market_cap=50_000_000_000,
            avg_price_change_24h=8.5,
            total_volume_24h=2_500_000_000,
            momentum_score=85.5,
            divergence_signal="early_entry",
            lifecycle_stage="EMERGING",
            weighted_velocity=145.2,
            acceleration=25.5,
            novelty_score=0.68,
            innovation_rate=0.45
        )
        session.add(ai_metrics)

        # Add sample metrics for RWA narrative
        rwa_metrics = NarrativeMetrics(
            timestamp=datetime.utcnow(),
            narrative_category="RWA",
            mention_count=800,
            mention_velocity=65.2,
            sentiment_avg=0.60,
            sentiment_bullish_pct=0.70,
            total_tvl=2_000_000_000,
            tvl_change_24h=8.2,
            active_protocols=15,
            total_market_cap=15_000_000_000,
            avg_price_change_24h=3.2,
            total_volume_24h=800_000_000,
            momentum_score=62.3,
            divergence_signal="accumulation",
            lifecycle_stage="MAINSTREAM",
            weighted_velocity=78.5,
            acceleration=12.3,
            novelty_score=0.45,
            innovation_rate=0.32
        )
        session.add(rwa_metrics)

        # Add sample divergence history
        divergence = DivergenceHistory(
            timestamp=datetime.utcnow(),
            narrative="AI",
            social_velocity=125.5,
            sentiment_strength=0.75,
            social_buzz_trend=25.5,
            onchain_activity=85.2,
            onchain_delta=15.3,
            tvl=5_000_000_000,
            tvl_change_24h=15.3,
            price=2.85,
            price_change_24h=8.5,
            volume_24h=2_500_000_000,
            market_cap=50_000_000_000,
            momentum_score=85.5,
            price_momentum=35.2,
            divergence_score=92.3,
            divergence_signal="early_entry",
            lifecycle_stage="EMERGING",
            confidence=0.85
        )
        session.add(divergence)

        await session.commit()
        print("✅ Sample data added to database")


async def test_alert_manager():
    """Test the alert manager functionality."""
    print("\nTesting alert manager...")

    alert_manager = AlertManager()
    await alert_manager.connect()

    # Test creating different alert types
    divergence_alert = alert_manager.create_divergence_alert(
        narrative="AI",
        social_change=85.5,
        onchain_change=65.2,
        price_change=12.3,
        signal_type="EARLY_ENTRY"
    )
    print(f"✅ Created divergence alert: {divergence_alert.message[:50]}...")

    lifecycle_alert = alert_manager.create_lifecycle_alert(
        narrative="RWA",
        old_stage="EMERGING",
        new_stage="MAINSTREAM"
    )
    print(f"✅ Created lifecycle alert: {lifecycle_alert.message[:50]}...")

    momentum_alert = alert_manager.create_momentum_alert(
        narrative="DePIN",
        momentum_score=95.5,
        change_24h=125.3
    )
    print(f"✅ Created momentum alert: {momentum_alert.message[:50]}...")

    # Test rate limiting
    can_send = await alert_manager.can_send_alert("AI", AlertSeverity.INFO)
    print(f"✅ Rate limiting check: Can send = {can_send}")

    await alert_manager.disconnect()
    print("✅ Alert manager tests completed")


async def test_bot_initialization():
    """Test bot initialization (without actual Telegram connection)."""
    print("\nTesting bot initialization...")

    if not settings.telegram_bot_token:
        print("⚠️ No bot token configured. Add TELEGRAM_BOT_TOKEN to .env file")
        print("   Get a token from @BotFather on Telegram")
        return False

    if not settings.telegram_chat_id:
        print("⚠️ No chat ID configured. Add TELEGRAM_CHAT_ID to .env file")
        print("   Get your chat ID by messaging @userinfobot on Telegram")
        return False

    print(f"✅ Bot token configured: ...{settings.telegram_bot_token[-10:]}")
    print(f"✅ Chat ID configured: {settings.telegram_chat_id}")

    return True


async def main():
    """Run all tests."""
    print("=" * 50)
    print("NarrativeFlow Telegram Bot Test Suite")
    print("=" * 50)

    try:
        # Test database
        await test_database_setup()

        # Test alert manager
        await test_alert_manager()

        # Test bot configuration
        bot_ready = await test_bot_initialization()

        print("\n" + "=" * 50)
        print("Test Results Summary")
        print("=" * 50)
        print("✅ Database: PASSED")
        print("✅ Alert Manager: PASSED")

        if bot_ready:
            print("✅ Bot Configuration: PASSED")
            print("\n📱 Bot is ready! Run the following to start:")
            print("   python -m narrative_flow.telegram.main")
        else:
            print("⚠️ Bot Configuration: NEEDS SETUP")
            print("\n📋 Next steps:")
            print("1. Create a bot with @BotFather on Telegram")
            print("2. Get your chat ID from @userinfobot")
            print("3. Add to .env file:")
            print("   TELEGRAM_BOT_TOKEN=your_bot_token")
            print("   TELEGRAM_CHAT_ID=your_chat_id")

    except Exception as e:
        print(f"\n❌ Error during tests: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())