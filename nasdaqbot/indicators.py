"""Teknik göstergeler.

Hepsi pandas Series alır ve aynı indeksli Series döndürür; yan etkisizdir.
"""

from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    """Basit hareketli ortalama (Simple Moving Average)."""
    if window <= 0:
        raise ValueError("window pozitif olmalı")
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """Üstel hareketli ortalama (Exponential Moving Average)."""
    if window <= 0:
        raise ValueError("window pozitif olmalı")
    return series.ewm(span=window, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Göreceli Güç Endeksi (Relative Strength Index), 0-100 arası.

    Wilder yumuşatması (ewm alpha=1/window) kullanılır.
    """
    if window <= 0:
        raise ValueError("window pozitif olmalı")
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))
    # avg_loss == 0 iken RSI = 100 (sadece artış olmuş).
    out = out.where(avg_loss != 0, 100.0)
    return out
