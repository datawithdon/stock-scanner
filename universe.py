"""
Fetches ALL US-listed common stocks from the NASDAQ screener API.
Free, no API key needed. Covers NYSE, NASDAQ, AMEX (~8,000+ stocks).
Filters out ETFs, warrants, rights, preferred shares, and test issues.
"""
import logging
import re

import requests

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
}

_SCREENER_URL = (
    "https://api.nasdaq.com/api/screener/stocks"
    "?tableonly=true&limit=5000&exchange={exchange}&download=true"
)

_EXCHANGES = ["nasdaq", "nyse", "amex"]

# Valid common stock ticker: 1-5 uppercase letters only
_VALID_SYMBOL = re.compile(r'^[A-Z]{1,5}$')
_SKIP_SUFFIXES = ("W", "R", "U", "WS", "WT", "RT", "WI", "VI", "PR", "PL")


def _is_common_stock(symbol: str) -> bool:
    if not _VALID_SYMBOL.match(symbol):
        return False
    for suffix in _SKIP_SUFFIXES:
        if symbol.endswith(suffix) and len(symbol) > len(suffix):
            return False
    return True


def _fetch_exchange(exchange: str) -> list[str]:
    try:
        url = _SCREENER_URL.format(exchange=exchange)
        r = requests.get(url, headers=_HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        rows = data.get("data", {}).get("rows", [])
        tickers = []
        for row in rows:
            symbol = str(row.get("symbol", "")).strip().upper()
            if _is_common_stock(symbol):
                tickers.append(symbol)
        logger.info(f"  {exchange.upper()}: {len(tickers)} common stocks")
        return tickers
    except Exception as e:
        logger.warning(f"Could not fetch {exchange} listing: {e}")
        return []


def get_universe() -> list[str]:
    all_tickers: list[str] = []
    for exchange in _EXCHANGES:
        all_tickers.extend(_fetch_exchange(exchange))

    unique = list(set(all_tickers))

    if not unique:
        raise RuntimeError("Could not fetch any tickers — check internet connection")

    logger.info(f"Total universe: {len(unique)} US common stocks")
    return unique
