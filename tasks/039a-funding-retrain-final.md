---
id: 039a
status: CANCELLED
owner: headless
depends_on: []
touches_live_process: false
writes_242_data: false
resource: kaggle
kaggle_slots: 1
checkpoint: false
max_retry: 2
report: docs/reports/039a.md
require_review: true
---

# TASK-039a: Retrain FINAL funding selector + xuất model artifact

## Mục tiêu
Chạy lại train code đã chốt (commit c0c4d11, seed cố định) để (1) có bản FINAL reproducible,
(2) **XUẤT MODEL artifact** cho TASK-039c generate dùng. KHÔNG đổi logic train (chỉ thêm save model).
Đây là "đóng băng version" funding selector v1.

## Bối cảnh (đã có, KHÔNG làm lại)
- Train code: `ml/funding_selector/train_funding_selector.py` (đã có SEED, SMOKE, REPORT_QUARTERS).
- 3 Kaggle dataset SẴN: `chuyendinh/funding-tool1-features`, `chuyendinh/funding-oi-percoin`, `chuyendinh/funding-label-full`.
- Kaggle mount path = `/kaggle/input/datasets/<user>/<slug>/` → header dùng glob đệ quy `/kaggle/input/**/...` (xem `ml/funding_selector/kaggle/kernel_header_per_horizon.py`).
- Kết quả v1 tham chiếu (results_v1/): 4h LIFT 2.58, 12h 1.82, 24h 1.54, 72h 1.26.

## Việc cần làm

### Bước 1 — Thêm SAVE_MODEL vào train code (append-only, KHÔNG phá logic)
Trong `run_one`, sau `clf.fit(...)`, thêm khối điều khiển bởi env `SAVE_MODEL=1`:
```python
if os.environ.get("SAVE_MODEL") == "1":
    clf.save_model(os.path.join(OUT_DIR, f"model_{HORIZON}.ubj"))          # xgb native, load lai bang xgb.Booster
    json.dump({"horizon": HORIZON, "seed": SEED, "feat": feat,
               "params": clf.get_params(),
               "win_threshold": WIN, "h_steps": H_STEPS[HORIZON],
               "n_train": int(len(tr)), "n_val": int(len(va)), "n_test": int(len(te)),
               "ts_train_max": int(tr.ts.max()), "ts_test_min": int(te.ts.min()), "ts_test_max": int(te.ts.max())},
              open(os.path.join(OUT_DIR, f"train_meta_{HORIZON}.json"), "w"), indent=2, default=str)
```
Commit thay đổi này TRƯỚC khi chạy (1 commit nhỏ "thêm SAVE_MODEL").

### Bước 2 — Build + push kernel `funding-final`
- Header (giống kernel_header_per_horizon.py) set: `HORIZONS="4h,12h,24h,72h"`, `SAVE_MODEL=1`, `SEED=42`, resolve path đệ quy, `OUT_DIR=/kaggle/working`.
- `kernel-metadata.json`: id `chuyendinh/funding-final`, kernel_type script, enable_internet false, 3 dataset_sources như trên.
- Push: `cd <dir> && kaggle kernels push -p .`

### Bước 3 — Monitor (BẮT lỗi, không chỉ chờ)
```bash
until s=$(kaggle kernels status chuyendinh/funding-final 2>&1); echo "$s" | grep -qiE "complete|error|cancel"; do sleep 60; done
```
Nếu ERROR → tải log, đọc, sửa, retry (tối đa 2 lần). KHÔNG bỏ qua lỗi.

### Bước 4 — Tải output + commit version
Tải `kaggle kernels output chuyendinh/funding-final -p <dir>`:
- `model_{4h,12h,24h,72h}.ubj` (4 model)
- `metrics_{H}.json`, `train_meta_{H}.json`
Copy vào repo `ml/funding_selector/models_v1/` + commit "TASK-039a: model funding selector v1 (4 horizon) + meta".

## OUTPUT FILE (rõ ràng)
| File | Nơi | Nội dung |
|---|---|---|
| `model_<H>.ubj` ×4 | Kaggle working → repo `ml/funding_selector/models_v1/` | model XGBoost native (load `xgb.Booster().load_model`) |
| `train_meta_<H>.json` ×4 | cùng trên | seed, params, feat list (45, đúng thứ tự), threshold, n rows, ts range |
| `metrics_<H>.json` ×4 | cùng trên | LIFT/z/rankIC/t_IC/baseline/PASS (như v1) |
| `docs/reports/039a.md` | repo | bảng 4 horizon + so với v1 (reproducible?) + kết luận |

## TIẾN TRÌNH theo dõi (ghi vào report khi chạy)
1. commit SAVE_MODEL — sha?
2. push kernel — version?
3. status theo thời gian (queued→running→complete) + thời gian chạy.
4. tải output — đủ 12 file (4×3)?
5. commit models_v1 — sha?

## NGHIỆM THU (pass/fail)
- [ ] Đủ 4 `model_<H>.ubj` + load lại được bằng xgb (sanity: `Booster().load_model` không lỗi).
- [ ] `feat` trong train_meta = đúng 45 feature đúng thứ tự (f0..f39 + 5 OI).
- [ ] metrics FINAL khớp v1 trong sai số nhỏ (LIFT lệch < 0.05 mỗi horizon) → CODE REPRODUCIBLE. Nếu lệch lớn → FAIL, báo người (code/data không ổn định).
- [ ] Đã commit models_v1 + report.

## Kiểm soát tài nguyên
- Dùng 1 Kaggle slot. TRƯỚC khi push: kiểm `kaggle kernels status` các kernel đang chạy (val-s42/s7, sel-*) — nếu đang chiếm ≥5 slot thì CHỜ, không push chồng.
- KHÔNG đụng 226/live. Read-only Kaggle dataset.
