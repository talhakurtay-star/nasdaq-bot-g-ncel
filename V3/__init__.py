"""
V3 — Günlük-hedef odaklı, çok-sembol prop-firm botu.

Tasarım ilkeleri:
  - HESAP SEVİYESİ risk: trailing DD (zirveden), günlük DD, günlük kâr kilidi.
  - Günlük gelir modeli: gün +hedefe ulaşınca o gün KİLİTLENİR.
  - Gerçek veri (MT5 CSV). Sentetik veri/ML iskelesi yoktur.
  - Saf-pandas göstergeler (talib/pandas_ta gerekmez).

V1/V2'den TAŞINAN kanıtlanmış fikirler:
  - Dürüst dolum (bar-içi SL/TP çakışmasında SL kazanır).
  - ATR-bazlı pozisyon boyutlandırma.
  - İki katmanlı kural motoru (erken trend + pullback).
  - Guardrails (circuit breaker, seans penceresi, hafta sonu flatten).
"""

__version__ = "3.0.0"
