import logging
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


TICKERS = [
    "INFY.NS",
    "HINDUNILVR.NS",
    "SBIN.NS",
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "BHARTIARTL.NS",
    "ITC.NS",
    "ICICIBANK.NS",
    "LT.NS",
    "AXISBANK.NS",
    "KOTAKBANK.NS",
    "ASIANPAINT.NS",
    "M&M.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS",
    "ULTRACEMCO.NS",
    "TATASTEEL.NS",
    "WIPRO.NS",
    "HCLTECH.NS",
    "POWERGRID.NS",
    "NTPC.NS",
    "ONGC.NS",
    "ADANIENT.NS",
    "JSWSTEEL.NS",
    "GRASIM.NS",
    "HINDALCO.NS",
    "BPCL.NS",
    "COALINDIA.NS",
    "BAJFINANCE.NS"
]

BENCHMARK = "^NSEI"

INITIAL_VIRTUAL_CASH = 100000.0
MAX_OPEN_POSITIONS = 3
CAPITAL_PER_TRADE = 25000.0

TRANSACTION_FEE_PCT = 0.00075


def fetch_historical_data(tickers, benchmark, years=2):

    end_date = datetime.today()
    start_date = end_date - timedelta(
        days=years * 365
    )

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    logging.info(
        f"Downloading historical daily data "
        f"from {start_str} to {end_str}..."
    )

    ticker_data = {}

    for ticker in tickers:

        try:

            df = yf.download(
                ticker,
                start=start_str,
                end=end_str,
                progress=False,
                auto_adjust=True
            )

            if df.empty:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            required_columns = [
                "Open",
                "High",
                "Low",
                "Close",
                "Volume"
            ]

            if not all(
                column in df.columns
                for column in required_columns
            ):
                logging.warning(
                    f"Skipping {ticker}: missing columns."
                )
                continue

            ticker_data[ticker] = df

        except Exception as e:

            logging.error(
                f"Error fetching {ticker}: {e}"
            )

    try:

        benchmark_df = yf.download(
            benchmark,
            start=start_str,
            end=end_str,
            progress=False,
            auto_adjust=True
        )

        if isinstance(
            benchmark_df.columns,
            pd.MultiIndex
        ):
            benchmark_df.columns = (
                benchmark_df.columns
                .get_level_values(0)
            )

    except Exception as e:

        logging.error(
            f"Error fetching benchmark: {e}"
        )

        benchmark_df = pd.DataFrame()

    return ticker_data, benchmark_df


def precompute_indicators(ticker_data):

    processed_data = {}

    for ticker, df in ticker_data.items():

        if len(df) < 25:
            continue

        df = df.copy()

        df["Prev_Close"] = (
            df["Close"].shift(1)
        )

        df["pct_change"] = (
            (
                df["Close"]
                - df["Prev_Close"]
            )
            / df["Prev_Close"]
        ) * 100

        df["roll_vol_avg"] = (
            df["Volume"]
            .rolling(20)
            .mean()
        )

        df["relative_volume"] = (
            df["Volume"]
            / df["roll_vol_avg"]
        )

        df["price_near_high"] = (
            df["Close"]
            / df["High"]
        ) * 100 - 95

        tr1 = (
            df["High"]
            - df["Low"]
        )

        tr2 = (
            df["High"]
            - df["Prev_Close"]
        ).abs()

        tr3 = (
            df["Low"]
            - df["Prev_Close"]
        ).abs()

        tr = pd.concat(
            [tr1, tr2, tr3],
            axis=1
        ).max(axis=1)

        df["atr"] = (
            tr
            .rolling(14)
            .mean()
        )

        processed_data[ticker] = df.dropna()

    return processed_data


def calculate_exit(
    position,
    day_data
):

    high = float(day_data["High"])
    low = float(day_data["Low"])
    open_price = float(day_data["Open"])

    sl = position["sl"]
    tp = position["tp"]

    if low <= sl:

        exit_price = min(
            open_price,
            sl
        )

        return exit_price, "SL"

    if high >= tp:

        exit_price = max(
            open_price,
            tp
        )

        return exit_price, "TP"

    return None, None


def run_backtest(
    ticker_data,
    benchmark_dates,
    weights
):

    cash = INITIAL_VIRTUAL_CASH

    open_positions = []
    closed_trades = []
    equity_curve = []

    pending_entries = []

    master_dates = sorted(
        list(benchmark_dates)
    )

    for i in range(
        21,
        len(master_dates)
    ):

        current_date = master_dates[i]

        # -------------------------------------------------
        # STEP A: ENTER ORDERS GENERATED ON PREVIOUS DAY
        # -------------------------------------------------

        if pending_entries:

            for pending in pending_entries:

                if len(open_positions) >= MAX_OPEN_POSITIONS:
                    break

                stock = pending["stock"]

                if stock not in ticker_data:
                    continue

                stock_df = ticker_data[stock]

                if current_date not in stock_df.index:
                    continue

                entry_price = float(
                    stock_df.loc[
                        current_date,
                        "Open"
                    ]
                )

                if entry_price <= 0:
                    continue

                quantity = int(
                    CAPITAL_PER_TRADE
                    / entry_price
                )

                if quantity <= 0:
                    continue

                entry_cost = (
                    entry_price
                    * quantity
                    * (1 + TRANSACTION_FEE_PCT)
                )

                if entry_cost > cash:
                    continue

                atr = pending["atr"]

                if pd.isna(atr) or atr <= 0:
                    continue

                sl_price = (
                    entry_price
                    - (1.5 * atr)
                )

                tp_price = (
                    entry_price
                    + (3.0 * atr)
                )

                cash -= entry_cost

                open_positions.append(
                    {
                        "stock": stock,
                        "entry_date": current_date,
                        "entry_price": entry_price,
                        "quantity": quantity,
                        "entry_cost": entry_cost,
                        "sl": sl_price,
                        "tp": tp_price
                    }
                )

            pending_entries = []

        # -------------------------------------------------
        # STEP B: CHECK EXITS
        # -------------------------------------------------

        still_open = []

        for position in open_positions:

            stock = position["stock"]

            stock_df = ticker_data[stock]

            if current_date not in stock_df.index:

                still_open.append(position)

                continue

            day_data = stock_df.loc[
                current_date
            ]

            exit_price, reason = calculate_exit(
                position,
                day_data
            )

            if exit_price is None:

                still_open.append(position)

                continue

            quantity = position["quantity"]

            entry_cost = position["entry_cost"]

            exit_proceeds = (
                exit_price
                * quantity
                * (1 - TRANSACTION_FEE_PCT)
            )

            net_pnl = (
                exit_proceeds
                - entry_cost
            )

            net_return = (
                net_pnl
                / entry_cost
            ) * 100

            cash += exit_proceeds

            closed_trades.append(
                {
                    "stock": stock,
                    "entry_date": position["entry_date"],
                    "exit_date": current_date,
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "quantity": quantity,
                    "pnl": net_pnl,
                    "return_pct": net_return,
                    "reason": reason
                }
            )

        open_positions = still_open

        # -------------------------------------------------
        # STEP C: SCORE STOCKS USING CURRENT DAY CLOSE
        # -------------------------------------------------

        candidates = []

        for stock, df in ticker_data.items():

            if current_date not in df.index:
                continue

            if any(
                position["stock"] == stock
                for position in open_positions
            ):
                continue

            row = df.loc[current_date]

            pct_change = float(
                row["pct_change"]
            )

            relative_volume = float(
                row["relative_volume"]
            )

            proximity = float(
                row["price_near_high"]
            )

            atr = float(
                row["atr"]
            )

            score = (
                pct_change
                * weights["momentum"]
            ) + (
                relative_volume
                * weights["volume"]
            ) + (
                proximity
                * weights["proximity"]
            )

            candidates.append(
                (
                    stock,
                    score,
                    atr
                )
            )

        candidates.sort(
            key=lambda x: x[1],
            reverse=True
        )

        # -------------------------------------------------
        # STEP D: SCHEDULE NEXT-DAY ENTRIES
        # -------------------------------------------------

        slots_available = (
            MAX_OPEN_POSITIONS
            - len(open_positions)
        )

        for stock, score, atr in candidates:

            if slots_available <= 0:
                break

            if any(
                pending["stock"] == stock
                for pending in pending_entries
            ):
                continue

            pending_entries.append(
                {
                    "stock": stock,
                    "score": score,
                    "atr": atr
                }
            )

            slots_available -= 1

        # -------------------------------------------------
        # STEP E: MARK PORTFOLIO TO CURRENT CLOSE
        # -------------------------------------------------

        current_equity = cash

        for position in open_positions:

            stock = position["stock"]

            stock_df = ticker_data[stock]

            if current_date in stock_df.index:

                close_price = float(
                    stock_df.loc[
                        current_date,
                        "Close"
                    ]
                )

            else:

                close_price = position[
                    "entry_price"
                ]

            current_equity += (
                position["quantity"]
                * close_price
            )

        equity_curve.append(
            current_equity
        )

    return (
        equity_curve,
        closed_trades
    )


def compute_performance_metrics(
    equity_curve,
    closed_trades,
    nifty_df
):

    if not equity_curve:
        return {}

    equity_series = pd.Series(
        equity_curve
    )

    total_return = (
        (
            equity_series.iloc[-1]
            - INITIAL_VIRTUAL_CASH
        )
        / INITIAL_VIRTUAL_CASH
    ) * 100

    rolling_max = (
        equity_series
        .cummax()
    )

    drawdowns = (
        equity_series
        - rolling_max
    ) / rolling_max

    max_drawdown = (
        drawdowns.min()
        * 100
    )

    daily_returns = (
        equity_series
        .pct_change()
        .dropna()
    )

    if (
        not daily_returns.empty
        and daily_returns.std() > 0
    ):

        sharpe = (
            daily_returns.mean()
            / daily_returns.std()
        ) * np.sqrt(252)

    else:

        sharpe = 0.0

    wins = [
        trade
        for trade in closed_trades
        if trade["pnl"] > 0
    ]

    losses = [
        trade
        for trade in closed_trades
        if trade["pnl"] <= 0
    ]

    if closed_trades:

        win_rate = (
            len(wins)
            / len(closed_trades)
        ) * 100

    else:

        win_rate = 0.0

    avg_win = (
        np.mean(
            [trade["pnl"] for trade in wins]
        )
        if wins
        else 0.0
    )

    avg_loss = (
        np.mean(
            [trade["pnl"] for trade in losses]
        )
        if losses
        else 0.0
    )

    total_win_amount = sum(
        trade["pnl"]
        for trade in wins
    )

    total_loss_amount = abs(
        sum(
            trade["pnl"]
            for trade in losses
        )
    )

    if total_loss_amount > 0:

        profit_factor = (
            total_win_amount
            / total_loss_amount
        )

    else:

        profit_factor = float("inf")

    benchmark_return = 0.0

    if not nifty_df.empty:

        valid_dates = [
            date
            for date in nifty_df.index
            if date in pd.Index(
                nifty_df.index
            )
        ]

        if len(valid_dates) >= 22:

            benchmark_start = float(
                nifty_df.loc[
                    valid_dates[21],
                    "Close"
                ]
            )

            benchmark_end = float(
                nifty_df.loc[
                    valid_dates[-1],
                    "Close"
                ]
            )

            if benchmark_start > 0:

                benchmark_return = (
                    (
                        benchmark_end
                        - benchmark_start
                    )
                    / benchmark_start
                ) * 100

    return {
        "Total Return (%)": round(
            total_return,
            2
        ),
        "Nifty 50 Return (%)": round(
            benchmark_return,
            2
        ),
        "Max Drawdown (%)": round(
            max_drawdown,
            2
        ),
        "Sharpe Ratio": round(
            sharpe,
            2
        ),
        "Trades Closed": len(
            closed_trades
        ),
        "Win Rate (%)": round(
            win_rate,
            2
        ),
        "Avg Win (₹)": round(
            avg_win,
            2
        ),
        "Avg Loss (₹)": round(
            avg_loss,
            2
        ),
        "Profit Factor": round(
            profit_factor,
            2
        )
    }


def main():

    raw_data, benchmark_df = (
        fetch_historical_data(
            TICKERS,
            BENCHMARK,
            years=2
        )
    )

    if (
        not raw_data
        or benchmark_df.empty
    ):

        logging.critical(
            "Insufficient historical data downloaded."
        )

        sys.exit(1)

    processed_data = (
        precompute_indicators(
            raw_data
        )
    )

    benchmark_dates = (
        benchmark_df.index
    )

    active_tickers = list(
        processed_data.keys()
    )

    logging.info(
        f"System loaded with "
        f"{len(active_tickers)} parsed stocks."
    )

    test_profiles = {

        "1. Integrated Strategy": {
            "momentum": 10.0,
            "volume": 5.0,
            "proximity": 1.0
        },

        "2. Pure Momentum Only": {
            "momentum": 10.0,
            "volume": 0.0,
            "proximity": 0.0
        },

        "3. Pure Vol Activity Only": {
            "momentum": 0.0,
            "volume": 5.0,
            "proximity": 0.0
        },

        "4. Pure High Proximity Only": {
            "momentum": 0.0,
            "volume": 0.0,
            "proximity": 1.0
        }
    }

    comparison_sheet = {}

    for profile_name, weights in test_profiles.items():

        logging.info(
            f"\nEvaluating performance profile: "
            f"{profile_name}..."
        )

        equity_curve, closed_trades = (
            run_backtest(
                processed_data,
                benchmark_dates,
                weights
            )
        )

        metrics = (
            compute_performance_metrics(
                equity_curve,
                closed_trades,
                benchmark_df
            )
        )

        comparison_sheet[
            profile_name
        ] = metrics

    print("\n" + "=" * 95)

    print(
        " "
        * 20
        + "HISTORICAL STRATEGY ANALYSIS CARD"
    )

    print("=" * 95)

    headers = (
        f"{'Metric Name':<28}"
    )

    for name in test_profiles.keys():

        headers += (
            f" | "
            f"{name.split('.')[1].strip():<20}"
        )

    print(headers)

    print("-" * 95)

    metrics_to_show = [
        "Total Return (%)",
        "Nifty 50 Return (%)",
        "Max Drawdown (%)",
        "Sharpe Ratio",
        "Trades Closed",
        "Win Rate (%)",
        "Profit Factor"
    ]

    for metric in metrics_to_show:

        row = f"{metric:<28}"

        for name in test_profiles.keys():

            value = (
                comparison_sheet[name]
                .get(metric, "N/A")
            )

            row += (
                f" | "
                f"{str(value):<20}"
            )

        print(row)

    print("=" * 95)

    print("ANALYSIS SUMMARY:")
    print(
        "- Entries use next-day Open after "
        "signals from the previous Close."
    )
    print(
        "- Transaction fees are included "
        "in trade-level net P&L."
    )
    print(
        "- Portfolio equity is marked to "
        "the correct trading day's Close."
    )
    print(
        "- SL/TP use ATR-based volatility scaling."
    )
    print("=" * 95)


if __name__ == "__main__":

    main()