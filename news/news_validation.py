import os
import json
import requests
from datetime import datetime, timedelta

from dotenv import load_dotenv


load_dotenv(os.path.expanduser("~/.env"))


VALIDATION_FILE = "data/news_validation.json"

VALIDATION_HOURS = 1


STOCKS = {
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


def load_data():

    if not os.path.exists(VALIDATION_FILE):
        return []

    with open(
        VALIDATION_FILE,
        "r"
    ) as f:

        return json.load(f)


def save_data(data):

    os.makedirs(
        "data",
        exist_ok=True
    )

    with open(
        VALIDATION_FILE,
        "w"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )


def get_current_price(stock):

    token = os.getenv(
        "UPSTOX_ACCESS_TOKEN"
    )

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    url = (
        "https://api.upstox.com/v2/"
        "market-quote/quotes"
    )

    params = {
        "instrument_key": STOCKS[stock]
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    stock_data = list(
        data["data"].values()
    )[0]

    return stock_data["last_price"]


def update_validation_records():

    validation_data = load_data()

    now = datetime.now()

    updated = 0
    skipped = 0

    for record in validation_data:

        if record.get("price_after") is not None:
            skipped += 1
            continue

        if record.get("price_at_signal") is None:
            skipped += 1
            continue

        try:

            signal_time = datetime.strptime(
                record["timestamp"],
                "%Y-%m-%d %H:%M:%S"
            )

        except Exception:

            skipped += 1
            continue

        required_time = (
            signal_time
            + timedelta(hours=VALIDATION_HOURS)
        )

        if now < required_time:
            skipped += 1
            continue

        stock = record["stock"]

        try:

            current_price = get_current_price(
                stock
            )

        except Exception as e:

            print(
                f"Price error for {stock}: {e}"
            )

            continue

        signal_price = record[
            "price_at_signal"
        ]

        return_percent = (
            (
                current_price
                - signal_price
            )
            / signal_price
        ) * 100

        record["price_after"] = current_price

        record["return_percent"] = round(
            return_percent,
            2
        )

        record["validated_at"] = (
            now.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        updated += 1

        print(
            f"\n{stock}"
        )

        print(
            f"Signal Price : {signal_price}"
        )

        print(
            f"Price After  : {current_price}"
        )

        print(
            f"Return       : "
            f"{round(return_percent, 2)}%"
        )

    save_data(
        validation_data
    )

    print("\n" + "=" * 70)
    print("NEWS VALIDATION UPDATE")
    print("=" * 70)

    print(
        f"\nRecords updated: {updated}"
    )

    print(
        f"Records skipped: {skipped}"
    )

    print(
        f"\nValidation horizon: "
        f"{VALIDATION_HOURS} hour"
    )

    print(
        f"Saved to: {VALIDATION_FILE}"
    )

    print("\n" + "=" * 70)


if __name__ == "__main__":

    update_validation_records()