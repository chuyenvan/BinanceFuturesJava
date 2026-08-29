# WFO V4.1 — VẾ C (leaked FULL universe) + BẢNG SO 3 VẾ (2026-07-05)

**Env:** Oracle local ns=test, DATA_DIR=wfo_dataset (leaked), jar task113 (38b503dd), N=30, fitness V4.1.
**Diễn tiến run:** nhiều đợt (2×9g OOM w2 76 lần → FAILED=0 nhờ lease/retry; reset máy 16:18 jobstore sống; chốt 1×16g cày 10 window cuối 0 OOM). Provenance: BAO_CAO_SANG_20260703.md.

# WFO STRATEGY — report

## VERDICT: ❌ FAIL/REVIEW

Ngưỡng pre-registered: WFE_median ≥ 0.5, %cửa-sổ-OOS-dương ≥ 70%, maxDD-OOS xấu nhất ≤ 50% vốn

## Tổng hợp
- Số cửa sổ DONE: 17
- % cửa sổ OOS dương: 76.5% (13/17)
- WFE trung vị: 0.259
- maxDD OOS xấu nhất: 44.0% vốn (abs 15401)

## Bảng cửa sổ
| win | OOS | IS_fit | OOS_fit | WFE | OOS_pnl | OOS_maxDD | OOS_calmar | trades | oosNote | reject |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 20220101..20220401 | 3.3207 | 1.0415 | 0.034 | 1298.4814 | 1246.7791 | 1.0415 | 688 | SUCCESS | 0/30 |
| 1 | 20220401..20220701 | 2.4287 | 3.4064 | 0.3465 | 9925.418 | 2913.7209 | 3.4064 | 2823 | SUCCESS | 0/30 |
| 2 | 20220701..20221001 | 5.7749 | -100000 | 0 | 0 | 0 | 0 | 0 | ZERO_TRADES | 0/30 |
| 3 | 20221001..20230101 | 4.7324 | 3.2095 | 0.2587 | 3231.2937 | 1006.7792 | 3.2095 | 1057 | SUCCESS | 0/30 |
| 4 | 20230101..20230401 | 6.1004 | -99999 | 0.00010 | 0.7882 | 0.1965 | 0.7882 | 1 | TOO_FEW_TRADES | 0/30 |
| 5 | 20230401..20230701 | 5.7949 | -100008.9219 | 0.2957 | 3883.1587 | 1749.9041 | 2.2191 | 370 | TOO_MUCH_CAPITAL_LOCK | 0/30 |
| 6 | 20230701..20231001 | 7.0361 | 0.1371 | 0.0459 | 324.3829 | 2366.3369 | 0.1371 | 167 | SUCCESS | 20/30 |
| 7 | 20231001..20240101 | 4.768 | 5.1388 | 0.2606 | 1844.0148 | 358.8429 | 5.1388 | 136 | SUCCESS | 22/30 |
| 8 | 20240101..20240401 | 5.5345 | 2.3911 | 0.9101 | 6092.0273 | 2547.7605 | 2.3911 | 787 | SUCCESS | 21/30 |
| 9 | 20240401..20240701 | 6.5252 | -100003.3047 | 0.3461 | 4977.6519 | 3401.1357 | 1.4635 | 1664 | TOO_MUCH_CAPITAL_LOCK | 9/30 |
| 10 | 20240701..20241001 | 7.3009 | 2.6998 | 0.2877 | 4383.0513 | 1623.4628 | 2.6998 | 1513 | SUCCESS | 1/30 |
| 11 | 20241001..20250101 | 7.9691 | 3.4483 | 0.3818 | 8488.7158 | 2461.7356 | 3.4483 | 1975 | SUCCESS | 0/30 |
| 12 | 20250101..20250401 | 11.1517 | 1.1295 | 0.2201 | 6549.1929 | 5798.3066 | 1.1295 | 1155 | SUCCESS | 0/30 |
| 13 | 20250401..20250701 | 7.3776 | 3.5235 | 0.0259 | 833.6787 | 236.6035 | 3.5235 | 84 | SUCCESS | 0/30 |
| 14 | 20250701..20251001 | 5.8919 | 4.5441 | 0.0102 | 278.6497 | 61.321 | 4.5441 | 50 | SUCCESS | 0/30 |
| 15 | 20251001..20260101 | 3.773 | 0.805 | 0.7444 | 12396.959 | 15400.5117 | 0.805 | 6012 | SUCCESS | 0/30 |
| 16 | 20260101..20260401 | 2.5077 | 1.4524 | 0.14 | 4273.7988 | 2942.5525 | 1.4524 | 974 | SUCCESS | 0/30 |

## Độ ổn định gene qua cửa sổ (min..max best value)
- MIN_MOMENTUM_15M: 0.0377 .. 0.0496
- PREDICT_SYMBOL_RATE_MAX_THRESHOLD: 0.0587 .. 0.1835
- AI_DYNAMIC_MULTIPLIER: 1.5567 .. 1.9958
- AI_DYNAMIC_MIN: 0.1110 .. 0.4935
- HARD_RISK_LIMIT_4H: -0.2829 .. -0.0772
- MS_DOWN_BIG_AVG: -0.0549 .. -0.0225
- DCA_LOSS_BIG_DOWN: -0.2057 .. -0.1055
- DCA_TIME_BIG_DOWN: 3.4329 .. 6.9157
- DCA_TIME_BIG_Up: 21.9307 .. 29.1828
- RATE_PROFIT_STOP_MARKET: 0.0126 .. 0.0245
- TS_PROFIT_MULTIPLIER: 4.6546 .. 7.8389
- TS_DYNAMIC_K: 0.1013 .. 0.2474
- TS_MAX_GAP: 0.0422 .. 0.0596
- TS_MAX_GAP_WEAK: 0.0481 .. 0.0598
- TS_WEAK_MOMENTUM_THRES: 0.0041 .. 0.0077
- BUDGET_MARGIN_RATIO_1: 0.3390 .. 0.4927
- BUDGET_MARGIN_RATIO_2: 0.6000 .. 0.7746
- BUDGET_DIVIDER_2: 1.6160 .. 2.4382

> ⚠️ WFE<0.3 = overfit; WFE≥0.5 tốt. maxDD backtest hiểu nhẹ (chưa margin-call) → biên an toàn.

---
# BẢNG SO 3 VẾ (pre-registered: docs/insights/WFO_PREREG_3WAY_V41.md)

| Vế | Universe | WFE_med | %OOS+ | worst maxDD | Verdict |
|---|---|---|---|---|---|
| A leak-free | ~9–34 coins/tick | 0.227 | 47.1% (8/17) | 30.7% | ❌ FAIL/REVIEW |
| B leaked-restricted | = symbol set A | 0.240 | 70.6% (12/17) | 32.7% | ❌ FAIL/REVIEW |
| C leaked full | ~78–545 coins/tick | 0.259 | 76.5% (13/17) | 44.0% | ❌ FAIL/REVIEW |

## Phân rã (thiết kế 3 vế cho phép tách 2 hiệu ứng):
- **Leak thuần (B−A, cùng coverage): +23.5 điểm %OOS-dương** (47.1→70.6), WFE +0.013 (≈0).
- **Coverage thuần (C−B, cùng leak): +5.9 điểm %OOS-dương** (70.6→76.5), WFE +0.019 (≈0); worst maxDD 32.7→44.0 (universe to → khoá vốn sâu hơn).
- ⇒ ~80% độ "đẹp" %OOS của run leaked cũ đến từ LEAK, ~20% từ coverage.
- **WFE 0.23–0.26 ở CẢ BA VẾ** ⇒ WFE thấp KHÔNG do leak, KHÔNG do coverage — là bệnh chung của tầng chọn-tham-số/chiến-lược (selection noise N=30, minTrades, regime). Đối chiếu IC: funding selector leak-free rankIC 0.344 ổn định 21/21 quý (model_quality_wfo_20260704.md) ⇒ nút thắt nằm ở CHUYỂN tín hiệu→PnL OOS, không nằm ở model funding.
- Đối chiếu khó khăn regime: 2022Q3 — C w2 ZERO_TRADES, funding hit_SEL rơi còn 42% (vẫn > universe +13đ): quý bear đáy, chọn giỏi vẫn thua.

## Việc mở ra từ kết quả:
1. N-noise (N=30 vs N=100) trên kaggle-file — định lượng selection noise trong WFE.
2. Market model IC leak-free (pred WF đã nạp set ai_pred_market_gate_wfo) sau export dataset v3 — so trần trên in-sample IC 0.60.
3. TASK-119 maxDD margin-call (worst 44% vế C sát ngưỡng 50% khi maxDD còn hiểu nhẹ).
