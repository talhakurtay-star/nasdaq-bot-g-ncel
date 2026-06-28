"""
V3/indicators.py
----------------
Saf-pandas teknik göstergeler (talib/pandas_ta gerekmez).

calculate_indicators(df) çağrısı OHLCV DataFrame'ine tüm gösterge sütunlarını
ekler ve döndürür. Strateji bu sütunları okur.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


def ema(s: pd.Series, p: int) -> pd.Series:
    return s.ewm(span=p, adjust=False).mean()


def rsi(s: pd.Series, p: int) -> pd.Series:
    d = s.diff()
    gain = d.clip(lower=0).ewm(com=p - 1, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(com=p - 1, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).where(loss != 0, 100.0)


def atr(h: pd.Series, l: pd.Series, c: pd.Series, p: int) -> pd.Series:
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / p, adjust=False).mean()


def adx(h: pd.Series, l: pd.Series, c: pd.Series, p: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    up, down = h.diff(), -l.diff()
    plus_dm  = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=c.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=c.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr_s = tr.ewm(alpha=1.0 / p, adjust=False).mean().replace(0, np.nan)
    plus_di  = 100 * plus_dm.ewm(alpha=1.0 / p, adjust=False).mean() / atr_s
    minus_di = 100 * minus_dm.ewm(alpha=1.0 / p, adjust=False).mean() / atr_s
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1.0 / p, adjust=False).mean(), plus_di, minus_di


def macd(s: pd.Series, fast: int, slow: int, signal: int):
    line = ema(s, fast) - ema(s, slow)
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig, line - sig


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c, h, l = df["Close"], df["High"], df["Low"]

    df[f"EMA_{C.EMA_FAST}"] = ema(c, C.EMA_FAST)
    df[f"EMA_{C.EMA_SLOW}"] = ema(c, C.EMA_SLOW)
    df[f"EMA_{C.EMA_50}"]   = ema(c, C.EMA_50)
    df["RSI"] = rsi(c, C.RSI_PERIOD)
    df["ATR"] = atr(h, l, c, C.ATR_PERIOD)

    adx_s, dmp, dmn = adx(h, l, c, C.ADX_PERIOD)
    df["ADX"] = adx_s

    _, _, df["MACD_Hist"] = macd(c, C.MACD_FAST, C.MACD_SLOW, C.MACD_SIGNAL)

    # EMA hizalama süresi (kaç bardır fast>slow?), short için negatif
    aligned = (df[f"EMA_{C.EMA_FAST}"] > df[f"EMA_{C.EMA_SLOW}"]).astype(int)
    grp = (aligned != aligned.shift()).cumsum()
    bars = aligned.groupby(grp).cumcount() + 1
    df["EMA_Align_Bars"] = bars * (2 * aligned - 1)

    # Close'un EMA50'ye göre konumu (SHORT/LONG filtresi)
    ema50 = df[f"EMA_{C.EMA_50}"].replace(0, np.nan)
    df["Close_vs_EMA50"] = (df["Close"] - df[f"EMA_{C.EMA_50}"]) / ema50

    return df
