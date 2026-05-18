import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _fetch_wikipedia_tickers(url: str, symbol_col: str = "Symbol") -> list[str]:
    try:
        tables = pd.read_html(url, attrs={"id": "constituents"})
        return tables[0][symbol_col].tolist()
    except Exception:
        try:
            tables = pd.read_html(url)
            for t in tables:
                if symbol_col in t.columns:
                    return t[symbol_col].tolist()
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
    return []


def get_universe() -> list[str]:
    sp500 = _fetch_wikipedia_tickers(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    )
    sp400 = _fetch_wikipedia_tickers(
        "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
    )

    if not sp500:
        logger.error("Could not fetch S&P 500 — aborting")
        raise RuntimeError("Universe fetch failed")

    all_tickers = list({t.replace(".", "-") for t in sp500 + sp400})
    logger.info(f"Universe: {len(all_tickers)} tickers (SP500={len(sp500)}, SP400={len(sp400)})")
    return all_tickers
