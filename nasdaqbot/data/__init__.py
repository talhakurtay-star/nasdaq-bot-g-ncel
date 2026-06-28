"""Veri sağlayıcılar."""

from .base import DataProvider
from .synthetic import SyntheticProvider
from .yfinance_provider import YFinanceProvider

__all__ = ["DataProvider", "SyntheticProvider", "YFinanceProvider", "get_provider"]


def get_provider(name: str, **kwargs) -> DataProvider:
    """İsme göre bir veri sağlayıcı örneği döndürür.

    Args:
        name: "yfinance" veya "synthetic".
    """
    name = (name or "").lower()
    if name in ("yfinance", "yf", "yahoo"):
        return YFinanceProvider(**kwargs)
    if name in ("synthetic", "fake", "offline", "sim"):
        return SyntheticProvider(**kwargs)
    raise ValueError(f"Bilinmeyen veri sağlayıcı: {name!r}")
