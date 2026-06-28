"""
V3/risk.py
----------
Hesap-seviyesi risk yöneticisi (guardrails).

Savunma hatları (öncelik sırasıyla):
  1. Trailing DD (zirveden)  → limit aşılırsa hesap KAYBEDİLDİ (kalıcı kill).
  2. Toplam DD (başlangıçtan) → yedek hard limit.
  3. Günlük DD (gün-içi zirveden) → o gün yeni işlem yok (ertesi gün resetlenir).
  4. Günlük kâr kilidi → gün +hedefe ulaşınca o gün yeni işlem yok.
  5. Circuit breaker → N ardışık SL → o gün dur.
  6. Seans penceresi / hafta sonu flatten.

Kill-switch aktifken AÇIK pozisyonlar yönetilmeye devam eder (kapatılabilir),
ama yeni pozisyon AÇILMAZ.
"""

from __future__ import annotations

import logging

from . import config as C
from .account import Account

logger = logging.getLogger(__name__)

_FRIDAY = 4


class RiskManager:
    def __init__(self) -> None:
        self.account_blown = False        # trailing/total DD → kalıcı
        self.daily_locked = False         # günlük DD / kâr hedefi / breaker
        self.daily_trades = 0
        self.consecutive_sl = 0
        self.profit_target_hit = False

    # ── Günlük reset ─────────────────────────────────────────────────────
    def reset_daily(self, account: Account) -> None:
        if self.account_blown:
            return
        account.reset_daily()
        self.daily_locked = False
        self.daily_trades = 0
        self.consecutive_sl = 0
        self.profit_target_hit = False

    # ── Kalıcı limitler (her bar kontrol) ────────────────────────────────
    def check_account_limits(self, account: Account) -> bool:
        """Trailing veya toplam DD aşıldıysa True (hesap kaybedildi)."""
        if self.account_blown:
            return True
        if account.trailing_dd() >= C.TRAILING_DD_LIMIT:
            self.account_blown = True
            logger.critical("TRAILING DD %.2f%% >= %.1f%% — hesap kaybedildi (zirveden).",
                            account.trailing_dd() * 100, C.TRAILING_DD_LIMIT * 100)
            return True
        if account.total_dd() >= C.TOTAL_DD_LIMIT:
            self.account_blown = True
            logger.critical("TOPLAM DD %.2f%% >= %.1f%% — hesap kaybedildi.",
                            account.total_dd() * 100, C.TOTAL_DD_LIMIT * 100)
            return True
        return False

    # ── Günlük limitler ──────────────────────────────────────────────────
    def update_daily_state(self, account: Account) -> None:
        """Günlük DD / kâr hedefi durumunu günceller (kilit set eder)."""
        if account.daily_dd() >= C.DAILY_DD_LIMIT:
            if not self.daily_locked:
                logger.warning("Günlük DD %.2f%% — gün kilitlendi.", account.daily_dd() * 100)
            self.daily_locked = True
        if account.daily_gain() >= C.DAILY_PROFIT_TARGET:
            if not self.profit_target_hit:
                logger.info("🔒 Günlük kâr hedefi +%.2f%% — gün kilitlendi (kâr korunuyor).",
                            account.daily_gain() * 100)
            self.profit_target_hit = True
            self.daily_locked = True

    # ── Yeni işleme izin var mı? ─────────────────────────────────────────
    def can_open(self, account: Account, ts) -> bool:
        if self.account_blown:
            return False
        self.update_daily_state(account)
        if self.daily_locked:
            return False
        if self.daily_trades >= C.MAX_DAILY_TRADES:
            return False
        if account.open_count >= C.MAX_OPEN_POSITIONS:
            return False
        if not self._in_session(ts):
            return False
        return True

    def record_result(self, won: bool) -> None:
        if won:
            self.consecutive_sl = 0
        else:
            self.consecutive_sl += 1
            if self.consecutive_sl >= C.MAX_CONSECUTIVE_SL:
                self.daily_locked = True
                logger.warning("Circuit breaker — %d ardışık SL, gün kilitlendi.", self.consecutive_sl)

    # ── Seans / zaman (dakika-hassas: 16:30–23:00 broker saati) ──────────
    @staticmethod
    def _in_session(ts) -> bool:
        tod = (ts.hour, ts.minute)
        start = (C.TRADE_START_HOUR, C.TRADE_START_MIN)
        end   = (C.TRADE_END_HOUR, C.TRADE_END_MIN)
        if not (start <= tod < end):
            return False
        if C.BLOCK_FRIDAY_LATE and ts.weekday() == _FRIDAY and ts.hour >= C.FORCE_CLOSE_HOUR:
            return False
        return True

    @staticmethod
    def should_force_close(ts) -> bool:
        if C.ALLOW_WEEKEND_HOLDING:
            return False
        return ts.weekday() == _FRIDAY and ts.hour >= C.FORCE_CLOSE_HOUR
