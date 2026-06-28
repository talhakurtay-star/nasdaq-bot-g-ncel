"""Çevrimdışı (sentetik) veri sağlayıcı.

İnternet erişimi olmadan geliştirme/test/demo yapabilmek için deterministik
bir geometrik rastgele yürüyüş (random walk) ile OHLCV verisi üretir. Aynı
sembol + period + interval her zaman aynı veriyi verir (seed sembole bağlı),
böylece testler tekrarlanabilir olur.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import DataProvider

# period dizgesini yaklaşık işlem günü sayısına çevirir.
_PERIOD_DAYS = {
    "1mo": 21,
    "3mo": 63,
    "6mo": 126,
    "1y": 252,
    "2y": 504,
    "5y": 1260,
    "max": 1260,
}


class SyntheticProvider(DataProvider):
    """Deterministik sahte OHLCV verisi üretir (ağ gerektirmez)."""

    def __init__(self, start_price: float = 100.0, annual_vol: float = 0.25) -> None:
        self.start_price = start_price
        self.annual_vol = annual_vol

    @staticmethod
    def _periods(period: str) -> int:
        return _PERIOD_DAYS.get(period.lower(), 252)

    def history(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        n = self._periods(period)
        # Seed'i sembole bağla: tekrarlanabilir ama sembole özgü seri.
        seed = abs(hash(symbol)) % (2**32)
        rng = np.random.default_rng(seed)

        daily_vol = self.annual_vol / np.sqrt(252)
        drift = 0.05 / 252  # hafif yukarı eğilim
        returns = rng.normal(loc=drift, scale=daily_vol, size=n)
        close = self.start_price * np.exp(np.cumsum(returns))

        # Bar içi Open/High/Low'u kapanış etrafında türet.
        open_ = np.empty(n)
        open_[0] = self.start_price
        open_[1:] = close[:-1]
        noise = np.abs(rng.normal(0, daily_vol, size=n)) * close
        high = np.maximum(open_, close) + noise
        low = np.minimum(open_, close) - noise
        volume = rng.integers(1_000_000, 5_000_000, size=n)

        index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
        df = pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "Volume": volume,
            },
            index=index,
        )
        return self._validate(df, symbol)
