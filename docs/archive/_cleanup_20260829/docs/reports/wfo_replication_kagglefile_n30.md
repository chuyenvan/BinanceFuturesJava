# REPLICATION vế A trên node-type KAGGLE-FILE (N=30, leak-free wf) — 14/17 window (2026-07-05)

**Env:** Kaggle 5 kernel, TICKER_SOURCE=file (hpo-ticker-daily), store 226 ns=ticker, jar e82c4846 (task121), V4.1.
**Thiếu 3 window:** w13/w14 (2 FAILED — nghi geo-block exchange_info, TASK-129) + w16 (w5 chạm trần 12h Kaggle bị CANCEL).
**Confound ghi nhận:** ClientSingleton fallback API bị geo-block trên Kaggle → quantity không normalize stepSize
(Oracle normalize qua API OK) → Δ so Oracle gồm cả hiệu ứng này + khác nguồn ticker. CHỈ so xu hướng, không so số tuyệt đối
(quy tắc 1-experiment-1-node-type giữ nguyên). Mục đích replication ĐẠT: pipeline kaggle-file chạy 14 window end-to-end,
FAILED có nguyên nhân xác định, số cùng bậc với Oracle-A (WFE thấp, nhiều TOO_FEW — cùng bức tranh).

# WFO STRATEGY — report

## VERDICT: ❌ FAIL/REVIEW

Ngưỡng pre-registered: WFE_median ≥ 0.5, %cửa-sổ-OOS-dương ≥ 70%, maxDD-OOS xấu nhất ≤ 50% vốn

## Tổng hợp
- Số cửa sổ DONE: 14
- % cửa sổ OOS dương: 71.4% (10/14)
- WFE trung vị: 0.220
- maxDD OOS xấu nhất: 36.0% vốn (abs 12594)

## Bảng cửa sổ
| win | OOS | IS_fit | OOS_fit | WFE | OOS_pnl | OOS_maxDD | OOS_calmar | trades | oosNote | reject |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 20220101..20220401 | 4.3813 | 2.3207 | 0.0431 | 341.6956 | 147.2387 | 2.3207 | 30 | SUCCESS | 0/30 |
| 1 | 20220401..20220701 | 5.3815 | 1.012 | 0.3596 | 1723.438 | 1702.9817 | 1.012 | 426 | SUCCESS | 0/30 |
| 2 | 20220701..20221001 | 1.8189 | -99990 | 0.0208 | 78.4697 | 107.7697 | 0.7281 | 10 | TOO_FEW_TRADES | 1/30 |
| 3 | 20221001..20230101 | 1.9538 | 1.9786 | 0.1796 | 677.7628 | 342.5406 | 1.9786 | 143 | SUCCESS | 0/30 |
| 4 | 20230101..20230401 | 6.1004 | -99999 | 0.00010 | 0.7882 | 0.1965 | 0.7882 | 1 | TOO_FEW_TRADES | 0/30 |
| 5 | 20230401..20230701 | 1.6886 | -99996 | -0.027 | -38.1766 | 134.4684 | -0.2839 | 4 | TOO_FEW_TRADES | 4/30 |
| 6 | 20230701..20231001 | 7.0361 | 0.1371 | 0.0459 | 324.3829 | 2366.3369 | 0.1371 | 167 | SUCCESS | 20/30 |
| 7 | 20231001..20240101 | 4.768 | 5.1388 | 0.2606 | 1844.0148 | 358.8429 | 5.1388 | 136 | SUCCESS | 22/30 |
| 8 | 20240101..20240401 | -99886 | 0.3962 | 0.2638 | 244.7718 | 617.7713 | 0.3962 | 32 | SUCCESS | 30/30 |
| 9 | 20240401..20240701 | 3.2186 | -99984 | -0.1517 | -171.313 | 563.8158 | -0.3038 | 16 | TOO_FEW_TRADES | 29/30 |
| 10 | 20240701..20241001 | -99882 | 5.5492 | 2.273 | 1466.8079 | 264.3268 | 5.5492 | 424 | SUCCESS | 30/30 |
| 11 | 20241001..20250101 | 2.8015 | 3.4862 | 0.8987 | 928.1059 | 266.2206 | 3.4862 | 33 | SUCCESS | 28/30 |
| 12 | 20250101..20250401 | 5.2228 | 0.7501 | 0.4955 | 1999.4292 | 2665.4932 | 0.7501 | 298 | SUCCESS | 24/30 |
| 15 | 20251001..20260101 | 1.7702 | 0.6733 | 6.4997 | 8479.8984 | 12593.7695 | 0.6733 | 1179 | SUCCESS | 15/30 |

## Độ ổn định gene qua cửa sổ (min..max best value)
- MIN_MOMENTUM_15M: 0.0228 .. 0.0472
- PREDICT_SYMBOL_RATE_MAX_THRESHOLD: 0.0518 .. 0.1880
- AI_DYNAMIC_MULTIPLIER: 1.2876 .. 1.9450
- AI_DYNAMIC_MIN: 0.1573 .. 0.4965
- HARD_RISK_LIMIT_4H: -0.2829 .. -0.0650
- MS_DOWN_BIG_AVG: -0.0511 .. -0.0239
- DCA_LOSS_BIG_DOWN: -0.2170 .. -0.1109
- DCA_TIME_BIG_DOWN: 3.1588 .. 8.0000
- DCA_TIME_BIG_Up: 15.0000 .. 29.0464
- RATE_PROFIT_STOP_MARKET: 0.0103 .. 0.0248
- TS_PROFIT_MULTIPLIER: 4.1672 .. 7.9041
- TS_DYNAMIC_K: 0.1116 .. 0.2977
- TS_MAX_GAP: 0.0407 .. 0.0800
- TS_MAX_GAP_WEAK: 0.0300 .. 0.0590
- TS_WEAK_MOMENTUM_THRES: 0.0040 .. 0.0076
- BUDGET_MARGIN_RATIO_1: 0.3107 .. 0.4820
- BUDGET_MARGIN_RATIO_2: 0.6166 .. 0.7706
- BUDGET_DIVIDER_2: 1.5984 .. 2.4206

> ⚠️ WFE<0.3 = overfit; WFE≥0.5 tốt. maxDD backtest hiểu nhẹ (chưa margin-call) → biên an toàn.
