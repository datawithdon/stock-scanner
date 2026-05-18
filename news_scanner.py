#!/usr/bin/env python3
"""
Pre-Market News Intelligence Scanner
Runs at 6am ET before market open and emails early-warning signals.

Signal layers (fastest to slowest lead time):
  1. SEC EDGAR filings — M&A, activist investors (1–3 days early)
  2. RSS feeds — analyst upgrades, sector momentum headlines (same day)
  3. Reddit mention velocity — social hype building (same day / next day)

All items pass keyword pre-filter then Claude Haiku scoring.
"""
import logging
from collections import defaultdict
from datetime import date
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD, SMTP_HOST, SMTP_PORT,
    NEWS_LOOKBACK_HOURS, REDDIT_LOOKBACK_HOURS, NEWS_MIN_SCORE, NEWS_TOP_N,
)
from news_edgar import scan_edgar
from news_feeds import scan_feeds
from news_reddit import scan_reddit
from news_scorer import score_with_claude

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_CATALYST_EMOJI = {
    "M&A": "🏦",
    "analyst": "📈",
    "sector": "🌐",
    "insider": "🔍",
    "social": "🔥",
    "other": "📰",
}


def _aggregate(items: list[dict]) -> list[dict]:
    """Collapse items by ticker, summing scores and collecting headlines."""
    by_ticker: dict[str, dict] = defaultdict(lambda: {
        "score_sum": 0, "count": 0, "signals": [], "catalysts": set(),
    })

    for item in items:
        score = item.get("bullish_score", 0)
        if score < 3:
            continue
        tickers = item.get("tickers", []) or ([item.get("ticker")] if item.get("ticker") else [])
        for ticker in tickers:
            t = ticker.upper()
            by_ticker[t]["score_sum"] += score
            by_ticker[t]["count"] += 1
            by_ticker[t]["catalysts"].add(item.get("catalyst", "other"))
            by_ticker[t]["signals"].append({
                "headline": item.get("headline", ""),
                "source": item.get("source", ""),
                "score": score,
                "reason": item.get("reason", ""),
                "url": item.get("url", ""),
                "catalyst": item.get("catalyst", "other"),
            })

    results = []
    for ticker, data in by_ticker.items():
        composite = min(100, data["score_sum"] * 8 + data["count"] * 5)
        results.append({
            "ticker": ticker,
            "composite_score": composite,
            "signal_count": data["count"],
            "catalysts": sorted(data["catalysts"]),
            "top_signals": sorted(data["signals"], key=lambda x: x["score"], reverse=True)[:3],
        })

    results.sort(key=lambda x: x["composite_score"], reverse=True)
    return results[:NEWS_TOP_N]


def _build_html(stocks: list[dict], scan_date: str) -> str:
    rows = ""
    for i, s in enumerate(stocks):
        bg = "#f0fff4" if i % 2 == 0 else "#fff"
        catalyst_badges = " ".join(
            f'<span style="background:#1565c0;color:#fff;padding:2px 6px;border-radius:3px;font-size:11px">'
            f'{_CATALYST_EMOJI.get(c,"📰")} {c}</span>'
            for c in s["catalysts"]
        )
        score_color = "#1b5e20" if s["composite_score"] >= 70 else "#e65100"
        signals_html = ""
        for sig in s["top_signals"]:
            link = f'<a href="{sig["url"]}" style="color:#1565c0">{sig["headline"][:90]}</a>' if sig["url"] else sig["headline"][:90]
            signals_html += (
                f'<div style="font-size:12px;margin:3px 0;color:#424242">'
                f'{_CATALYST_EMOJI.get(sig["catalyst"],"📰")} {link}'
                f'<span style="color:#757575"> — {sig["reason"]}</span></div>'
            )
        rows += (
            f'<tr style="background:{bg};vertical-align:top">'
            f'<td style="padding:10px 12px;font-weight:700;font-size:16px">{s["ticker"]}</td>'
            f'<td style="padding:10px 12px">{catalyst_badges}</td>'
            f'<td style="padding:10px 12px">{signals_html}</td>'
            f'<td style="padding:10px 12px;font-weight:700;color:{score_color};font-size:18px">'
            f'{s["composite_score"]}</td>'
            f'</tr>'
        )

    return f"""
<html><body style="font-family:Arial,sans-serif;max-width:980px;margin:0 auto;color:#212121">
<h2 style="color:#1a237e;border-bottom:3px solid #1a237e;padding-bottom:8px">
  &#9888; Pre-Market News Intelligence &mdash; {scan_date}
</h2>
<p>
  Early-warning signals from SEC EDGAR filings, news headlines, and Reddit
  mention velocity — ranked by composite catalyst score.
</p>
<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%">
  <thead>
    <tr style="background:#1a237e;color:#fff">
      <th style="padding:10px 12px;text-align:left">Ticker</th>
      <th style="padding:10px 12px;text-align:left">Signal Type</th>
      <th style="padding:10px 12px;text-align:left">Headlines / Reason</th>
      <th style="padding:10px 12px;text-align:left">Score</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<p style="color:#757575;font-size:11px;margin-top:24px;border-top:1px solid #eee;padding-top:12px">
  Sources: SEC EDGAR (8-K, SC 13D), Yahoo Finance / MarketWatch / Benzinga RSS,
  Reddit (WSB, stocks, investing) &bull;
  Scored by Claude Haiku AI &bull; Not financial advice.
</p>
</body></html>
"""


def _send_email(stocks: list[dict], scan_date: str) -> None:
    if not stocks:
        print("No stocks above threshold — skipping news email.")
        return

    if not EMAIL_FROM or not EMAIL_PASSWORD:
        print("Email not configured — printing results:")
        for s in stocks:
            print(f"  {s['ticker']:6s} score={s['composite_score']} catalysts={s['catalysts']}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Pre-Market] {len(stocks)} News Catalysts — {scan_date}"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(_build_html(stocks, scan_date), "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

    print(f"Pre-market email sent: {len(stocks)} stocks")


def run() -> None:
    scan_date = date.today().strftime("%Y-%m-%d")
    logger.info(f"=== Pre-Market News Scanner — {scan_date} ===")

    # Layer 1: SEC EDGAR (M&A + activist filings)
    logger.info("Scanning EDGAR filings...")
    edgar_items = scan_edgar(hours_back=NEWS_LOOKBACK_HOURS)

    # Layer 2: RSS news feeds
    logger.info("Scanning RSS feeds...")
    feed_items = scan_feeds(hours_back=NEWS_LOOKBACK_HOURS)

    # Layer 3: Reddit mention velocity
    logger.info("Scanning Reddit...")
    reddit_items = scan_reddit(hours_back=REDDIT_LOOKBACK_HOURS, min_mentions=3)

    # Score with Claude (RSS + EDGAR only — reddit uses its own scoring)
    logger.info("Scoring with Claude Haiku...")
    scorable = edgar_items + feed_items
    if scorable:
        scorable = score_with_claude(scorable)

    all_items = scorable + reddit_items

    # Aggregate by ticker and rank
    stocks = _aggregate(all_items)
    logger.info(f"\nTop {len(stocks)} news candidates:")
    for s in stocks[:10]:
        logger.info(f"  {s['ticker']:6s} score={s['composite_score']:3d}  catalysts={s['catalysts']}")

    _send_email(stocks, scan_date)


if __name__ == "__main__":
    run()
