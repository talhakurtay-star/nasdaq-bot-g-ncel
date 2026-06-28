"""RSI eşik (mean-reversion) stratejisi.

RSI alt eşiğin (oversold) altına inince long'a geç, üst eşiği (overbought)
aşınca nakte dön. Pozisyon, eşikler arasında "tut" mantığıyla taşınır.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..indicators import rsi
from .base import Strategy


class RSIStrategy(Strategy):
    name = "rsi"

    def __init__(self, window: int = 14, lower: float = 30.0, upper: float = 70.0) -> None:
        if not (0 < lower < upper < 100):
            raise ValueError("0 < lower < upper < 100 olmalı")
        self.window = window
        self.lower = lower
        self.upper = upper

    def generate(self, df: pd.DataFrame) -> pd.Series:
        r = rsi(df["Close"], self.window)

        target = pd.Series(np.nan, index=df.index, dtype=float)
        target[r < self.lower] = 1.0   # oversold -> al
        target[r > self.upper] = 0.0   # overbought -> sat
        # Eşikler arasında önceki pozisyonu koru; başlangıçta nakit.
        target = target.ffill().fillna(0.0)
        target[r.isna()] = 0.0
        target.name = "target_weight"
        return target

    def describe(self) -> str:
        return f"RSI (window={self.window}, lower={self.lower}, upper={self.upper})"
