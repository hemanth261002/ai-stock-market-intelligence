# AI-Powered Stock Market Intelligence & Paper Trading System

A Python project combining Indian stock-market data, technical screening, financial news sentiment analysis, simulated trading, and historical strategy evaluation.

## Features

- Fetches NSE market quotes using the Upstox API.
- Ranks stocks using price movement and trading volume.
- Collects financial news and analyzes sentiment and potential impact.
- Simulates trades with take-profit and stop-loss rules.
- Tracks portfolio profit and loss.
- Backtests historical trading strategies.
- Evaluates strategies on out-of-sample data.

## Technology Stack

Python, Upstox API, Marketaux API, yfinance, pandas, NumPy, Requests, python-dotenv, JSON.

## Project Structure

- `bot.py` — market scanner and paper-trading logic
- `test1.py` — historical strategy backtesting
- `test2.py` — out-of-sample evaluation
- `news/news_engine.py` — financial news collection
- `news/news_impact.py` — news impact scoring
- `news/news_validation.py` — news signal validation

## Setup

1. Install Python 3.11 or later.
2. Clone this repository.
3. Create and activate a virtual environment.
4. Install dependencies:

   `pip install -r requirements.txt`

5. Configure API credentials in a local `.env` file:

   `UPSTOX_ACCESS_TOKEN=your_token`

   `MARKETAUX_API_TOKEN=your_token`

6. Run the scanner:

   `python bot.py`

7. Run the historical backtest:

   `python test1.py`

8. Run the out-of-sample evaluation:

   `python test2.py`

## Evaluation

Initial experiments compared momentum, volume activity, price proximity, and combined technical strategies. The volume-only strategy performed best among the tested alternatives in the evaluated out-of-sample period.

Historical performance does not guarantee future results. The news-enhanced strategy still requires further historical validation.

## Limitations

- Trading is simulated; no live orders are placed.
- News coverage and API availability may be limited.
- Sentiment scoring is not a custom-trained predictive ML model.
- Backtest results depend on the selected period and assumptions.

## Disclaimer

For educational and research purposes only. Not financial advice.
