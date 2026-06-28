"""
V3/validate.py
--------------
Robustluk / overfitting kontrolü: IS %70 vs OOS %30, her enstrüman tek tek
ve birlikte. Tek dönemde güzel sonuç yanıltıcıdır; OOS tutarlılık aranır.

Çalıştırma:
    python -m V3.validate
"""

from __future__ import annotations

import logging

from . import config as C
from .backtest import run

logging.disable(logging.WARNING)


def _line(tag: str, r: dict) -> str:
    return (f"  {tag:<14} ret={r['total_pct']:+7.2f}% | aylık={r['monthly_pct']:+6.3f}% | "
            f"PF={r['profit_factor']:>5} | WR={r['win_rate']:>4}% | DD={r['max_dd_pct']:>5.2f}% | "
            f"Sharpe={r['sharpe']:>5} | yeşil-gün={r['green_day_rate']:>4}% | "
            f"{'BATTI' if r['blown'] else 'ok'}")


def _verdict(is_r: dict, oos_r: dict) -> str:
    ip, op = is_r["total_pct"], oos_r["total_pct"]
    if is_r["n_trades"] < 15 or oos_r["n_trades"] < 8:
        return "yetersiz işlem"
    if ip > 0 and op > 0:
        ratio = op / ip if ip else 0
        return f"✅ TUTARLI (OOS/IS={ratio:.2f})" if ratio >= 0.4 else f"⚠️ zayıf genelleme ({ratio:.2f})"
    if ip > 0 >= op:
        return "🚩 OVERFIT SİNYALİ (IS kâr, OOS zarar)"
    return "❌ edge yok"


def main() -> None:
    groups = [["NAS100"], ["US30"], C.SYMBOLS]
    print("=" * 104)
    print("  V3 ROBUSTLUK TESTİ — IS %70 / OOS %30 (gerçek veri)")
    print("=" * 104)
    for g in groups:
        tag = "+".join(g)
        is_r  = run(g, verbose=False, frac=(0.0, 0.70))
        oos_r = run(g, verbose=False, frac=(0.70, 1.0))
        print(f"\n── {tag} " + "─" * (98 - len(tag)))
        print(_line("IS (70%)", is_r))
        print(_line("OOS (30%)", oos_r))
        print(f"  → {_verdict(is_r, oos_r)}")
    print("\n" + "=" * 104)


if __name__ == "__main__":
    main()
