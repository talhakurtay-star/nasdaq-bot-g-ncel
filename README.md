# nasdaq-bot

NAS100 (NASDAQ-100) için prop-firm odaklı algoritmik alım-satım botu.
İki sürüm içerir:

- **V1** — Kural-bazlı çekirdek: iki katmanlı sinyal motoru (erken trend +
  pullback), ATR-bazlı pozisyon boyutlandırma, prop-firm guardrail'leri
  (günlük/toplam drawdown kill-switch, circuit breaker, hafta sonu flatten),
  bar-by-bar backtest simülatörü, MT5 köprüsü ve walk-forward optimizer.
- **V2** — V1'in üzerine kurulu 3 aşamalı pipeline:
  - Stage 1 `RegimeDetector` — piyasa rejimi sınıflandırması (TREND/CHOPPY/BREAKOUT)
  - Stage 2 `EnsembleSignal` — V1 kural motoru (+ opsiyonel LightGBM ensemble)
  - Stage 3 `AdaptiveExit` — momentum-bazlı erken çıkış

## Çalıştırma

```bash
pip install -r requirements.txt   # pandas, numpy, pandas_ta/talib, xgboost, lightgbm
cd V2 && python backtest_v2.py    # dahili cache ile backtest
CSV_PATH=/yol/nas100_15m.csv python backtest_v2.py   # kendi verinle
```

## ⚠️ Veri uyarısı

`V1/cache/` içindeki dosyalar **sentetik/proxy** verilerdir (örn. `VIX_Close`
sabit 15.0, `SPY_Close = Close`). Gerçek sonuç için MT5'ten export edilmiş
gerçek NAS100 15m verisini `V1/csv/nasdaq_15m.csv` olarak koyun.

## Risk profili

Bot, **funded hesabı uzun süre yaşatmak** hedefiyle konservatif risk profiline
ayarlanmıştır (bkz. `V1/config/settings.py`):

- İşlem başına risk: **%1.0**
- Günlük iç DD limiti: **%3.0** (firma %5'inin altında tampon)
- Toplam iç DD limiti: **%6.0** (firma %10'unun altında tampon)
- Günlük kâr kilidi: **+%2 → o gün yeni işlem yok** (kârı geri vermeyi önler)
- Eşzamanlı pozisyon: **2** · Kaldıraç tavanı: **10×** · Ardışık SL breaker: **3**

Tüm parametreler `os.getenv` ile ortam değişkeninden override edilebilir
(örn. `STRESS_RISK_PCT`, `STRESS_DAILY_DD`).
