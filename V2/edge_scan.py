"""
V2/edge_scan.py
---------------
HAM EDGE taraması — risk overlay'i KAPALI.

Amaç: stratejinin gerçek tavanını ölçmek. DD kill-switch ve günlük kâr kilidi
truncation yapmasın diye devre dışı bırakılır (yüksek limitler), sabit %1 risk
ile tüm veri üzerinde çalıştırılır. Sonra basit lineer ölçekleme ile:

    "%8 toplam DD bütçesinde aylık getiri ne olurdu?"

sorusu yanıtlanır:  scaled_monthly ≈ monthly × (8 / natural_MaxDD)

NOT: Lineer ölçekleme (fixed-fractional sizing) bir yaklaşımdır; gerçek değil,
gerçekçilik kontrolüdür. Negatif edge'li enstrümanlarda ölçekleme de negatiftir.

Çalıştırma:
    cd V2 && python edge_scan.py NAS100 US30 ...
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

# ── Overlay'i KAPAT (settings import'undan ÖNCE) ──────────────────────────────
os.environ["STRESS_TOTAL_DD"]          = "100"   # toplam DD kill kapalı
os.environ["STRESS_DAILY_DD"]          = "100"   # günlük DD kill kapalı
os.environ["STRESS_DAILY_PROFIT_LOCK"] = "0"     # kâr kilidi kapalı
os.environ["STRESS_MAX_DAILY_TRADES"]  = "999"   # günlük işlem tavanı kapalı
os.environ["BACKTEST_DAYS"]            = os.environ.get("BACKTEST_DAYS", "3000")
os.environ["STRESS_RISK_PCT"]          = os.environ.get("STRESS_RISK_PCT", "1.0")
os.environ.setdefault("STRESS_TEST_MODE", "1")

import logging  # noqa: E402
logging.disable(logging.WARNING)

_V2 = Path(__file__).resolve().parent
_V1 = _V2.parent / "V1"
for p in (str(_V2), str(_V1)):
    if p not in sys.path:
        sys.path.insert(0, p)

from backtest_v2 import run_backtest  # noqa: E402

_REAL = _V1 / "csv" / "real"
ALL = ["NAS100", "US30", "GER40", "UK100", "XAUUSD"]
DD_BUDGET = 8.0  # hedef toplam DD %


def _months(path: Path) -> float:
    """CSV ilk/son data satırından kapsanan ay sayısını hesaplar."""
    lines = path.read_text(encoding="utf-8").splitlines()
    def _d(line: str) -> datetime:
        date_str = line.split("\t")[0]  # '2022.01.03'
        return datetime.strptime(date_str, "%Y.%m.%d")
    first, last = _d(lines[1]), _d(lines[-1])
    return max((last - first).days / 30.44, 0.1)


def main() -> None:
    names = [a for a in sys.argv[1:]] or ALL
    print("=" * 96)
    print(f"  HAM EDGE TARAMASI (overlay KAPALI, risk=%{os.environ['STRESS_RISK_PCT']}) "
          f"| %{DD_BUDGET:.0f} DD bütçesine ölçekli aylık getiri")
    print("=" * 96)
    print(f"  {'Enstr':<7} {'Ay':>5} {'Toplam%':>9} {'Aylık%':>8} {'MaxDD%':>7} "
          f"{'PF':>5} {'WR%':>5} {'Trade':>6}  ║ {'%8DD-aylık%':>11} {'risk%':>6}")
    print("  " + "-" * 92)

    for name in names:
        path = _REAL / f"{name}_15m.csv"
        if not path.exists():
            print(f"  {name:<7} dosya yok: {path}")
            continue
        m = run_backtest(csv_path=str(path))
        months = _months(path)
        tot = m["net_pnl_pct"]
        dd  = max(m["max_dd_pct"], 1e-6)
        # Bileşik aylık getiri
        monthly = ((1 + tot / 100) ** (1 / months) - 1) * 100 if tot > -100 else -100
        # %8 DD bütçesine lineer ölçekleme
        scale = DD_BUDGET / dd
        scaled_risk = float(os.environ["STRESS_RISK_PCT"]) * scale
        scaled_monthly = monthly * scale
        print(f"  {name:<7} {months:>5.1f} {tot:>+9.2f} {monthly:>+8.2f} {dd:>7.2f} "
              f"{m['profit_factor']:>5.2f} {m['win_rate']:>5.1f} {m['total_trades']:>6d}  ║ "
              f"{scaled_monthly:>+11.2f} {scaled_risk:>6.2f}")

    print("=" * 96)
    print("  Not: Pozitif edge'li enstrümanlarda '%8DD-aylık%' ulaşılabilir tavandır.")
    print("  Negatifse strateji o enstrümanda para kaybediyor (ölçekleme de negatif).")


if __name__ == "__main__":
    main()
