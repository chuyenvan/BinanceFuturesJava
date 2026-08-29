# WFO — recipe dữ liệu train + khoảng vênh go-live (2026-08-16)

Doc này chốt CHÍNH XÁC dữ liệu dùng để train trong WFO đã ra kết quả canonical (G015-K5), và phân tích chỗ go-live có thể vênh. Viết để nghiên cứu, không phải log thao tác.

## 0. Phát hiện quan trọng (đảo ngược nhánh regen)
- `predwf_G015x26e` có **18 fold** `predict_wf_20220101 … predict_wf_20260401`, cùng sinh 1 lô **2026-08-14 15:03–15:05**.
- Fold **2026Q2 (`predict_wf_20260401`) ĐÃ TỒN TẠI và hợp lệ**: 4.89M record, cột **4h = preds thật (0 NaN)**; 12h/24h/72h = NaN **đúng thiết kế** (WFO đọc `WFO_SEL_HORIZON_IDX=0` = chỉ 4h).
- ⇒ Việc regen selector cho 2026Q2 (chuỗi Kaggle v11–v20) là **nhánh cụt**. Code regen train **cả 4 horizon** (H_LIST hardcode) → gấp 4 RAM = đúng thủ phạm OOM. Fold gốc chỉ train 4h nên nhẹ.
- ⇒ Regen còn **tạo vênh**: fold gốc = expanding 2021→cutoff, 4h; fold regen = 2.5y (2024–2026) + 4 horizon. Không đồng nhất với 17 fold kia.

## 1. Selector — dữ liệu train mỗi fold (đây là "model" đi cùng WFO)
- **Lưới:** 15m. **Purge:** 72h. **Horizon dùng:** chỉ **4h** (idx 0). **Nhãn:** `y = (maxFav_4h >= 0.06)` — binary, chỉ dùng `maxFav`, bỏ maxAdv/tHit*/retEnd. **Gate threshold train:** NET_THR=0.015.
- **Kiểu WFO:** expanding walk-forward. Fold có cutoff C ⇒ **train = [2021-01 .. C−72h]**, **OOS = [C .. C+3 tháng)** disjoint. Leak-free.
- **Features (45 cột):** 40 per-coin từ Tool1 (`ExportFeaturesForPythonTool`, extractor 40-channel: momentum/dominance/RSI/funding market+basket #1-21, funding sâu per-coin #22-26, volume #27-28, cấu trúc giá #29-32, cross-sectional rank #33-35, microstructure 1m #36-40) + 5 OI (`oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy`) merge_asof theo (symId, ts) tol 2h.
- **Model:** XGBoost hist, max_depth=5, lr=0.05, subsample=0.8, colsample=0.8, min_child_weight=20, scale_pos_weight theo base-rate, eval=auc.

### Bảng expanding (OOS = range file; train = 2021-01 .. cutoff−72h)
| Fold (cutoff) | OOS quý | OOS record | Train ~ (năm) |
|---|---|---:|---|
| 20220101 | 2022Q1 | 1.12M | 2021 (~1y) |
| 20230101 | 2023Q1 | 1.30M | 2021–2022 (~2y) |
| 20240101 | 2024Q1 | 2.14M | 2021–2023 (~3y) |
| 20250101 | 2025Q1 | 3.06M | 2021–2024 (~4y) |
| 20260101 | 2026Q1 | 4.59M | 2021–2025 (~5y) |
| **20260401** | **2026Q2** | **4.89M** | **2021–2026Q1 (~5.25y)** |
(record OOS tăng đơn điệu do số coin sống tăng theo thời gian.)

## 2. Gate (layer độc lập)
- Feature KHÁC hẳn selector: 33-channel **market-level** (`ComprehensiveMarketFeatureExtractor`), không per-coin. Cũng expanding per-fold (`train_gate_fold.py`, ONNX). Label lấy `predRisk4H` từ set cũ; `predReturn15M` train lại. Gặp selector chỉ ở `build_ds`.

## 3. Backtest WFO (fanout) — KHÔNG train
- `WfoDataset.java` (Oracle) gộp: market_data (live Aerospike) + gate pred (live Aerospike `ai_pred_market_gate_wfo`) + `predict_wf_*.bin` (từ Kaggle). Worker sim K5 + moveSL0.05 + fee 0.1% + funding ON + 1x. Ra `wfo_strategy_window.md`.

## 4. Go-live vênh với WFO ở đâu (câu hỏi của user)
Go-live = train 1 model trên toàn lịch sử tới hiện tại rồi deploy. Về nguyên tắc = fold cuối của expanding-WFO kéo dài thêm ⇒ **đồng nhất NẾU giữ nguyên recipe**. Các nguồn vênh THẬT cần canh:
1. **Recipe phải trùng khít:** grid 15m, 40+5 feature (đúng extractor), nhãn maxFav_4h WIN=6%, purge 72h, XGB params, NET_THR 1.5%, chỉ 4h. Regen 2.5y/4-horizon là ví dụ vênh.
2. **Feature parity export-vs-live:** WFO train trên feature EXPORT ra file (snapshot Aerospike qua Tool1). Go-live đọc feature TÍNH LIVE. Nếu code extractor live ≠ code export ⇒ vênh âm thầm (cùng tên feature, giá trị lệch). Đây là rủi ro tinh vi nhất.
3. **Gate parity:** gate live phải trùng gate trong build_ds.
4. **Data coverage:** blocker 2026Q2 hiện tại KHÔNG phải selector mà là market_data+funding dừng ~2026-06-07 (canonical doc) + fold OOS kết thúc 2026-06-30 16:45 < 2026-07-01 ⇒ window 2026Q2 chưa sinh. Fix = rebuild market_data_object→2026-08 (ExportMarketData2File) + nới buildJobs OOS lệch <1 ngày. KHÔNG cần đụng selector.

## 5. Việc đúng cần làm (thay cho regen)
1. Rebuild market_data_object + funding tới 2026-08 (ExportMarketData2File — cần lệnh/args từ user).
2. Nới buildJobs cho OOS lệch <1 ngày (nhận fold kết thúc 2026-06-30 16:45).
3. Re-fanout G015-K5 tag mới, xác nhận window 2026Q1 + 2026Q2 vào, in PnL từng quý.
4. Nếu muốn train full 2021-2026 lại (vd đổi recipe): sửa selector chỉ train 4h (HORIZONS lọc H_LIST) ⇒ ~1/4 RAM ⇒ full lịch sử lọt Kaggle 32.9GB, không cần cắt năm.
