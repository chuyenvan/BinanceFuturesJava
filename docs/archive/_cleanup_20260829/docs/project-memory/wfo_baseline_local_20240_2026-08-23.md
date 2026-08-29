# BASELINE WFO reproducible ĐẦU TIÊN (local ground-truth) — 2026-08-23

## KẾT QUẢ: FULL_16w = 20240.8 (14/16 window dương = 88%)
Chạy local trên Oracle (WfoWorker tuần tự, WFO_SMART_CACHE=0 + -Xmx16g, KHÔNG thrash, KHÔNG Kaggle).
Config = CANARY: arm26 (TS_PROFIT_MULTIPLIER=5.2185) + DCA-off + K5 + nSamples=1 + $35k.
Data: ticker frozen local d521edb0 (verify đủ 1613 ngày 1440'), ds_base funding md5 779e2f8e (=G015).
Determinism + build + data ĐÃ PROVEN → số này reproducible.

Per-window (oosPnl | trades | note):
w00 2022Q1 854.6|115|caplock ; w01 2022Q2 2681.7|388 ; w02 2022Q3 419.1|39 ; w03 2022Q4 159.6|165
w04 2023Q1 463.7|49 ; w05 2023Q2 198.7|95 ; w06 2023Q3 663.9|52 ; w07 2023Q4 1429.5|98
w08 2024Q1 2659.3|212 ; w09 2024Q2 1223.3|256 ; w10 2024Q3 2248.2|146 ; w11 2024Q4 1356.3|248
w12 2025Q1 -371.9|468 BURN ; w13 2025Q2 1356.5|172 ; w14 2025Q3 -963.2|64 BURN ; w15 2025Q4 5861.5|758
w16 2026Q1 + w17 2026Q2: FAIL-FAST (thiếu ticker 2026-03-02+; data ends 2026-03-01) → LOẠI hợp lệ, KHÔNG phải bug.
(Nên đặt WFO_MAX_OOS_DATE<=20260301 để chỉ tạo window có đủ ticker.)

## PHÁT HIỆN LỚN: 10k (Kaggle) là ARTIFACT do ticker Kaggle thiếu; ~20k mới ĐÚNG
- Local (ticker verify đủ) 16w = 20240.8 ≈ aerospike baseline cũ 19840.
- Kaggle file-mode 18w = 9936/10502 (~10k). Cùng config arm26/DCA-off + cùng funding md5 779e2f8e + nSamples=1.
- Khác biệt DUY NHẤT = TICKER (local frozen-verified vs Kaggle datasets). ⟹ **Kaggle ticker thiếu/khác kéo PnL
  xuống ~2×**. Kaggle unpinned ticker không chỉ gây drift 0.3% per-window mà làm SAI HẲN tổng (~10k thay vì ~20k).
- ⟹ Đảo lại kết luận trước: 19840 KHÔNG phải "aerospike thổi phồng"; nó gần số thật. Cái sai là Kaggle-file ~10k.
- Band canary [18000,21500] hoá ra HỢP LÝ với ticker đúng (20240 nằm trong band!). Guard fail suốt là vì
  chạy trên Kaggle-ticker-thiếu (~10k, ngoài band) — đúng ra guard đang bảo vệ (báo "harness không sound").

## Việc tiếp (cross-val matrix, serial 1 jobstore)
(A) Kaggle 12/3 PIN-TICKER (upload ticker verified d521edb0 lên Kaggle + checksum gate) → phải ra ~20k
    (xác nhận Kaggle-ticker là thủ phạm). Chạy 2-3 run độc lập → per-window khớp local.
(B) Local 4yr-train expanding-capped: OOS 3mo vs 1mo (recompile StrategyWfoTask JAR COPY: MIN_TRAIN=12,
    trainStart=max(dataStart,oosStart-48mo)). So %OOS-dương/WFE/maxDD 3mo vs 1mo.
(C) Backtest LIVE 2021→nay: selector deploy đơn selector_wfo_4h (md5 f5152a57, =live) + config live
    (arm15/predgap/K5/DCA-on/$14k/NUMBER_ENTRY=4) → đánh giá model đang trade. KHÁC canary.
Bảng cross-compare per-window: local vs Kaggle-pinned vs live-config.

## Lưu ý chiến lược (thesis project: pump+lướt, đuôi maxDD)
- 2022-2024: 12/12 window dương, ổn định.
- 2025 CHOPPY: w12 -372 (BURN, 468 trades — over-trade lỗ), w14 -963 (BURN) — 2 quý cháy; nhưng w15 +5862 (758 trades) bù lại. 
  → Đuôi rủi ro tập trung 2025 (regime khó), khớp lo ngại "ăn ít khi thường, cháy khi regime xấu".
- Artifacts Oracle: ~/localbase/{RESULT2.txt, REPORT_final16.md, BASELINE.txt, worker2.log}.
