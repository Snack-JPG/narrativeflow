"""
Backtest engine to simulate trading based on divergence signals.
Tests the hypothesis: "Follow divergence signals for alpha."
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from dataclasses import dataclass, asdict

@dataclass
class Trade:
    """Represents a single trade based on divergence signal."""
    entry_time: datetime
    exit_time: Optional[datetime]
    narrative: str
    signal_type: str
    entry_price: float
    exit_price: Optional[float]
    position_size: float
    pnl: Optional[float]
    pnl_pct: Optional[float]
    max_drawdown: Optional[float]
    time_to_peak_hours: Optional[int]
    signal_strength: float

@dataclass
class BacktestResults:
    """Aggregated backtest results."""
    # Overall performance
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    # Returns
    total_return_pct: float
    avg_return_per_trade: float
    best_trade_return: float
    worst_trade_return: float
    sharpe_ratio: float
    max_drawdown_pct: float

    # Timing
    avg_time_to_peak_hours: float
    avg_holding_period_hours: float

    # By signal type
    performance_by_signal: Dict[str, Dict]

    # By narrative
    performance_by_narrative: Dict[str, Dict]

    # False positives
    false_positive_rate: float

    # Capital efficiency
    avg_capital_deployed: float
    capital_turnover: float

    # Risk metrics
    value_at_risk_95: float
    conditional_value_at_risk: float

class BacktestEngine:
    """Engine for backtesting divergence signal trading strategy."""

    def __init__(self,
                 initial_capital: float = 100000,
                 max_position_size: float = 0.1,  # Max 10% per position
                 stop_loss: float = 0.15,  # 15% stop loss
                 take_profit: float = 0.5,  # 50% take profit
                 signal_threshold: float = 0.6):  # Min signal strength
        self.initial_capital = initial_capital
        self.max_position_size = max_position_size
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.signal_threshold = signal_threshold
        self.current_capital = initial_capital
        self.trades: List[Trade] = []

    def load_historical_data(self, filepath: str) -> pd.DataFrame:
        """Load generated historical data."""
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        return df

    def identify_entry_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify valid entry points based on divergence signals."""
        # Filter for strong signals only
        signals = df[
            (df['divergence_type'].isin(['early_entry', 'accumulation'])) &
            (df['divergence_strength'] >= self.signal_threshold)
        ].copy()

        # Remove signals too close together (min 24 hours between entries per narrative)
        signals['narrative_time'] = signals.groupby('narrative').cumcount()

        # Calculate hours since last signal for each narrative
        hours_since_last = []
        for narrative in signals['narrative'].unique():
            narrative_signals = signals[signals['narrative'] == narrative]
            time_diffs = narrative_signals.index.to_series().diff().dt.total_seconds() / 3600
            hours_since_last.extend(time_diffs.tolist())

        # Reorder to match original dataframe order
        signals = signals.sort_index()
        signals['hours_since_last'] = pd.Series(hours_since_last, index=signals.index)

        # Keep only signals with sufficient spacing
        valid_signals = signals[
            (signals['hours_since_last'].isna()) |  # First signal for narrative
            (signals['hours_since_last'] >= 24)  # Or 24+ hours since last
        ]

        return valid_signals

    def simulate_trade(self, entry_signal: pd.Series, df: pd.DataFrame) -> Trade:
        """Simulate a single trade from entry to exit."""
        entry_time = entry_signal.name
        narrative = entry_signal['narrative']
        signal_type = entry_signal['divergence_type']
        entry_price = 100  # Normalized price

        # Calculate position size based on signal strength
        position_size = min(
            self.max_position_size * self.current_capital,
            self.current_capital * 0.1  # Never risk more than 10%
        )

        # Find exit point
        future_data = df[
            (df.index > entry_time) &
            (df['narrative'] == narrative)
        ].head(240)  # Look max 10 days ahead

        if len(future_data) == 0:
            # No future data, consider trade incomplete
            return Trade(
                entry_time=entry_time,
                exit_time=None,
                narrative=narrative,
                signal_type=signal_type,
                entry_price=entry_price,
                exit_price=None,
                position_size=position_size,
                pnl=None,
                pnl_pct=None,
                max_drawdown=None,
                time_to_peak_hours=None,
                signal_strength=entry_signal['divergence_strength']
            )

        # Track price movement
        price_series = entry_price * (1 + future_data['price_change_pct'] / 100)
        max_price = price_series.max()
        min_price = price_series.min()

        # Exit conditions
        exit_time = None
        exit_price = None

        # Check for stop loss
        if min_price <= entry_price * (1 - self.stop_loss):
            stop_loss_time = price_series[price_series <= entry_price * (1 - self.stop_loss)].index[0]
            exit_time = stop_loss_time
            exit_price = entry_price * (1 - self.stop_loss)

        # Check for take profit
        elif max_price >= entry_price * (1 + self.take_profit):
            take_profit_time = price_series[price_series >= entry_price * (1 + self.take_profit)].index[0]
            if exit_time is None or take_profit_time < exit_time:
                exit_time = take_profit_time
                exit_price = entry_price * (1 + self.take_profit)

        # Check for exit signal (late_exit)
        exit_signals = future_data[future_data['divergence_type'] == 'late_exit']
        if len(exit_signals) > 0:
            signal_exit_time = exit_signals.index[0]
            if exit_time is None or signal_exit_time < exit_time:
                exit_time = signal_exit_time
                exit_price = price_series.loc[signal_exit_time]

        # If no exit condition met, exit at end of period
        if exit_time is None:
            exit_time = future_data.index[-1]
            exit_price = price_series.iloc[-1]

        # Calculate P&L
        pnl = position_size * ((exit_price - entry_price) / entry_price)
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100

        # Calculate max drawdown during trade
        cumulative_returns = (price_series[:exit_time] / entry_price - 1) * 100
        running_max = cumulative_returns.expanding().max()
        drawdown = cumulative_returns - running_max
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0

        # Time to peak
        if max_price > entry_price:
            peak_time = price_series[price_series == max_price].index[0]
            time_to_peak_hours = int((peak_time - entry_time).total_seconds() / 3600)
        else:
            time_to_peak_hours = None

        # Update capital
        self.current_capital += pnl

        return Trade(
            entry_time=entry_time,
            exit_time=exit_time,
            narrative=narrative,
            signal_type=signal_type,
            entry_price=entry_price,
            exit_price=exit_price,
            position_size=position_size,
            pnl=pnl,
            pnl_pct=pnl_pct,
            max_drawdown=max_drawdown,
            time_to_peak_hours=time_to_peak_hours,
            signal_strength=entry_signal['divergence_strength']
        )

    def run_backtest(self, df: pd.DataFrame) -> BacktestResults:
        """Run full backtest on historical data."""
        # Reset state
        self.current_capital = self.initial_capital
        self.trades = []

        # Identify all entry signals
        entry_signals = self.identify_entry_signals(df)
        print(f"Found {len(entry_signals)} valid entry signals")

        # Sort by time
        entry_signals = entry_signals.sort_index()

        # Track active positions to avoid overexposure
        active_positions = {}

        # Simulate each trade
        for idx, signal in entry_signals.iterrows():
            narrative = signal['narrative']

            # Check if we already have an active position in this narrative
            if narrative in active_positions:
                # Check if previous position is closed
                prev_trade = active_positions[narrative]
                if prev_trade.exit_time and idx > prev_trade.exit_time:
                    # Previous trade closed, can enter new position
                    del active_positions[narrative]
                else:
                    # Still in position, skip signal
                    continue

            # Simulate trade
            trade = self.simulate_trade(signal, df)
            self.trades.append(trade)

            # Track active position
            if trade.exit_time:
                active_positions[narrative] = trade

        # Calculate results
        results = self.calculate_results()
        return results

    def calculate_results(self) -> BacktestResults:
        """Calculate comprehensive backtest metrics."""
        if not self.trades:
            return self._empty_results()

        # Filter completed trades
        completed_trades = [t for t in self.trades if t.pnl is not None]

        if not completed_trades:
            return self._empty_results()

        # Basic metrics
        winning_trades = [t for t in completed_trades if t.pnl > 0]
        losing_trades = [t for t in completed_trades if t.pnl <= 0]

        total_trades = len(completed_trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        # Returns
        returns = [t.pnl_pct for t in completed_trades]
        total_return_pct = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        avg_return_per_trade = np.mean(returns) if returns else 0
        best_trade_return = max(returns) if returns else 0
        worst_trade_return = min(returns) if returns else 0

        # Sharpe ratio (assuming 0% risk-free rate, annualized)
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(365 * 24 / 48)  # Assuming 48-hour avg holding
        else:
            sharpe_ratio = 0

        # Maximum drawdown
        capital_curve = [self.initial_capital]
        current = self.initial_capital
        for trade in completed_trades:
            current += trade.pnl
            capital_curve.append(current)

        capital_series = pd.Series(capital_curve)
        running_max = capital_series.expanding().max()
        drawdown_series = (capital_series - running_max) / running_max * 100
        max_drawdown_pct = drawdown_series.min()

        # Timing metrics
        holding_periods = [(t.exit_time - t.entry_time).total_seconds() / 3600
                          for t in completed_trades if t.exit_time]
        avg_holding_period_hours = np.mean(holding_periods) if holding_periods else 0

        time_to_peaks = [t.time_to_peak_hours for t in completed_trades
                        if t.time_to_peak_hours is not None]
        avg_time_to_peak_hours = np.mean(time_to_peaks) if time_to_peaks else 0

        # Performance by signal type
        performance_by_signal = {}
        for signal_type in ['early_entry', 'accumulation']:
            signal_trades = [t for t in completed_trades if t.signal_type == signal_type]
            if signal_trades:
                signal_returns = [t.pnl_pct for t in signal_trades]
                performance_by_signal[signal_type] = {
                    'trades': len(signal_trades),
                    'win_rate': len([t for t in signal_trades if t.pnl > 0]) / len(signal_trades),
                    'avg_return': np.mean(signal_returns),
                    'total_return': sum(signal_returns)
                }

        # Performance by narrative
        performance_by_narrative = {}
        for narrative in set(t.narrative for t in completed_trades):
            narrative_trades = [t for t in completed_trades if t.narrative == narrative]
            if narrative_trades:
                narrative_returns = [t.pnl_pct for t in narrative_trades]
                performance_by_narrative[narrative] = {
                    'trades': len(narrative_trades),
                    'win_rate': len([t for t in narrative_trades if t.pnl > 0]) / len(narrative_trades),
                    'avg_return': np.mean(narrative_returns),
                    'total_return': sum(narrative_returns)
                }

        # False positive rate (trades that lost money despite strong signal)
        strong_signal_trades = [t for t in completed_trades if t.signal_strength >= 0.7]
        if strong_signal_trades:
            false_positives = [t for t in strong_signal_trades if t.pnl < 0]
            false_positive_rate = len(false_positives) / len(strong_signal_trades)
        else:
            false_positive_rate = 0

        # Capital efficiency
        avg_capital_deployed = np.mean([t.position_size for t in completed_trades])
        capital_turnover = sum(t.position_size for t in completed_trades) / self.initial_capital

        # Risk metrics (VaR and CVaR)
        if returns:
            sorted_returns = sorted(returns)
            var_index = int(len(sorted_returns) * 0.05)  # 5% VaR
            value_at_risk_95 = sorted_returns[var_index] if var_index < len(sorted_returns) else sorted_returns[0]
            conditional_value_at_risk = np.mean(sorted_returns[:var_index]) if var_index > 0 else sorted_returns[0]
        else:
            value_at_risk_95 = 0
            conditional_value_at_risk = 0

        return BacktestResults(
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            total_return_pct=total_return_pct,
            avg_return_per_trade=avg_return_per_trade,
            best_trade_return=best_trade_return,
            worst_trade_return=worst_trade_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown_pct=max_drawdown_pct,
            avg_time_to_peak_hours=avg_time_to_peak_hours,
            avg_holding_period_hours=avg_holding_period_hours,
            performance_by_signal=performance_by_signal,
            performance_by_narrative=performance_by_narrative,
            false_positive_rate=false_positive_rate,
            avg_capital_deployed=avg_capital_deployed,
            capital_turnover=capital_turnover,
            value_at_risk_95=value_at_risk_95,
            conditional_value_at_risk=conditional_value_at_risk
        )

    def _empty_results(self) -> BacktestResults:
        """Return empty results when no trades."""
        return BacktestResults(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            total_return_pct=0,
            avg_return_per_trade=0,
            best_trade_return=0,
            worst_trade_return=0,
            sharpe_ratio=0,
            max_drawdown_pct=0,
            avg_time_to_peak_hours=0,
            avg_holding_period_hours=0,
            performance_by_signal={},
            performance_by_narrative={},
            false_positive_rate=0,
            avg_capital_deployed=0,
            capital_turnover=0,
            value_at_risk_95=0,
            conditional_value_at_risk=0
        )

    def save_results(self, results: BacktestResults, output_dir: str = "backtest/results"):
        """Save backtest results to files."""
        import os
        os.makedirs(output_dir, exist_ok=True)

        # Save detailed results as JSON
        results_dict = asdict(results)
        with open(f"{output_dir}/backtest_results.json", "w") as f:
            json.dump(results_dict, f, indent=2, default=str)

        # Save trades log
        trades_data = []
        for trade in self.trades:
            if trade.pnl is not None:  # Only completed trades
                trades_data.append({
                    'entry_time': str(trade.entry_time),
                    'exit_time': str(trade.exit_time),
                    'narrative': trade.narrative,
                    'signal_type': trade.signal_type,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'position_size': trade.position_size,
                    'pnl': trade.pnl,
                    'pnl_pct': trade.pnl_pct,
                    'signal_strength': trade.signal_strength
                })

        trades_df = pd.DataFrame(trades_data)
        if not trades_df.empty:
            trades_df.to_csv(f"{output_dir}/trades_log.csv", index=False)

        # Generate performance report
        report = self.generate_performance_report(results)
        with open(f"{output_dir}/performance_report.txt", "w") as f:
            f.write(report)

        return results_dict

    def generate_performance_report(self, results: BacktestResults) -> str:
        """Generate human-readable performance report."""
        report = """
================================================================================
                     NARRATIVEFLOW BACKTEST PERFORMANCE REPORT
                            2024-2025 Historical Simulation
================================================================================

THESIS VALIDATION: "Follow divergence signals for alpha"

--------------------------------------------------------------------------------
OVERALL PERFORMANCE
--------------------------------------------------------------------------------
Total Return:           {:.2f}%
Total Trades:           {}
Win Rate:              {:.1f}%
Sharpe Ratio:          {:.2f}

Winning Trades:        {} ({:.1f}%)
Losing Trades:         {} ({:.1f}%)
Avg Return per Trade:  {:.2f}%

Best Trade:            +{:.2f}%
Worst Trade:           {:.2f}%
Max Drawdown:          {:.2f}%

--------------------------------------------------------------------------------
RISK METRICS
--------------------------------------------------------------------------------
Value at Risk (95%):        {:.2f}%
Conditional VaR:            {:.2f}%
False Positive Rate:        {:.1f}%
Capital Turnover:           {:.1f}x

--------------------------------------------------------------------------------
TIMING ANALYSIS
--------------------------------------------------------------------------------
Avg Time to Peak:          {:.0f} hours
Avg Holding Period:        {:.0f} hours

--------------------------------------------------------------------------------
PERFORMANCE BY SIGNAL TYPE
--------------------------------------------------------------------------------
""".format(
            results.total_return_pct,
            results.total_trades,
            results.win_rate * 100,
            results.sharpe_ratio,
            results.winning_trades, (results.winning_trades / max(results.total_trades, 1)) * 100,
            results.losing_trades, (results.losing_trades / max(results.total_trades, 1)) * 100,
            results.avg_return_per_trade,
            results.best_trade_return,
            results.worst_trade_return,
            results.max_drawdown_pct,
            results.value_at_risk_95,
            results.conditional_value_at_risk,
            results.false_positive_rate * 100,
            results.capital_turnover,
            results.avg_time_to_peak_hours,
            results.avg_holding_period_hours
        )

        # Add signal type performance
        for signal_type, perf in results.performance_by_signal.items():
            report += f"{signal_type.upper()}:\n"
            report += f"  Trades: {perf['trades']}\n"
            report += f"  Win Rate: {perf['win_rate']*100:.1f}%\n"
            report += f"  Avg Return: {perf['avg_return']:.2f}%\n"
            report += f"  Total Return: {perf['total_return']:.2f}%\n\n"

        report += """
--------------------------------------------------------------------------------
PERFORMANCE BY NARRATIVE
--------------------------------------------------------------------------------
"""
        # Sort narratives by total return
        sorted_narratives = sorted(
            results.performance_by_narrative.items(),
            key=lambda x: x[1]['total_return'],
            reverse=True
        )

        for narrative, perf in sorted_narratives:
            report += f"{narrative}:\n"
            report += f"  Trades: {perf['trades']}\n"
            report += f"  Win Rate: {perf['win_rate']*100:.1f}%\n"
            report += f"  Avg Return: {perf['avg_return']:.2f}%\n"
            report += f"  Total Return: {perf['total_return']:.2f}%\n\n"

        report += """
================================================================================
CONCLUSION
================================================================================
"""

        if results.total_return_pct > 50 and results.win_rate > 0.5:
            report += """
The backtest STRONGLY VALIDATES the thesis. Following divergence signals
would have generated significant alpha with a positive win rate. The strategy
successfully identified narrative rotations before price movements.

Key Success Factors:
- Early entry signals (high social/onchain, low price) were profitable
- Narrative rotation patterns were predictable and tradeable
- Risk management (stop losses) prevented major drawdowns
"""
        elif results.total_return_pct > 0:
            report += """
The backtest PARTIALLY VALIDATES the thesis. Following divergence signals
would have generated positive returns, but with room for improvement in
signal quality and risk management.

Areas for Optimization:
- Signal strength thresholds may need adjustment
- Consider adding filters for market conditions
- Timing of exits could be improved
"""
        else:
            report += """
The backtest suggests the strategy needs refinement. While divergence signals
were identified, they did not consistently translate to profitable trades.

Required Improvements:
- Re-examine signal generation logic
- Add additional confirmation indicators
- Improve entry and exit timing
"""

        report += """
================================================================================
                              END OF REPORT
================================================================================
"""
        return report


if __name__ == "__main__":
    # Run backtest
    engine = BacktestEngine(
        initial_capital=100000,
        max_position_size=0.1,
        stop_loss=0.15,
        take_profit=0.5,
        signal_threshold=0.6
    )

    # Load historical data
    df = engine.load_historical_data("backtest/data/historical_data_2024_2025.csv")
    print(f"Loaded {len(df)} hours of historical data")

    # Run backtest
    print("\nRunning backtest...")
    results = engine.run_backtest(df)

    # Save results
    engine.save_results(results)

    # Print summary
    print("\n" + "="*80)
    print("BACKTEST COMPLETE")
    print("="*80)
    print(f"Total Return: {results.total_return_pct:.2f}%")
    print(f"Win Rate: {results.win_rate*100:.1f}%")
    print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {results.max_drawdown_pct:.2f}%")
    print("\nDetailed results saved to backtest/results/")