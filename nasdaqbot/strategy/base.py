"""Strateji arayüzü.

Bir strateji, OHLCV DataFrame'i alıp her bar için bir hedef pozisyon sinyali
üretir. Sinyaller "target weight" olarak ifade edilir: 0.0 = tamamen nakit,
1.0 = tamamen yatırımda (long). Bu soyutlama hem backtest hem canlı paper
döngüsünde aynı şekilde kullanılır.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

import pandas as pd


class Signal(str, Enum):
    """İnsan-okunur sinyal türleri (loglama/raporlama için)."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Strategy(ABC):
    """Tüm stratejiler için soyut taban sınıf."""

    name: str = "strategy"

    @abstractmethod
    def generate(self, df: pd.DataFrame) -> pd.Series:
        """Her bar için hedef pozisyon ağırlığı üretir.

        Args:
            df: OHLCV DataFrame (Open/High/Low/Close/Volume).

        Returns:
            df ile aynı indeksli, [0.0, 1.0] aralığında float Series.
            Gösterge ısınma dönemindeki barlar için değer 0.0 olmalıdır.
        """
        raise NotImplementedError

    def describe(self) -> str:
        """Parametreleri içeren kısa bir açıklama döndürür."""
        return self.name
