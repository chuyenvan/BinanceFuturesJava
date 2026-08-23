# Gate A/B qua WFO (leak-free, Kaggle fanout) — plan chốt 2026-08-17

Uni duyệt: A/B chạy trên Kaggle (Oracle 1 process), window win4–15 (2022–2025) canonical, tái dùng luồng
`wfo_ops_runbook_2026-08-13`. Mục tiêu: label nào cho gate PnL tốt nhất, so cả gate-off — dứt điểm câu hỏi
"gate có edge PnL không" bằng sim thật có phí+funding (thay proxy IC ở Phase 1).

## Sửa hướng quan trọng
3 model single ≤2025 đã train (~/claudedata/gatemodels/*) **KHÔNG dùng** cho A/B: chúng leaky khi áp lên
window 2022–2025 (train tới 20260101). A/B đúng phải per-fold leak-free qua `WFOGateRunner` (giống gate live
fold_20 đã deploy). Giữ 3 model đó chỉ để tham chiếu Phase 1.

## Mắt xích đã xác định (đọc code)
- `WFOGateRunner.main [start end oosMonths csvStore modelTmpDir outFile pyScript minTrainMonths]` — Oracle.
  - Pha1: `ExportGateDataset.replayToCsv` → featureStore RAM (per-minute, ~2.6M) + CSV (HIỆN chỉ label_oldbasket).
  - Pha2: 14 fold expanding, mỗi fold `runPythonTrain` (env DATA/CUTOFF/OUT_DIR, **KHÔNG có GATE_LABEL**) →
    train_gate_fold.py → ONNX → predict OOS từ RAM → ghi `wfo_gate_pred.csv` (cols: timestamp,predReturn15M,predRisk4H).
- `LoadWfoGatePredTool`: nạp csv → Aerospike set `ai_pred_market_gate_wfo`.
- `ExportWfoDataset` (build_ds): gộp market(live Aerospike)+gate(WFO_SET_PRED set)+selector predict_wf → wfo_ds.
- Fanout: `drive_exp.sh <tag> <hidx>` → 5 worker Kaggle (run_worker.py) → `WfoCoordinator report` → DONE_<tag>.txt.

## Code changes cần (2 file) + rebuild
1. `ExportGateDataset.replayToCsv`: emit thêm `label_ret15m`, `label_ret60m` (port `basketRetEnd` đã có ở
   ExportGate15mV2). Callback/CSV header mở rộng 3 label.
2. `WFOGateRunner`: (a) `runPythonTrain` truyền env `GATE_LABEL`; (b) refactor **replay 1 lần → loop 3 label ×
   14 fold** (mỗi (label,fold) train model riêng → ghi outFile riêng theo label + set riêng). Tránh replay 3×
   (replay là bottleneck ~30–45s/ngày). Output: wfo_gate_pred_{oldbasket,ret15m,ret60m}.csv.
3. Rebuild fat jar (IntelliJ mvn) → scp Oracle (verify_stage đếm field Configs tránh jar stale).

## Chạy (theo runbook)
- Oracle serial: WFOGateRunner (đã sửa) → 3 csv → LoadWfoGatePredTool 3× → set `ai_pred_market_gate_ab_oldbasket/ret15m/ret60m`.
- build_ds 3× (WFO_SET_PRED=<set>, WFO_SEL_HORIZON_IDX=0) → 3 dataset Kaggle (chỉ khác pred.bin gate; selector+market giữ).
- Fanout 4 nhánh: off (dùng dataset bất kỳ + worker SIM_MIN_MOMENTUM_15M=-1) / old / net15 / net60.
  Worker env canonical: SELECTOR_RANK_TOPK=5, SIM_MIN_MOMENTUM_15M=0.008 (0.008 cho nhánh có gate; -1 cho off),
  SIM_RATE_PROFIT_STOP_MARKET=0.05, SIM_APPLY_FUNDING=true, SIM_BREAKER_MODE=OFF, WFO_HARNESS_FIX=true.
  ⚠️ jobstore chung → fanout tuần tự (2 song song = đè verdict). autosnap trước reset.
- Verdict: DONE_<tag>.txt TOTAL_12w + posRatio(≥70%) + maxDD(≤50%), win4–15 apples-to-apples. Tự tính Sharpe/t/PF.

## Bẫy (từ runbook, đừng lặp)
- Jar stale (quên scp) = kết quả byte-identical baseline → verify_stage trước fanout.
- RAM Oracle: 1 batch/lần, free -g trước. Kaggle CPU 5 slot, fanout serial.
- Kernel false-COMPLETE ngay sau push → sleep 90s trước poll. datasets create ; version (vô điều kiện).

## Ước lượng
Nặng: 1 replay + 3×14 fold train/predict (Oracle) + 3 build_ds (upload 4.3GB/ds là nghẽn) + 4 fanout serial
(30–50′/fanout). Tổng nhiều giờ. Phase 1 đã gợi ý gate yếu → A/B này để XÁC NHẬN dứt điểm bằng PnL thật.
