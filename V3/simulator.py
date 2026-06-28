"""
V3/simulator.py
---------------
Bar-by-bar dolum motoru (V1'den taşınan dürüst mantık).

Kritik kural: bir bar içinde hem SL hem TP'ye temas varsa → SL kazanır
(over-optimistic backtest engellenir). SL'de küçük slippage uygulanır.
"""

from __future__ import annotations

import logging

from .account import Account, Position

logger = logging.getLogger(__name__)

SL_SLIPPAGE_PCT = 0.0002
TRAILING_ACTIVATION_R = 1.0
TRAILING_ATR_MULT = 1.5


def manage_position(account: Account, symbol: str, high: float, low: float,
                    close: float, ts) -> str | None:
    """Açık pozisyonu mevcut barla yönetir. Kapanış olduysa sebebi döndürür."""
    pos = account.positions.get(symbol)
    if pos is None:
        return None

    if pos.is_long:
        sl_touch = low <= pos.stop_loss
        tp_touch = high >= pos.take_profit
    else:
        sl_touch = high >= pos.stop_loss
        tp_touch = low <= pos.take_profit

    # Çakışma veya tek başına SL → SL kazanır
    if sl_touch:
        fill = pos.stop_loss * (1 + SL_SLIPPAGE_PCT) if pos.is_long else pos.stop_loss * (1 - SL_SLIPPAGE_PCT)
        account.close(symbol, fill, ts, "SL")
        return "SL"
    if tp_touch:
        account.close(symbol, pos.take_profit, ts, "TP")
        return "TP"

    # Trailing stop
    _update_trailing(pos, high, low)
    return None


def _update_trailing(pos: Position, high: float, low: float) -> None:
    if pos.atr_at_open <= 0:
        return
    activation = pos.sl_distance * TRAILING_ACTIVATION_R
    if not pos.trailing_active:
        if pos.is_long and high >= pos.entry_price + activation:
            pos.trailing_active = True
        elif not pos.is_long and low <= pos.entry_price - activation:
            pos.trailing_active = True
    if pos.trailing_active:
        trail = pos.atr_at_open * TRAILING_ATR_MULT
        if pos.is_long:
            pos.stop_loss = max(pos.stop_loss, high - trail)
        else:
            pos.stop_loss = min(pos.stop_loss, low + trail)
