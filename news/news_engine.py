import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.env"))

API_TOKEN = os.getenv("MARKETAUX_API_TOKEN")

BASE_URL = "https://api.marketaux.com/v1/news/all"

STOCK_SYMBOLS = {
    "INFY": "INFY.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "SBIN": "SBIN.NS",
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "ITC": "ITC.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "LT": "LT.NS"
}


def get_news():

    if not API_TOKEN:
        print("ERROR: MARKETAUX_API_TOKEN not found")
        return []

    symbols = ",".join(STOCK_SYMBOLS.values())

    published_after = (
        datetime.now(timezone.utc) - timedelta(hours=24)
    ).strftime("%Y-%m-%dT%H:%M")

    params = {
        "api_token": API_TOKEN,
        "symbols": symbols,
        "language": "en",
        "filter_entities": "true",
        "must_have_entities": "true",
        "published_after": published_after,
        "limit": 3
    }

    try:

        response = requests.get(
            BASE_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        return data.get("data", [])

    except requests.exceptions.RequestException as e:

        print(f"News API error: {e}")

        return []


def get_our_stock_entities(article):

    matched = []

    entities = article.get("entities", [])

    our_symbols = set(STOCK_SYMBOLS.values())

    for entity in entities:

        symbol = entity.get("symbol")

        if symbol in our_symbols:

            stock_name = next(
                (
                    name
                    for name, ticker in STOCK_SYMBOLS.items()
                    if ticker == symbol
                ),
                None
            )

            sentiment = entity.get("sentiment_score")

            matched.append({
                "stock": stock_name,
                "symbol": symbol,
                "company": entity.get("name"),
                "sentiment": (
                    round(sentiment, 3)
                    if sentiment is not None
                    else None
                ),
                "match_score": round(
                    entity.get("match_score", 0),
                    2
                )
            })

    return matched


def display_news(news):

    print("\n" + "=" * 70)
    print("STOCK NEWS INTELLIGENCE")
    print("=" * 70)

    if not news:

        print("\nNo relevant news found.")

        return

    for article in news:

        title = article.get(
            "title",
            "No title"
        )

        source = article.get(
            "source",
            "Unknown"
        )

        published = article.get(
            "published_at",
            "Unknown"
        )

        matched_stocks = get_our_stock_entities(
            article
        )

        if not matched_stocks:

            continue

        print(f"\nNEWS: {title}")
        print(f"SOURCE: {source}")
        print(f"PUBLISHED: {published}")

        print("\nAFFECTED STOCKS:")

        for stock in matched_stocks:

            sentiment = stock["sentiment"]

            if sentiment is None:

                label = "UNKNOWN"

            elif sentiment >= 0.3:

                label = "POSITIVE"

            elif sentiment <= -0.3:

                label = "NEGATIVE"

            else:

                label = "NEUTRAL"

            print(
                f"  {stock['stock']} | "
                f"Sentiment: {sentiment} | "
                f"{label} | "
                f"Match: {stock['match_score']}"
            )

        print(f"\nURL: {article.get('url', '')}")

    print("\n" + "=" * 70)


if __name__ == "__main__":

    news = get_news()

    display_news(news)
