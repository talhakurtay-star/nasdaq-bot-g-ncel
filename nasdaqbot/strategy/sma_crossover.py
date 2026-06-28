"""SMA kesişim (crossover) stratejisi.

Hızlı SMA, yavaş SMA'nın üzerindeyken long (hedef ağırlık 1.0), altındayken
nakit (0.0). Klasik bir trend takip stratejisidir.
"""

from __future__ import annotations

import pandas as pd

from ..indicators import sma
from .base import Strategy


class SMACrossoverStrategy(Strategy):
    name = "sma_crossover"

    def __init__(self, fast: int = 20, slow: int = 50) -> None:
        if fast >= slow:
            raise ValueError(f"fast ({fast}) < slow ({slow}) olmalı")
        self.fast = fast
        self.slow = slow

    def generate(self, df: pd.DataFrame) -> pd.Series:
        close = df["Close"]
        fast_ma = sma(close, self.fast)
        slow_ma = sma(close, self.slow)
        # Hızlı > yavaş iken yatırımda ol.
        target = (fast_ma > slow_ma).astype(float)
        # Göstergeler hazır olmadan (NaN) pozisyon alma.
        target[fast_ma.isna() | slow_ma.isna()] = 0.0
        target.name = "target_weight"
        return target

    def describe(self) -> str:
        return f"SMA crossover (fast={self.fast}, slow={self.slow})"
