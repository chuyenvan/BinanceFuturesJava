# WFO STRATEGY — report

## VERDICT: ❌ FAIL/REVIEW

Ngưỡng pre-registered: WFE_median ≥ 0.5, %cửa-sổ-OOS-dương ≥ 70%, maxDD-OOS xấu nhất ≤ 50% vốn

## Tổng hợp
- Số cửa sổ DONE: 10
- % cửa sổ OOS dương: 90.0% (9/10)  _[P1 lenient; strict=70.0%]_
- WFE trung vị: 0.089
- maxDD OOS xấu nhất: 5.6% vốn (abs 1973)

- **[119 report-only]** maxDD_mtm OOS xấu nhất: 8.7% vốn | cửa sổ dính MARGIN_CALL: 0/10 _(maxDD_mtm = drawdown equity mark-to-market từ đỉnh, gồm realized; margin-call = equity ≤ 0.5% notional, proxy Binance cross 1x — chỉ báo cáo, verdict vẫn đọc maxDD cũ)_

## Bảng cửa sổ
| win | OOS | IS_fit | OOS_fit | WFE | OOS_pnl | OOS_maxDD | OOS_calmar | trades | oosNote | reject | ddPct% | ddPct_mtm% | marginCall | minEq_mtm% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 20220101..20220401 | -100000 | 2.7548 | 0 | 1113.7814 | 404.3036 | 2.7548 | 325 | SUCCESS | 1/1 | 1.2 | 1.9 | no | 99.4 |
| 1 | 20220401..20220701 | 2.7548 | 1.5313 | 2.4181 | 2693.2261 | 1758.8219 | 1.5313 | 2023 | SUCCESS | 0/1 | 5.0 | 3.9 | no | 99.1 |
| 2 | 20220701..20221001 | 2.1645 | -73333.3359 | 0.002 | 7.4344 | 53.486 | 0.139 | 8 | TOO_FEW_TRADES | 0/1 | 0.2 | 0.3 | no | 99.9 |
| 3 | 20221001..20230101 | 2.1669 | 0.4877 | 0.2525 | 962.2982 | 1973.189 | 0.4877 | 903 | SUCCESS | 0/1 | 5.6 | 8.7 | no | 97.3 |
| 4 | 20230101..20230401 | 2.3307 | -79310.3437 | -0.00070 | -3.3936 | 29.2254 | -0.1161 | 6 | TOO_FEW_TRADES | 0/1 | 0.1 | 0.2 | no | 99.9 |
| 5 | 20230401..20230701 | 1.9629 | -100003.3359 | 0.0226 | 89.7991 | 366.3263 | 0.2451 | 30 | TOO_MUCH_CAPITAL_LOCK | 0/1 | 1.1 | 1.3 | no | 98.9 |
| 6 | 20230701..20231001 | 0.6001 | 8.6359 | 1.3566 | 1682.8925 | 194.8721 | 8.6359 | 275 | SUCCESS | 0/1 | 0.6 | 1.6 | no | 99.5 |
| 7 | 20231001..20240101 | 1.5256 | 2.3001 | 0.0563 | 169.531 | 73.7051 | 2.3001 | 67 | SUCCESS | 0/1 | 0.2 | 0.3 | no | 100.0 |
| 8 | 20240101..20240401 | 5.8952 | 0.6857 | 0.4723 | 863.923 | 1259.9735 | 0.6857 | 411 | SUCCESS | 0/1 | 3.6 | 4.6 | no | 95.7 |
| 9 | 20240401..20240701 | 2.6382 | 1.7582 | 0.0885 | 235.6376 | 134.02 | 1.7582 | 68 | SUCCESS | 0/1 | 0.4 | 1.0 | no | 99.6 |

## Độ ổn định gene qua cửa sổ (min..max best value)
- MIN_MOMENTUM_15M: 0.0228 .. 0.0228
- PREDICT_SYMBOL_RATE_MAX_THRESHOLD: 0.1500 .. 0.1500
- AI_DYNAMIC_MULTIPLIER: 1.2876 .. 1.2876
- AI_DYNAMIC_MIN: 0.2679 .. 0.2679
- HARD_RISK_LIMIT_4H: -0.2000 .. -0.2000
- MS_DOWN_BIG_AVG: -0.0316 .. -0.0316
- DCA_LOSS_BIG_DOWN: -0.1500 .. -0.1500
- DCA_TIME_BIG_DOWN: 8.0000 .. 8.0000
- RATE_PROFIT_STOP_MARKET: 0.0103 .. 0.0103
- TS_PROFIT_MULTIPLIER: 5.2185 .. 5.2185
- TS_DYNAMIC_K: 0.2977 .. 0.2977
- TS_MAX_GAP: 0.0800 .. 0.0800
- TS_MAX_GAP_WEAK: 0.0300 .. 0.0300
- TS_WEAK_MOMENTUM_THRES: 0.0040 .. 0.0040
- BUDGET_MARGIN_RATIO_1: 0.4820 .. 0.4820
- BUDGET_MARGIN_RATIO_2: 0.7475 .. 0.7475
- BUDGET_DIVIDER_2: 1.5984 .. 1.5984

> ⚠️ WFE<0.3 = overfit; WFE≥0.5 tốt. maxDD backtest hiểu nhẹ (chưa margin-call) → biên an toàn.
