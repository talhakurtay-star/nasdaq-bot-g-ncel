"""
V3/account.py
-------------
Hesap-seviyesi portföy: çoklu sembol, hesap genelinde equity / peak / günlük P&L.

V1'den fark: equity ZİRVESİ (high-water-mark) takip edilir → trailing DD buradan
ölçülür. Böylece kâr da korunur (V1'de DD sadece başlangıç bakiyesinden ölçülüp
hesap kârdayken korumasız kalıyordu).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from . import config as C

logger = logging.getLogger(__name__)


@dataclass
class Position:
    symbol: str
    direction: str          # "LONG" | "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    sl_distance: float
    atr_at_open: float
    open_time: datetime
    trailing_active: bool = False

    @property
    def is_long(self) -> bool:
        return self.direction == "LONG"

    def unrealized(self, price: float) -> float:
        diff = (price - self.entry_price) if self.is_long else (self.entry_price - price)
        return diff * self.lot_size * C.CONTRACT_SIZE


@dataclass
class Trade:
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    lot_size: float
    net_pnl: float
    commission: float
    reason: str
    open_time: datetime
    close_time: datetime


class Account:
    """Çoklu sembol, hesap-seviyesi muhasebe."""

    def __init__(self) -> None:
        self.balance = C.INITIAL_BALANCE
        self.equity = C.INITIAL_BALANCE
        self.peak_equity = C.INITIAL_BALANCE          # high-water-mark (trailing DD)
        self.daily_start_equity = C.INITIAL_BALANCE   # günlük hedef/DD referansı
        self.daily_peak_equity = C.INITIAL_BALANCE    # gün-içi zirve (günlük DD)
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.total_commission = 0.0

    # ── Boyutlandırma ────────────────────────────────────────────────────
    def position_size(self, price: float, atr: float) -> float:
        if atr <= 0 or price <= 0:
            return 0.0
        sl_distance = atr * C.ATR_MULTIPLIER
        risk_amount = self.balance * C.RISK_PER_TRADE
        raw_lot = risk_amount / (sl_distance * C.CONTRACT_SIZE)
        lot_cap = (self.balance * C.MAX_NOTIONAL_LEVERAGE) / (price * C.CONTRACT_SIZE)
        return max(0.0, min(raw_lot, lot_cap))

    # ── Emirler ──────────────────────────────────────────────────────────
    def open(self, symbol: str, direction: str, price: float, atr: float, ts) -> Position | None:
        if symbol in self.positions:
            return None
        lot = self.position_size(price, atr)
        if lot <= 0:
            return None
        sl_dist = atr * C.ATR_MULTIPLIER
        half_spread = C.SPREAD_POINTS / 2.0
        if direction == "LONG":
            entry = price + half_spread
            sl = entry - sl_dist
            tp = entry + sl_dist * C.REWARD_RISK_RATIO
        else:
            entry = price - half_spread
            sl = entry + sl_dist
            tp = entry - sl_dist * C.REWARD_RISK_RATIO

        entry_comm = entry * lot * C.CONTRACT_SIZE * C.COMMISSION_RATE
        self.balance -= entry_comm
        self.total_commission += entry_comm

        pos = Position(symbol, direction, entry, sl, tp, lot, sl_dist, atr, ts)
        self.positions[symbol] = pos
        return pos

    def close(self, symbol: str, exit_price: float, ts, reason: str) -> float:
        pos = self.positions.get(symbol)
        if pos is None:
            return 0.0
        gross = (exit_price - pos.entry_price) if pos.is_long else (pos.entry_price - exit_price)
        gross *= pos.lot_size * C.CONTRACT_SIZE
        exit_comm = exit_price * pos.lot_size * C.CONTRACT_SIZE * C.COMMISSION_RATE
        net = gross - exit_comm
        self.balance += net
        self.total_commission += exit_comm
        self.trades.append(Trade(symbol, pos.direction, pos.entry_price, exit_price,
                                 pos.lot_size, net, exit_comm, reason, pos.open_time, ts))
        del self.positions[symbol]
        return net

    # ── Değerleme ────────────────────────────────────────────────────────
    def mark(self, prices: dict[str, float]) -> None:
        """Açık pozisyonları güncel fiyatlarla değerle, equity/peak güncelle."""
        unreal = 0.0
        for sym, pos in self.positions.items():
            p = prices.get(sym)
            if p is not None:
                unreal += pos.unrealized(p)
        self.equity = self.balance + unreal
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        if self.equity > self.daily_peak_equity:
            self.daily_peak_equity = self.equity

    def reset_daily(self) -> None:
        self.daily_start_equity = self.equity
        self.daily_peak_equity = self.equity

    @property
    def open_count(self) -> int:
        return len(self.positions)

    # ── Oranlar ──────────────────────────────────────────────────────────
    def trailing_dd(self) -> float:
        return (self.peak_equity - self.equity) / self.peak_equity if self.peak_equity > 0 else 0.0

    def daily_dd(self) -> float:
        return (self.daily_peak_equity - self.equity) / self.daily_peak_equity if self.daily_peak_equity > 0 else 0.0

    def total_dd(self) -> float:
        return (C.INITIAL_BALANCE - self.equity) / C.INITIAL_BALANCE

    def daily_gain(self) -> float:
        return (self.equity - self.daily_start_equity) / self.daily_start_equity if self.daily_start_equity > 0 else 0.0
