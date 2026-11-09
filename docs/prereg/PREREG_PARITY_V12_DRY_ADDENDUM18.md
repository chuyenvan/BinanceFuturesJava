# PREREG_PARITY_V12_DRY — ADDENDUM 18: phép BIG_DOWN-SEL (chọn leg BIG_DOWN của live phải trùng logic sim) (2026-11-10)

MASTER duyệt bản nháp (11-09). **Khai:** viết sau phát hiện R1: live r4t chọn top-2 BIG_DOWN theo `tier1Score` (net015 raw), còn
sim/B0 chọn theo S1-map (DEV: 89,7 % leg BIG_DOWN của sim là coin live không chọn). Harness v12 chưa có phép nào so với logic sim
ở tầng này. Log live 11-04..11-08: 0 sự kiện BIG_DOWN (chỉ có dòng khởi động `[CADENCE-SPLIT]`).

## 1. Phép BIG_DOWN-SEL (jar r4u trở đi)
- **Nguồn live:** mỗi sự kiện BIG_DOWN có dòng `[BIG_DOWN-SEL] <phút> level= n= pool= top=SYM=v,...` (r4u, `DetectEntrySignal2TradeNormal.bigDownSelectS1`).
- **Tập tính lại offline dùng logic S1-map của SIM** (`SimulatorMarketLevelTicker1MStopLoss:368-380` =
  `MarketBigChangeDetector.getTopSymbolArray(n, tickers, locked, bins S1-map)`), **không dùng logic live**:
  - Xếp symbolPred S1-map tăng dần, như TreeMap<Float> của sim. Giá trị symbolPred lấy từ GV-I offline của harness (`gv_off`).
  - Bỏ coin đang giữ: sổ c3 theo ADD1, cộng LEGACY đang giữ.
  - Lấy n coin đầu.
- **ĐẠT:** mọi sự kiện trong ngày có tập top-n live == tập offline, và không có ô KHÔNG ĐO ĐƯỢC.
- **XÁM:** lệch chỉ do hòa điểm ở biên hạng n/n+1 (|Δ| ≤ 1e-6 · max|v|), hoặc có giá trị trùng trong top (sim TreeMap mất 1).
  Hoặc có ≥ 1 sự kiện KHÔNG ĐO ĐƯỢC (thiếu S1-map hay thiếu giá trị offline). Ngày đó không được SẠCH hay SẠCH-T.
- **TRƯỢT:** có sự kiện mà tập top-n khác không do hòa điểm. Hoặc có sự kiện BIG_DOWN (`Market level change ... level: BIG_DOWN`) mà không
  có dòng `[BIG_DOWN-SEL]`. Có TRƯỢT thì dừng đếm G-MICRO (ADD11 §3).
- **Ngày không có BIG_DOWN:** "KHÔNG ÁP DỤNG (0 sự kiện)", trung tính, không chặn SẠCH. Ghi số sự kiện.

## 2. Kiểm một lần khi swap r4u (vì BIG_DOWN hiếm)
- Phát lại các sự kiện BIG_DOWN của DEV (printDone sim B0-A1, leg `BIG_DOWN`) qua `BigDownSelect.select` của jar r4u, chạy offline,
  với map symbolPred của sim tại phút đó. Tập top-2 phải trùng sim ở 100 % sự kiện, ngoại trừ ca hòa điểm.
- Nếu phải dựng nhiều (cần map S1-map lịch sử theo phút) thì được bỏ qua, nhưng phải ghi cách làm.

## 3. Áp dụng
- Từ ngày chạy trọn đầu tiên trên r4u (jar có `[BIG_DOWN-SEL]`). Ngày r4n/r4q/r4t không chấm phép này, chỉ đếm số sự kiện BIG_DOWN
  (ADD19 dùng số này cho (i)).
- (ii) và smoke của G-MICRO chuyển sang r4u: xem ADD19.
