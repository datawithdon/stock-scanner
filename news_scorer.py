"""
Claude Haiku scores news items that passed the keyword pre-filter.

Sends batches of headlines to Claude and receives structured JSON back:
  { ticker, bullish_score (0-10), catalyst_type, reason, confidence }

Cost estimate: ~$0.001–0.005 per run at current Haiku pricing.
"""
import json
import logging
from typing import Any

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

_BATCH_SIZE = 15  # headlines per Claude API call


def _build_prompt(items: list[dict]) -> str:
    lines = "\n".join(
        f"{i+1}. [{item.get('catalyst','?').upper()}] {item.get('headline','')}"
        for i, item in enumerate(items)
    )
    return f"""You are a financial news analyst. Evaluate each headline below for pre-move potential — meaning you want to identify stocks likely to surge in the next 1–10 trading days.

Headlines:
{lines}

For each headline, respond with a JSON array entry:
- "idx": 1-based index
- "tickers": list of stock tickers mentioned or implied (empty list if none)
- "bullish_score": integer 0–10 (0 = irrelevant/bearish, 10 = strong early catalyst)
- "catalyst": one of "M&A", "analyst", "sector", "insider", "social", "other"
- "reason": ≤15 words explaining the score

Return ONLY a valid JSON array, no other text. Example:
[{{"idx":1,"tickers":["SDSK"],"bullish_score":9,"catalyst":"M&A","reason":"Spin-off creates pure-play, typical 20–40% premium"}}]"""


def score_with_claude(items: list[dict]) -> list[dict]:
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — skipping Claude scoring")
        # Fall back to keyword-based score
        for item in items:
            item.setdefault("bullish_score", 5)
            item.setdefault("reason", "keyword match only")
        return items

    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed — run: pip install anthropic")
        return items

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    scored: list[dict] = []

    for batch_start in range(0, len(items), _BATCH_SIZE):
        batch = items[batch_start: batch_start + _BATCH_SIZE]
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": _build_prompt(batch)}],
            )
            raw = msg.content[0].text.strip()
            results: list[dict] = json.loads(raw)

            for r in results:
                idx = r.get("idx", 0) - 1
                if 0 <= idx < len(batch):
                    item = batch[idx].copy()
                    item["bullish_score"] = r.get("bullish_score", 0)
                    item["reason"] = r.get("reason", "")
                    # Merge Claude's tickers with RSS-extracted tickers
                    existing = set(item.get("tickers", []))
                    claude_tickers = set(r.get("tickers", []))
                    item["tickers"] = list(existing | claude_tickers)
                    item["catalyst"] = r.get("catalyst", item.get("catalyst", "other"))
                    scored.append(item)

        except Exception as e:
            logger.warning(f"Claude scoring batch failed: {e}")
            # Pass batch through with no score rather than dropping
            for item in batch:
                item.setdefault("bullish_score", 0)
                item.setdefault("reason", "scoring unavailable")
                scored.append(item)

    return scored
