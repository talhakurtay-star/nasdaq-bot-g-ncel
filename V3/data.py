"""
V3/data.py
----------
Gerçek MT5 15m CSV yükleyici (çok-sembol).

Format: tab-ayraçlı `<DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> ...`
Sentetik veri / SPY-VIX proxy YOKTUR. Sadece gerçek OHLCV.
"""

from __future__ import annotations

import pandas as pd

from . import config as C


def load_mt5_csv(path: str) -> pd.DataFrame:
    """Tek bir MT5 CSV'sini OHLCV DataFrame'ine (DatetimeIndex) yükler."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        first = f.readline()
    sep = "\t" if first.count("\t") >= 3 else (";" if first.count(";") > first.count(",") else ",")

    df = pd.read_csv(path, sep=sep)
    df.columns = [c.strip().strip("<>").upper() for c in df.columns]

    if "DATE" in df.columns and "TIME" in df.columns:
        dt = pd.to_datetime(df["DATE"].astype(str) + " " + df["TIME"].astype(str), errors="coerce")
    elif "DATETIME" in df.columns:
        dt = pd.to_datetime(df["DATETIME"], errors="coerce")
    else:
        dt = pd.to_datetime(df.iloc[:, 0], errors="coerce")

    df = df.assign(Datetime=dt).dropna(subset=["Datetime"]).set_index("Datetime")
    df.index = pd.DatetimeIndex(df.index)

    rename = {"OPEN": "Open", "HIGH": "High", "LOW": "Low", "CLOSE": "Close"}
    vol = next((v for v in ("TICKVOL", "VOLUME", "VOL", "REAL_VOLUME") if v in df.columns), None)
    if vol:
        rename[vol] = "Volume"
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "Volume" not in df.columns:
        df["Volume"] = 0.0

    df = df.dropna(subset=["Open", "High", "Low", "Close"]).sort_index()
    return df[["Open", "High", "Low", "Close", "Volume"]]


def load_symbols(symbols: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Yapılandırmadaki tüm sembolleri yükler → {symbol: DataFrame}."""
    symbols = symbols or C.SYMBOLS
    out: dict[str, pd.DataFrame] = {}
    for s in symbols:
        path = C.CSV_PATHS.get(s)
        if not path:
            raise KeyError(f"{s} için CSV yolu tanımlı değil")
        out[s] = load_mt5_csv(path)
    return out
