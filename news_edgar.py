"""
Scans SEC EDGAR for recent 8-K filings (material events), SC 13D/13G (activist investors),
and Form 4 (insider buying) containing M&A / catalyst keywords.

Uses EDGAR EFTS full-text search — no API key required.
"""
import json
import logging
import time
from datetime import datetime, timedelta, timezone

import requests

from news_keywords import MA, INSIDER, passes_filter

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "StockBreakoutScanner malithdisala@gmail.com"}
_EFTS = "https://efts.sec.gov/EFTS/hits"
_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{}.json"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

_ticker_map: dict[int, str] = {}  # cik -> ticker


def _load_ticker_map() -> None:
    global _ticker_map
    if _ticker_map:
        return
    try:
        r = requests.get(_TICKERS_URL, headers=_HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        _ticker_map = {v["cik_str"]: v["ticker"] for v in data.values()}
        logger.info(f"EDGAR ticker map loaded: {len(_ticker_map)} companies")
    except Exception as e:
        logger.warning(f"Could not load EDGAR ticker map: {e}")


def _cik_to_ticker(cik_str: str) -> str:
    try:
        return _ticker_map.get(int(cik_str), "")
    except Exception:
        return ""


def _search_efts(query: str, forms: str, since: datetime) -> list[dict]:
    start_dt = since.strftime("%Y-%m-%d")
    end_dt = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    params = {
        "q": f'"{query}"',
        "forms": forms,
        "dateRange": "custom",
        "startdt": start_dt,
        "enddt": end_dt,
        "hits.hits._source": "period_of_report,entity_name,file_num,form_type",
        "hits.hits.total.value": "true",
    }
    try:
        r = requests.get(_EFTS, params=params, headers=_HEADERS, timeout=20)
        r.raise_for_status()
        return r.json().get("hits", {}).get("hits", [])
    except Exception as e:
        logger.debug(f"EFTS query '{query}' failed: {e}")
        return []


def _hits_to_items(hits: list, catalyst_type: str, query: str) -> list[dict]:
    items = []
    for h in hits:
        src = h.get("_source", {})
        entity = src.get("entity_name", "")
        form = src.get("form_type", "")
        # derive ticker from CIK embedded in filing accession
        cik_raw = h.get("_id", "")[:10].lstrip("0")
        ticker = _cik_to_ticker(cik_raw)
        if not ticker:
            continue
        items.append({
            "ticker": ticker,
            "company": entity,
            "headline": f"SEC {form}: {entity} — '{query}'",
            "source": "SEC EDGAR",
            "catalyst": catalyst_type,
            "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_raw}&type={form}",
        })
    return items


def scan_edgar(hours_back: int = 24) -> list[dict]:
    _load_ticker_map()
    since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    items: list[dict] = []
    seen: set[str] = set()

    # M&A and separation events in 8-K filings
    ma_queries = [
        "strategic alternatives",
        "merger agreement",
        "acquisition agreement",
        "spin-off",
        "tender offer",
        "separation agreement",        # e.g. SanDisk separating from WD
        "distribution agreement",      # parent distributing shares of new company
        "plan of separation",
        "independent company",         # "will become an independent company"
        "carve-out",
        "split-off",
    ]
    for q in ma_queries:
        hits = _search_efts(q, "8-K", since)
        for item in _hits_to_items(hits, "M&A", q):
            key = (item["ticker"], item["catalyst"])
            if key not in seen:
                seen.add(key)
                items.append(item)
        time.sleep(0.3)

    # Form 10 — spin-off registration statements (filed before a company separates)
    # This is how the market finds out weeks/months early about a spin-off
    hits = _search_efts("spin-off", "10-12B", since)
    for item in _hits_to_items(hits, "M&A", "spin-off registration (Form 10)"):
        key = (item["ticker"], "Form10")
        if key not in seen:
            seen.add(key)
            items.append(item)
    time.sleep(0.3)

    # Stock splits in 8-K filings
    split_queries = [
        "stock split",
        "forward stock split",
        "share split",
    ]
    for q in split_queries:
        hits = _search_efts(q, "8-K", since)
        for item in _hits_to_items(hits, "catalyst", q):
            key = (item["ticker"], "split")
            if key not in seen:
                seen.add(key)
                items.append(item)
        time.sleep(0.3)

    # Activist investors: SC 13D (>5% stake with intent to influence)
    hits = _search_efts("beneficial ownership", "SC 13D", since)
    for item in _hits_to_items(hits, "insider", "SC 13D activist stake"):
        key = (item["ticker"], "SC13D")
        if key not in seen:
            seen.add(key)
            items.append(item)
    time.sleep(0.3)

    logger.info(f"EDGAR scan: {len(items)} items found")
    return items
