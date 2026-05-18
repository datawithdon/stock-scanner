#!/usr/bin/env python3
"""
Stock Breakout Scanner
Scans S&P 500 + S&P 400 MidCap for volume surge + price breakout signals.
Runs daily after market close and emails a ranked list of candidates.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import yfinance as yf

from alerts import send_alert
from config import FETCH_WORKERS, TOP_N
from screener import analyze
from universe import get_universe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _fetch(ticker: str) -> tuple[str, object]:
    try:
        hist = yf.download(
            ticker,
            period="1y",
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
        return ticker, (hist if not hist.empty and len(hist) >= 50 else None)
    except Exception as e:
        logger.debug(f"{ticker}: download error — {e}")
        return ticker, None


def run() -> None:
    tickers = get_universe()
    total = len(tickers)
    logger.info(f"Scanning {total} stocks with {FETCH_WORKERS} workers...")

    candidates: list[dict] = []

    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        futures = {pool.submit(_fetch, t): t for t in tickers}
        for done, future in enumerate(as_completed(futures), 1):
            ticker, hist = future.result()
            signal = analyze(ticker, hist)
            if signal:
                candidates.append(signal)
            if done % 100 == 0 or done == total:
                logger.info(f"  {done}/{total} processed — {len(candidates)} candidates so far")

    candidates.sort(key=lambda x: x["score"], reverse=True)
    top = candidates[:TOP_N]

    logger.info(f"\nTop {len(top)} candidates:")
    for c in top:
        flags = " ".join(filter(None, [
            "BREAKOUT" if c["is_breakout"] else "",
            ">50MA" if c["above_sma50"] else "",
            ">200MA" if c["above_sma200"] else "",
        ]))
        logger.info(
            f"  {c['ticker']:6s}  score={c['score']:5.1f}  "
            f"vol={c['volume_ratio']}x  RSI={c['rsi']}  {flags}"
        )

    send_alert(top, date.today().strftime("%Y-%m-%d"))


if __name__ == "__main__":
    run()
