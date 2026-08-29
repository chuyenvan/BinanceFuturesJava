# v1 live deploy — WFO gate (fold_20) lên live (2026-08-17)

Đóng nốt Gate 1 / Gap 1 phần GATE (selector đã xong trước). Sau deploy: cả selector + gate trên live = model WFO, khớp backtest.

## WFO dùng gate nào (đã truy tận gốc)
- Gate WFO = per-fold, train bởi `~/java/simulator/train_gate_fold.py` (XGBoost, expanding). 21 fold: `~/claudedata/wfo_models/fold_0…fold_20/Model_Regressor_Return15M.onnx`.
- **fold_20 = fold cuối** (train nhiều data nhất), 144,774 B, Aug 6 09:46 — cùng batch sinh `wfo_gate_pred.csv` (102MB) → `LoadWfoGatePredTool` nạp Aerospike `ai_pred_market_gate_wfo` → backtest `build_ds` đọc. ⇒ fold_20 chính là model gate của backtest +878.
- Trước đây nhầm `gate_model_v2` (Jun 2025) là gate WFO — SAI, đó là experiment cũ.

## Vì sao trước đó chưa lên live
Chỉ mới swap selector; gate chưa động. Live chạy gate CŨ `ai_models_reg_v3/Model_Regressor_Return15M.onnx` (Dec 2025, 189MB) + `Scaler_Return15M.onnx`.

## Signature parity (verify trước khi swap — KEY)
- `train_gate_fold.py` khai báo: feature order = **V3FULL copy chính xác từ `OnnxInferenceManager.extractFeaturesV3Full`** (33 feat) → thứ tự khớp tuyệt đối. Input `FloatTensorType([None,33])`.
- **"KHÔNG scaler (XGBoost bất biến scale; OnnxInferenceManager chạy raw)"** → fold_20 ăn feature RAW.
- Live `SinglePredictor` áp scaler NẾU file tồn tại. reg_v3 có `Scaler_Return15M.onnx` → nếu giữ scaler + thay model = feed input đã scale vào fold_20 = SAI. ⇒ phải BỎ scaler.
- Feature extractor `ComprehensiveMarketFeatureExtractor` dùng chung 2 phía (live `:623` + gate export `ExportGate15mV2`/`GenerateGate15mV2Predictions`) → giá trị feature khớp.
- `predictAll`: p15M (Return15M) + pRisk4H (maxDrawdown4H) dùng chung 33-feat V3Full. Bỏ `Scaler_Return15M` chỉ ảnh hưởng p15M; pRisk4H giữ scaler riêng `Scaler_maxDrawdown4H` → risk path KHÔNG vỡ (risk4H vốn không dùng để gate nữa).

## Thao tác deploy (242, dir `../storage/ai_ml_data/ai_models_reg_v3`)
- Backup: `Model_Regressor_Return15M.onnx.bak_gatewfo_20260817` (189MB) + `Scaler_Return15M.onnx.bak_gatewfo_20260817` (564B).
- Kéo `fold_20/Model_Regressor_Return15M.onnx` (Oracle) → local → scp 242. Size khớp 144,774.
- `mv new_wfo → Model_Regressor_Return15M.onnx`; `mv Scaler_Return15M.onnx → Scaler_Return15M.onnx.disabled_wfo`.
- daemon stop/start. Bot pid 26230 (16:28).

## Verify
- Init: `AI Brain (V3 Full features)`, `⚠️ Scaler missing: Scaler_Return15M.onnx` (xác nhận feed RAW), `Loaded Regressor Model for futureReturn15M` + `maxDrawdownNext4H`, `All Models loaded successfully` — không exception.
- Tick 16:30 (đúng lưới 15m): `market[15M:0.93% Risk4H:-1.74%] Min15M:0.80%` → **predReturn15M=0.0093**, nằm đúng khoảng wfo_gate_pred.csv (~0.007) → raw path đúng, không lệch feature. Gate bind thật (reject 5 coin).

## Rollback
`mv .bak_gatewfo_20260817 → Model_Regressor_Return15M.onnx` + `mv Scaler_Return15M.onnx.disabled_wfo → Scaler_Return15M.onnx` + restart.

## Trạng thái Gate 1 sau deploy
- Signal source (Gap 1): selector ✓ + gate ✓ = cả 2 model WFO khớp backtest.
- Còn lại: reconcile per-trade (Gap 2, cần chạy comparator trên Oracle — 242 hết RAM), config NUMBER_ENTRY_EACH_SIGNAL/CAPITAL_START (Gap 3).
