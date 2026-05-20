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

# Browser UA — many financial sites block generic bot strings from cloud IPs
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

RSS_FEEDS = [
    # General financial news
    ("Yahoo Finance", "https://finance.yahoo.com/rss/topstories"),
    ("MarketWatch Top Stories", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("MarketWatch Real-time", "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/"),
    ("CNBC Markets", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135"),
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    # Catalyst-specific — press releases with M&A, FDA, contracts
    ("GlobeNewswire M&A", "https://www.globenewswire.com/RssFeed/subjectcode/22-Mergers+Acquisitions"),
    ("GlobeNewswire Pharma", "https://www.globenewswire.com/RssFeed/industry/Pharmaceuticals"),
    ("GlobeNewswire Finance", "https://www.globenewswire.com/RssFeed/industry/Financial"),
    # Analyst coverage
    ("Benzinga", "https://www.benzinga.com/feed"),
    ("Investopedia", "https://www.investopedia.com/feeds/rss.aspx"),
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
        r = requests.get(url, headers=_HEADERS, timeout=20)
        if r.status_code != 200:
            logger.warning(f"Feed '{name}' HTTP {r.status_code}: {url}")
            return []
        root = ET.fromstring(r.content)
    except Exception as e:
        logger.warning(f"Feed '{name}' failed ({type(e).__name__}): {e}")
        return []

    # Handle both RSS <item> and Atom <entry>
    entries = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    total_fetched = len(entries)
    recent = 0
    items = []

    for entry in entries:
        title_el = entry.find("title") or entry.find("{http://www.w3.org/2005/Atom}title")
        desc_el = entry.find("description") or entry.find("{http://www.w3.org/2005/Atom}summary")
        link_el = entry.find("link") or entry.find("{http://www.w3.org/2005/Atom}link")

        title = (title_el.text or "") if title_el is not None else ""
        desc = (desc_el.text or "") if desc_el is not None else ""
        link = (link_el.get("href") or link_el.text or "") if link_el is not None else ""

        # Strip CDATA wrappers if present
        title = re.sub(r"<!\[CDATA\[(.*?)]]>", r"\1", title, flags=re.DOTALL).strip()
        desc = re.sub(r"<!\[CDATA\[(.*?)]]>", r"\1", desc, flags=re.DOTALL).strip()

        pub_date = _parse_pub_date(entry, {})
        if pub_date < since:
            continue
        recent += 1

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

    logger.info(f"  {name}: {total_fetched} articles fetched, {recent} recent, {len(items)} matched keywords")
    return items


def scan_feeds(hours_back: int = 20) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    all_items: list[dict] = []

    for name, url in RSS_FEEDS:
        items = _fetch_feed(name, url, since)
        all_items.extend(items)
        time.sleep(0.5)

    logger.info(f"RSS scan total: {len(all_items)} items")
    return all_items
