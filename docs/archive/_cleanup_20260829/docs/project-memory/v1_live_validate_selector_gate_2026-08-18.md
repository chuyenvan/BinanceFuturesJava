# Validate LIVE (242) selector + gate — 2026-08-18

Validate nhẹ live-side (Oracle bận chạy gate A/B matrix, không chạy được comparator đầy đủ). Đọc log + env + model + độ tươi OI.

## ✅ GATE — hợp lệ hoàn toàn
- predReturn15M live = **0.0085** (log rõ `Predict:{"return15M":0.008514577,"riskDrawdown4H":-0.015330672}`), nằm ĐÚNG dải backtest (~0.006–0.01, wfo_gate_pred.csv). 
- Lưới 15m chuẩn (tick 07:44/07:59/08:14 — cách nhau 15'). Model = fold_20 (144774B, Aug17 16:27) đúng.
- Gate threshold Min15M=0.80% (=0.008×scale) đúng. Gate là 33 market feature, KHÔNG phụ thuộc OI → không dính vấn đề OI.

## ✅ EXIT param — moveSL 0.05 vẫn active sau auto-restart
- Bot tự restart theo lịch mỗi ~4h (ThreadAutoRestartProgram, "Reset by Schedule 06:40"). pid 7030→17940.
- Restart qua daemon → env.sh giữ nguyên: pid 17940 có SIM_RATE_PROFIT_STOP_MARKET=0.05, SELECTOR_RANK_TOPK=5, SIM_MIN_MOMENTUM_15M=0.008. ✓

## ✅ SELECTOR — model + rank + CS-rank OK; đang produce score
- Funding_Classifier_Final.onnx (788KB, Aug17 08:19), rank-K5 env set, produce score per-coin mỗi tick (vd GPS 0.160, AKE 0.169...). Active.
- Raw OI ingest TƯƠI: OpenInterestIngestor2AerospikeNew ghi 3469 metric/697 symbol lúc 08:06. ✓ (đây là OI THÔ, không phải feature computed)

## ⚠️ SELECTOR — LỆCH PARITY: OI computed feature (oi_feat_*) STALE/NaN
- Selector canonical dùng 45 feature = 40 Tool1 + **5 OI** (oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy).
- 5 OI này ở live do `LiveOiFeatProvider.lookup` đọc set `oi_feat_*` trên 242, mà set đó do `ComputeOiFeat2Live242` (Oracle) sinh + push.
- **ComputeOiFeat2Live242 KHÔNG được schedule** (đã defer "wire as Java thread — mai"), không chạy gần đây (không log/cron/history/process trên Oracle). Chạy tay lần cuối ~Aug 17.
- LiveOiFeatProvider tol 2h → giờ Aug 18 08:00, cách lần push cuối >12h → **floorKey out-of-tol → trả NaN**.
- ⇒ Live selector đang chạy **40/45 feature (5 OI = NaN)** → **LỆCH backtest** (predwf train/predict với đủ 45 OI thật). XGBoost xử lý NaN như missing nên vẫn ra score, nhưng score ≠ backtest.
- (asinfo/aql trên 242 không dùng được để đo trực tiếp last-ts của set; kết luận dựa trên fact compute không schedule + không chạy — độ tin cao. Đo per-feature chính xác cần comparator.)

## KHUYẾN NGHỊ
1. **Đóng parity OI**: chạy + SCHEDULE `ComputeOiFeat2Live242` (đúng task defer "wire oi-compute as Java thread mỗi 15m trên Oracle"). Không có nó, selector live vĩnh viễn 40/45. Oracle đang bận matrix → chạy sau khi matrix xong, hoặc chấp nhận 2-process (RAM 23G, matrix ~14G — cân nhắc).
2. **Đo chính xác gap**: chạy `ProductionVsBacktestFundingComparator` trên Oracle (recompute feature backtest cho timestamp live gần đây, so từng feature) — QUEUE sau matrix. Cái này cho biết chính xác feature nào lệch bao nhiêu (kỳ vọng: 5 OI lệch lớn/NaN, phần còn lại khớp sau fix Part A CS-rank).
3. Gate KHÔNG cần làm gì (đã đúng).

## Tóm tắt 1 dòng
Gate live ✅ đúng. Selector live ✅ về model/rank/CS-rank nhưng ⚠️ **5 OI feature đang NaN vì compute OI chưa schedule** → cần bật/định kỳ ComputeOiFeat2Live242 để đạt full 45/45 parity.
