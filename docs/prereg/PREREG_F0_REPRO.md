# PREREG_F0_REPRO — tái lập pipeline dự báo selector (DEV ≤ 2025-12-31)

Ngày: 2026-09-29. Owner: Uni. Task: **F0** — tái lập được pipeline dự báo selector (điều kiện
tiên quyết cho tối ưu features/label và holdout). Kế thừa blocker đã phát hiện trong
`docs/plan/E3_HOLDOUT_2026_PREP.md` (E3 `24c1aeec`): (a) `CLOSES_1H.bin` KHÔNG có generator;
(b) `predwf_G015x26` (bins net015 dùng trong sim R4) tưởng KHÔNG tái lập được.

**Phạm vi: CHỈ DEV (≤ 2025-12-31). KHÔNG dùng dữ liệu/kết quả 2026. KHÔNG xoá/ghi đè data dir
đang dùng (ghi ra thư mục mới `/home/ubuntu/f0_repro/`). KHÔNG chạm 242. KHÔNG đọc key/secret.**

---

## 0. Đầu vào đã có (kiểm kê 2026-09-29)

| đầu vào | đường dẫn | trạng thái |
|---|---|---|
| `CLOSES_1H.bin` (tham chiếu, KHÔNG ghi đè) | `/home/ubuntu/java/fsrun/CLOSES_1H.bin` | sha256 `24fd3e93f90a8f9aecb6866ce30e9bd9c8890d34b327ed048772f0df2b4d94b5` |
| symbol map | `/home/ubuntu/selector_pred_out/symbol_map.csv` (782 dòng, symId 1..789) | ✅ |
| model G015 gốc (18 fold) | `/home/ubuntu/claudedata/predwf_G015/model_f{0..17}_4h.json` | ✅ |
| bins G015x26 gốc (16 fold) | `/home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin` | ✅ |
| Tool1 feature 15m | `/home/ubuntu/ds_feat15m/features_*.t1c.gz` | ✅ |
| OI percoin | `/home/ubuntu/claudedata/oi/oi_percoin_full.bin` | ✅ |
| label .pb | `/home/ubuntu/label_15m/funding_label_*.pb` (23 file) | ✅ |
| gate p15 | `/home/ubuntu/claudedata/wfo_gate_pred.csv` | ✅ |
| Aerospike funding | `127.0.0.1:3222` (asd đang chạy) | ✅ |

Môi trường: python 3.10.12, numpy 2.2.6, pandas 2.3.3, xgboost 3.2.0, pyarrow 25.0.1.

---

## 1. VIỆC 1 — kiểm kê chuỗi build (không tính số kết quả, chỉ ghi provenance)

Ghi vào `docs/runbooks/PRED_PIPELINE_REPRO.md` + tài liệu đi kèm. Mỗi artifact: script/commit
sinh ra, ngày, sha256, có chạy lại được không. Các artifact: `predwf_map_s1a2_x1`,
`pred_s1a2x1.parquet`, `predwf_G015x26`, `CLOSES_1H.bin`.

---

## 2. VIỆC 2 — generator `CLOSES_1H.bin`

**Định dạng (đo trực tiếp + đọc reader Java, KHÔNG đoán):** bản ghi 14 B big-endian
`[ts>i8][symId>i2][close>f4]`; `ts = open_time + 3600000` (close time nến 1h); trong cùng `ts`,
symbol xếp alphabet theo tên; 0 trùng khoá `(ts, symId)`; 627 symId; 10 322 386 rec.

**Nguồn:** Binance Vision futures UM kline 1h, tháng 2021-01..2025-12. Universe = 627 symId
thực sự có trong file tham chiếu, map qua `symbol_map.csv`. Parse close = `float64(str) → float32`
(y hệt `fs_dl.py` đã đo khớp sai số 4.14e-08 = float32 rounding).

**Cổng (quyết định):** `sha256(OUT) == 24fd3e93…`. **FAIL ⇒** tìm record đầu tiên khác, báo rõ
độ lệch (ts/sym/close), KHÔNG sửa file đang dùng. Ghi ra `/home/ubuntu/f0_repro/CLOSES_1H.bin`.

---

## 3. VIỆC 3 — tái lập `predwf_G015x26` (16 fold, DEV)

**Phương pháp:** predict từ 18 model gốc đã lưu bằng `research/pipeline/g015x26_train.py`
(recipe chốt từ log gốc + model JSON — xem `docs/experiment/G3_X26_RECOVERY.md` §4). Nhãn
`retEnd_4h > 0.015` (net015), 45 feature, XGB 400 cây / depth 5 / seed 42 / hist, WFO expanding
purge 72h, 16 cutoff `20220101..20251001` (train < cutoff, dự báo OOS 3 tháng kế tiếp).

**So sánh từng fold vs bins gốc** (ghep theo khoá `(ts, symId)`): số record, khoá trùng,
spearman (rank correlation), rank-IC, `max|d|`, **% giá trị float32 bit-identical**.

**Ngưỡng PASS:** spearman ≥ 0.999 VÀ `max|d|` ≤ 1 ULP (1.192e-07). **KHÔNG đòi byte-identical**
(pipeline gốc dùng `sort_values("ts")` = quicksort không ổn định, thứ tự dòng trong cùng ts là
tuỳ ý — khiếm khuyết của pipeline gốc, không phải mất input).

**Ghi rõ dự kiến:** G3 (`docs/experiment/G3_X26_RECOVERY.md`) đã đo spearman 1.00000000,
max|d| 1.192e-07 trên 16/16 fold. Việc này chạy lại để (i) xác nhận độc lập, (ii) bổ sung
**% bit-identical** mà G3 chưa báo.

---

## 4. VIỆC 4 — đo độ nhạy của sim R4 với bins tái lập (ĐIỀU KIỆN)

**Điều kiện kích hoạt:** nếu `predwf_G015x26` tái lập KHÔNG byte-identical (dự kiến đúng do
1 ULP + sort), thì chuỗi bins map tái lập sẽ khác bản đang dùng → kích hoạt sim.

**Chuỗi (DEV, Oracle, Python ≤ 6 GB, `nice -n 10`):**
1. `x1_gates.py g1` → feat_v2_x1 (feature 45 + S1 9 feat).
2. `x1_ledger.py build` → cand_dev_x1.
3. `x1_s1_rank.py 2x1` → pred_s1a2x1.parquet (S1 16 fold, CPU seed 42).
4. `x1_build_map.py s1a2x1` (dùng `predwf_G015x26` **tái lập** ở việc 3) → `predwf_map_s1a2_x1` tái lập.

**Sim R4 (Kaggle, `TICKER_SOURCE=file`, profile `r4_kg0_k16_f015_g155.properties`, bundle
`chuyendinh/sim-x1-2021-bundle` + overlay):** chạy với `WFO_FUNDING_PRED_DIR` = bins map tái lập.

**So sánh với R4 gốc `06fd6e9a…`:** md5 `printDone.csv`, `n`, equity, tỷ lệ trùng khoá `(sym,start)`.
Ngưỡng đọc: nếu chỉ lệch md5 (do 1 ULP + thứ tự) mà n/eq/trùng-khoá gần như nguyên vẹn (≥ 99.9%),
thì độ nhạy = NHỎ; nếu n/eq lệch đáng kể thì độ nhạy = LỚN (báo ngay).

**KHÔNG thay file/bins đang dùng.** Không chạy Java/sim trên Oracle (chỉ Kaggle).

---

## 5. VIỆC 5 — runbook

`docs/runbooks/PRED_PIPELINE_REPRO.md`: lệnh 1-phát build lại toàn bộ pred map cho 1 cấu hình
features/label bất kỳ (tham số hoá), kèm thời gian + tài nguyên đo được.

---

## 6. Cổng hợp lệ / tuân thủ (bắt buộc)

- 0 đọc 2026 (mọi file .pb/feature đọc ≤ 2025-12-31; bins map chỉ 16 fold DEV).
- 0 ghi đè data dir đang dùng; ghi ra `/home/ubuntu/f0_repro/`.
- Python dùng `logging` (cấm `print`), Java SLF4J.
- Sim trên Kaggle (không Oracle). Commit script + docs (không commit data lớn).
- Pre-reg commit TRƯỚC khi chạy bất kỳ số nào. Mọi đổi thiết kế = AMENDMENT có lý do, commit
  trước khi xem số bị ảnh hưởng.
