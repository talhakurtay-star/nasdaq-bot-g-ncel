"""Veri sağlayıcı arayüzü.

Tüm sağlayıcılar, sütunları ['Open', 'High', 'Low', 'Close', 'Volume'] olan,
DatetimeIndex ile indekslenmiş ve tarihe göre artan sıralı bir pandas
DataFrame döndürmelidir. Bu sözleşme sayesinde strateji ve motor kodu
verinin nereden geldiğini bilmek zorunda kalmaz.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


class DataProvider(ABC):
    """Tarihsel OHLCV verisi sağlayan soyut taban sınıf."""

    @abstractmethod
    def history(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Tek bir sembol için OHLCV geçmişini döndürür.

        Args:
            symbol: Hisse sembolü (ör. "AAPL").
            period: Geriye dönük süre (ör. "6mo", "1y", "2y", "max").
            interval: Bar aralığı (ör. "1d", "1h").

        Returns:
            OHLCV_COLUMNS sütunlarına sahip, DatetimeIndex'li DataFrame.
        """
        raise NotImplementedError

    @staticmethod
    def _validate(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Dönen DataFrame'in sözleşmeye uyduğunu doğrular/normalize eder."""
        if df is None or df.empty:
            raise ValueError(f"{symbol!r} için veri bulunamadı (boş sonuç).")
        missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"{symbol!r} verisinde eksik sütunlar: {missing}")
        df = df[OHLCV_COLUMNS].copy()
        df = df[~df.index.duplicated(keep="last")]
        return df.sort_index()
