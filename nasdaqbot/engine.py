"""Simülasyon motoru: backtest ve canlı paper-trade döngüsü.

Önemli kural: bir bardaki sinyale göre işlem, sinyal-kaçağını (lookahead bias)
önlemek için BİR SONRAKİ barın açılışında uygulanır.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data.base import DataProvider
from .portfolio import Portfolio
from .strategy.base import Strategy


@dataclass
class BacktestResult:
    """Bir backtest çalışmasının sonucu."""

    symbol: str
    equity_curve: pd.Series      # tarih -> toplam özsermaye
    target_weight: pd.Series     # tarih -> hedef ağırlık (sinyal)
    portfolio: Portfolio
    initial_cash: float

    @property
    def final_equity(self) -> float:
        return float(self.equity_curve.iloc[-1])

    @property
    def total_return(self) -> float:
        return self.final_equity / self.initial_cash - 1.0

    @property
    def n_trades(self) -> int:
        return len(self.portfolio.trades)

    def metrics(self, periods_per_year: int = 252) -> dict:
        """Özet performans metrikleri (oran cinsinden)."""
        eq = self.equity_curve
        rets = eq.pct_change().dropna()
        total_ret = self.total_return

        # Yıllık Sharpe (risksiz oran 0 varsayımı).
        if rets.std(ddof=0) > 0:
            sharpe = np.sqrt(periods_per_year) * rets.mean() / rets.std(ddof=0)
        else:
            sharpe = 0.0

        # Maksimum düşüş (max drawdown).
        running_max = eq.cummax()
        drawdown = eq / running_max - 1.0
        max_dd = float(drawdown.min()) if len(drawdown) else 0.0

        # CAGR.
        n = len(eq)
        years = n / periods_per_year if n else 0.0
        if years > 0 and self.initial_cash > 0:
            cagr = (self.final_equity / self.initial_cash) ** (1.0 / years) - 1.0
        else:
            cagr = 0.0

        return {
            "total_return": total_ret,
            "cagr": cagr,
            "sharpe": float(sharpe),
            "max_drawdown": max_dd,
            "n_trades": self.n_trades,
            "final_equity": self.final_equity,
        }


def backtest(
    df: pd.DataFrame,
    strategy: Strategy,
    symbol: str = "",
    cash: float = 10_000.0,
    commission: float = 0.0,
) -> BacktestResult:
    """Tarihsel veri üzerinde stratejiyi simüle eder.

    Sinyal t barında üretilir, işlem t+1 barının Open fiyatından uygulanır,
    özsermaye t+1 barının Close fiyatından değerlenir.
    """
    if df.empty:
        raise ValueError("Backtest için boş DataFrame")

    target = strategy.generate(df).reindex(df.index).fillna(0.0)
    portfolio = Portfolio(cash=cash, commission=commission)

    equity = pd.Series(index=df.index, dtype=float)
    opens = df["Open"]
    closes = df["Close"]

    prev_weight = 0.0
    for i, ts in enumerate(df.index):
        # Bir önceki barın sinyalini bu barın açılışında uygula.
        if i > 0:
            exec_price = float(opens.iloc[i])
            if not np.isnan(exec_price) and exec_price > 0:
                portfolio.rebalance_to(prev_weight, exec_price, ts)
        # Bu barı kapanışla değerle.
        equity.iloc[i] = portfolio.equity(float(closes.iloc[i]))
        prev_weight = float(target.iloc[i])

    return BacktestResult(
        symbol=symbol,
        equity_curve=equity,
        target_weight=target,
        portfolio=portfolio,
        initial_cash=cash,
    )


class PaperTrader:
    """Canlı (gecikmeli) paper-trade döngüsü.

    Periyodik olarak son veriyi çeker, stratejinin EN SON bar için hedefini
    hesaplar ve sanal portföyü güncel kapanış fiyatına göre yeniden dengeler.
    Gerçek emir gönderilmez.
    """

    def __init__(
        self,
        provider: DataProvider,
        strategy: Strategy,
        symbol: str,
        cash: float = 10_000.0,
        commission: float = 0.0,
        period: str = "6mo",
        interval: str = "1d",
    ) -> None:
        self.provider = provider
        self.strategy = strategy
        self.symbol = symbol
        self.period = period
        self.interval = interval
        self.portfolio = Portfolio(cash=cash, commission=commission)

    def step(self) -> dict:
        """Tek bir değerlendirme adımı çalıştırır ve durum sözlüğü döndürür."""
        df = self.provider.history(self.symbol, self.period, self.interval)
        target = self.strategy.generate(df)
        last_ts = df.index[-1]
        last_close = float(df["Close"].iloc[-1])
        target_weight = float(target.iloc[-1])

        before_shares = self.portfolio.shares
        self.portfolio.rebalance_to(target_weight, last_close, last_ts)
        delta = self.portfolio.shares - before_shares
        action = "BUY" if delta > 1e-9 else "SELL" if delta < -1e-9 else "HOLD"

        return {
            "timestamp": last_ts,
            "symbol": self.symbol,
            "price": last_close,
            "target_weight": target_weight,
            "action": action,
            "shares": self.portfolio.shares,
            "cash": self.portfolio.cash,
            "equity": self.portfolio.equity(last_close),
        }

    def run(self, poll_seconds: int = 3600, max_steps: int | None = None,
            on_step=None) -> None:
        """Döngüyü başlatır. max_steps=None ise süresiz çalışır.

        on_step verilirse her adımın durum sözlüğüyle çağrılır (loglama için).
        """
        steps = 0
        while max_steps is None or steps < max_steps:
            status = self.step()
            if on_step is not None:
                on_step(status)
            steps += 1
            if max_steps is not None and steps >= max_steps:
                break
            time.sleep(poll_seconds)
