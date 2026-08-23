# WFO HANDOFF — 2026-08-10 (đêm) — nối tiếp `wfo_handoff_2026-08-10_pm.md`

> Session đêm: kernel unf15 ERROR → tìm + fix **landmine 5** → re-push dataset → **kernel v2 RUNNING**.
> Đọc file pm trước để có bối cảnh đầy đủ (chẩn đoán universe filter, runbook §4 downstream).

## 1. LANDMINE 5 (mới) — glob per-year hardcode `.t1c*`
- Kernel `chuyendinh/selector-unf15-maxfav` v1 ERROR ở t=40s: `FileNotFoundError features_2021*.t1c*`.
- Nguyên nhân: `gen_funding_wf_predictions_1m.py` dòng 361 (`build_features_memmap`, vòng per-year) dựng glob
  `features_%s*.t1c*` — hardcode đuôi `.t1c`, trong khi features unf15 trên Kaggle là `.bin` (auto-giải nén từ
  `.bin.gz`). Features CÓ ĐỦ 2021-2026 (23 file), không thiếu năm.
- FIX: đổi thành `features_%s*` (khớp cả `.bin` lẫn `.t1c`, đồng bộ `TOOL1_GLOB` mà sel_kernel.py set).
  `resolve_files` trong tool1_col.py chỉ glob + loại `.part`, KHÔNG lọc theo đuôi → `.bin` được nhận, `read_tool1`
  tự detect format qua magic. Fix verified end-to-end trước khi chạy.

## 2. ⚠️ BÀI HỌC HẠ TẦNG — dir staging trên `C:\Users\pc\` KHÔNG bền
- `sel1m_code`, `sel1m_kernel_unf15`, `unf15_out` **biến mất** giữa session (sau khi bridge reconnect). Base FS
  còn (`_ora.bat` cũ còn) nhưng 3 dir kaggle-staging mất sạch → edit trực tiếp vào chúng KHÔNG bền.
- Nguồn thật của gen script `_1m` (26KB, có memmap) KHÔNG ở repo (repo `ml/training/gen_funding_wf_predictions.py`
  không có code memmap) và KHÔNG ở Oracle bản cũ (`/home/ubuntu/claudedata/...` chỉ 8880b, stale, không memmap).
  Bản 26KB thật CHỈ nằm trong **Kaggle dataset `chuyendinh/sel1m-code`**.
- Cách xử lý đã dùng: tải thẳng gen script từ Kaggle dataset (bản deploy thật) → fix trên đó → `kaggle datasets
  version` → verify tải lại. AN TOÀN NHẤT khi cần sửa code kernel: lấy từ Kaggle dataset, đừng tin dir C: local.
- ĐÃ BACKUP bản fix (26561b) lên Oracle `/home/ubuntu/claudedata/gen_funding_wf_predictions_1m.py` (thay bản stale)
  để `stage_code_sel1m.sh` (chạy trên Oracle, copy từ path này) dùng đúng nguồn cho lần sau.
- ⚠️ Kaggle CLI trên Windows lỗi path temp khi `kaggle datasets version -p <ABS_PATH>` → dùng `cd <dir> && ... -p .`.

## 3. TRẠNG THÁI HIỆN TẠI
- Dataset `chuyendinh/sel1m-code` đã có version mới (fix landmine5), status ready, verified live.
- Kernel **`chuyendinh/selector-unf15-maxfav` version 2 — RUNNING** (push ~23:24 Bangkok). Đã qua mốc crash 40s.
- Kernel dir tái tạo tại `C:\Users\pc\sel1m_kernel_unf15\` (sel_kernel.py + kernel-metadata.json), config y hệt bản pm
  (GRID_MIN=15, CHUNK_YEARS=1, FIRST_CUTOFF=20230101, PURGE_STEPS=288, WIN maxFav 0.06).

## 4. RUNBOOK NỐI TIẾP (khi kernel v2 xong) = §4 của handoff pm, tóm tắt:
1. `kaggle kernels status chuyendinh/selector-unf15-maxfav`. RUNNING→chờ. ERROR→`kaggle kernels output ... -p
   C:\Users\pc\unf15_out` đọc log, fix, re-push (nhớ landmine 1-5). COMPLETE→đếm predict_wf_*.bin (~14).
2. scp predict 2023-2025 → Oracle `/home/ubuntu/claudedata/predwf_unf15/`.
3. build_ds (WFO_CODE_SHA=8741f85154e04d57c48da9c55472cea7e55eed2a, WFO_FUNDING_PRED_DIR=predwf_unf15,
   WFO_SEL_HORIZON_IDX=0) → `wfo_ds_unf15clean`.
4. fanout mcp_tools-v3.py (tag unf15clean, JAVA_TOOL_OPTIONS=-Xmx16g, ...), chờ DONE=16.
5. verdict `WfoCoordinator report strategy_window` → **so vs +14,225** (kỳ vọng ~bằng = deploy-grade leak-free).
   Cập nhật `wfo_goforward_design §0`, báo Uni.

## 5. SCHEDULED TASK
- send_later `trig_015APpFkxiTCjXFA57XYnJGp` (bind session này) đã cập nhật nội dung = monitor kernel v2 →
  downstream. Sẽ tự check + reschedule nếu còn RUNNING.
