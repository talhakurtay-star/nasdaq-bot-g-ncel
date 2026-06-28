"""Yahoo Finance (yfinance) tabanlı veri sağlayıcı.

Gerçek piyasa verisi için kullanılır; internet erişimi gerekir. yfinance bir
MultiIndex sütun yapısı dönebildiğinden burada düzleştirilir.
"""

from __future__ import annotations

import pandas as pd

from .base import OHLCV_COLUMNS, DataProvider


class YFinanceProvider(DataProvider):
    """Yahoo Finance'ten OHLCV verisi indirir."""

    def __init__(self, auto_adjust: bool = True) -> None:
        self.auto_adjust = auto_adjust

    def history(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover - ortam bağımlı
            raise RuntimeError(
                "yfinance kurulu değil. `pip install yfinance` çalıştırın "
                "veya --provider synthetic kullanın."
            ) from exc

        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=self.auto_adjust,
            progress=False,
        )

        if isinstance(df.columns, pd.MultiIndex):
            # ('Close', 'AAPL') -> 'Close' biçimine düzleştir.
            df.columns = df.columns.get_level_values(0)

        # Bazı sürümlerde 'Adj Close' gelir; Close yoksa onu kullan.
        if "Close" not in df.columns and "Adj Close" in df.columns:
            df = df.rename(columns={"Adj Close": "Close"})
        for col in OHLCV_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA

        return self._validate(df, symbol)
