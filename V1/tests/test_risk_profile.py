"""
V1/tests/test_risk_profile.py
-----------------------------
funded-survival risk profili davranış testleri.

Tam backtest (talib/pandas_ta) gerektirmez — yalnızca risk modüllerini test eder.

Çalıştırma:
    cd V1 && STRESS_TEST_MODE=1 python tests/test_risk_profile.py
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime

os.environ.setdefault("STRESS_TEST_MODE", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk.portfolio import PortfolioManager  # noqa: E402
from risk.guardrails import RiskGuardrails    # noqa: E402

logging.disable(logging.CRITICAL)

# Pazartesi 17:00 UTC — işlem penceresi içi, hafta sonu tuzakları dışı
TS = datetime(2026, 1, 5, 17, 0)


def _fresh():
    return PortfolioManager(), RiskGuardrails()


def test_daily_profit_lock_blocks_new_trades():
    p, g = _fresh()
    assert g.is_trading_allowed(p, TS) is True
    p.equity = p.daily_start_equity * 1.02   # +%2 gün-içi kazanç
    assert g.is_trading_allowed(p, TS) is False
    assert g.daily_profit_locked is True


def test_daily_drawdown_killswitch_at_3pct():
    p, g = _fresh()
    p.daily_peak_equity = 100_000
    p.equity = 100_000 * 0.97               # -%3
    assert g.check_drawdown_limits(p) is True
    assert g.kill_switch_active is True


def test_total_drawdown_killswitch_at_6pct():
    p, g = _fresh()
    p.daily_peak_equity = p.equity = 100_000 * 0.94   # -%6 toplam
    assert g.check_drawdown_limits(p) is True
    assert g.total_drawdown_triggered is True


def test_one_percent_risk_no_overshoot():
    p, g = _fresh()
    risk_amt = p.balance * 0.01
    p.daily_peak_equity = 100_000
    p.equity = 100_000 - risk_amt           # 1 kayıp = -%1 < limit
    assert g.check_drawdown_limits(p) is False
    p.equity = 100_000 - 3 * risk_amt       # 3 kayıp = -%3 = limit
    assert g.check_drawdown_limits(p) is True


def test_max_daily_trades_cap():
    p, g = _fresh()
    g.daily_trades_count = g.max_daily_trades
    assert g.is_trading_allowed(p, TS) is False


def test_profit_lock_is_not_killswitch():
    p, g = _fresh()
    p.equity = p.daily_start_equity * 1.02
    g.check_daily_profit_lock(p)
    assert g.daily_profit_locked is True
    assert g.kill_switch_active is False     # açık pozisyon yönetilmeye devam eder


def test_daily_reset_clears_lock_and_counters():
    p, g = _fresh()
    p.equity = p.daily_start_equity * 1.02
    g.check_daily_profit_lock(p)
    g.daily_trades_count = 3
    g.reset_daily_drawdown(p)
    assert g.daily_profit_locked is False
    assert g.daily_trades_count == 0


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        print(f"  ✅ {t.__name__}")
        passed += 1
    print(f"\n🎉 {passed}/{len(tests)} risk-profili testi GEÇTİ")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
