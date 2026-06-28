"""
V3/tests/test_risk.py
---------------------
Hesap-seviyesi risk davranış testleri (veri/backtest gerektirmez).

Çalıştırma:
    python -m V3.tests.test_risk
"""

from __future__ import annotations

from datetime import datetime

from .. import config as C
from ..account import Account
from ..risk import RiskManager

TS = datetime(2026, 1, 5, 17, 0)  # Pazartesi 17:00, seans içi (16:30–23:00)


def _fresh():
    return Account(), RiskManager()


def test_trailing_dd_from_peak_not_initial():
    """V1 bug fix: hesap kârdayken bile zirveden düşüş yakalanmalı."""
    a, r = _fresh()
    a.equity = a.peak_equity = 120_000          # +%20 → zirve 120k
    a.equity = 120_000 * (1 - C.TRAILING_DD_LIMIT) - 1  # zirveden limitin az ötesi
    assert r.check_account_limits(a) is True
    assert r.account_blown is True


def test_account_survives_small_pullback_in_profit():
    a, r = _fresh()
    a.equity = a.peak_equity = 120_000
    a.equity = 120_000 * (1 - C.TRAILING_DD_LIMIT / 2)   # limitin yarısı
    assert r.check_account_limits(a) is False


def test_daily_profit_lock_blocks_new_trades():
    a, r = _fresh()
    assert r.can_open(a, TS) is True
    a.equity = a.daily_start_equity * (1 + C.DAILY_PROFIT_TARGET) + 1  # eşiğin az ötesi
    assert r.can_open(a, TS) is False
    assert r.profit_target_hit is True


def test_daily_dd_locks_day():
    a, r = _fresh()
    a.daily_peak_equity = 100_000
    a.equity = 100_000 * (1 - C.DAILY_DD_LIMIT) - 1   # eşiğin az ötesi
    assert r.can_open(a, TS) is False
    assert r.daily_locked is True


def test_circuit_breaker_after_consecutive_sl():
    a, r = _fresh()
    for _ in range(C.MAX_CONSECUTIVE_SL):
        r.record_result(won=False)
    assert r.daily_locked is True
    assert r.can_open(a, TS) is False


def test_session_window_blocks_outside_hours():
    a, r = _fresh()
    assert r.can_open(a, datetime(2026, 1, 5, 2, 0)) is False    # seans dışı (gece)
    assert r.can_open(a, datetime(2026, 1, 5, 15, 0)) is False   # 16:30 öncesi → dışı
    assert r.can_open(a, datetime(2026, 1, 5, 16, 15)) is False  # 16:15 < 16:30 → dışı
    assert r.can_open(a, datetime(2026, 1, 5, 16, 30)) is True   # 16:30 → içi
    assert r.can_open(a, datetime(2026, 1, 5, 22, 45)) is True   # 22:45 → içi
    assert r.can_open(a, datetime(2026, 1, 5, 23, 0)) is False   # 23:00 → kapanış, dışı


def test_daily_reset_clears_locks():
    a, r = _fresh()
    a.equity = a.daily_start_equity * (1 + C.DAILY_PROFIT_TARGET)
    r.update_daily_state(a)
    r.daily_trades = 5
    r.reset_daily(a)
    assert r.daily_locked is False and r.daily_trades == 0 and r.profit_target_hit is False


def test_max_positions_cap():
    a, r = _fresh()
    a.open("NAS100", "LONG", 16000, 30, TS)
    a.open("US30", "LONG", 36000, 50, TS)
    assert a.open_count == C.MAX_OPEN_POSITIONS
    assert r.can_open(a, TS) is False   # tavan dolu


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ✅ {t.__name__}")
    print(f"\n🎉 {len(tests)}/{len(tests)} V3 risk testi GEÇTİ")


if __name__ == "__main__":
    _run_all()
