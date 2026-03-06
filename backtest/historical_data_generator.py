"""
Generate mock historical data for 2024-2025 showing realistic narrative rotation cycles.
Based on actual crypto market patterns from that period.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

class HistoricalDataGenerator:
    """Generate realistic historical data for backtesting narrative rotation."""

    # Major narrative cycles that actually happened in crypto 2024-2025
    NARRATIVE_CYCLES = {
        "AI": {
            "cycles": [
                {"start": "2024-01-15", "peak": "2024-02-20", "end": "2024-03-10", "catalyst": "GPT-5 announcement"},
                {"start": "2024-06-01", "peak": "2024-07-15", "end": "2024-08-01", "catalyst": "TAO ecosystem growth"},
                {"start": "2024-11-10", "peak": "2024-12-25", "end": "2025-01-15", "catalyst": "AI agent meta"},
            ],
            "tokens": ["TAO", "FET", "RNDR", "AGIX", "OCEAN"],
            "peak_multiplier": 3.5
        },
        "RWA": {
            "cycles": [
                {"start": "2024-02-01", "peak": "2024-03-15", "end": "2024-04-01", "catalyst": "BlackRock tokenization"},
                {"start": "2024-08-20", "peak": "2024-10-05", "end": "2024-10-25", "catalyst": "Treasury yields on-chain"},
                {"start": "2025-01-05", "peak": "2025-02-10", "end": "2025-02-28", "catalyst": "Bank partnerships"},
            ],
            "tokens": ["ONDO", "MKR", "PENDLE", "MPL", "GFI"],
            "peak_multiplier": 2.8
        },
        "DePIN": {
            "cycles": [
                {"start": "2024-03-20", "peak": "2024-05-10", "end": "2024-05-30", "catalyst": "Helium Mobile launch"},
                {"start": "2024-09-15", "peak": "2024-11-01", "end": "2024-11-20", "catalyst": "Hivemapper coverage"},
            ],
            "tokens": ["HNT", "MOBILE", "RNDR", "FIL", "AR"],
            "peak_multiplier": 4.2
        },
        "Memecoins": {
            "cycles": [
                {"start": "2024-01-01", "peak": "2024-01-25", "end": "2024-02-05", "catalyst": "BONK listing Coinbase"},
                {"start": "2024-04-15", "peak": "2024-05-20", "end": "2024-06-01", "catalyst": "PEPE resurgence"},
                {"start": "2024-10-10", "peak": "2024-11-15", "end": "2024-12-01", "catalyst": "WIF to $1"},
                {"start": "2025-02-01", "peak": "2025-02-20", "end": "2025-03-01", "catalyst": "New dog meta"},
            ],
            "tokens": ["DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI"],
            "peak_multiplier": 5.5
        },
        "L2": {
            "cycles": [
                {"start": "2024-05-01", "peak": "2024-06-20", "end": "2024-07-10", "catalyst": "Base TVL growth"},
                {"start": "2024-12-01", "peak": "2025-01-20", "end": "2025-02-05", "catalyst": "zkSync airdrop"},
            ],
            "tokens": ["ARB", "OP", "MATIC", "IMX", "METIS"],
            "peak_multiplier": 2.2
        },
        "Gaming": {
            "cycles": [
                {"start": "2024-07-01", "peak": "2024-08-15", "end": "2024-09-01", "catalyst": "AAA game launches"},
                {"start": "2025-01-15", "peak": "2025-02-25", "end": "2025-03-10", "catalyst": "Mobile gaming boom"},
            ],
            "tokens": ["IMX", "GALA", "SAND", "AXS", "MANA"],
            "peak_multiplier": 3.0
        }
    }

    def __init__(self, start_date: str = "2024-01-01", end_date: str = "2025-03-01"):
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.date_range = pd.date_range(self.start_date, self.end_date, freq='H')

    def generate_narrative_lifecycle(self, narrative: str, cycle: Dict) -> pd.DataFrame:
        """Generate lifecycle data for a single narrative cycle."""
        start = pd.to_datetime(cycle["start"])
        peak = pd.to_datetime(cycle["peak"])
        end = pd.to_datetime(cycle["end"])

        # Create hourly data
        hours = pd.date_range(start, end, freq='H')
        df = pd.DataFrame(index=hours)

        # Calculate lifecycle position (0 to 1)
        total_hours = len(hours)
        peak_hour = int((peak - start).total_seconds() / 3600)

        lifecycle_position = np.zeros(total_hours)

        # Rising phase (exponential growth)
        for i in range(peak_hour):
            lifecycle_position[i] = (i / peak_hour) ** 1.5

        # Declining phase (faster decay)
        decline_hours = total_hours - peak_hour
        for i in range(peak_hour, total_hours):
            progress = (i - peak_hour) / decline_hours
            lifecycle_position[i] = 1.0 - (progress ** 0.7)

        # Add noise
        noise = np.random.normal(0, 0.05, total_hours)
        lifecycle_position = np.clip(lifecycle_position + noise, 0, 1)

        df['lifecycle_position'] = lifecycle_position
        df['narrative'] = narrative
        df['catalyst'] = cycle["catalyst"]

        # Generate social metrics based on lifecycle
        df['social_mentions_per_hour'] = (
            100 + lifecycle_position * 2000 +
            np.random.poisson(50, total_hours)
        )

        df['sentiment_score'] = np.clip(
            0.5 + lifecycle_position * 0.4 + np.random.normal(0, 0.1, total_hours),
            0, 1
        )

        df['influencer_score'] = np.clip(
            lifecycle_position * 0.8 + np.random.normal(0, 0.1, total_hours),
            0, 1
        )

        # Generate on-chain metrics (lag behind social)
        lag_hours = 24  # On-chain lags social by ~1 day
        onchain_lifecycle = np.roll(lifecycle_position, lag_hours)
        onchain_lifecycle[:lag_hours] = 0

        df['tvl_change_pct'] = np.clip(
            -5 + onchain_lifecycle * 30 + np.random.normal(0, 3, total_hours),
            -10, 50
        )

        df['active_addresses_change_pct'] = np.clip(
            -2 + onchain_lifecycle * 20 + np.random.normal(0, 2, total_hours),
            -5, 30
        )

        df['dex_volume_change_pct'] = np.clip(
            -10 + onchain_lifecycle * 50 + np.random.normal(0, 5, total_hours),
            -20, 100
        )

        # Generate price movement (lags both social and on-chain)
        price_lag_hours = 48  # Price lags social by ~2 days
        price_lifecycle = np.roll(lifecycle_position, price_lag_hours)
        price_lifecycle[:price_lag_hours] = 0

        # Price with higher volatility
        base_price = 100
        multiplier = self.NARRATIVE_CYCLES[narrative]["peak_multiplier"]
        df['price_change_pct'] = np.clip(
            -5 + price_lifecycle * (multiplier - 1) * 100 + np.random.normal(0, 10, total_hours),
            -30, multiplier * 100
        )

        # Add market cap and volume
        df['market_cap_millions'] = base_price * (1 + df['price_change_pct'] / 100) * 10
        df['volume_millions'] = df['market_cap_millions'] * (0.1 + lifecycle_position * 0.5)

        # Funding rates (positive during FOMO, negative during accumulation)
        df['funding_rate'] = np.clip(
            -0.01 + price_lifecycle * 0.05 + np.random.normal(0, 0.005, total_hours),
            -0.02, 0.08
        )

        return df

    def generate_divergence_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify divergence signals in the data."""
        df = df.copy()

        # Calculate momentum scores with proper normalization
        window = 12  # 12-hour rolling window for smoother signals

        # Social momentum
        social_mentions_norm = df['social_mentions_per_hour'].rolling(window, min_periods=1).mean()
        social_mentions_norm = (social_mentions_norm - social_mentions_norm.min()) / (social_mentions_norm.max() - social_mentions_norm.min() + 0.001)

        sentiment_norm = df['sentiment_score'].rolling(window, min_periods=1).mean()
        influencer_norm = df['influencer_score'].rolling(window, min_periods=1).mean()

        df['social_momentum'] = (social_mentions_norm * 0.5 + sentiment_norm * 0.3 + influencer_norm * 0.2)

        # On-chain momentum
        tvl_norm = df['tvl_change_pct'].rolling(window, min_periods=1).mean()
        tvl_norm = np.clip((tvl_norm + 10) / 60, 0, 1)  # Normalize from [-10, 50] to [0, 1]

        addresses_norm = df['active_addresses_change_pct'].rolling(window, min_periods=1).mean()
        addresses_norm = np.clip((addresses_norm + 5) / 35, 0, 1)  # Normalize from [-5, 30] to [0, 1]

        volume_norm = df['dex_volume_change_pct'].rolling(window, min_periods=1).mean()
        volume_norm = np.clip((volume_norm + 20) / 120, 0, 1)  # Normalize from [-20, 100] to [0, 1]

        df['onchain_momentum'] = (tvl_norm * 0.4 + addresses_norm * 0.3 + volume_norm * 0.3)

        # Price momentum (with lag adjustment)
        price_change = df['price_change_pct'].rolling(window, min_periods=1).mean()
        df['price_momentum'] = np.clip((price_change + 30) / 130, 0, 1)  # Normalize from [-30, 100] to [0, 1]

        # Detect divergences with more realistic thresholds
        df['divergence_type'] = 'none'
        df['divergence_strength'] = 0.0

        # Early entry: High social/onchain, relatively lower price
        early_mask = (
            (df['social_momentum'] > 0.55) &
            (df['onchain_momentum'] > 0.45) &
            (df['price_momentum'] < df['social_momentum'] - 0.2)  # Price lags social by at least 0.2
        )
        df.loc[early_mask, 'divergence_type'] = 'early_entry'
        df.loc[early_mask, 'divergence_strength'] = (
            (df.loc[early_mask, 'social_momentum'] + df.loc[early_mask, 'onchain_momentum']) / 2 -
            df.loc[early_mask, 'price_momentum']
        ).clip(0.3, 1.0)

        # Late/exit: High price, declining social/onchain
        late_mask = (
            (df['price_momentum'] > 0.65) &
            ((df['social_momentum'] < 0.45) | (df['onchain_momentum'] < 0.4))
        )
        df.loc[late_mask, 'divergence_type'] = 'late_exit'
        df.loc[late_mask, 'divergence_strength'] = (
            df.loc[late_mask, 'price_momentum'] -
            (df.loc[late_mask, 'social_momentum'] + df.loc[late_mask, 'onchain_momentum']) / 2
        ).clip(0.3, 1.0)

        # Smart money accumulation: Low social, high onchain
        accumulation_mask = (
            (df['social_momentum'] < 0.35) &
            (df['onchain_momentum'] > 0.55) &
            (df['price_momentum'] < 0.4)
        )
        df.loc[accumulation_mask, 'divergence_type'] = 'accumulation'
        df.loc[accumulation_mask, 'divergence_strength'] = (
            df.loc[accumulation_mask, 'onchain_momentum'] - df.loc[accumulation_mask, 'social_momentum']
        ).clip(0.3, 1.0)

        return df

    def generate_full_dataset(self) -> pd.DataFrame:
        """Generate complete historical dataset for all narratives."""
        all_data = []

        for narrative, config in self.NARRATIVE_CYCLES.items():
            for cycle in config["cycles"]:
                cycle_data = self.generate_narrative_lifecycle(narrative, cycle)
                cycle_data = self.generate_divergence_signals(cycle_data)
                all_data.append(cycle_data)

        # Combine all narratives
        full_df = pd.concat(all_data, axis=0)
        full_df = full_df.sort_index()

        # Add some inter-narrative correlation (capital rotation)
        # When one narrative peaks, another often starts
        narratives = full_df['narrative'].unique()
        for i, narrative in enumerate(narratives):
            next_narrative = narratives[(i + 1) % len(narratives)]

            # Find peaks in current narrative
            narrative_data = full_df[full_df['narrative'] == narrative]
            peaks = narrative_data[narrative_data['lifecycle_position'] > 0.9]

            # Boost next narrative slightly after peaks
            for peak_time in peaks.index:
                boost_start = peak_time + timedelta(days=3)
                boost_end = boost_start + timedelta(days=7)

                boost_mask = (
                    (full_df.index >= boost_start) &
                    (full_df.index <= boost_end) &
                    (full_df['narrative'] == next_narrative)
                )

                if boost_mask.any():
                    full_df.loc[boost_mask, 'social_mentions_per_hour'] *= 1.3
                    full_df.loc[boost_mask, 'sentiment_score'] *= 1.1

        return full_df

    def save_to_files(self, df: pd.DataFrame, output_dir: str = "backtest/data"):
        """Save generated data to files."""
        import os
        os.makedirs(output_dir, exist_ok=True)

        # Save full dataset
        df.to_csv(f"{output_dir}/historical_data_2024_2025.csv")

        # Save summary statistics
        summary = {
            "date_range": f"{self.start_date.date()} to {self.end_date.date()}",
            "total_hours": len(df),
            "narratives": list(df['narrative'].unique()),
            "total_divergence_signals": {
                "early_entry": len(df[df['divergence_type'] == 'early_entry']),
                "late_exit": len(df[df['divergence_type'] == 'late_exit']),
                "accumulation": len(df[df['divergence_type'] == 'accumulation']),
            },
            "cycles_per_narrative": {
                narrative: len(config["cycles"])
                for narrative, config in self.NARRATIVE_CYCLES.items()
            }
        }

        with open(f"{output_dir}/data_summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"Generated {len(df)} hours of historical data")
        print(f"Saved to {output_dir}/")
        print(f"Total divergence signals: {summary['total_divergence_signals']}")

        return summary


if __name__ == "__main__":
    generator = HistoricalDataGenerator()
    historical_data = generator.generate_full_dataset()
    summary = generator.save_to_files(historical_data)
    print("\nData generation complete!")