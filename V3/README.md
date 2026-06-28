# V3 — Günlük-hedef, çok-sembol prop-firm botu

Sıfırdan, temiz mimari. V1/V2'deki kanıtlanmış fikirler taşındı; ölü yük
(devre dışı ML, sentetik veri, V1/V2 ikiliği) atıldı.

## Tasarım

- **Hesap-seviyesi risk** (çoklu sembol tek hesap).
- **Trailing DD** (zirveden/high-water-mark) — V1'in "kârdayken korumayan"
  bug'ı düzeltildi.
- **Günlük gelir modeli**: gün +hedefe ulaşınca o gün yeni işlem yok (kâr kilidi).
- Saf-pandas göstergeler (talib/pandas_ta gerekmez).
- Sadece gerçek MT5 verisi.

## Modüller

| Dosya | Görev |
|---|---|
| `config.py` | Tüm parametreler (env override'lı) |
| `indicators.py` | EMA/RSI/ATR/ADX/MACD (saf pandas) |
| `strategy.py` | İki katmanlı kural motoru (erken trend + pullback) |
| `account.py` | Hesap + pozisyonlar + boyutlandırma + equity zirvesi |
| `risk.py` | Trailing/günlük DD, kâr kilidi, circuit breaker, seans |
| `simulator.py` | Dolum (bar-içi SL kazanır) + trailing stop |
| `backtest.py` | Çok-sembol birleşik zaman çizgisi + günlük rapor |
| `validate.py` | IS/OOS robustluk (overfitting kontrolü) |

## Çalıştırma

```bash
python -m V3.backtest                  # config sembolleri (NAS100,US30)
V3_SYMBOLS=NAS100 python -m V3.backtest
python -m V3.validate                  # IS/OOS robustluk testi
python -m V3.tests.test_risk           # risk davranış testleri
```

## Risk profili (varsayılan)

| Parametre | Değer |
|---|---|
| Risk/işlem | %0.5 |
| RR | 1:2.0 |
| Günlük kâr hedefi (kilit) | +%0.5 |
| Trailing DD limiti (zirveden) | %6 |
| Günlük DD limiti | %3 |
| Toplam DD (hard) | %8 |

## Mevcut durum (gerçek veri, IS/OOS)

- **NAS100**: IS +%15.5 / OOS +%7.0 — ✅ tutarlı, DD <%5, Sharpe >2. Umut verici.
- **US30**: bu config ile zarar + trailing DD kırıyor — eklenmemeli (kendi
  config'i gerekebilir).

⚠️ Sadece ~1 yıllık (2022-2023) NAS100 verisi var. Güvenmeden önce daha çok yıl
gerekir — 2022 trend'li bir yıldı, choppy dönemlerde test edilmeli.
