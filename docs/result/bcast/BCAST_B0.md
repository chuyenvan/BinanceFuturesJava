# BCAST-B0 — khả thi kho backcast 2020-01 → 2021-06 (agent BCAST, 2026-10-12)

Pre-reg (NHÁP, chưa hiệu lực): `docs/prereg/PREREG_BACKCAST_RESERVOIR.md`. JSON `docs/result/bcast/BCAST_B0.json`. Script `research/analysis/bcast_b0_vision.py` (chỉ LIỆT KÊ bucket Vision, không tải giá). Không Kaggle, không sim, không PnL.

## Kết luận (rủi ro trước)
**RÒ RỈ ⇒ DỪNG trước B1, chờ MASTER.** Cả 3 họ model đóng băng đã train trên dữ liệu < 2021-07: gate 8 seed từ 2021-01-01 00:00 UTC, net015 f15 từ Tool1 2021-01, S1 từ 2021-04-01. Đoạn 2021-01..06 của kho không dùng được để xác nhận. Đoạn **2020-01-01 → 2020-12-31 UTC sạch về model**. Đề xuất P1 (PREREG §4): thu kho về 2020, cửa sổ chấm **2020-05-01 → 2020-12-31 +07** (~8 tháng, 25→80 symbol). Kho này yếu: universe nhỏ, OI NaN, chế độ 2020 khác DEV.

## 1. Vision `futures/um` (liệt kê 2026-10-12; 1 056 thư mục klines, 893 qua bộ lọc USDT live)
| Tháng | klines 1m | ∈ mapper 863 | fundingRate | aggTrades | ngoài mapper |
|---|---|---|---|---|---|
| 2019-09..12 | 0 | 0 | 0 | 0 | — |
| 2020-01 | 11 | 11 | 11 | 11 | |
| 2020-02 | 24 | 24 | 23 | 24 | |
| 2020-03 | 24 | 24 | 24 | 24 | |
| 2020-04 | 24 | 24 | 24 | 24 | |
| 2020-05 | 25 | 25 | 25 | 25 | |
| 2020-06 | 30 | 30 | 30 | 30 | |
| 2020-07 | 37 | 36 | 37 | 37 | LENDUSDT |
| 2020-08 | 43 | 42 | 43 | 43 | LENDUSDT |
| 2020-09 | 62 | 61 | 62 | 62 | LENDUSDT |
| 2020-10 | 71 | 70 | 71 | 71 | LENDUSDT |
| 2020-11 | 78 | 77 | 77 | 77 | LENDUSDT |
| 2020-12 | 80 | 80 | 80 | 80 | |
| 2021-01 | 86 | 86 | 86 | 86 | |
| 2021-02 | 93 | 93 | 93 | 93 | |
| 2021-03 | 106 | 105 | 106 | 106 | BTCSTUSDT |
| 2021-04 | 111 | 110 | 111 | 110 | BTCSTUSDT |
| 2021-05 | 114 | 113 | 113 | 113 | BTCSTUSDT |
| 2021-06 | 116 | 115 | 115 | 115 | BTCSTUSDT |
- Tháng có kline nhưng thiếu file fundingRate: QTUMUSDT 2020-02, LENDUSDT 2020-11, ICPUSDT 2021-05/06 (luật HO4: ở lại dữ liệu, loại khỏi giao dịch).
- metrics (OI/LS/taker) daily: **BTCUSDT từ 2020-09-01; 115/118 symbol còn lại từ 2021-12-01**; DOTECOUSDT, LENDUSDT không có ⇒ OI NaN toàn kho trừ BTC (khớp `DATA_EXTENT_SURVEY.md`).
- aggTrades monthly: có từ 2020-01 cho gần như mọi symbol (không dùng trong chuỗi HO4).

## 2. Model đóng băng — dữ liệu train (bảng đầy đủ ở PREREG §4)
- gate 8 seed: `train_ts_min` 2021-01-01 07:00 +07 cả 8 seed, `label_years` 2021–2025 (`manifest_gate.json`).
- net015 f15 `7921ceaf`: Tool1 bắt đầu `features_20210101_to_20210401.t1c`; fold dự đoán đầu 2022-01 ⇒ train expanding từ 2021-01 (log 08-14 gốc không còn trên đĩa — `~/claudedata` đã dọn; suy từ G3_X26_RECOVERY + manifest).
- S1 `af706dc6`: ledger T0 2021-04-01.
- Không model nào có dữ liệu 2020: store gate/ticker DEV bắt đầu 2021-01-01 (ticker 1 826 ngày = 2021-01-01..2025-12-31) ⇒ HPO/GA cũng không thể chạm 2020 qua store DEV.

## 3. Warm-up ⇒ cửa sổ chấm thực (nếu P1)
| Thành phần | Cần | Nguồn |
|---|---|---|
| kline Vision | bắt đầu 2020-01-01 (2019-12 không có) | §1 |
| HistoryManager (feature gate/Tool1 per-coin) | ring 2 048 phút ≈ 34 h | `HistoryManager.java:15` |
| feat_v2 (S1) | cửa sổ ≤ 30 ngày ⇒ ≥ 31 ngày | ADDENDUM-1 §5 ⇒ S1/bins có từ ~2020-02-01 |
| GateRollingRatio | buffer r ONLINE (cần sp từ bins), fallback 7 ngày, cửa sổ 90 ngày | `GateRollingRatio.java:29-32` ⇒ đủ 90 ngày ~2020-05-01 |
| pool S1 `nBars_72h ≥ 288` | 72 h nhìn trước ở mép cuối | dựng tới 2021-01-03 UTC |
| OI `oi_z` expanding | không áp dụng (OI NaN) | §1 |
⇒ **chấm 2020-05-01 00:00 → 2020-12-31 23:59 +07** (bộ đệm gate đầy như 2026 trong HO4). Tương đương "khởi lạnh" DEV (2021-07-01) thì sớm nhất 2020-02-08, nhưng khi đó 2020-02/03 (COVID) rơi vào lúc bộ đệm chưa đầy — không đề xuất. Sim kỹ thuật B2 (khi được dựng) dùng `TIME_RUN=20200101`, `SIM_END_DATE=20210101` (không phải 20210701).

## 4. Mapper
- Ngoài mapper 863: **LENDUSDT** (2020-07..11), **BTCSTUSDT** (2021-03..). Luật HO4 ⇒ drop + liệt kê, không cấp id. Nếu MASTER muốn giữ: id lỗ 752/753 (không symbol nào trong mapper 781/863/933 dùng) CHỈ trong bản mapper cục bộ của sim; assert duy nhất, < 1 000 (`HistoryManager.MAX_COINS`, `klineArray[1000]`); không ghi Aerospike 242. Cặp id trùng 843–850 (MAPAUD) là symbol niêm yết 2026-07 ⇒ không chạm kho.

## 5. Chưa làm (vì DỪNG)
B1 dựng, B2 md5 hai lần + sim kỹ thuật, B3 dataset Kaggle + `docs/plan/BACKCAST_RESERVOIR.md`. Kaggle: 0 kernel. Cache Oracle: chỉ `~/claude_master/1012/bcast/` (JSON liệt kê, < 1 MB).

## 6. Ước lượng B1 (nếu P1): 1 kernel exporter (như `ho4p1-x26-q*`, 13 tháng × ≤ 80 symbol ≈ 1/4 khối lượng 1 quý 2026) ~1 h; OI bỏ qua (NaN, chỉ BTC từ 09); chuỗi hạ nguồn 1 kernel; P3-DET = chạy 2 lần; 1 sim kỹ thuật. Tổng ~6 kernel-run.
