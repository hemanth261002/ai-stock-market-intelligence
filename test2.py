import logging
import sys
from datetime import datetime, timedelta

import pandas as pd

from test1 import (
    TICKERS,
    BENCHMARK,
    fetch_historical_data,
    precompute_indicators,
    run_backtest,
    compute_performance_metrics
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


def main():

    print("\n" + "=" * 80)
    print("OUT-OF-SAMPLE STRATEGY VALIDATION")
    print("=" * 80)

    # Download the same 2-year dataset
    raw_data, benchmark_df = fetch_historical_data(
        TICKERS,
        BENCHMARK,
        years=2
    )

    if not raw_data or benchmark_df.empty:

        logging.critical(
            "Insufficient historical data."
        )

        sys.exit(1)

    processed_data = precompute_indicators(
        raw_data
    )

    all_dates = sorted(
        list(benchmark_df.index)
    )

    # 70% historical period = development period
    # 30% = completely unseen test period
    split_index = int(
        len(all_dates) * 0.70
    )

    train_dates = all_dates[
        :split_index
    ]

    test_dates = all_dates[
        split_index:
    ]

    print(
        f"\nDevelopment period:"
        f" {train_dates[0].date()}"
        f" -> {train_dates[-1].date()}"
    )

    print(
        f"Out-of-sample period:"
        f" {test_dates[0].date()}"
        f" -> {test_dates[-1].date()}"
    )

    test_profiles = {

        "Integrated Strategy": {
            "momentum": 10.0,
            "volume": 5.0,
            "proximity": 1.0
        },

        "Pure Momentum Only": {
            "momentum": 10.0,
            "volume": 0.0,
            "proximity": 0.0
        },

        "Pure Vol Activity Only": {
            "momentum": 0.0,
            "volume": 5.0,
            "proximity": 0.0
        },

        "Pure High Proximity Only": {
            "momentum": 0.0,
            "volume": 0.0,
            "proximity": 1.0
        }
    }

    results = {}

    print("\nRunning unseen-data tests...\n")

    for profile_name, weights in test_profiles.items():

        logging.info(
            f"Testing: {profile_name}"
        )

        equity_curve, closed_trades = run_backtest(
            processed_data,
            test_dates,
            weights
        )

        metrics = compute_performance_metrics(
            equity_curve,
            closed_trades,
            benchmark_df
        )

        results[profile_name] = metrics

    print("\n" + "=" * 100)
    print("OUT-OF-SAMPLE RESULTS")
    print("=" * 100)

    header = (
        f"{'Metric':<25}"
        f" | {'Integrated':<15}"
        f" | {'Momentum':<15}"
        f" | {'Volume Only':<15}"
        f" | {'Proximity':<15}"
    )

    print(header)
    print("-" * 100)

    metric_names = [
        "Total Return (%)",
        "Nifty 50 Return (%)",
        "Max Drawdown (%)",
        "Sharpe Ratio",
        "Trades Closed",
        "Win Rate (%)",
        "Profit Factor"
    ]

    profile_order = [
        "Integrated Strategy",
        "Pure Momentum Only",
        "Pure Vol Activity Only",
        "Pure High Proximity Only"
    ]

    for metric in metric_names:

        row = f"{metric:<25}"

        for profile in profile_order:

            value = results[profile].get(
                metric,
                "N/A"
            )

            row += (
                f" | {str(value):<15}"
            )

        print(row)

    print("=" * 100)

    print("\nIMPORTANT:")
    print(
        "This test uses the final 30% of the "
        "2-year period as unseen data."
    )

    print(
        "No strategy performance from this "
        "period was used to select the winner."
    )

    print("=" * 100)


if __name__ == "__main__":

    main()