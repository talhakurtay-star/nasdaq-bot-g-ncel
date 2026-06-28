import numpy as np
import pandas as pd
import pytest

from nasdaqbot.data import SyntheticProvider, get_provider
from nasdaqbot.engine import PaperTrader, backtest
from nasdaqbot.strategy.sma_crossover import SMACrossoverStrategy


def _frame(close):
    close = np.asarray(close, dtype=float)
    return pd.DataFrame(
        {"Open": close, "High": close, "Low": close,
         "Close": close, "Volume": 1.0},
        index=pd.bdate_range("2020-01-01", periods=len(close)),
    )


def test_synthetic_provider_is_deterministic():
    a = SyntheticProvider().history("AAPL", "1y")
    b = SyntheticProvider().history("AAPL", "1y")
    pd.testing.assert_frame_equal(a, b)
    assert len(a) == 252
    assert list(a.columns) == ["Open", "High", "Low", "Close", "Volume"]


def test_synthetic_provider_high_low_consistent():
    df = SyntheticProvider().history("MSFT", "6mo")
    assert (df["High"] >= df["Low"]).all()
    assert (df["High"] >= df["Close"]).all()
    assert (df["Low"] <= df["Close"]).all()


def test_backtest_runs_and_tracks_equity():
    df = SyntheticProvider().history("NVDA", "2y")
    res = backtest(df, SMACrossoverStrategy(fast=10, slow=30),
                   symbol="NVDA", cash=10_000)
    assert len(res.equity_curve) == len(df)
    assert res.equity_curve.iloc[0] == pytest.approx(10_000, abs=1.0)
    m = res.metrics()
    assert set(m) >= {"total_return", "sharpe", "max_drawdown", "n_trades"}
    assert m["max_drawdown"] <= 0.0


def test_backtest_uptrend_makes_money():
    # İstikrarlı yükseliş trendinde trend-takip kâr etmeli.
    close = 100 * (1.01 ** np.arange(120))
    df = _frame(close)
    res = backtest(df, SMACrossoverStrategy(fast=5, slow=20), cash=10_000)
    assert res.total_return > 0.0
    assert res.n_trades >= 1


def test_backtest_no_lookahead_first_bar_unchanged():
    df = _frame(100 * (1.01 ** np.arange(60)))
    res = backtest(df, SMACrossoverStrategy(fast=5, slow=20), cash=10_000)
    # İlk barda hiç işlem olamaz (t+1 kuralı).
    assert res.equity_curve.iloc[0] == pytest.approx(10_000, abs=1e-6)


def test_paper_trader_single_step():
    provider = get_provider("synthetic")
    trader = PaperTrader(provider, SMACrossoverStrategy(fast=5, slow=20),
                         "AAPL", cash=10_000, period="1y")
    statuses = []
    trader.run(poll_seconds=0, max_steps=1, on_step=statuses.append)
    assert len(statuses) == 1
    s = statuses[0]
    assert s["symbol"] == "AAPL"
    assert s["action"] in {"BUY", "SELL", "HOLD"}
    assert s["equity"] > 0
