import numpy as np
import pandas as pd

from nasdaqbot.strategy import get_strategy
from nasdaqbot.strategy.rsi import RSIStrategy
from nasdaqbot.strategy.sma_crossover import SMACrossoverStrategy


def _frame(close):
    close = pd.Series(close, dtype=float)
    return pd.DataFrame({
        "Open": close, "High": close, "Low": close,
        "Close": close, "Volume": 1.0,
    })


def test_sma_crossover_goes_long_in_uptrend():
    # Sürekli artan fiyatta hızlı SMA yavaşın üstünde -> long.
    df = _frame(np.arange(1, 101, dtype=float))
    sig = SMACrossoverStrategy(fast=5, slow=20).generate(df)
    assert sig.iloc[-1] == 1.0
    # Isınma döneminde pozisyon yok.
    assert sig.iloc[0] == 0.0


def test_sma_crossover_cash_in_downtrend():
    df = _frame(np.arange(100, 0, -1, dtype=float))
    sig = SMACrossoverStrategy(fast=5, slow=20).generate(df)
    assert sig.iloc[-1] == 0.0


def test_sma_signal_values_are_binary():
    rng = np.random.default_rng(1)
    df = _frame(100 + np.cumsum(rng.normal(0, 1, 200)))
    sig = SMACrossoverStrategy(fast=10, slow=30).generate(df)
    assert set(sig.unique()).issubset({0.0, 1.0})


def test_rsi_strategy_index_aligned():
    rng = np.random.default_rng(2)
    df = _frame(100 + np.cumsum(rng.normal(0, 1, 100)))
    sig = RSIStrategy().generate(df)
    assert sig.index.equals(df.index)
    assert sig.between(0.0, 1.0).all()


def test_get_strategy_factory():
    assert isinstance(get_strategy("sma"), SMACrossoverStrategy)
    assert isinstance(get_strategy("rsi"), RSIStrategy)
