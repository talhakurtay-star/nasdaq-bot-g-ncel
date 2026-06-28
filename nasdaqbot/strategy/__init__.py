"""Alım-satım stratejileri."""

from .base import Signal, Strategy
from .rsi import RSIStrategy
from .sma_crossover import SMACrossoverStrategy

__all__ = [
    "Signal",
    "Strategy",
    "SMACrossoverStrategy",
    "RSIStrategy",
    "get_strategy",
]


def get_strategy(name: str, **params) -> Strategy:
    """İsme göre strateji örneği döndürür.

    Args:
        name: "sma_crossover" veya "rsi".
        **params: Stratejiye iletilecek parametreler.
    """
    name = (name or "").lower()
    if name in ("sma", "sma_crossover", "crossover"):
        return SMACrossoverStrategy(**params)
    if name in ("rsi",):
        return RSIStrategy(**params)
    raise ValueError(f"Bilinmeyen strateji: {name!r}")
