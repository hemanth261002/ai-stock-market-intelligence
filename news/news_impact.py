import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from news_engine import get_news, get_our_stock_entities


load_dotenv(os.path.expanduser("~/.env"))


NEWS_TYPES = {
    "EARNINGS": [
        "earnings",
        "profit",
        "loss",
        "revenue",
        "quarterly results",
        "results",
        "ebitda"
    ],
    "REGULATION": [
        "regulation",
        "regulator",
        "rbi",
        "sebi",
        "government",
        "policy",
        "rules",
        "ban",
        "approval"
    ],
    "MANAGEMENT": [
        "ceo",
        "cfo",
        "director",
        "resigns",
        "resignation",
        "appointed",
        "appointment",
        "management"
    ],
    "LEGAL": [
        "court",
        "lawsuit",
        "legal",
        "fraud",
        "penalty",
        "fine",
        "investigation",
        "notice"
    ],
    "DEAL": [
        "deal",
        "contract",
        "partnership",
        "agreement",
        "acquisition",
        "merger",
        "order"
    ],
    "PRODUCT": [
        "product",
        "launch",
        "service",
        "technology",
        "platform"
    ],
    "MARKET": [
        "market",
        "sensex",
        "nifty",
        "stocks",
        "shares",
        "trading"
    ]
}


NEWS_TYPE_WEIGHTS = {
    "EARNINGS": 1.30,
    "REGULATION": 1.20,
    "MANAGEMENT": 1.10,
    "LEGAL": 1.20,
    "DEAL": 1.15,
    "PRODUCT": 1.00,
    "MARKET": 0.70,
    "OTHER": 0.80
}


def calculate_recency_score(published_at):

    if not published_at:
        return 0.20

    try:

        published_time = datetime.fromisoformat(
            published_at.replace("Z", "+00:00")
        )

        now = datetime.now(timezone.utc)

        age_hours = (
            now - published_time
        ).total_seconds() / 3600

        if age_hours < 2:
            return 1.00

        elif age_hours < 6:
            return 0.80

        elif age_hours < 12:
            return 0.60

        elif age_hours < 24:
            return 0.40

        else:
            return 0.20

    except Exception:

        return 0.20


def is_stock_specific(article, stock_name):

    title = article.get(
        "title",
        ""
    ).lower()

    description = article.get(
        "description",
        ""
    ).lower()

    stock_keywords = {
        "INFY": ["infosys", "infy"],
        "HINDUNILVR": [
            "hindustan unilever",
            "hul"
        ],
        "SBIN": [
            "state bank of india",
            "sbi",
            "sbin"
        ],
        "RELIANCE": [
            "reliance industries",
            "reliance"
        ],
        "TCS": [
            "tata consultancy services",
            "tcs"
        ],
        "HDFCBANK": [
            "hdfc bank",
            "hdfcbank"
        ],
        "BHARTIARTL": [
            "bharti airtel",
            "airtel"
        ],
        "ITC": [
            "itc"
        ],
        "ICICIBANK": [
            "icici bank",
            "icicibank"
        ],
        "LT": [
            "larsen",
            "larsen & toubro",
            "l&t"
        ]
    }

    keywords = stock_keywords.get(
        stock_name,
        []
    )

    text = f"{title} {description}"

    for keyword in keywords:

        if keyword in text:
            return True

    return False


def classify_news_type(article):

    title = article.get(
        "title",
        ""
    ).lower()

    description = article.get(
        "description",
        ""
    ).lower()

    text = f"{title} {description}"

    detected_types = []

    for news_type, keywords in NEWS_TYPES.items():

        for keyword in keywords:

            if keyword in text:

                detected_types.append(
                    news_type
                )

                break

    if not detected_types:

        return "OTHER"

    return detected_types[0]


def calculate_article_impact(
    sentiment,
    match_score,
    published_at,
    news_type
):

    if sentiment is None:
        sentiment = 0

    relevance = min(
        match_score / 50,
        1
    )

    recency = calculate_recency_score(
        published_at
    )

    type_weight = NEWS_TYPE_WEIGHTS.get(
        news_type,
        0.80
    )

    impact = (
        sentiment
        * relevance
        * recency
        * type_weight
        * 100
    )

    return round(
        impact,
        2
    )


def get_news_impact():

    news = get_news()

    stock_scores = {}

    for article in news:

        published_at = article.get(
            "published_at"
        )

        news_type = classify_news_type(
            article
        )

        matched_stocks = get_our_stock_entities(
            article
        )

        for stock in matched_stocks:

            stock_name = stock["stock"]

            if not is_stock_specific(
                article,
                stock_name
            ):
                continue

            sentiment = stock["sentiment"]

            match_score = stock["match_score"]

            impact = calculate_article_impact(
                sentiment,
                match_score,
                published_at,
                news_type
            )

            if stock_name not in stock_scores:

                stock_scores[stock_name] = []

            stock_scores[stock_name].append(
                {
                    "impact": impact,
                    "sentiment": sentiment,
                    "match_score": match_score,
                    "news_type": news_type,
                    "title": article.get(
                        "title",
                        "Unknown"
                    ),
                    "published_at": published_at
                }
            )

    return stock_scores


def display_impact(stock_scores):

    print("\n" + "=" * 70)
    print("NEWS IMPACT ENGINE V3")
    print("=" * 70)

    if not stock_scores:

        print("\nNo stock-specific news found.")

        return

    for stock, articles in stock_scores.items():

        total_impact = sum(
            article["impact"]
            for article in articles
        )

        average_impact = round(
            total_impact / len(articles),
            2
        )

        if average_impact >= 20:
            signal = "POSITIVE"

        elif average_impact <= -20:
            signal = "NEGATIVE"

        else:
            signal = "NEUTRAL"

        print(f"\n{stock}")
        print(f"News Score : {average_impact}")
        print(f"Signal     : {signal}")
        print(f"Articles   : {len(articles)}")

        for article in articles:

            print(
                f"  Impact: {article['impact']} | "
                f"Sentiment: {article['sentiment']} | "
                f"Match: {article['match_score']} | "
                f"Type: {article['news_type']}"
            )

            print(
                f"  {article['title']}"
            )

    print("\n" + "=" * 70)


if __name__ == "__main__":

    stock_scores = get_news_impact()

    display_impact(
        stock_scores
    )