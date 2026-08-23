# NHẬT KÝ THỰC THI MỨC 1 (fresh filtered 15m) — bắt đầu 2026-08-09 ~07:15 ICT

> Uni chốt: "dựng fresh filtered" = bước 1-2 của Mức 1. Chi tiết quyết định: `claude/wfo_muc1_decision_2026-08-08.md`.
> Lý do KHÔNG dựng lại Mức-0 gốc: môi trường 02/8 đã mất trên Oracle (dataset `wfo_ds_ret2wf_4h_ff` không còn,
> jar `binance-futures-preflight.jar` = symlink gãy). Chỉ còn bản Kaggle + `wf_pred_ret2wf`. Dựng fresh sạch hơn.

## Trạng thái hạ tầng (đo 09/08 ~06:20–07:15 ICT)
- Oracle SỐNG lại: SSH:22 ✅, Aerospike:3222 ✅. `symbol_lifecycle` = 698 symbol OK.
- CE (`ce.cmd`) chạm Oracle bình thường qua Desktop Commander.
- WFO jobstore vẫn trỏ box 226 (`103.157.218.226:3222 ns=ticker`) — dirty (16 window, 2 RUNNING stale
  −6 ngày của worker chết `instance-20260622-1647`, DONE=4). `wfo_fanout` reset trước khi chạy nên sẽ dọn.
- Đợt canonical-1m (636M) ĐÃ DỪNG: 2 trigger (launcher + verify/merge) đã xoá. 3 shard 2021/2022/2025 để tự xong, bỏ output.

## KẾ HOẠCH MỨC 1 (fresh filtered 15m)
1. **[ĐANG CHẠY] Label 15m** — `ce label_export .../wfo15m/label_ds_15m/funding_label_15m.csv 15 20210101 20260701 gatecount_gate_20260808.jar 12.0 4`.
   Job `label_export_funding_label_15m.csv`. Bắn 07:15 ICT (lần 1 fail vì thiếu dir output → đã `mkdir -p` → bắn lại 07:15:32, đang chạy OK). ETA ~30-60' (15m nhẹ hơn 1m ~15×). Verify by-số khi xong.
2. **tool1 15m CÓ FILTER** — `ExportFeaturesForPythonTool`, `FF_GRID_MIN=15`, KHÔNG set `FF_UNFILTERED` (=> chế độ EntrySignalFilter, ~20M dòng). Đây là "filtered" Uni muốn (khác canonical unfiltered).
3. **selector predict 15m** — `gen_funding_wf_predictions.py` trên Kaggle, `SELECTOR_GRID_MIN=15`, `FIRST_CUTOFF=20230101`, `CHUNK_YEARS` không cần (15m nhẹ). Ra `predict_wf_*.bin`.
4. **build_ds** — `WfoDataset.export` trên Oracle (market live + gate + predict_wf). ⚠️ Oracle repo không git → phải truyền `code_sha` tường minh (nếu không throw). `WFO_SEL_HORIZON_IDX=0` (4h). `WFO_SET_PRED=ai_pred_market_gate_wfo`.
5. **WFO fanout** — `ce wfo_fanout <ds> <jar> 1 42 2 0 muc1filt "<frozen_env>,WFO_HARNESS_FIX=true"`. n=1 frozen (rank-K8, giveback-floor, funding ON). Đọc verdict qua `wfo_report`/coordinator. N=30 confirm sau. ⚠️ jar frozen ĐÚNG chưa xác định — phải chốt trước bước 5 (grep env-knob trong jar fat 99MB thất bại; cần javap hoặc Uni chỉ jar).

## Landmine đã biết (đừng vấp lại)
- Node `label_export` KHÔNG tự `mkdir -p` dir output → phải tạo dir trước (đã sửa tay lần này).
- `bg_status` trả khối `result` CŨ lẫn `state`/`log_tail` MỚI → chỉ tin `log_tail` + `state.status`.
- Grid PHẢI đồng bộ: `LABEL_STEP_MIN=FF_GRID_MIN=SELECTOR_GRID_MIN=15`, lệch → join (symbol,ts) rớt ~93% âm thầm.
- `WFO_SEL_HORIZON_IDX` default code = 1 (12h); canonical cần 0 (4h) — nhớ override ở build_ds.
- Jar chạy WFO phải là bản có rank-K + WFO_HARNESS_FIX + funding + frozen-genome-inject; dùng nhầm = số sai âm thầm.

## Còn treo (STAGE sau, không chặn bước 1-3)
ExportFundingLabel exit-0-khi-BLOCKED (lần này fail loud exit1, tốt); jobstore trỏ 226 retired; code_sha=unknown ở build_ds.
