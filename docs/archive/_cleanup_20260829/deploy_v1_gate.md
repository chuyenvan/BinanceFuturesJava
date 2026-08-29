# Deploy v1 — WFO gate (fold_20) lên live (2026-08-17)

Runbook tái lập việc swap gate live reg_v3 -> gate WFO. **KHÔNG cần sửa code Java** (khác selector):
code path `OnnxInferenceManager` + `SinglePredictor` (scaler-optional) + `extractFeaturesV3Full` đã hỗ trợ
sẵn model raw. Align gate = thao tác artifact trên box, không có diff source. Runbook này LÀ artifact tái lập.

## Provenance model
- WFO gate = per-fold, train bởi `~/java/simulator/train_gate_fold.py` (XGBoost reg:squarederror,
  max_depth=4, n_estimators=150, lr=0.05). 21 fold: Oracle `~/claudedata/wfo_models/fold_0..fold_20/Model_Regressor_Return15M.onnx`.
- **fold_20** = fold cuối (train nhiều data nhất) = artifact deploy. 144,774 B, cùng batch (Aug 6 09:46)
  sinh `wfo_gate_pred.csv` -> Aerospike `ai_pred_market_gate_wfo` -> backtest `build_ds` đọc. Chính là gate của +878.

## Parity signature (verify TRƯỚC swap — bắt buộc)
1. Feature order: `train_gate_fold.py` V3FULL = copy chính xác `OnnxInferenceManager.extractFeaturesV3Full` (33 feat). Khớp tuyệt đối.
2. Input: `FloatTensorType([None,33])`. Output: 1 giá trị (predReturn15M).
3. **RAW, KHÔNG scaler** (comment train script: "XGBoost bất biến scale; OnnxInferenceManager chạy raw").
   -> reg_v3 có `Scaler_Return15M.onnx`; giữ scaler + thay model = feed input scaled vào model raw = SAI.
   -> phải VÔ HIỆU HÓA scaler để `SinglePredictor.fileExists(scaler)=false` -> feed raw.
4. Extractor `ComprehensiveMarketFeatureExtractor` dùng chung live + gate export -> giá trị feature khớp.
5. `predictAll` = p15M (Return15M) + pRisk4H (maxDrawdown4H) cùng 33-feat. Bỏ `Scaler_Return15M` CHỈ ảnh hưởng p15M;
   pRisk4H giữ `Scaler_maxDrawdown4H` -> risk path không vỡ (risk4H không dùng để gate nữa).

## Các bước (242, dir FILE_AI_PREDICTIONS = ../storage/ai_ml_data/ai_models_reg_v3)
```
# 1. Backup
cp -p Model_Regressor_Return15M.onnx  Model_Regressor_Return15M.onnx.bak_gatewfo_20260817   # 189MB reg_v3
cp -p Scaler_Return15M.onnx           Scaler_Return15M.onnx.bak_gatewfo_20260817             # 564B

# 2. Đưa fold_20 lên (Oracle -> local -> 242), verify size 144774
scp ubuntu@ORACLE:~/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx  ./fold20.onnx
scp ./fold20.onnx  root@242:$DIR/Model_Regressor_Return15M.onnx.new_wfo

# 3. Swap + disable scaler (stop bot trước)
bin/daemon.sh stop
mv -f Model_Regressor_Return15M.onnx.new_wfo  Model_Regressor_Return15M.onnx
mv -f Scaler_Return15M.onnx  Scaler_Return15M.onnx.disabled_wfo
bin/daemon.sh start
```

## Verify sau restart
- Log: `AI Brain (V3 Full features)`, `⚠️ Scaler missing: Scaler_Return15M.onnx` (xác nhận raw),
  `Loaded Regressor Model for futureReturn15M` + `maxDrawdownNext4H`, `All Models loaded successfully`, không exception.
- Tick lưới 15m: `market[15M:X% ...]` -> predReturn15M nằm đúng khoảng `wfo_gate_pred.csv` (~0.007).
  Deploy 2026-08-17: 16:30 tick -> predReturn15M=0.0093. PASS.

## Rollback
```
bin/daemon.sh stop
mv -f Model_Regressor_Return15M.onnx.bak_gatewfo_20260817  Model_Regressor_Return15M.onnx
mv -f Scaler_Return15M.onnx.disabled_wfo                   Scaler_Return15M.onnx
bin/daemon.sh start
```
