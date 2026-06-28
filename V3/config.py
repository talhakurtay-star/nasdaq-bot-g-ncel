"""
V3/config.py
------------
Merkezi yapılandırma. Tüm değerler ortam değişkeniyle override edilebilir.

Hedef profili (kullanıcı): aylık ~%5 = günlük ~%0.22, max toplam DD %8, günlük %4.
İç limitler firma limitlerinin ALTINDA tampon bırakır.
"""

from __future__ import annotations

import os


def _f(key: str, default: float) -> float:
    return float(os.getenv(key, str(default)))


def _i(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


def _b(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes")


# ── Enstrümanlar ──────────────────────────────────────────────────────────────
# İsim → CSV dosya yolu (V1/csv/real altındaki gerçek MT5 verileri)
_CSV_DIR = os.getenv("V3_CSV_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "V1", "csv", "real"))

SYMBOLS = os.getenv("V3_SYMBOLS", "NAS100,US30").split(",")
CSV_PATHS = {s: os.path.join(_CSV_DIR, f"{s}_15m.csv") for s in SYMBOLS}

# ── Sermaye ──────────────────────────────────────────────────────────────────
INITIAL_BALANCE = _f("V3_INITIAL_BALANCE", 100_000.0)

# ── Risk / boyutlandırma ─────────────────────────────────────────────────────
RISK_PER_TRADE_PCT = _f("V3_RISK_PCT", 0.5)          # işlem başına risk %
RISK_PER_TRADE     = RISK_PER_TRADE_PCT / 100.0
REWARD_RISK_RATIO  = _f("V3_RR", 2.0)                # TP = RR × SL mesafesi
ATR_MULTIPLIER     = _f("V3_ATR_MULT", 2.0)          # SL mesafesi = ATR × bu
MAX_OPEN_POSITIONS = _i("V3_MAX_POSITIONS", 2)       # hesap genelinde
MAX_NOTIONAL_LEVERAGE = _f("V3_MAX_LEVERAGE", 10.0)

# ── HESAP SEVİYESİ prop-firm limitleri ───────────────────────────────────────
# Firma (FundingPips): toplam %10, günlük %5. Hedef: toplam %8, günlük %4.
# İç limitler hedefin de altında tampon:
TRAILING_DD_LIMIT_PCT = _f("V3_TRAIL_DD", 6.0)   # ZİRVEDEN düşüş limiti (kârı da korur)
DAILY_DD_LIMIT_PCT    = _f("V3_DAILY_DD", 3.0)   # gün-içi zirveden düşüş limiti
TOTAL_DD_LIMIT_PCT    = _f("V3_TOTAL_DD", 8.0)   # başlangıçtan düşüş (yedek/hard limit)

TRAILING_DD_LIMIT = TRAILING_DD_LIMIT_PCT / 100.0
DAILY_DD_LIMIT    = DAILY_DD_LIMIT_PCT / 100.0
TOTAL_DD_LIMIT    = TOTAL_DD_LIMIT_PCT / 100.0

# ── Günlük gelir modeli ──────────────────────────────────────────────────────
# Gün +hedefe ulaşınca o gün YENİ işlem yok (açık pozisyonlar yönetilmeye devam).
# Hedef: günde +%0.22 → ~%5/ay (22 işlem günü). Kilit kazancı korur.
DAILY_PROFIT_TARGET_PCT = _f("V3_DAILY_TARGET", 0.22)   # günlük kâr hedefi %
DAILY_PROFIT_TARGET     = DAILY_PROFIT_TARGET_PCT / 100.0
MAX_DAILY_TRADES        = _i("V3_MAX_DAILY_TRADES", 6)  # overtrading koruması
MAX_CONSECUTIVE_SL      = _i("V3_MAX_CONSEC_SL", 3)     # circuit breaker

# ── Göstergeler ──────────────────────────────────────────────────────────────
EMA_FAST = _i("V3_EMA_FAST", 9)
EMA_SLOW = _i("V3_EMA_SLOW", 21)
EMA_50, EMA_200 = 50, 200
RSI_PERIOD = _i("V3_RSI_PERIOD", 14)
ATR_PERIOD = _i("V3_ATR_PERIOD", 14)
ADX_PERIOD = 14
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
BB_PERIOD, BB_STD = 20, 2.0
WARMUP_BARS = 210

# ── Seans / zaman filtreleri (VERİNİN BROKER SAATİ ~EET/GMT+2) ───────────────
# NAS100 RTH seansı broker saatinde 16:30–23:00 (hacim/spread en iyi).
# Hacim analizi: pik 17:00, yüksek 16:00–22:00, 23:00'te çöküyor.
TRADE_START_HOUR = _i("V3_START_HOUR", 16)
TRADE_START_MIN  = _i("V3_START_MIN", 30)
TRADE_END_HOUR   = _i("V3_END_HOUR", 23)      # 23:00'a kadar yeni giriş
TRADE_END_MIN    = _i("V3_END_MIN", 0)
FORCE_CLOSE_HOUR = _i("V3_FORCE_CLOSE_HOUR", 22)  # Cuma flatten / hafta sonu
BLOCK_FRIDAY_LATE = _b("V3_BLOCK_FRIDAY_LATE", True)  # Cuma geç saat yeni işlem yok
ALLOW_WEEKEND_HOLDING = _b("V3_ALLOW_WEEKEND", False)

# ── İşlem maliyetleri ────────────────────────────────────────────────────────
SPREAD_POINTS   = _f("V3_SPREAD", 1.5)        # enstrüman puanı cinsinden spread
COMMISSION_RATE = _f("V3_COMMISSION", 0.000015)  # notional başına (ICMarkets raw)
CONTRACT_SIZE   = _f("V3_CONTRACT_SIZE", 1.0)

# ── Strateji eşikleri (kural motoru) ─────────────────────────────────────────
ADX_STRONG = _f("V3_ADX_STRONG", 22.0)
EARLY_MIN_BARS, EARLY_MAX_BARS = 1, 25
PULLBACK_MIN_BARS, PULLBACK_MAX_BARS = 25, 120
RSI_EARLY_LONG = (38, 70)
RSI_EARLY_SHORT = (30, 62)
RSI_PULLBACK_LONG = (35, 52)
RSI_PULLBACK_SHORT = (48, 65)
ATR_MIN_PCT = _f("V3_ATR_MIN_PCT", 0.0005)  # fiyatın %0.05'i — enstrümandan bağımsız
