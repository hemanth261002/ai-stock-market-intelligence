import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MAX_OPEN_POSITIONS = 3
TAKE_PROFIT = 3
STOP_LOSS = -2

token = os.getenv("UPSTOX_ACCESS_TOKEN")

headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {token}"
}

stocks = {
    "INFY": "NSE_EQ|INE009A01021",
    "HINDUNILVR": "NSE_EQ|INE030A01027",
    "SBIN": "NSE_EQ|INE062A01020",
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "ITC": "NSE_EQ|INE154A01025",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "LT": "NSE_EQ|INE018A01030"
}

results = []

for name, key in stocks.items():

    try:

        url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={key}"

        response = requests.get(url, headers=headers)
        data = response.json()

        stock_data = list(data["data"].values())[0]

        price = stock_data["last_price"]
        volume = stock_data["volume"] or 0
        change = stock_data["net_change"]

        previous_close = stock_data["ohlc"]["close"]
        day_high = stock_data["ohlc"]["high"]

        pct_change = (
            (change / previous_close) * 100
        ) if previous_close else 0

        score = (
            (pct_change * 10)
            + (volume / 10000000)
            + (
                ((price / day_high) * 100) - 95
                if day_high > 0 else 0
            )
        )

        results.append({
            "stock": name,
            "price": price,
            "score": round(score, 2)
        })

    except Exception as e:
        print(f"Error in {name}: {e}")

if len(results) == 0:
    print("No stocks scanned")
    quit()

results.sort(key=lambda x: x["score"], reverse=True)

with open("paper_trades.json", "r") as f:
    trades = json.load(f)

print("\nCHECKING TP/SL\n")

for trade in trades:

    if trade["status"] != "OPEN":
        continue

    stock = trade["stock"]

    if stock not in stocks:
        continue

    key = stocks[stock]

    url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={key}"

    response = requests.get(url, headers=headers)
    data = response.json()

    stock_data = list(data["data"].values())[0]

    current_price = stock_data["last_price"]

    invested = trade["buy_price"]

    pnl_percent = (
        (current_price - invested)
        / invested
    ) * 100

    if pnl_percent <= STOP_LOSS:

        trade["status"] = "CLOSED"
        trade["sell_price"] = current_price
        trade["sell_time"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        trade["pnl_percent"] = round(
            pnl_percent,
            2
        )
        trade["pnl_rupees"] = round(
            current_price - invested,
            2
        )

        print(
            f"STOP LOSS HIT -> {stock}"
        )

    elif pnl_percent >= TAKE_PROFIT:

        trade["status"] = "CLOSED"
        trade["sell_price"] = current_price
        trade["sell_time"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        trade["pnl_percent"] = round(
            pnl_percent,
            2
        )
        trade["pnl_rupees"] = round(
            current_price - invested,
            2
        )

        print(
            f"TAKE PROFIT HIT -> {stock}"
        )

with open("paper_trades.json", "w") as f:
    json.dump(
        trades,
        f,
        indent=4
    )

open_trades = [
    t for t in trades
    if t["status"] == "OPEN"
]

print(
    f"\nOpen Positions After Sell Check: "
    f"{len(open_trades)}"
)

for candidate in results:

    if len(open_trades) >= MAX_OPEN_POSITIONS:
        break

    already_open = False

    for trade in open_trades:

        if trade["stock"] == candidate["stock"]:
            already_open = True
            break

    if already_open:
        continue

    new_trade = {
        "stock": candidate["stock"],
        "buy_price": candidate["price"],
        "quantity": 1,
        "status": "OPEN",
        "buy_time": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    trades.append(new_trade)
    open_trades.append(new_trade)

    print(
        f"BOUGHT -> {candidate['stock']}"
    )

with open("paper_trades.json", "w") as f:
    json.dump(
        trades,
        f,
        indent=4
    )

print("\nFINAL OPEN POSITIONS\n")

for trade in open_trades:

    print(
        trade["stock"]
    )