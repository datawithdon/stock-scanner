import numpy as np
import pandas as pd
from config import (
    VOLUME_SURGE_MIN, BREAKOUT_LOOKBACK, RSI_PERIOD,
    RSI_MIN, RSI_MAX, MIN_PRICE, MIN_AVG_VOLUME,
)

_MIN_BARS = max(BREAKOUT_LOOKBACK + 5, 210)


def _rsi(close: pd.Series, period: int = RSI_PERIOD) -> float:
    delta = close.diff().iloc[-period * 2:]
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean().iloc[-1]
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    return round(100 - 100 / (1 + avg_gain / avg_loss), 1)


def analyze(ticker: str, hist: pd.DataFrame):
    if hist is None or len(hist) < _MIN_BARS:
        return None

    try:
        close = hist["Close"].squeeze()
        volume = hist["Volume"].squeeze()

        price = float(close.iloc[-1])
        prev_close = float(close.iloc[-2])
        if price < MIN_PRICE or np.isnan(price):
            return None

        # Volume filter
        avg_vol = float(volume.iloc[-21:-1].mean())
        today_vol = float(volume.iloc[-1])
        if avg_vol < MIN_AVG_VOLUME:
            return None
        vol_ratio = today_vol / avg_vol if avg_vol else 0
        if vol_ratio < VOLUME_SURGE_MIN:
            return None

        # Breakout: today closes above the highest close of the prior LOOKBACK days
        lookback_high = float(close.iloc[-(BREAKOUT_LOOKBACK + 1):-1].max())
        is_breakout = price > lookback_high
        breakout_pct = (price - lookback_high) / lookback_high * 100 if is_breakout else 0.0

        # Moving averages (computed on prior-day data to avoid lookahead)
        sma50 = float(close.iloc[-51:-1].mean()) if len(close) >= 51 else None
        sma200 = float(close.iloc[-201:-1].mean()) if len(close) >= 201 else None
        above_50 = price > sma50 if sma50 else False
        above_200 = price > sma200 if sma200 else False

        rsi = _rsi(close)
        rsi_ok = RSI_MIN <= rsi <= RSI_MAX

        pct_change = (price - prev_close) / prev_close * 100
        ret_3m = (price - float(close.iloc[-63])) / float(close.iloc[-63]) * 100 if len(close) >= 63 else 0.0

        # --- Scoring (max 100) ---
        # Volume: 35 pts
        vol_score = min(35, 12 + (vol_ratio - 3) / 7 * 23)

        # Breakout: 25 pts
        breakout_score = min(25, 15 + breakout_pct * 2) if is_breakout else 0

        # MA trend: 20 pts
        ma_score = (10 if above_50 else 0) + (10 if above_200 else 0)

        # RSI: 20 pts
        rsi_score = 20 if rsi_ok else (10 if (45 <= rsi < 50 or 75 < rsi <= 80) else 0)

        score = round(vol_score + breakout_score + ma_score + rsi_score, 1)

        return {
            "ticker": ticker,
            "price": round(price, 2),
            "pct_change": round(pct_change, 2),
            "volume_ratio": round(vol_ratio, 1),
            "avg_volume": int(avg_vol),
            "rsi": rsi,
            "is_breakout": is_breakout,
            "above_sma50": above_50,
            "above_sma200": above_200,
            "ret_3m": round(ret_3m, 1),
            "score": score,
        }

    except Exception:
        return None
