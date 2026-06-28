# NASDAQ Paper-Trading Botu

NASDAQ hisseleri için **kağıt üzerinde (paper trading)** alım-satım botu.
**Gerçek para riski yoktur** — tüm emirler sanal bir portföy üzerinde simüle
edilir. Geçmiş veride strateji test etme (backtest) ve gecikmeli canlı
simülasyon (paper-trade döngüsü) yapabilir.

## Özellikler

- 📊 **Backtest motoru** — geçmiş veride strateji simülasyonu, Sharpe / max
  drawdown / CAGR gibi metrikler.
- 🤖 **Canlı paper-trade döngüsü** — periyodik olarak veri çekip sanal
  portföyü günceller (gerçek emir göndermez).
- 🔌 **Eklenebilir veri katmanı** — `yfinance` (gerçek piyasa) veya
  `synthetic` (internet gerektirmeyen çevrimdışı test/demo).
- 📈 **Stratejiler** — SMA kesişimi (trend takip) ve RSI (mean-reversion).
- ✅ Tamamı pytest ile test edilmiştir, ağ bağımlılığı yoktur.

> **Uyarı:** Bu bir eğitim/araştırma projesidir, yatırım tavsiyesi değildir.
> Sadece simülasyon yapar; gerçek bir broker'a emir göndermez.

## Kurulum

```bash
pip install -r requirements.txt
```

Geliştirme (testler dahil):

```bash
pip install -r requirements-dev.txt
```

## Kullanım

### Backtest

```bash
# Gerçek veri (internet gerekir) - SMA kesişim stratejisi
python -m nasdaqbot backtest --symbol AAPL --strategy sma --fast 20 --slow 50 --period 2y

# RSI stratejisi
python -m nasdaqbot backtest --symbol MSFT --strategy rsi --rsi-lower 30 --rsi-upper 70

# İnternetsiz / çevrimdışı demo (sentetik veri)
python -m nasdaqbot backtest --provider synthetic --symbol DEMO --strategy sma
```

Örnek çıktı:

```
=== Backtest: AAPL | SMA crossover (fast=20, slow=50) ===
Veri    : 504 bar (2024-07-23 → 2026-06-26)
------------------------------------------------
Başlangıç :    10,000.00 USD
Son değer :    11,240.00 USD
Getiri    :       12.40 %
CAGR      :        6.02 %
Sharpe    :        0.71
Max düşüş :      -14.30 %
İşlem     :           8
```

### Canlı paper-trade döngüsü

```bash
# Her saat başı (3600 sn) AAPL'yi değerlendir, sanal işlem yap
python -m nasdaqbot run --symbol AAPL --strategy sma --poll-seconds 3600

# Tek adım çalıştır (test için)
python -m nasdaqbot run --symbol AAPL --max-steps 1
```

Durdurmak için `Ctrl-C`.

### Önemli: İnternet / veri erişimi

`yfinance` sağlayıcısı Yahoo Finance'e erişim gerektirir. Bazı kısıtlı/proxy'li
ortamlarda (ör. CI veya sandbox) bu engellenebilir; o durumda komutlar
`--provider synthetic` ile çalıştırılarak tüm akış internetsiz test edilebilir.

## Yapılandırma

`config.yaml` örnek varsayılanları içerir. Şu an CLI bayrakları birincil
yapılandırma yöntemidir; tüm değerler komut satırından geçilebilir.

## Mimari

```
nasdaqbot/
├── data/                 # Veri katmanı (pluggable)
│   ├── base.py           #   DataProvider arayüzü (OHLCV sözleşmesi)
│   ├── yfinance_provider.py
│   └── synthetic.py      #   çevrimdışı deterministik veri
├── indicators.py         # SMA, EMA, RSI
├── strategy/             # Stratejiler
│   ├── base.py           #   Strategy arayüzü (hedef ağırlık 0..1)
│   ├── sma_crossover.py
│   └── rsi.py
├── portfolio.py          # Sanal long-only hesap (paper trading)
├── engine.py             # backtest() + PaperTrader (canlı döngü)
└── cli.py                # argparse komut satırı arayüzü
```

**Tasarım ilkeleri:**

- Strateji "hedef pozisyon ağırlığı" (0.0 = nakit, 1.0 = tam yatırım) üretir;
  motor bunu uygular. Bu sayede aynı strateji hem backtest hem canlı döngüde
  çalışır.
- **Sinyal-kaçağı (lookahead bias) yok:** `t` barındaki sinyal `t+1` barının
  açılış fiyatından uygulanır.
- Veri katmanı arayüz arkasında; gerçek/sahte veri arasında geçiş tek bayrak.

## Testler

```bash
python -m pytest -q
```

Tüm testler sentetik veriyle çalışır, ağ erişimi gerektirmez.

## Yeni strateji ekleme

1. `nasdaqbot/strategy/` altında `Strategy`'den türeyen bir sınıf yaz;
   `generate(df) -> pd.Series` (0..1 hedef ağırlık) uygula.
2. `nasdaqbot/strategy/__init__.py` içindeki `get_strategy` fabrikasına ekle.
3. CLI'da `--strategy <isim>` ile kullan.
