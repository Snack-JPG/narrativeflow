"""
FastAPI routes for backtest results and historical performance.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from datetime import datetime
import json
import os
import pandas as pd

router = APIRouter(prefix="/backtest", tags=["backtest"])

@router.get("/results")
async def get_backtest_results() -> Dict:
    """
    Get comprehensive backtest results showing historical performance.

    Returns:
        Backtest performance metrics including win rate, returns, and risk metrics
    """
    try:
        # Load backtest results
        results_path = "backtest/results/backtest_results.json"
        if not os.path.exists(results_path):
            # Run backtest if results don't exist
            from backtest.backtest_engine import BacktestEngine
            engine = BacktestEngine()
            df = engine.load_historical_data("backtest/data/historical_data_2024_2025.csv")
            results = engine.run_backtest(df)
            engine.save_results(results)

        with open(results_path, "r") as f:
            results = json.load(f)

        # Add interpretation
        results["interpretation"] = interpret_results(results)

        return {
            "success": True,
            "backtest_period": "2024-01-15 to 2025-02-26",
            "thesis": "Follow divergence signals for alpha",
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trades")
async def get_trade_history(
    narrative: Optional[str] = None,
    signal_type: Optional[str] = None,
    limit: int = 100
) -> Dict:
    """
    Get historical trades from backtest.

    Args:
        narrative: Filter by narrative (AI, RWA, DePIN, etc.)
        signal_type: Filter by signal type (early_entry, accumulation, late_exit)
        limit: Maximum number of trades to return

    Returns:
        List of historical trades with performance metrics
    """
    try:
        trades_path = "backtest/results/trades_log.csv"
        if not os.path.exists(trades_path):
            return {
                "success": True,
                "trades": [],
                "message": "No trades found. Run backtest first."
            }

        # Load trades
        df = pd.read_csv(trades_path)

        # Apply filters
        if narrative:
            df = df[df['narrative'] == narrative]
        if signal_type:
            df = df[df['signal_type'] == signal_type]

        # Limit results
        df = df.head(limit)

        # Convert to dict
        trades = df.to_dict(orient='records')

        # Calculate summary stats
        if len(trades) > 0:
            summary = {
                "total_trades": len(trades),
                "avg_return": df['pnl_pct'].mean(),
                "best_trade": df['pnl_pct'].max(),
                "worst_trade": df['pnl_pct'].min(),
                "win_rate": len(df[df['pnl_pct'] > 0]) / len(df) * 100
            }
        else:
            summary = {}

        return {
            "success": True,
            "trades": trades,
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/narrative/{narrative}")
async def get_narrative_performance(narrative: str) -> Dict:
    """
    Get performance metrics for a specific narrative.

    Args:
        narrative: Narrative name (AI, RWA, DePIN, Memecoins, L2, Gaming)

    Returns:
        Performance metrics for the specified narrative
    """
    try:
        # Load backtest results
        results_path = "backtest/results/backtest_results.json"
        if not os.path.exists(results_path):
            raise HTTPException(status_code=404, detail="Backtest results not found")

        with open(results_path, "r") as f:
            results = json.load(f)

        # Get narrative performance
        if narrative not in results.get("performance_by_narrative", {}):
            return {
                "success": False,
                "message": f"No data found for narrative: {narrative}",
                "available_narratives": list(results.get("performance_by_narrative", {}).keys())
            }

        perf = results["performance_by_narrative"][narrative]

        # Load historical data for this narrative
        df = pd.read_csv("backtest/data/historical_data_2024_2025.csv", index_col=0, parse_dates=True)
        narrative_data = df[df['narrative'] == narrative]

        # Calculate additional metrics
        if len(narrative_data) > 0:
            avg_social = narrative_data['social_mentions_per_hour'].mean()
            peak_social = narrative_data['social_mentions_per_hour'].max()
            avg_tvl_change = narrative_data['tvl_change_pct'].mean()
            peak_price_change = narrative_data['price_change_pct'].max()
        else:
            avg_social = peak_social = avg_tvl_change = peak_price_change = 0

        return {
            "success": True,
            "narrative": narrative,
            "performance": perf,
            "metrics": {
                "avg_social_mentions": avg_social,
                "peak_social_mentions": peak_social,
                "avg_tvl_change": avg_tvl_change,
                "peak_price_change": peak_price_change
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/summary")
async def get_signals_summary() -> Dict:
    """
    Get summary of all divergence signals detected in historical data.

    Returns:
        Summary of signal types, counts, and effectiveness
    """
    try:
        # Load historical data
        df = pd.read_csv("backtest/data/historical_data_2024_2025.csv", index_col=0, parse_dates=True)

        # Count signals by type
        signal_counts = df['divergence_type'].value_counts().to_dict()

        # Calculate signal quality
        strong_signals = len(df[df['divergence_strength'] > 0.7])
        medium_signals = len(df[(df['divergence_strength'] > 0.5) & (df['divergence_strength'] <= 0.7)])
        weak_signals = len(df[(df['divergence_strength'] > 0) & (df['divergence_strength'] <= 0.5)])

        # Load backtest results for effectiveness
        results_path = "backtest/results/backtest_results.json"
        if os.path.exists(results_path):
            with open(results_path, "r") as f:
                backtest_results = json.load(f)
                signal_performance = backtest_results.get("performance_by_signal", {})
        else:
            signal_performance = {}

        return {
            "success": True,
            "total_signals": len(df[df['divergence_type'] != 'none']),
            "signal_counts": signal_counts,
            "signal_quality": {
                "strong": strong_signals,
                "medium": medium_signals,
                "weak": weak_signals
            },
            "signal_performance": signal_performance,
            "interpretation": {
                "early_entry": "High social/onchain momentum, price hasn't caught up yet",
                "accumulation": "Smart money accumulating while retail ignores",
                "late_exit": "Price peaked, momentum declining, time to exit"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report")
async def get_performance_report() -> Dict:
    """
    Get human-readable performance report.

    Returns:
        Formatted performance report with interpretation
    """
    try:
        report_path = "backtest/results/performance_report.txt"
        if not os.path.exists(report_path):
            return {
                "success": False,
                "message": "Performance report not found. Run backtest first."
            }

        with open(report_path, "r") as f:
            report = f.read()

        return {
            "success": True,
            "report": report,
            "format": "text",
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def interpret_results(results: Dict) -> Dict:
    """Interpret backtest results with actionable insights."""

    interpretation = {
        "verdict": "",
        "key_findings": [],
        "recommendations": [],
        "risk_assessment": ""
    }

    # Determine overall verdict
    if results["total_return_pct"] > 50 and results["win_rate"] > 0.6:
        interpretation["verdict"] = "HIGHLY SUCCESSFUL - The strategy would have generated significant alpha"
    elif results["total_return_pct"] > 20 and results["win_rate"] > 0.5:
        interpretation["verdict"] = "SUCCESSFUL - The strategy shows promise with positive returns"
    elif results["total_return_pct"] > 0:
        interpretation["verdict"] = "MARGINALLY SUCCESSFUL - Positive but modest returns"
    else:
        interpretation["verdict"] = "UNSUCCESSFUL - The strategy needs refinement"

    # Key findings
    interpretation["key_findings"] = [
        f"Total return of {results['total_return_pct']:.2f}% over the backtest period",
        f"Win rate of {results['win_rate']*100:.1f}% on {results['total_trades']} trades",
        f"Average return per trade: {results['avg_return_per_trade']:.2f}%",
        f"Maximum drawdown: {abs(results['max_drawdown_pct']):.2f}%",
        f"Sharpe ratio: {results['sharpe_ratio']:.2f}"
    ]

    # Recommendations based on performance
    if results["false_positive_rate"] > 0.3:
        interpretation["recommendations"].append(
            "Consider tightening signal thresholds to reduce false positives"
        )

    if results["avg_holding_period_hours"] > 120:
        interpretation["recommendations"].append(
            "Long holding periods suggest signals may be too late - consider earlier entry triggers"
        )

    if results["win_rate"] < 0.5:
        interpretation["recommendations"].append(
            "Low win rate - add confirmation indicators or adjust signal parameters"
        )

    if abs(results["max_drawdown_pct"]) > 20:
        interpretation["recommendations"].append(
            "High drawdown risk - implement tighter stop losses or position sizing"
        )

    # Risk assessment
    if abs(results["value_at_risk_95"]) > 10:
        interpretation["risk_assessment"] = "HIGH RISK - Expect significant volatility"
    elif abs(results["value_at_risk_95"]) > 5:
        interpretation["risk_assessment"] = "MODERATE RISK - Normal volatility for crypto"
    else:
        interpretation["risk_assessment"] = "LOW RISK - Conservative returns with limited downside"

    return interpretation