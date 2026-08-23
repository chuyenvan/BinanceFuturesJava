# Reconcile: LIVE model = WFO last-fold selector (md5 proof) — 2026-08-23

## Đính chính lỗi nhận định (2026-08-23)
Trước đó tôi (Claude) nói "live dùng hệ khác WFO (ai_models_reg_v3)". SAI. Kiểm md5:
- Oracle `~/selector_kaggle_out/selector_wfo_4h.onnx` (=model_wfo_last_4h, selector fold cuối):
  md5 **f5152a578e3be4f61b784ab2843bad46**, 788710 bytes, Aug17.
- 242 live `storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx` (deploy 17/08):
  md5 **f5152a578e3be4f61b784ab2843bad46**, 788710 bytes.
→ BYTE-IDENTICAL. **Selector live = selector WFO fold-cuối.** User đúng.
Thư mục ai_models_reg_v3/ (Return1H/4H/24H, maxDrawdown4H/24H — Dec2025) là lớp regressor AI-prediction
PHỤ, KHÔNG phải selector. Model_Regressor_Return15M.onnx swap 17/08 (144KB, Scaler_Return15M.disabled_wfo)
là model 15M riêng, md5 8ec99757... (khác selector).

## Phân biệt THẬT còn lại (không phải bug — provenance cố hữu)
- Live = **1 selector đơn (fold cuối)** áp mọi dữ liệu realtime.
- Backtest WFO = **selector per-fold** (mỗi window tự train). 
- ⇒ "backtest live 2021→nay" = áp selector-deploy-đơn lên TOÀN lịch sử (deploy-model backtest),
  KHÁC walk-forward. Đây đúng là thứ đo "model live hành xử ra sao".

## Config LIVE thực tế (env.sh ĐÈ config.properties) — KHÁC canary
env.sh (/home/chuyennd/java/v_t_m/conf/env.sh):
  SELECTOR_RANK_TOPK=5, SIM_MIN_MOMENTUM_15M=0.008, SIM_RATE_PROFIT_STOP_MARKET=0.05,
  SIM_TS_PROFIT_MULTIPLIER=3.0 (arm~15, KHÔNG phải arm26=5.2185), TS_PRED_GAP=1 (predgap ON),
  SHADOW_NO_PUSH=false (real từ 21/08 16:30).
config.properties: CAPITAL_START=14000, NUMBER_ENTRY_EACH_SIGNAL=4, LEVERAGE_ORDER=1,
  RATE_PROFIT_STOP_MARKET=0.01 (BỊ env đè →0.05), RATE_TARGET=0.01, TIME_START=1714150800000 (2024-04-26).
⇒ LIVE = arm15 + predgap + K5 + $14k. Canary WFO tôi đang baseline = arm26 + DCA-off + $35k/100k. KHÁC NHAU.
Runbook rev5 §11 cũng flag "baseline chưa apples-to-apples (live arm15+predgap vs canonical arm26)".

## Backtest live 2021→nay — plan (khả thi, đúng hạ tầng)
1. Sinh prediction từ selector deploy đơn (selector_wfo_4h.onnx) trên feature toàn 2021-2026
   (GenerateSelectorPredictionsTool / SelectorExportSetTool có sẵn) → 1 pred set "deploy" (không per-fold).
2. Sim toàn 2021-2026 với config LIVE (arm15/predgap/K5/$14k/NUMBER_ENTRY=4) → equity + PnL + maxDD + bóc năm.
3. Đối chiếu vs WFO per-fold (deploy-model thường yếu hơn walk-forward — đo khoảng cách).
Xếp sau local full-18 canary (serialize 1 jobstore) trừ khi user ưu tiên trước.

## Trạng thái WFO trust (giữ nguyên, đã proven)
engine det, build det (funding md5 779e2f8e), data complete (1613/0/0), ticker frozen (d521edb0).
Kaggle fanout untrusted (unpinned ticker + flaky) → dùng LOCAL Oracle làm ground truth.
Local full-18 canary đang chạy (WFO_SMART_CACHE=0 + -Xmx16g chống thrash, DONE~10+/18, không thrash).
