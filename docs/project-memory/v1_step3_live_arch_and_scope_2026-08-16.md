# Step 3 — Kiến trúc live thật + scope đã sửa (2026-08-16)

Nguồn: đọc source THẬT (E:\...\BinanceFuturesJava, branch module). Đính chính hiểu nhầm ở step 2.

## Đính chính step 2
Trước tôi nói "live không tính Tool1 feature" — SAI. Đúng là `collectData` (box ingest) chỉ thu raw. NHƯNG **trading app** (`DetectEntrySignal2TradeNormal` trong v_t_m) CÓ tính feature + chạy model per-symbol.

## Kiến trúc live (đã có sẵn khung selector+gate)
`DetectEntrySignal2TradeNormal.predictAllCandidates()`:
1. `basket = CoinRankManager.getInstance().getTopCoin(time)` — **y hệt backtest** feature extractor.
2. Mỗi symbol: `fundingExtractor.extractFeatures(time, dummyOrder, symbol2FinalTicker, marketData, basket)` → `FundingMarketFeatures` = **feature extractor live**.
3. `fundingBrain.extractFeaturesToArray(f)` → `float[]`; `fundingBrain.predictBatch(featureArrays)` → `preds[0]` (fail prob). Rank tăng dần (prob thấp = tốt). = **model selector per-symbol**.
4. Filter: `preds[0] > PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MAX` → reject.
5. Gate market-level: `aiBrain.predictAll(features)` → return15M/riskDrawdown4H; `AIRejectFilter.checkSignalDynamic(predict, symbolPred)` — **y hệt backtest gate**.

=> backtest + live **dùng chung repo + chung CoinRankManager/AIRejectFilter**. Khung selector+gate live đã tồn tại.

## Scope step 3 ĐÃ SỬA (nhỏ hơn nhiều so với "dựng service từ đầu")
1. **Feature parity** (quan trọng nhất): `fundingExtractor.extractFeatures` + `fundingBrain.extractFeaturesToArray` (`FundingMarketFeatures`) có tạo ĐÚNG 45 feature (40 Tool1 + 5 OI), đúng thứ tự, đúng công thức như WFO `ExportFeaturesForPythonTool.convertFeaturesToArray` không? → verify field-by-field. Nếu lệch → sửa extractor cho khớp.
2. **Swap model `fundingBrain`**: hiện load model cũ (reg_v3-era). Thay bằng **selector WFO** (XGBoost/ONNX từ campaign WFO). Cần: (a) tìm chỗ fundingBrain load model file, (b) format model WFO (XGBoost json) có nạp được qua fundingBrain không, hay cần convert sang ONNX.
3. **Khớp config gate**: `MIN_MOMENTUM_15M`, `PREDICT_SYMBOL_RATE_MAX_THRESHOLD`, `AI_DYNAMIC_*`, `SELECTOR_RANK_TOPK` → set đúng giá trị canonical WFO (K5, thr...).
4. **OI Infinity fix**: ✅ DONE (commit fc1ee32 trên module).
5. **Reconcile**: dump quyết định live (predictAllCandidates + gate) vs sim (SimulatorMarketLevelTicker1MStopLoss) cùng 1 timestamp/feature → phải khớp.

## Việc đọc tiếp (bước kế)
- `FundingMarketFeatures` (field) + `fundingBrain.extractFeaturesToArray` vs `convertFeaturesToArray` → parity.
- `fundingBrain` = class nào, load model ở đâu (file path) → điểm swap.
- Model WFO selector campaign hiện lưu format gì (XGBoost json từ Kaggle) → có cần convert.

## Git
Commit thẳng `module` (test). v1 release Uni đẩy master (live=master, module=test). OI fix đã trên module.
