"""
Scans Reddit for ticker mention velocity — a leading indicator of retail hype
building before a price move.

Uses Reddit's public JSON API (no auth needed).
Tracks: mentions in last 24h vs baseline, and average sentiment in post titles.
"""
import logging
import re
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "StockBreakoutScanner/1.0 (research bot)"}
_BASE = "https://www.reddit.com/r/{}/new.json?limit=100&t=day"

SUBREDDITS = ["wallstreetbets", "stocks", "investing", "SecurityAnalysis"]

_TICKER_RE = re.compile(r'\b\$?([A-Z]{2,5})\b')
_NOISE = {
    "US", "EU", "UK", "DD", "IPO", "ETF", "CEO", "CFO", "AI", "IT",
    "PE", "VC", "FD", "ATH", "ATL", "EPS", "YOY", "QOQ", "AM", "PM",
    "WSB", "IV", "OTM", "ITM", "SPY", "QQQ", "DIA", "IWM", "VIX",
    "YOLO", "GME", "AMC", "IMO", "TBH", "FYI", "GDP", "CPI", "FED",
}

BULLISH_WORDS = {"bullish", "moon", "rocket", "long", "calls", "buy", "squeeze", "breakout", "catalyst"}
BEARISH_WORDS = {"bearish", "short", "puts", "crash", "dump", "sell", "scam", "overvalued"}


def _sentiment(text: str) -> float:
    t = text.lower()
    score = sum(1 for w in BULLISH_WORDS if w in t) - sum(1 for w in BEARISH_WORDS if w in t)
    return max(-1.0, min(1.0, score / 3.0))


def _extract_tickers(text: str) -> list[str]:
    matches = _TICKER_RE.findall(text)
    return [t for t in matches if t not in _NOISE and 2 <= len(t) <= 5]


def _fetch_subreddit(sub: str, hours_back: int) -> dict[str, dict]:
    cutoff = datetime.now(timezone.utc).timestamp() - hours_back * 3600
    counts: dict[str, dict] = {}

    url = _BASE.format(sub)
    after = None

    for page in range(3):  # max 3 pages = 300 posts
        try:
            params = {"after": after} if after else {}
            r = requests.get(url, headers=_HEADERS, params=params, timeout=15)
            if r.status_code == 429:
                logger.warning(f"Reddit r/{sub} rate-limited (429) — skipping")
                break
            if r.status_code == 403:
                logger.warning(f"Reddit r/{sub} blocked (403) — API may require auth")
                break
            if r.status_code != 200:
                logger.warning(f"Reddit r/{sub} HTTP {r.status_code}")
                break
            data = r.json()
        except Exception as e:
            logger.warning(f"Reddit r/{sub} page {page} error: {e}")
            break

        posts = data.get("data", {}).get("children", [])
        if not posts:
            break

        oldest_ts = None
        for post in posts:
            d = post.get("data", {})
            created = d.get("created_utc", 0)
            if created < cutoff:
                oldest_ts = created
                continue

            text = f"{d.get('title', '')} {d.get('selftext', '')[:400]}"
            tickers = _extract_tickers(text)
            upvotes = d.get("score", 0)
            comments = d.get("num_comments", 0)
            sent = _sentiment(text)
            weight = 1 + min(10, (upvotes + comments * 2) / 100)

            for t in tickers:
                if t not in counts:
                    counts[t] = {"mentions": 0, "weighted_sentiment": 0.0, "weight_sum": 0.0}
                counts[t]["mentions"] += 1
                counts[t]["weighted_sentiment"] += sent * weight
                counts[t]["weight_sum"] += weight

        after = data.get("data", {}).get("after")
        # stop paging if oldest post is outside lookback
        if oldest_ts and oldest_ts < cutoff:
            break
        time.sleep(1.0)

    return counts


def _fetch_stocktwits_trending() -> list[dict]:
    """
    Stocktwits free trending API — no auth required.
    Returns tickers currently trending on Stocktwits with bullish/bearish sentiment.
    """
    url = "https://api.stocktwits.com/api/2/trending/symbols.json"
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.warning(f"Stocktwits trending HTTP {r.status_code}")
            return []
        symbols = r.json().get("symbols", [])
        results = []
        for sym in symbols:
            ticker = sym.get("symbol", "")
            watchlist_count = sym.get("watchlist_count", 0)
            if not ticker or len(ticker) > 5:
                continue
            results.append({
                "ticker": ticker,
                "mentions": watchlist_count,
                "sentiment": 0.3,  # trending = mild bullish bias
                "source": "Stocktwits",
                "catalyst": "social",
                "bullish_score": 5,
                "headline": f"Stocktwits trending: {ticker} — {watchlist_count:,} watchers",
                "reason": "trending on Stocktwits",
                "url": f"https://stocktwits.com/symbol/{ticker}",
            })
        logger.info(f"  Stocktwits: {len(results)} trending tickers")
        return results
    except Exception as e:
        logger.warning(f"Stocktwits trending failed: {e}")
        return []


def scan_reddit(hours_back: int = 24, min_mentions: int = 3) -> list[dict]:
    merged: dict[str, dict] = {}

    for sub in SUBREDDITS:
        counts = _fetch_subreddit(sub, hours_back)
        for ticker, data in counts.items():
            if ticker not in merged:
                merged[ticker] = {"mentions": 0, "weighted_sentiment": 0.0, "weight_sum": 0.0}
            merged[ticker]["mentions"] += data["mentions"]
            merged[ticker]["weighted_sentiment"] += data["weighted_sentiment"]
            merged[ticker]["weight_sum"] += data["weight_sum"]
        logger.info(f"  r/{sub}: {len(counts)} tickers mentioned")

    results = []
    for ticker, data in merged.items():
        if data["mentions"] < min_mentions:
            continue
        avg_sent = data["weighted_sentiment"] / data["weight_sum"] if data["weight_sum"] else 0
        results.append({
            "ticker": ticker,
            "mentions": data["mentions"],
            "sentiment": round(avg_sent, 2),
            "source": "Reddit",
            "catalyst": "social",
            "bullish_score": min(8, 4 + data["mentions"]),
            "headline": f"Reddit: {data['mentions']} mentions across WSB/stocks/investing",
            "reason": f"{data['mentions']} mentions, sentiment {round(avg_sent, 2):+.2f}",
            "url": f"https://www.reddit.com/search/?q={ticker}&sort=new&t=day",
        })

    results.sort(key=lambda x: x["mentions"], reverse=True)
    logger.info(f"Reddit scan: {len(results)} tickers with {min_mentions}+ mentions")

    # Stocktwits trending as supplementary social signal
    stocktwits = _fetch_stocktwits_trending()

    return results + stocktwits
