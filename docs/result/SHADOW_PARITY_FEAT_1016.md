# SHADOW_PARITY_FEAT_1016 — feature / p15 / gate: shadow ↔ backtest (MASTER 2026-10-16, audit-only)

Cách đo: dựng lại 33 feature gate theo đúng công thức export DEV (`research/analysis/devexport_202609.py`, bản sao vá mapper `~/claude_master/1016/parity/devexport_1016.py`: đọc `symbol_mapper` ns `ticker` 242 = 937 symbol, bản gốc đọc ns `test` cũ 863 symbol ⇒ sai breadth) từ kline/funding Aerospike 242 (`--md-inline`), ghép từng phút với `feat_dump` của shadow; chạy model gate `Model_Regressor_Return15M.onnx` (fold_20) trên cả hai vector. Script: `par_feat.py`, `par_gate.py`, `par_burst.py` (cùng thư mục).

## 1. Model + vector live: KHỚP
ORT trên vector live tái tạo `p15_out` của shadow: max|Δ| 5,6e-9 (cả c3 và c3b) ⇒ model, thứ tự feature, không scaler: đúng.

## 2. Cửa sổ yên 10-15 15:00 → 10-16 13:53 (+07), c3b 1 264 phút
- Khớp tuyệt đối (≥ 96 % phút, |Δ| ≤ 1e-6·(1+|x|)): momentum1M/5M/1H/4H/24H, trendStrengthETH, trendConsistency, volatility1M/15M/1H/24H, rsi14, volumeSpike, distMA20, lịch.
- Lệch có hệ thống nhưng nhỏ (rank corr ≥ 0,99): họ breadth — advanceDeclineRatio (lệch tương đối trung vị 1,6 %, p95 5,8 %), percentAboveMA20 0,75 %, marketBreadthStrength 1,0 %, basketMomentum15M 1,6 %, basketVolSpike 0,9 %; momentum15M (= marketDown15M) / momentumAcceleration / volatilityTermStructure khớp 44 % phút, lệch tương đối trung vị 5e-4; funding ×3 corr 0,95–0,97.
- p15: |Δ| trung vị 3,7e-9, p99 2,4e-4, max 1,5e-3. Không phút nào qua gate ở cả hai phía; 0 phút lật quyết định; phút gần ngưỡng nhất còn cách 0,75 pp.

## 3. Cửa sổ đợt 10-08 14:50 → 10-10 (c3b 3 426 phút) — LỆCH LỚN ĐÚNG LÚC HỆ VÀO LỆNH
- p15 |Δ| trung vị 1,4e-4, p99 2,7e-3, **max 1,32e-2**.
- **Phút 10-08 22:20 (đợt 24 chân):** live p15 **3,045 %** (≥ thr_min 2,28 % ⇒ n_pass = 24); offline **1,722 %** ⇒ backtest **KHÔNG vào**. advanceDeclineRatio live 0,169 vs offline 0,110; momentum15M −4,15 % vs −4,25 %.
- Các phút sau đó lệch hai chiều: 22:21 live 2,27 % vs 1,54 %; 22:24 1,57 % vs 2,09 % (advanceDecline 2,85 vs 0,47); 22:29 1,64 % vs 2,30 %; 22:37 1,85 % vs 2,40 %.
- Lật quyết định gate trong cửa sổ: 1 (chính đợt 22:20: live vào, backtest không).
- Dấu hiệu thời điểm: tick 22:21:06 (nến 22:20) mất **25 s** (`selector tick total=25083ms`), quyết định in lúc 22:21:31 ngay SAU một lần đọc ticker Aerospike 22:21:30 ⇒ nghi feature live dùng trạng thái dữ liệu trộn/mới hơn nến quyết định; thêm nữa ingest 242 settle nến sau +8 s trong khi tick chạy ở +6 s.

## 4. Kết luận
- Code feature + model live ≈ backtest khi dữ liệu đầy đủ và thị trường yên.
- Ở phút sập (đúng lúc hệ có lệnh), feature live — nhất là breadth — lệch lớn so với dữ liệu đã settle ⇒ p15 lệch tới ~1,3 pp ⇒ quyết định vào lệnh khác backtest. Đợt duy nhất của shadow #2 (10-08 22:20) là đợt backtest không có.
- CHẶN-TIỀN-THẬT cho release v1 cho tới khi khoanh được nguyên nhân (thời điểm dữ liệu vs code).

## 5. Việc tiếp (đề xuất)
1. Log mỗi tick: số symbol có nến phút M trong cache tại lúc tính feature + timestamp đọc dữ liệu (code nhỏ, sau cờ) ⇒ phân biệt "dữ liệu chưa settle" vs "code".
2. Tick quá hạn (vd > 10 s) ⇒ bỏ quyết định / tính lại đúng nến M (sửa ở live).
3. Đo lại cùng phép này trên c3 (K16) và 242 cho các phút sập 10-08/10-13.
4. Chưa đo: S1/selector (sel_dump vs offline), OI feature.
