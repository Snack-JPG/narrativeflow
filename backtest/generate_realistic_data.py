"""
Generate more realistic historical data with proper divergence patterns.
This ensures we have tradeable signals for backtesting.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

def generate_realistic_narrative_cycle(start_date, narrative, duration_days=30):
    """Generate a realistic narrative cycle with proper divergence patterns."""

    # Create hourly timestamps
    hours = duration_days * 24
    timestamps = pd.date_range(start_date, periods=hours, freq='H')
    df = pd.DataFrame(index=timestamps)

    # Define cycle phases (in hours)
    whisper_phase = int(hours * 0.15)      # 15% - Early whispers
    accumulation_phase = int(hours * 0.20)  # 20% - Smart money accumulates
    momentum_phase = int(hours * 0.25)      # 25% - Mainstream adoption
    fomo_phase = int(hours * 0.15)          # 15% - Peak FOMO
    distribution_phase = int(hours * 0.15)   # 15% - Smart money exits
    decline_phase = int(hours * 0.10)       # 10% - Decline

    # Initialize arrays
    social_buzz = np.zeros(hours)
    onchain_activity = np.zeros(hours)
    price = np.zeros(hours)

    # Phase 1: Whisper (Low everything)
    end_whisper = whisper_phase
    social_buzz[:end_whisper] = np.linspace(0.1, 0.3, end_whisper) + np.random.normal(0, 0.02, end_whisper)
    onchain_activity[:end_whisper] = np.linspace(0.05, 0.2, end_whisper) + np.random.normal(0, 0.02, end_whisper)
    price[:end_whisper] = np.linspace(0.0, 0.05, end_whisper) + np.random.normal(0, 0.01, end_whisper)

    # Phase 2: Accumulation (Onchain picks up, social still low, price flat) - KEY DIVERGENCE
    start_acc = end_whisper
    end_acc = start_acc + accumulation_phase
    social_buzz[start_acc:end_acc] = np.linspace(0.3, 0.5, accumulation_phase) + np.random.normal(0, 0.03, accumulation_phase)
    onchain_activity[start_acc:end_acc] = np.linspace(0.2, 0.7, accumulation_phase) + np.random.normal(0, 0.03, accumulation_phase)
    price[start_acc:end_acc] = np.linspace(0.05, 0.15, accumulation_phase) + np.random.normal(0, 0.02, accumulation_phase)

    # Phase 3: Momentum (Everything picks up) - EARLY ENTRY SIGNALS HERE
    start_mom = end_acc
    end_mom = start_mom + momentum_phase
    social_buzz[start_mom:end_mom] = np.linspace(0.5, 0.85, momentum_phase) + np.random.normal(0, 0.03, momentum_phase)
    onchain_activity[start_mom:end_mom] = np.linspace(0.7, 0.9, momentum_phase) + np.random.normal(0, 0.02, momentum_phase)
    price[start_mom:end_mom] = np.linspace(0.15, 0.5, momentum_phase) + np.random.normal(0, 0.03, momentum_phase)

    # Phase 4: FOMO (Price runs ahead of fundamentals) - EXIT SIGNALS
    start_fomo = end_mom
    end_fomo = start_fomo + fomo_phase
    social_buzz[start_fomo:end_fomo] = np.linspace(0.85, 0.95, fomo_phase) + np.random.normal(0, 0.02, fomo_phase)
    onchain_activity[start_fomo:end_fomo] = np.linspace(0.9, 0.85, fomo_phase) + np.random.normal(0, 0.02, fomo_phase)
    price[start_fomo:end_fomo] = np.linspace(0.5, 1.0, fomo_phase) + np.random.normal(0, 0.04, fomo_phase)

    # Phase 5: Distribution (Smart money exits)
    start_dist = end_fomo
    end_dist = start_dist + distribution_phase
    social_buzz[start_dist:end_dist] = np.linspace(0.95, 0.6, distribution_phase) + np.random.normal(0, 0.03, distribution_phase)
    onchain_activity[start_dist:end_dist] = np.linspace(0.85, 0.4, distribution_phase) + np.random.normal(0, 0.03, distribution_phase)
    price[start_dist:end_dist] = np.linspace(1.0, 0.7, distribution_phase) + np.random.normal(0, 0.04, distribution_phase)

    # Phase 6: Decline
    start_decline = end_dist
    social_buzz[start_decline:] = np.linspace(0.6, 0.2, len(social_buzz[start_decline:])) + np.random.normal(0, 0.02, len(social_buzz[start_decline:]))
    onchain_activity[start_decline:] = np.linspace(0.4, 0.1, len(onchain_activity[start_decline:])) + np.random.normal(0, 0.02, len(onchain_activity[start_decline:]))
    price[start_decline:] = np.linspace(0.7, 0.3, len(price[start_decline:])) + np.random.normal(0, 0.03, len(price[start_decline:]))

    # Clip values to [0, 1]
    social_buzz = np.clip(social_buzz, 0, 1)
    onchain_activity = np.clip(onchain_activity, 0, 1)
    price = np.clip(price, 0, 1)

    # Convert to realistic metrics
    df['narrative'] = narrative
    df['social_mentions_per_hour'] = 50 + social_buzz * 2000
    df['sentiment_score'] = 0.4 + social_buzz * 0.5
    df['influencer_score'] = social_buzz * 0.9
    df['tvl_change_pct'] = -10 + onchain_activity * 60
    df['active_addresses_change_pct'] = -5 + onchain_activity * 35
    df['dex_volume_change_pct'] = -20 + onchain_activity * 120
    df['price_change_pct'] = -10 + price * 110
    df['funding_rate'] = -0.01 + price * 0.08
    df['market_cap_millions'] = 100 * (1 + df['price_change_pct'] / 100)
    df['volume_millions'] = df['market_cap_millions'] * (0.1 + onchain_activity * 0.4)

    # Calculate momentums for divergence detection
    df['social_momentum'] = social_buzz
    df['onchain_momentum'] = onchain_activity
    df['price_momentum'] = price

    # Identify divergences
    df['divergence_type'] = 'none'
    df['divergence_strength'] = 0.0

    # Accumulation signals (Phase 2)
    accumulation_mask = (
        (df.index >= timestamps[start_acc]) &
        (df.index < timestamps[end_acc]) &
        (df['onchain_momentum'] > df['social_momentum'] + 0.1) &
        (df['price_momentum'] < 0.3)
    )
    df.loc[accumulation_mask, 'divergence_type'] = 'accumulation'
    df.loc[accumulation_mask, 'divergence_strength'] = (
        df.loc[accumulation_mask, 'onchain_momentum'] * 0.8
    )

    # Early entry signals (Early Phase 3)
    early_entry_mask = (
        (df.index >= timestamps[start_mom]) &
        (df.index < timestamps[start_mom + momentum_phase // 2]) &
        (df['social_momentum'] > 0.4) &
        (df['onchain_momentum'] > 0.6) &
        (df['price_momentum'] < df['onchain_momentum'] - 0.2)
    )
    df.loc[early_entry_mask, 'divergence_type'] = 'early_entry'
    df.loc[early_entry_mask, 'divergence_strength'] = (
        (df.loc[early_entry_mask, 'social_momentum'] + df.loc[early_entry_mask, 'onchain_momentum']) / 2
    )

    # Exit signals (Phase 4 and 5)
    exit_mask = (
        (df.index >= timestamps[start_fomo]) &
        (df['price_momentum'] > 0.7) &
        (df['onchain_momentum'] < df['price_momentum'])
    )
    df.loc[exit_mask, 'divergence_type'] = 'late_exit'
    df.loc[exit_mask, 'divergence_strength'] = df.loc[exit_mask, 'price_momentum'] * 0.7

    # Add some noise but keep signals intact
    df['lifecycle_position'] = np.zeros(len(df))
    df.loc[df.index < timestamps[end_whisper], 'lifecycle_position'] = 0.1
    df.loc[(df.index >= timestamps[start_acc]) & (df.index < timestamps[end_acc]), 'lifecycle_position'] = 0.2
    df.loc[(df.index >= timestamps[start_mom]) & (df.index < timestamps[end_mom]), 'lifecycle_position'] = 0.5
    df.loc[(df.index >= timestamps[start_fomo]) & (df.index < timestamps[end_fomo]), 'lifecycle_position'] = 0.8
    df.loc[(df.index >= timestamps[start_dist]) & (df.index < timestamps[end_dist]), 'lifecycle_position'] = 0.9
    df.loc[df.index >= timestamps[start_decline], 'lifecycle_position'] = 0.3

    return df

def generate_full_historical_data():
    """Generate complete dataset with multiple narrative cycles."""

    # Define narrative rotation schedule (realistic for 2024-2025)
    cycles = [
        # Q1 2024 - AI narrative
        {"narrative": "AI", "start": "2024-01-15", "duration": 35},

        # Q1 2024 - Meme season overlaps
        {"narrative": "Memecoins", "start": "2024-02-01", "duration": 25},

        # Q2 2024 - RWA picks up
        {"narrative": "RWA", "start": "2024-03-10", "duration": 40},

        # Q2 2024 - DePIN narrative
        {"narrative": "DePIN", "start": "2024-04-15", "duration": 35},

        # Q3 2024 - L2 wars
        {"narrative": "L2", "start": "2024-06-01", "duration": 30},

        # Q3 2024 - Gaming resurgence
        {"narrative": "Gaming", "start": "2024-07-10", "duration": 25},

        # Q4 2024 - AI agents return
        {"narrative": "AI", "start": "2024-09-15", "duration": 45},

        # Q4 2024 - Memecoins again
        {"narrative": "Memecoins", "start": "2024-10-20", "duration": 20},

        # Q4 2024 - RWA institutional
        {"narrative": "RWA", "start": "2024-11-15", "duration": 35},

        # Q1 2025 - DePIN infrastructure
        {"narrative": "DePIN", "start": "2025-01-10", "duration": 30},

        # Q1 2025 - AI final run
        {"narrative": "AI", "start": "2025-02-01", "duration": 25},
    ]

    all_data = []
    for cycle in cycles:
        cycle_data = generate_realistic_narrative_cycle(
            cycle["start"],
            cycle["narrative"],
            cycle["duration"]
        )
        all_data.append(cycle_data)

    # Combine all cycles
    full_df = pd.concat(all_data, axis=0)
    full_df = full_df.sort_index()

    # Remove duplicates if any overlap
    full_df = full_df[~full_df.index.duplicated(keep='first')]

    # Fill any gaps with low activity data
    full_range = pd.date_range(full_df.index.min(), full_df.index.max(), freq='H')
    full_df = full_df.reindex(full_range)

    # Fill NaN values
    full_df['narrative'] = full_df['narrative'].fillna('Market_Neutral')
    for col in full_df.columns:
        if col != 'narrative' and col != 'divergence_type':
            full_df[col] = full_df[col].fillna(full_df[col].mean())

    full_df['divergence_type'] = full_df['divergence_type'].fillna('none')
    full_df['divergence_strength'] = full_df['divergence_strength'].fillna(0.0)

    return full_df

if __name__ == "__main__":
    print("Generating realistic historical data with proper divergences...")

    df = generate_full_historical_data()

    # Save the data
    import os
    os.makedirs("backtest/data", exist_ok=True)
    df.to_csv("backtest/data/historical_data_2024_2025.csv")

    # Generate summary
    summary = {
        "total_records": len(df),
        "date_range": f"{df.index.min()} to {df.index.max()}",
        "narratives": list(df['narrative'].unique()),
        "divergence_signals": {
            "early_entry": len(df[df['divergence_type'] == 'early_entry']),
            "accumulation": len(df[df['divergence_type'] == 'accumulation']),
            "late_exit": len(df[df['divergence_type'] == 'late_exit']),
        },
        "signal_strength": {
            "avg_strength": df[df['divergence_strength'] > 0]['divergence_strength'].mean(),
            "max_strength": df['divergence_strength'].max(),
            "signals_above_0.6": len(df[df['divergence_strength'] > 0.6])
        }
    }

    with open("backtest/data/data_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nGenerated {len(df)} hours of data")
    print(f"Divergence signals:")
    print(f"  Early Entry: {summary['divergence_signals']['early_entry']}")
    print(f"  Accumulation: {summary['divergence_signals']['accumulation']}")
    print(f"  Late Exit: {summary['divergence_signals']['late_exit']}")
    print(f"  Signals > 0.6 strength: {summary['signal_strength']['signals_above_0.6']}")
    print("\nData saved to backtest/data/")