# WFO STRATEGY — report

## VERDICT: ❌ FAIL/REVIEW

Ngưỡng pre-registered: WFE_median ≥ 0.5, %cửa-sổ-OOS-dương ≥ 70%, maxDD-OOS xấu nhất ≤ 50% vốn

## Provenance (run 2026-07-02, xong 18:20)
- Dataset: `~/claudedata/wfo_dataset_wf` (Oracle) — manifest exportedAt 2026-07-02 11:02, funding LEAKFREE-perfold-24h
  score=1−P(win), md5_market=65ac483d… · md5_pred=44061d68… · md5_funding=d714390a… (WfoDataset.load verify PASS)
- Jar: `binance-futures-wfo-lf.jar` (Oracle, aerospike-client 6.1.11) · fitness **V4** · funding fee **OFF** (mặc định HPO/WFO)
- Env worker: `WFO_KAGGLE=1 WFO_SMART_CACHE=1 WFO_DATA_DIR=…/wfo_dataset_wf` — ticker từ Aerospike Oracle-local
- 17 window × N=30 mẫu (18 gene) · budget 35000 · jobstore Aerospike Oracle-local ns=test
- Khung diễn giải: WFO **loại 1** (pred cố định) — số OOS tuyệt đối window <2025-06 bị tâng (pred sinh in-sample)

## Tổng hợp
- Số cửa sổ DONE: 17
- % cửa sổ OOS dương: 76.5% (13/17)
- WFE trung vị: 0.098
- maxDD OOS xấu nhất: 30.7% vốn (abs 10735)

## Bảng cửa sổ
| win | OOS | IS_fit | OOS_fit | WFE | OOS_pnl | OOS_maxDD | OOS_calmar | trades | reject |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 20220101..20220401 | 6.2536 | 2.502 | 0.0287 | 328.3754 | 131.2451 | 2.502 | 30 | 0/30 |
| 1 | 20220401..20220701 | 8.631 | 1.1286 | 0.2413 | 1878.4518 | 1664.4479 | 1.1286 | 426 | 0/30 |
| 2 | 20220701..20221001 | 2.4864 | 0.6123 | 0.0126 | 58.545 | 95.6097 | 0.6123 | 10 | 0/30 |
| 3 | 20221001..20230101 | 2.5351 | -100002.0234 | 0.0979 | 339.6871 | 248.3558 | 1.3677 | 99 | 0/30 |
| 4 | 20230101..20230401 | 3.223 | -100000 | 0 | 0 | 0 | 0 | 0 | 0/30 |
| 5 | 20230401..20230701 | 2.6553 | 0.0631 | 0.0084 | 25.9824 | 411.7809 | 0.0631 | 10 | 1/30 |
| 6 | 20230701..20231001 | 2.9049 | -100003.2266 | 0.4856 | 517.4775 | 340.608 | 1.5193 | 31 | 8/30 |
| 7 | 20231001..20240101 | 3.6282 | -99992 | 0 | 0 | 0 | 0 | 8 | 9/30 |
| 8 | 20240101..20240401 | 3.0246 | 1.2387 | 0.6393 | 658.6094 | 531.7029 | 1.2387 | 94 | 29/30 |
| 9 | 20240401..20240701 | 3.3559 | 1.3886 | 0.5614 | 876.0234 | 630.8836 | 1.3886 | 201 | 27/30 |
| 10 | 20240701..20241001 | 3.3525 | 6.2732 | 0.6349 | 1342.7695 | 214.0497 | 6.2732 | 424 | 28/30 |
| 11 | 20241001..20250101 | 4.1361 | 3.2167 | 0.5829 | 884.7578 | 275.0547 | 3.2167 | 33 | 17/30 |
| 12 | 20250101..20250401 | 6.7365 | 0.7833 | 0.3803 | 1798.6049 | 2296.1262 | 0.7833 | 281 | 19/30 |
| 13 | 20250401..20250701 | 3.1398 | -100000 | 0 | 0 | 0 | 0 | 0 | 15/30 |
| 14 | 20250701..20251001 | 5.0744 | -99996 | 0 | 0 | 0 | 0 | 4 | 5/30 |
| 15 | 20251001..20260101 | 1.8662 | 1.4695 | 8.8737 | 15775.2725 | 10735.2178 | 1.4695 | 1441 | 11/30 |
| 16 | 20260101..20260401 | 2.175 | 1.5245 | 0.0145 | 215.8205 | 141.5657 | 1.5245 | 12 | 0/30 |

**Chú giải bảng (fitness V4 — sentinel encoding, sẽ hết cần sau TASK-113/V4.1):**
- `OOS_fit = -100000` → ZERO_TRADES; `-100000+n` → TOO_FEW_TRADES với n lệnh (win 7: −99992 = 8 lệnh; win 14: −99996 = 4 lệnh)
  — các window này `OOS_pnl/maxDD/WFE` bị V4 ghi 0 dù có lệnh thật (bug che số, fix ở [TASK-113](../../tasks/113-fitness-v41-do-du-metrics-mintrade-window-that.md)).
- `-100000−x` → TOO_MUCH_CAPITAL_LOCK với pctHeldOver7d=x% vượt cap 2.00% (win 3: 2.02% · win 6: 3.23%) — nhánh này
  chạy SAU khối thống kê nên pnl/maxDD trong bảng là số THẬT.
- `OOS_maxDD` trong bảng = USD tuyệt đối; % vốn = /35000 (verdict dùng %: worst = win 15, 10735/35000 = 30.7%).
- WFE = OOS_pnl / best_IS_pnl (win 15 WFE=8.87: OOS Q4-2025 nổ +15,775 trên IS 12 tháng ~+1,778 — 1 window kéo, đọc thận trọng).

## Độ ổn định gene qua cửa sổ (min..max best value)
- MIN_MOMENTUM_15M: 0.0228 .. 0.0494
- PREDICT_SYMBOL_RATE_MAX_THRESHOLD: 0.0518 .. 0.1964
- AI_DYNAMIC_MULTIPLIER: 1.2876 .. 1.9533
- AI_DYNAMIC_MIN: 0.1869 .. 0.4935
- HARD_RISK_LIMIT_4H: -0.2939 .. -0.0650
- MS_DOWN_BIG_AVG: -0.0509 .. -0.0236
- DCA_LOSS_BIG_DOWN: -0.2117 .. -0.1065
- DCA_TIME_BIG_DOWN: 3.1588 .. 8.0000
- DCA_TIME_BIG_Up: 15.0000 .. 29.9217
- RATE_PROFIT_STOP_MARKET: 0.0103 .. 0.0245
- TS_PROFIT_MULTIPLIER: 4.1672 .. 7.9041
- TS_DYNAMIC_K: 0.1003 .. 0.2977
- TS_MAX_GAP: 0.0425 .. 0.0800
- TS_MAX_GAP_WEAK: 0.0300 .. 0.0553
- TS_WEAK_MOMENTUM_THRES: 0.0040 .. 0.0079
- BUDGET_MARGIN_RATIO_1: 0.3185 .. 0.4942
- BUDGET_MARGIN_RATIO_2: 0.6000 .. 0.7630
- BUDGET_DIVIDER_2: 1.5984 .. 2.4531

> ⚠️ WFE<0.3 = overfit; WFE≥0.5 tốt. maxDD backtest hiểu nhẹ (chưa margin-call) → biên an toàn.
