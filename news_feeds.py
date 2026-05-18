"""
Scans free RSS feeds for news headlines containing catalyst keywords.
No API key required for any source.

Ticker extraction: looks for $TICKER patterns and known S&P 500/400 company names.
"""
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import requests

from news_keywords import passes_filter, classify

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "StockBreakoutScanner/1.0"}

RSS_FEEDS = [
    ("Yahoo Finance", "https://finance.yahoo.com/rss/topstories"),
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("Benzinga", "https://www.benzinga.com/feed"),
    ("Seeking Alpha", "https://seekingalpha.com/feed.xml"),
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
]

# Common financial news ticker patterns
_TICKER_RE = re.compile(r'\$([A-Z]{1,5})\b|NYSE:\s*([A-Z]{1,5})|NASDAQ:\s*([A-Z]{1,5})')
_COMMON_NOISE = {"CEO", "CFO", "COO", "IPO", "ETF", "US", "EU", "UK", "AI", "IT", "AT"}


def _extract_tickers(text: str) -> list[str]:
    matches = _TICKER_RE.findall(text)
    tickers = []
    for groups in matches:
        t = next((g for g in groups if g), "")
        if t and t not in _COMMON_NOISE and len(t) <= 5:
            tickers.append(t)
    return list(set(tickers))


def _parse_pub_date(entry: ET.Element, ns: dict) -> datetime:
    for tag in ["{http://www.w3.org/2005/Atom}updated", "{http://www.w3.org/2005/Atom}published", "pubDate"]:
        el = entry.find(tag)
        if el is not None and el.text:
            try:
                return parsedate_to_datetime(el.text).astimezone(timezone.utc)
            except Exception:
                try:
                    return datetime.fromisoformat(el.text.rstrip("Z")).replace(tzinfo=timezone.utc)
                except Exception:
                    pass
    return datetime.now(timezone.utc)


def _fetch_feed(name: str, url: str, since: datetime) -> list[dict]:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        logger.debug(f"Feed '{name}' failed: {e}")
        return []

    items = []
    # Handle both RSS <item> and Atom <entry>
    entries = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

    for entry in entries:
        title_el = entry.find("title") or entry.find("{http://www.w3.org/2005/Atom}title")
        desc_el = entry.find("description") or entry.find("{http://www.w3.org/2005/Atom}summary")
        link_el = entry.find("link") or entry.find("{http://www.w3.org/2005/Atom}link")

        title = (title_el.text or "") if title_el is not None else ""
        desc = (desc_el.text or "") if desc_el is not None else ""
        link = (link_el.get("href") or link_el.text or "") if link_el is not None else ""

        pub_date = _parse_pub_date(entry, {})
        if pub_date < since:
            continue

        full_text = f"{title} {desc}"
        if not passes_filter(full_text):
            continue

        tickers = _extract_tickers(full_text)
        items.append({
            "tickers": tickers,
            "headline": title.strip(),
            "source": name,
            "catalyst": classify(full_text),
            "url": link,
            "published": pub_date.isoformat(),
        })

    return items


def scan_feeds(hours_back: int = 20) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    all_items: list[dict] = []

    for name, url in RSS_FEEDS:
        items = _fetch_feed(name, url, since)
        logger.info(f"  {name}: {len(items)} relevant articles")
        all_items.extend(items)
        time.sleep(0.5)

    logger.info(f"RSS scan total: {len(all_items)} items")
    return all_items
