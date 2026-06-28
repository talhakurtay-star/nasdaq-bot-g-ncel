"""
V2/overfit_test.py
------------------
Overfitting / robustluk test harness'i.

Aynı strateji + aynı parametreleri:
  (a) In-Sample (ilk %70) vs Out-of-Sample (son %30)  → IS/OOS tutarlılık
  (b) Birden fazla enstrüman (TECH / EURUSD / XAUUSD)  → çapraz-piyasa robustluk

Mantık:
  - Gerçek edge'i olan bir strateji OOS'ta IS'e yakın performans gösterir.
  - OOS performansı çöküyorsa → overfitting (veya edge yok).
  - Strateji yalnızca tek enstrümanda/dilimde çalışıyorsa → ezber.

UYARI: Eldeki cache'ler SENTETİKtir (proxy). Bu harness metodolojiyi gösterir
ve gerçek veri geldiğinde aynı şekilde çalışır. Sentetik veride kesin
'edge var/yok' yargısı verilemez — yalnızca tutarlılık ölçülür.

Çalıştırma:
    cd V2 && STRESS_TEST_MODE=1 python overfit_test.py
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("STRESS_TEST_MODE", "1")

_V2 = Path(__file__).resolve().parent
_V1 = _V2.parent / "V1"
for p in (str(_V2), str(_V1)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Gürültüyü kıs (her run kendi raporunu basmasın)
logging.disable(logging.WARNING)

from backtest_v2 import run_backtest  # noqa: E402

CACHES = {
    "TECH":   _V1 / "cache" / "cache_15m_360d.csv",
    "EURUSD": _V1 / "cache" / "cache_EURUSD_15m.csv",
    "XAUUSD": _V1 / "cache" / "cache_XAUUSD_15m.csv",
}

IS_FRACTION = 0.70


def _split_csv(src: Path, frac: float) -> tuple[str, str]:
    """CSV'yi başlığı koruyarak IS (ilk frac) / OOS (kalan) olarak böler."""
    lines = src.read_text(encoding="utf-8").splitlines()
    header, rows = lines[0], lines[1:]
    cut = int(len(rows) * frac)
    is_path  = Path(tempfile.gettempdir()) / f"{src.stem}_IS.csv"
    oos_path = Path(tempfile.gettempdir()) / f"{src.stem}_OOS.csv"
    is_path.write_text("\n".join([header, *rows[:cut]]), encoding="utf-8")
    oos_path.write_text("\n".join([header, *rows[cut:]]), encoding="utf-8")
    return str(is_path), str(oos_path)


def _fmt(m: dict) -> str:
    return (
        f"PnL={m['net_pnl_pct']:+6.2f}% | WR={m['win_rate']:5.1f}% | "
        f"PF={m['profit_factor']:5.2f} | Sharpe={m['sharpe']:+7.3f} | "
        f"MaxDD={m['max_dd_pct']:5.2f}% | trades={m['total_trades']:3d}"
    )


def _verdict(is_m: dict, oos_m: dict) -> str:
    is_pnl, oos_pnl = is_m["net_pnl_pct"], oos_m["net_pnl_pct"]
    if is_m["total_trades"] < 10 or oos_m["total_trades"] < 5:
        return "YETERSİZ İŞLEM (yargı yok)"
    if is_pnl <= 0 and oos_pnl <= 0:
        return "EDGE YOK (her ikisinde de zarar)"
    if is_pnl > 0 and oos_pnl <= 0:
        return "⚠️ OVERFIT SİNYALİ (IS kârlı, OOS zarar)"
    if is_pnl > 0 and oos_pnl > 0:
        ratio = oos_pnl / is_pnl
        if ratio >= 0.5:
            return f"✅ TUTARLI (OOS/IS={ratio:.2f})"
        return f"⚠️ ZAYIF GENELLEME (OOS/IS={ratio:.2f})"
    return "KARARSIZ"


def main() -> None:
    print("=" * 78)
    print("  OVERFITTING / ROBUSTLUK TESTİ  (IS %70 / OOS %30 + çapraz-enstrüman)")
    print("  ⚠️  Veri SENTETİKtir — sonuçlar metodoloji gösterimidir, kesin yargı değil")
    print("=" * 78)

    for name, path in CACHES.items():
        if not path.exists():
            print(f"\n[{name}] cache yok: {path}")
            continue
        is_csv, oos_csv = _split_csv(path, IS_FRACTION)
        try:
            is_m  = run_backtest(csv_path=is_csv)
            oos_m = run_backtest(csv_path=oos_csv)
        except Exception as exc:
            print(f"\n[{name}] HATA: {exc}")
            continue

        print(f"\n── {name} " + "─" * (74 - len(name)))
        print(f"  IS  : {_fmt(is_m)}")
        print(f"  OOS : {_fmt(oos_m)}")
        print(f"  →  {_verdict(is_m, oos_m)}")

    print("\n" + "=" * 78)
    print("  Not: Gerçek yargı için V1/csv/nasdaq_15m.csv (GERÇEK NAS100) gerekir.")
    print("  Bu harness o veri gelince aynen çalışır.")
    print("=" * 78)


if __name__ == "__main__":
    main()
