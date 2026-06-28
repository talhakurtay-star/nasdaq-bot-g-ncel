# Overfitting / Robustluk Raporu — funded-survival risk profili

**Tarih:** 2026-06-28
**Kurulum:** V2 pipeline, RISK=%1, günlük DD %3, toplam DD %6, RR 1:2.5
**Metot:** Her enstrümanda IS %70 / OOS %30, `BACKTEST_DAYS=360` pencere
**Veri:** Gerçek MT5 15m (2022→2026)

## Sonuçlar

| Enstrüman | IS PnL | IS PF | OOS PnL | OOS PF | OOS WR | OOS MaxDD | Yargı |
|---|---|---|---|---|---|---|---|
| **US30** (Dow) | +20.08% | 1.16 | **+9.16%** | 1.07 | 65% | **26.96%** | ⚠️ zayıf genelleme (0.46) |
| **NAS100** | −5.72% | 0.90 | **+7.13%** | 1.17 | 71% | 11.04% | 🚩 kararsız (işaret değiştirdi) |
| **GER40** (DAX) | −5.96% | 0.75 | −5.60% | 0.59 | 59% | 10.02% | ❌ edge yok |
| **UK100** (FTSE) | −5.86% | 0.60 | −5.33% | 0.76 | 58% | 10.82% | ❌ edge yok |
| **XAUUSD** (Gold) | −5.31% | 0.78 | −5.43% | 0.16 | 36% | 6.59% | ❌ edge yok |

## Yorum

1. **Robust evrensel edge YOK.** 2/5 enstrümanda kâr (US30, OOS-NAS100),
   3/5'te zarar. Strateji bazı trend'li endekslerde bazı rejimlerde çalışıyor,
   diğerlerinde çöküyor.

2. **Saf overfitting değil, ama kırılgan.** US30 IS→OOS kârlı kalıyor (ezber
   olsaydı OOS çökerdi) — ama OOS getiri IS'in yarısına iniyor (0.46) ve
   NAS100 IS'te kaybedip OOS'ta kazanıyor. Bu **rejime aşırı bağımlılık**.
   Önceki +204% büyük olasılıkla US30-benzeri uygun bir döneme denk gelmiş.

3. **🔴 KRİTİK KUSUR — Toplam DD limiti kârdayken işe yaramıyor.**
   Kill-switch toplam DD'yi BAŞLANGIÇ bakiyesinden ölçüyor. Hesap +%20'ye
   çıkınca (US30), zirveden %27 düşse bile mutlak equity 94k'nın altına
   inmediği için limit TETİKLENMİYOR → gerçekleşen MaxDD %26.96.
   Funded hesapta (trailing drawdown) bu **hesabı patlatır**.
   **Çözüm:** zirveden (high-water-mark) ölçen trailing toplam DD limiti.

## Sonraki adım

`funded hesabı uzun süre yaşatmak` hedefi için en kritik düzeltme: **trailing
(zirveden) drawdown limiti** eklemek. Edge'in kırılganlığı ayrı bir problem;
ama önce DD koruması doğru olmalı.
