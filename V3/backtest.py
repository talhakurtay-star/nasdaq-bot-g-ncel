"""
V3/backtest.py
--------------
Çok-sembol, hesap-seviyesi, GÜNLÜK-hedef backtest.

Birleşik zaman çizgisi: tüm sembollerin barları kronolojik işlenir; risk
HESAP seviyesinde uygulanır (trailing DD, günlük DD, günlük kâr kilidi).

Çalıştırma:
    python -m V3.backtest                 # config'teki semboller
    V3_SYMBOLS=NAS100 python -m V3.backtest
"""

from __future__ import annotations

import logging
import math
from datetime import date

import numpy as np
import pandas as pd

from . import config as C
from . import indicators, strategy
from .account import Account
from .data import load_symbols
from .risk import RiskManager
from .simulator import manage_position

logger = logging.getLogger(__name__)


def run(symbols: list[str] | None = None, verbose: bool = True,
        frac: tuple[float, float] = (0.0, 1.0)) -> dict:
    raw = load_symbols(symbols)
    # IS/OOS için satır-fraksiyonu dilimi (her sembol kendi içinde)
    if frac != (0.0, 1.0):
        sliced = {}
        for s, df in raw.items():
            a, b = int(len(df) * frac[0]), int(len(df) * frac[1])
            sliced[s] = df.iloc[a:b]
        raw = sliced
    data = {s: indicators.calculate_indicators(df) for s, df in raw.items()}

    # Her sembol için timestamp → satır-indeksi haritası
    pos_index = {s: {ts: i for i, ts in enumerate(df.index)} for s, df in data.items()}

    # Birleşik kronolojik zaman çizgisi
    timeline = sorted(set().union(*[set(df.index) for df in data.values()]))

    account = Account()
    risk = RiskManager()
    last_price: dict[str, float] = {}
    equity_curve: list[float] = []
    daily_equity: dict[date, float] = {}   # gün → o günün son equity'si
    current_day: date | None = None

    for ts in timeline:
        d = ts.date()
        if current_day is None:
            current_day = d
        elif d != current_day:
            risk.reset_daily(account)
            current_day = d

        # Bu timestamp'te barı olan semboller
        present = [s for s in data if ts in pos_index[s]]

        # 1) Açık pozisyonları yönet (SL/TP/trailing) + fiyatları güncelle
        for s in present:
            i = pos_index[s][ts]
            bar = data[s].iloc[i]
            hi, lo, cl = float(bar["High"]), float(bar["Low"]), float(bar["Close"])
            last_price[s] = cl
            if s in account.positions:
                reason = manage_position(account, s, hi, lo, cl, ts)
                if reason in ("SL", "TP"):
                    risk.record_result(won=(reason == "TP"))

        # 2) Hesap-seviyesi mark + limit kontrolü
        account.mark(last_price)
        equity_curve.append(account.equity)
        daily_equity[d] = account.equity

        if risk.check_account_limits(account):
            # Hesap kaybedildi → tüm pozisyonları kapat ve dur
            for s in list(account.positions):
                account.close(s, last_price.get(s, account.positions[s].entry_price), ts, "ACCOUNT_BLOWN")
            break

        # 3) Hafta sonu flatten
        if risk.should_force_close(ts):
            for s in list(account.positions):
                account.close(s, last_price.get(s, account.positions[s].entry_price), ts, "WEEKEND_FLATTEN")

        # 4) Yeni giriş (kilit/limit izin veriyorsa)
        for s in present:
            if s in account.positions:
                continue
            if not risk.can_open(account, ts):
                break  # hesap/gün kilitli — bu bar yeni giriş yok
            i = pos_index[s][ts]
            if i < C.WARMUP_BARS:
                continue
            sig = strategy.generate_signal(data[s], i)
            if sig in ("LONG", "SHORT"):
                bar = data[s].iloc[i]
                atr = float(bar.get("ATR", 0.0) or 0.0)
                cl = float(bar["Close"])
                if atr > 0 and account.open(s, sig, cl, atr, ts):
                    risk.daily_trades += 1

    # Kalan açık pozisyonları kapat
    for s in list(account.positions):
        account.close(s, last_price.get(s, account.positions[s].entry_price),
                      timeline[-1], "EOD")

    return _report(account, equity_curve, daily_equity, raw, verbose,
                   blown=risk.account_blown)


def _report(account: Account, equity_curve, daily_equity, raw, verbose: bool,
            blown: bool = False) -> dict:
    eq = np.array(equity_curve) if equity_curve else np.array([C.INITIAL_BALANCE])
    total_pnl = account.balance - C.INITIAL_BALANCE
    total_pct = total_pnl / C.INITIAL_BALANCE * 100

    peak = np.maximum.accumulate(eq)
    max_dd = float(np.max((peak - eq) / peak) * 100) if len(eq) else 0.0

    trades = account.trades
    real = [t for t in trades if t.reason in ("SL", "TP", "WEEKEND_FLATTEN", "EOD", "ACCOUNT_BLOWN")]
    wins = [t for t in real if t.net_pnl > 0]
    gross_w = sum(t.net_pnl for t in wins)
    gross_l = abs(sum(t.net_pnl for t in real if t.net_pnl < 0))
    pf = gross_w / gross_l if gross_l > 0 else float("inf")
    wr = len(wins) / len(real) * 100 if real else 0.0

    # Günlük istatistikler (günlük-hedef modeli için kritik)
    days = sorted(daily_equity)
    daily_rets = []
    prev = C.INITIAL_BALANCE
    for d in days:
        daily_rets.append((daily_equity[d] - prev) / prev * 100)
        prev = daily_equity[d]
    daily_rets = np.array(daily_rets) if daily_rets else np.array([0.0])
    green_days = int((daily_rets > 0).sum())
    n_days = len(daily_rets)
    green_rate = green_days / n_days * 100 if n_days else 0.0
    avg_day = float(daily_rets.mean())
    months = n_days / 21.0 if n_days else 1.0
    monthly = ((1 + total_pct / 100) ** (1 / max(months, 0.1)) - 1) * 100

    # Sharpe (günlük)
    sharpe = float(daily_rets.mean() / daily_rets.std() * math.sqrt(252)) if daily_rets.std() > 0 else 0.0

    res = {
        "total_pct": round(total_pct, 2), "monthly_pct": round(monthly, 3),
        "max_dd_pct": round(max_dd, 2), "trailing_dd_breached": account.peak_equity > 0
        and (account.peak_equity - eq.min()) / account.peak_equity >= C.TRAILING_DD_LIMIT,
        "profit_factor": round(pf, 3) if pf != float("inf") else 999,
        "win_rate": round(wr, 1), "n_trades": len(real),
        "trading_days": n_days, "green_day_rate": round(green_rate, 1),
        "avg_day_pct": round(avg_day, 3), "sharpe": round(sharpe, 3),
        "final_balance": round(account.balance, 2),
        # battı = trailing/total DD limiti kırıldı (hesap kaybedildi)
        "blown": bool(blown or risk_blown(account)),
    }

    if verbose:
        _print(res, raw)
    return res


def risk_blown(account: Account) -> bool:
    return (C.INITIAL_BALANCE - account.equity) / C.INITIAL_BALANCE >= C.TOTAL_DD_LIMIT


def _print(r: dict, raw) -> None:
    syms = ", ".join(raw.keys())
    span = " | ".join(f"{s}:{df.index[0].date()}→{df.index[-1].date()}" for s, df in raw.items())
    print("=" * 70)
    print(f"  V3 GÜNLÜK-HEDEF BACKTEST | {syms}")
    print(f"  {span}")
    print("=" * 70)
    print(f"  Risk/işlem={C.RISK_PER_TRADE_PCT}% | RR=1:{C.REWARD_RISK_RATIO} | "
          f"Günlük hedef=+{C.DAILY_PROFIT_TARGET_PCT}% | TrailDD={C.TRAILING_DD_LIMIT_PCT}%")
    print("-" * 70)
    print(f"  Toplam getiri     : {r['total_pct']:+.2f}%")
    print(f"  Aylık (bileşik)   : {r['monthly_pct']:+.3f}%")
    print(f"  Max Drawdown      : {r['max_dd_pct']:.2f}%   (limit {C.TRAILING_DD_LIMIT_PCT}% trailing)")
    print(f"  Profit Factor     : {r['profit_factor']}")
    print(f"  Win Rate          : {r['win_rate']}%   ({r['n_trades']} işlem)")
    print(f"  Sharpe (günlük)   : {r['sharpe']}")
    print("-" * 70)
    print(f"  İşlem günü        : {r['trading_days']}")
    print(f"  YEŞİL-GÜN ORANI   : {r['green_day_rate']}%   (günlük-hedef modeli için kritik)")
    print(f"  Ort. günlük getiri: {r['avg_day_pct']:+.3f}%")
    print(f"  Hesap battı mı    : {'EVET ❌' if r['blown'] else 'HAYIR ✅'}")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")
    run()
