# Reconcile live↔backtest + model provenance (v1, 2026-08-16)

## Model production — XONG, verify đầy đủ
- `model_wfo_last_4h.ubj` (Jul 8 run, num_features=**45**, binary:logistic, train tới 2026-03, **LIFT 4h ~2.875×**, rankIC 0.29) → `selector_wfo_4h.onnx` (Oracle `/home/ubuntu/selector_kaggle_out/`).
- Verify: feature order = `f0..f39` (=convertFeaturesToArray, 40 Tool1) + `[oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy]` → **khớp chính xác** live `extractFeaturesToArray` (đã sửa 21→45, commit 663eed1).
- Output `[label, probabilities[batch,2]]`, `prob[i][0]=P(no-pump)` → live `preds[0]` sort tăng dần = chọn P(pump) cao nhất. **Đúng chiều.**
- Parity xgb↔onnx: max|diff| 4.5e-7. Script convert commit 92c8967 (`ml/training/convert_selector_to_onnx.py`).

## Reconcile — phát hiện: model đơn deploy ≠ per-fold backtest (cố hữu)
- Campaign +878 (`predwf_G015x26e`, Aug) chỉ xuất `predict_wf` **per-fold walk-forward**, KHÔNG lưu model đơn.
- Model deploy = `model_wfo_last` (fold cuối). Backtest WFO validate **phương pháp** selector; live dùng **1 model hiện tại**. Nhất quán phương pháp, không byte-identical — bản chất live vs walk-forward.
- **Quyết định v1**: dùng `model_wfo_last` (chính là WFO selector, đã validate qua phương pháp). Không retrain cho launch. Retrain tươi (all-data tới hiện tại) = cải tiến sau.

## Reconcile còn mở: feature runtime parity (việc step 4)
- Live `fundingExtractor` = `FundingDataCollectionManager.FundingFeatureExtractorV2`; WFO export dùng **CÙNG class** + `CoinRankManager.getTopCoin` + `ComprehensiveMarketFeatureExtractor`. → parity gần như by-construction.
- Rủi ro còn lại: **state buffer/warmup** khi chạy live realtime (funding history, market history) có thể khác lúc export batch.
- **Đóng triệt để**: Java harness — tại 1 timestamp lịch sử, chạy `fundingExtractor.extractFeatures` → 45 feature, so với feature WFO export cùng (symbol, ts). Live đã tự lưu feature ở `storage/data/predictionSymbol/{date}/{time}.features` (242) → dùng làm nguồn so. Đây là hạng mục step 4 (backtest chi tiết).

## Trạng thái v1 tổng
| Hạng mục | Trạng thái |
|---|---|
| Edge 2026 (Q1+Q2) | ✅ +808/+878 |
| Gate 0 exit | ✅ đóng (config hiện tối ưu) |
| Step 1 dọn rác | ✅ inventory (~20 param chết) |
| Step 2 ingress + OI fix | ✅ commit fc1ee32 |
| Step 3 feature 21→45 | ✅ commit 663eed1 |
| Step 3 model → ONNX | ✅ verify + commit 92c8967 |
| Reconcile model | ✅ (provenance rõ, dùng model_wfo_last) |
| Reconcile feature runtime | ⏳ cần Java harness (step 4) |
| Config align (K5, thresholds) | ⏳ nhỏ |
| Deploy (step 5, Uni) | atomic: jar module + onnx + config + restart |

## Deploy checklist (step 5)
1. Build jar từ branch `module` (có feature 45 + NUM_FEATURES=45).
2. Copy `selector_wfo_4h.onnx` → 242 `storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx`.
3. Set config gate canonical (SELECTOR_RANK_TOPK=5, MIN_MOMENTUM_15M, PREDICT_SYMBOL_RATE_MAX_THRESHOLD, AI_DYNAMIC_*).
4. Restart v_t_m. KHÔNG đè onnx mới khi jar cũ 21-input còn chạy (vỡ) — thay cùng lúc.
5. Chạy paper/size nhỏ + reconcile live-vs-sim trước khi tăng vốn.
