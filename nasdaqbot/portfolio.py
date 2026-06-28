"""Sanal portföy / paper-trading hesabı.

GERÇEK PARA YOKTUR. Tüm emirler bellekte simüle edilir. Tek sembollü, yalnızca
long (açığa satış yok) bir hesap modeli; backtest ve canlı paper döngüsü için
ortak kullanılır.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Trade:
    """Gerçekleşmiş tek bir alım/satım kaydı."""

    timestamp: object          # pd.Timestamp veya benzeri
    side: str                  # "BUY" | "SELL"
    shares: float
    price: float
    commission: float
    cash_after: float


@dataclass
class Portfolio:
    """Tek sembollü sanal long-only hesap.

    Args:
        cash: Başlangıç nakdi.
        commission: İşlem tutarına oranla komisyon (0.001 = %0.1).
    """

    cash: float = 10_000.0
    commission: float = 0.0
    shares: float = 0.0
    trades: list[Trade] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.cash < 0:
            raise ValueError("Başlangıç nakdi negatif olamaz")
        if not (0.0 <= self.commission < 1.0):
            raise ValueError("commission [0, 1) aralığında olmalı")
        self._initial_cash = self.cash

    # ----- değerleme -----
    def position_value(self, price: float) -> float:
        """Hisse pozisyonunun güncel piyasa değeri."""
        return self.shares * price

    def equity(self, price: float) -> float:
        """Toplam hesap değeri (nakit + pozisyon)."""
        return self.cash + self.position_value(price)

    @property
    def initial_cash(self) -> float:
        return self._initial_cash

    # ----- emirler -----
    def buy(self, shares: float, price: float, timestamp=None) -> None:
        """Belirtilen adet hisseyi piyasa fiyatından satın alır."""
        if shares <= 0:
            return
        cost = shares * price
        fee = cost * self.commission
        total = cost + fee
        if total > self.cash + 1e-9:
            raise ValueError(
                f"Yetersiz nakit: gerek {total:.2f}, mevcut {self.cash:.2f}"
            )
        self.cash -= total
        self.shares += shares
        self.trades.append(
            Trade(timestamp, "BUY", shares, price, fee, self.cash)
        )

    def sell(self, shares: float, price: float, timestamp=None) -> None:
        """Belirtilen adet hisseyi piyasa fiyatından satar."""
        if shares <= 0:
            return
        shares = min(shares, self.shares)
        if shares <= 0:
            return
        proceeds = shares * price
        fee = proceeds * self.commission
        self.cash += proceeds - fee
        self.shares -= shares
        self.trades.append(
            Trade(timestamp, "SELL", shares, price, fee, self.cash)
        )

    def rebalance_to(self, target_weight: float, price: float, timestamp=None) -> None:
        """Pozisyonu hedef ağırlığa (0..1) getirir.

        target_weight = istenen (pozisyon değeri / toplam özsermaye). Komisyon
        nedeniyle birebir tutmayabilir; basit ve öngörülebilir olması için
        hedef hisse adedini güncel özsermayeye göre hesaplarız.
        """
        target_weight = max(0.0, min(1.0, target_weight))
        equity = self.equity(price)
        target_value = equity * target_weight
        target_shares = target_value / price if price > 0 else 0.0
        delta = target_shares - self.shares
        if abs(delta * price) < 1e-6:
            return
        if delta > 0:
            # Komisyonu hesaba katarak alınabilecek maksimumu sınırla.
            affordable = self.cash / (price * (1.0 + self.commission))
            self.buy(min(delta, affordable), price, timestamp)
        else:
            self.sell(-delta, price, timestamp)
