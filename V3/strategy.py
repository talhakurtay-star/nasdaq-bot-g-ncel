"""
V3/strategy.py
--------------
İki katmanlı kural motoru (V1'den taşındı, sadeleştirildi).

Katman 1 — Erken trend: EMA kesişimi sonrası ilk 1-25 bar.
Katman 2 — Pullback:    Yerleşik trend (25-120 bar) + RSI geri çekilmesi.

generate_signal(df, i) → "LONG" | "SHORT" | "HOLD"
Yalnızca geçmiş + mevcut bar kullanılır (lookahead yok).
"""

from __future__ import annotations

import math

import pandas as pd

from . import config as C


def _f(bar, key, default=0.0) -> float:
    try:
        v = bar.get(key, default)
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def generate_signal(df: pd.DataFrame, i: int) -> str:
    if i < 1 or i >= len(df):
        return "HOLD"
    bar, prev = df.iloc[i], df.iloc[i - 1]

    ema_fast = _f(bar, f"EMA_{C.EMA_FAST}", math.nan)
    ema_slow = _f(bar, f"EMA_{C.EMA_SLOW}", math.nan)
    rsi      = _f(bar, "RSI", math.nan)
    if any(math.isnan(v) for v in (ema_fast, ema_slow, rsi)):
        return "HOLD"

    adx        = _f(bar, "ADX")
    macd_hist  = _f(bar, "MACD_Hist")
    align      = _f(bar, "EMA_Align_Bars")
    cls_ema50  = _f(bar, "Close_vs_EMA50")
    atr        = _f(bar, "ATR")
    close      = _f(bar, "Close")

    # Sıkışık piyasa filtresi (enstrümandan bağımsız: ATR/price)
    if atr > 0 and close > 0 and (atr / close) < C.ATR_MIN_PCT:
        return "HOLD"

    prev_hist = _f(prev, "MACD_Hist", macd_hist)
    accel_long  = (macd_hist - prev_hist) > 0
    accel_short = (macd_hist - prev_hist) < 0

    adx_ok = adx >= C.ADX_STRONG
    up, down = ema_fast > ema_slow, ema_fast < ema_slow
    rel, reh = C.RSI_EARLY_LONG
    res, rehs = C.RSI_EARLY_SHORT
    rpl, rph = C.RSI_PULLBACK_LONG
    rps, rphs = C.RSI_PULLBACK_SHORT

    # ── Katman 1: Erken trend ─────────────────────────────────────────────
    if (up and C.EARLY_MIN_BARS <= align <= C.EARLY_MAX_BARS and rel <= rsi <= reh
            and adx_ok and macd_hist > 0 and accel_long and cls_ema50 > -0.02):
        return "LONG"
    if (down and -C.EARLY_MAX_BARS <= align <= -C.EARLY_MIN_BARS and res <= rsi <= rehs
            and adx_ok and macd_hist < 0 and accel_short and cls_ema50 < 0.02):
        return "SHORT"

    # ── Katman 2: Pullback ────────────────────────────────────────────────
    if (up and C.PULLBACK_MIN_BARS <= align <= C.PULLBACK_MAX_BARS and rpl <= rsi <= rph
            and adx_ok and macd_hist > 0 and cls_ema50 > -0.015):
        return "LONG"
    if (down and -C.PULLBACK_MAX_BARS <= align <= -C.PULLBACK_MIN_BARS and rps <= rsi <= rphs
            and adx_ok and macd_hist < 0 and cls_ema50 < 0.015):
        return "SHORT"

    return "HOLD"
