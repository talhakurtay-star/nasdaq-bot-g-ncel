"""Komut satırı arayüzü.

Örnekler:
    python -m nasdaqbot backtest --symbol AAPL --strategy sma --fast 20 --slow 50
    python -m nasdaqbot backtest --provider synthetic --symbol DEMO
    python -m nasdaqbot run --symbol AAPL --max-steps 1
"""

from __future__ import annotations

import argparse
import sys

from .data import get_provider
from .engine import PaperTrader, backtest
from .strategy import get_strategy


def _strategy_from_args(args) -> object:
    if args.strategy in ("sma", "sma_crossover", "crossover"):
        return get_strategy("sma_crossover", fast=args.fast, slow=args.slow)
    if args.strategy == "rsi":
        return get_strategy("rsi", window=args.rsi_window,
                            lower=args.rsi_lower, upper=args.rsi_upper)
    raise SystemExit(f"Bilinmeyen strateji: {args.strategy}")


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--provider", default="yfinance",
                   help="Veri sağlayıcı: yfinance | synthetic")
    p.add_argument("--symbol", default="AAPL", help="Hisse sembolü")
    p.add_argument("--cash", type=float, default=10_000.0,
                   help="Başlangıç sanal nakit (USD)")
    p.add_argument("--commission", type=float, default=0.0,
                   help="İşlem komisyonu oranı (0.001 = %%0.1)")
    p.add_argument("--strategy", default="sma_crossover",
                   help="Strateji: sma_crossover | rsi")
    p.add_argument("--fast", type=int, default=20, help="Hızlı SMA periyodu")
    p.add_argument("--slow", type=int, default=50, help="Yavaş SMA periyodu")
    p.add_argument("--rsi-window", type=int, default=14, help="RSI periyodu")
    p.add_argument("--rsi-lower", type=float, default=30.0, help="RSI alt eşik")
    p.add_argument("--rsi-upper", type=float, default=70.0, help="RSI üst eşik")


def _cmd_backtest(args) -> int:
    provider = get_provider(args.provider)
    strategy = _strategy_from_args(args)
    df = provider.history(args.symbol, period=args.period, interval=args.interval)
    result = backtest(df, strategy, symbol=args.symbol,
                      cash=args.cash, commission=args.commission)
    m = result.metrics()

    print(f"\n=== Backtest: {args.symbol} | {strategy.describe()} ===")
    print(f"Veri    : {len(df)} bar ({df.index[0].date()} → {df.index[-1].date()})")
    print(f"Sağlayıcı: {args.provider}")
    print("-" * 48)
    print(f"Başlangıç : {result.initial_cash:>12,.2f} USD")
    print(f"Son değer : {m['final_equity']:>12,.2f} USD")
    print(f"Getiri    : {m['total_return']*100:>11.2f} %")
    print(f"CAGR      : {m['cagr']*100:>11.2f} %")
    print(f"Sharpe    : {m['sharpe']:>11.2f}")
    print(f"Max düşüş : {m['max_drawdown']*100:>11.2f} %")
    print(f"İşlem     : {m['n_trades']:>11d}")
    return 0


def _cmd_run(args) -> int:
    provider = get_provider(args.provider)
    strategy = _strategy_from_args(args)
    trader = PaperTrader(
        provider, strategy, args.symbol,
        cash=args.cash, commission=args.commission,
        period=args.period, interval=args.interval,
    )

    def log(s: dict) -> None:
        print(
            f"[{s['timestamp']}] {s['symbol']} fiyat={s['price']:.2f} "
            f"hedef={s['target_weight']:.2f} -> {s['action']:4s} "
            f"hisse={s['shares']:.4f} nakit={s['cash']:.2f} "
            f"özsermaye={s['equity']:.2f}"
        )

    print(f"Paper-trade başladı: {args.symbol} | {strategy.describe()}")
    print("(Gerçek para yok — simülasyon. Durdurmak için Ctrl-C.)\n")
    try:
        trader.run(poll_seconds=args.poll_seconds,
                   max_steps=args.max_steps, on_step=log)
    except KeyboardInterrupt:
        print("\nDurduruldu.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nasdaqbot",
        description="NASDAQ paper-trading botu (gerçek para riski yoktur).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="Tarihsel veride stratejiyi test et")
    _add_common(bt)
    bt.add_argument("--period", default="2y", help="Geçmiş süre (ör. 1y, 2y, max)")
    bt.add_argument("--interval", default="1d", help="Bar aralığı (ör. 1d, 1h)")
    bt.set_defaults(func=_cmd_backtest)

    run = sub.add_parser("run", help="Canlı paper-trade döngüsü")
    _add_common(run)
    run.add_argument("--period", default="6mo", help="Çekilecek geçmiş süre")
    run.add_argument("--interval", default="1d", help="Bar aralığı")
    run.add_argument("--poll-seconds", type=int, default=3600,
                     help="Adımlar arası bekleme (saniye)")
    run.add_argument("--max-steps", type=int, default=None,
                     help="Maksimum adım (varsayılan: süresiz)")
    run.set_defaults(func=_cmd_run)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
