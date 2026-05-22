"""
Social signal layer: Yahoo Finance trending + most-active tickers.

Reddit's JSON API now blocks GitHub Actions IPs (403 on all subreddits).
Stocktwits also blocks cloud IPs. Yahoo Finance trending/most-active APIs
are free, unauthenticated, and work reliably from GitHub Actions.
"""
import logging

import requests

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

_TRENDING_URL = "https://query1.finance.yahoo.com/v1/finance/trending/US?count=25&lang=en-US&region=US"
_MOVERS_URL = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&scrIds=day_gainers&count=25&region=US&lang=en-US"

_NOISE = {
    "SPY", "QQQ", "DIA", "IWM", "VIX", "GLD", "SLV", "TLT", "HYG", "LQD",
    "SQQQ", "TQQQ", "SPXU", "UPRO", "UVXY", "XIV",
}


def _fetch_trending() -> list[dict]:
    """Yahoo Finance US trending tickers — free, no auth."""
    try:
        r = requests.get(_TRENDING_URL, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.warning(f"Yahoo trending HTTP {r.status_code}")
            return []
        quotes = r.json().get("finance", {}).get("result", [{}])[0].get("quotes", [])
        results = []
        for q in quotes:
            ticker = q.get("symbol", "")
            if not ticker or ticker in _NOISE or len(ticker) > 5:
                continue
            results.append({
                "ticker": ticker,
                "source": "Yahoo Trending",
                "catalyst": "social",
                "bullish_score": 5,
                "headline": f"Trending on Yahoo Finance: {ticker}",
                "reason": "trending ticker on Yahoo Finance",
                "url": f"https://finance.yahoo.com/quote/{ticker}",
                "tickers": [ticker],
            })
        logger.info(f"  Yahoo trending: {len(results)} tickers")
        return results
    except Exception as e:
        logger.warning(f"Yahoo trending failed: {e}")
        return []


def _fetch_day_gainers() -> list[dict]:
    """Yahoo Finance top day gainers — stocks with biggest % gain today."""
    try:
        r = requests.get(_MOVERS_URL, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.warning(f"Yahoo day gainers HTTP {r.status_code}")
            return []
        quotes = (
            r.json()
            .get("finance", {})
            .get("result", [{}])[0]
            .get("quotes", [])
        )
        results = []
        for q in quotes:
            ticker = q.get("symbol", "")
            pct = q.get("regularMarketChangePercent", 0)
            volume = q.get("regularMarketVolume", 0)
            avg_vol = q.get("averageDailyVolume3Month", 1) or 1
            vol_ratio = round(volume / avg_vol, 1)

            if not ticker or ticker in _NOISE or len(ticker) > 5:
                continue
            if pct < 5:  # only include stocks up 5%+ today
                continue

            results.append({
                "ticker": ticker,
                "source": "Yahoo Day Gainers",
                "catalyst": "social",
                "bullish_score": min(8, 5 + int(pct / 10)),
                "headline": f"Yahoo Day Gainer: {ticker} +{pct:.1f}% today, {vol_ratio}x volume",
                "reason": f"up {pct:.1f}% with {vol_ratio}x avg volume",
                "url": f"https://finance.yahoo.com/quote/{ticker}",
                "tickers": [ticker],
            })
        logger.info(f"  Yahoo day gainers: {len(results)} tickers (≥5% gain)")
        return results
    except Exception as e:
        logger.warning(f"Yahoo day gainers failed: {e}")
        return []


def scan_reddit(hours_back: int = 24, min_mentions: int = 3) -> list[dict]:
    """
    Social signals via Yahoo Finance trending and day gainers.
    (Reddit API requires OAuth from cloud IPs — replaced with Yahoo Finance free APIs)
    """
    trending = _fetch_trending()
    gainers = _fetch_day_gainers()

    # Deduplicate: if a ticker appears in both trending and gainers, merge
    seen: dict[str, dict] = {}
    for item in trending + gainers:
        t = item["ticker"]
        if t not in seen:
            seen[t] = item
        else:
            # Boost score if it appears in both sources
            seen[t]["bullish_score"] = min(9, seen[t]["bullish_score"] + 2)
            seen[t]["reason"] += " + trending"
            seen[t]["source"] = "Yahoo Trending+Gainers"

    results = list(seen.values())
    logger.info(f"Social scan: {len(results)} tickers total")
    return results
