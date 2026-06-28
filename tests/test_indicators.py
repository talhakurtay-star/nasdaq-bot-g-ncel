import numpy as np
import pandas as pd
import pytest

from nasdaqbot.indicators import ema, rsi, sma


def test_sma_basic():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = sma(s, 2)
    assert np.isnan(out.iloc[0])
    assert out.iloc[1] == pytest.approx(1.5)
    assert out.iloc[4] == pytest.approx(4.5)


def test_sma_window_validation():
    with pytest.raises(ValueError):
        sma(pd.Series([1.0]), 0)


def test_ema_converges_to_constant():
    s = pd.Series([5.0] * 50)
    assert ema(s, 10).iloc[-1] == pytest.approx(5.0)


def test_rsi_all_gains_is_100():
    s = pd.Series(np.arange(1, 40, dtype=float))  # sürekli artan
    r = rsi(s, 14).dropna()
    assert (r > 99.0).all()


def test_rsi_bounds():
    rng = np.random.default_rng(0)
    s = pd.Series(100 + np.cumsum(rng.normal(0, 1, 200)))
    r = rsi(s, 14).dropna()
    assert r.min() >= 0.0
    assert r.max() <= 100.0
