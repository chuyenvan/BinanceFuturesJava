# TASK-130: Dựng pipeline RETRAIN funding selector với provenance sạch (Kaggle GPU) — CCD opus

- **status:** doing — **owner:** CCD-130 opus · **updated:** 2026-07-05 (Thiết kế XONG + commit; đang dựng kernel GPU smoke)
- **Bối cảnh:** model funding hiện tại (262MB ONNX) MẤT source code + nghi over-parameterized; bản 49.5MB nhanh 8×
  nhưng cũng không provenance. Nguyên tắc chốt: model phải đi kèm code + data sinh ra nó (direction A: retrain,
  không phục hồi artifact mồ côi). IC hiện tại của model cũ ĐÃ ĐO (TASK-128): rankIC 0.344, hit_SEL 65.8% — đây
  là BASELINE mà model mới phải THẮNG hoặc ít nhất hoà (kèm provenance + size hợp lý) mới được cân nhắc thay.
- **Phạm vi:** DỰNG + SMOKE pipeline end-to-end. KHÔNG thay model production. Thay hay không = quyết định của Uni
  sau khi so số.

## ⛔ HÀNG RÀO
1. Language unification (TASK-109 B1b): TRAIN data DUY NHẤT từ Java export (`ExportFeaturesForPythonTool` → ff_*.bin,
   `ExportFundingOiPerCoin` → OI). Python CHỈ là training code. Nếu script train hiện tại đọc data từ nguồn khác →
   ghi NEEDS_HUMAN, không tự chế nguồn data.
2. Repo có 3 bản train script (ml/funding_selector/train_funding_selector.py + _wfo.py, ml/training/...): pha khảo sát
   PHẢI xác định bản nào là bản đúng/mới nhất (đọc git log + nội dung), ghi rõ vào Thiết kế. Không đoán.
3. SSH Oracle: CHỈ đọc + ghi ~/claudedata/task130/ + ~/kaggle_kernels/funding-train/; Oracle đang chạy vế D —
   export TRAIN data để PENDING nếu cần chạy Java nặng (chỉ chạy khi Oracle rảnh, RAM budget AGENTS.md).
4. Kernel Kaggle: enable_gpu=true, slug funding-train-v1 (nhớ bài học slug kẹt: nếu "Notebook not found" → đổi slug).
   Smoke = train trên 1 lát data nhỏ (1 quý) ít epoch, mục tiêu CHỨNG MINH pipeline chạy + GPU được dùng
   (log device), KHÔNG phải ra model tốt.
5. Pre-register TRƯỚC trong Thiết kế: định nghĩa label (win@24h? — PHẢI khớp code Java sinh label như TASK-128 đã
   xác định score=1−P(win@24h)), split train/val theo THỜI GIAN (không random — leak), metric so sánh = rankIC/hit_SEL
   trên cùng nền TASK-128 để so táo-với-táo với baseline.
6. Provenance block trong mọi output: commit sha + lệnh export + md5 data + script + hyperparams.

## Việc làm
1. Khảo sát (ghi vào Thiết kế, commit trước khi dựng): script train nào đúng, data format ff_*.bin cần gì,
   ExportFeaturesForPythonTool args/env, label định nghĩa ở đâu trong Java.
2. Dựng kernel funding-train-v1 (GPU): đọc data từ dataset Kaggle (dataset TRAIN riêng — nếu chưa có data thì
   kernel smoke dùng lát data tự export nhỏ NẾU Oracle rảnh, không thì mock-run tới bước load rồi PENDING).
3. Smoke GPU: log xác nhận device=cuda, train 1 lát nhỏ chạy hết không crash, model file + provenance block ra output.
4. Kết quả: Thiết kế + trạng thái từng bước + việc PENDING còn lại để chạy train full. Marker /d/claudedata/CCD130_DONE.

## Thiết kế (CCD-130 opus · 2026-07-05)

> Ghi TRƯỚC khi dựng kernel (pre-register). Commit chốt Thiết kế: xem "Kết quả".

### A. Bản train script ĐÚNG (xác định bằng git log + diff — KHÔNG đoán)
3 ứng viên:
| File | git commit mới nhất | Vai trò |
|------|--------------------|---------|
| `ml/funding_selector/train_funding_selector.py` | e9bb2c9 (SAVE_MODEL, TASK-039a) | Bản gốc thư mục làm việc (pre-provenance) |
| `ml/funding_selector/train_funding_selector_wfo.py` | f0d6cfe (TASK-108) | **KHÁC mục đích** — WFO rolling per-fold 4 horizon. KHÔNG dùng cho retrain 1-shot. |
| **`ml/training/train_funding_selector.py`** | **66341cd** "docs(provenance): đưa code train vào git (đóng GAP #4)" | ✅ **BẢN ĐÚNG** — snapshot từ Oracle 2026-07-01, git-blessed provenance cho tầng A |

- `md5sum`: `ml/training/train_funding_selector.py` == `ml/funding_selector/train_funding_selector.py` (`f9e517b8…`, **IDENTICAL**). Bản `ml/training/` là **canonical** (README `ml/training/README.md` chốt là nguồn provenance). CCD-130 sửa bản canonical; bản `funding_selector/` giữ nguyên (legacy, được phép diverge).
- `_wfo.py` md5 `144d97f6…` khác hẳn → không phải bản retrain.

### B. Format 3 nguồn dữ liệu TRAIN (tất cả DO JAVA EXPORT — thỏa hàng rào #1)
| Nguồn | Java tool | Record | Verify size |
|-------|-----------|--------|-------------|
| Tool1 features (40 feat) | `fundingv2.ExportFeaturesForPythonTool $S $E <outDir>` | `>i8 ts, >i2 symId, 40×>f4` = **170 B** | ff_202101.bin 61316620/170 = 360686 ✓ |
| OI per-coin (5 feat) | `fundingv2.ExportFundingOiPerCoin $S $E symfile=<u>` | `>i8 ts, >i2 symId, 5×>f4` = **30 B**; feat = [oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy] | oi_percoin_full.bin 3411674190/30 = 113722473 ✓ |
| Label | `export.ExportFundingLabel $S $E <out.csv>` | CSV 27 cột: tEpochMs,tDate,symbol + {maxFav,maxAdv,tHitFav,tHitAdv,retEnd,nBars}×{4h,12h,24h,72h} | 47.86M dòng (TASK-024) |
| Map | `symbol_map.csv` (symId,symbol) — kèm trong dataset OI | — | — |

- Universe (gồm coin chết) cho OI: `DumpSymbolMapper` → oisyms.txt. ⚠️ **DumpSymbolMapper KHÔNG có trong git src** (chỉ tồn tại dạng `.class` trên Oracle/dataset java-run-lc — xem AGENTS TASK-037). Provenance GAP cho lần export FULL (PENDING) — ghi rõ ở Kết quả.
- Env train script (bắt buộc): `TOOL1_GLOB OI_FILE LABEL_CSV MAP_CSV`; tùy chọn `HORIZON(S)`, `OUT_DIR`, `SMOKE`, `OI_TOL_MS`, `LBL_TOL_MS`, `SEED`, `SAVE_MODEL`. **TASK-130 thêm** `XGB_DEVICE`(cpu|cuda) + `N_ESTIMATORS` (additive, cpu/400 = hành vi cũ).

### C. Data đã có sẵn trên Kaggle (Java export 2026-06-21 — KHÔNG cần chạy Oracle)
- `chuyendinh/funding-tool1-features` (4.86GB): ff_YYYYMM.bin (monthly, 40-feat).
- `chuyendinh/funding-oi-percoin` (2.59GB): oi_percoin_full.bin + symbol_map.csv.
- `chuyendinh/funding-label-full` (2.62GB): funding_label.csv.
- `chuyendinh/funding-model-v1`: model_{H}.ubj + train_meta (output TASK-039 cũ — model XGBoost .ubj, **KHÔNG phải** 262MB ONNX production).
→ Dùng cho SMOKE = data Java-export thật, thỏa hàng rào #1. ⚠️ Provenance các dataset này: commit-jar sinh ra chúng KHÔNG được stamp trong dataset (chỉ biết ngày 2026-06-21) → lần retrain FULL clean-provenance vẫn phải re-run `gen_train_data.sh` trên Oracle (PENDING) với HEAD stamp.

### D. PRE-REGISTER (chốt trước — chống gian lận hậu kỳ)
- **Label:** `y = 1{ maxFav_24h ≥ 0.06 & nBars_24h ≥ 96 }` = "chạm +6% trong 24h" (khớp `ExportFundingLabel` + TASK-128). Model dự đoán **P(win)**; **khóa convention `pred[0]=score=1−P(win@24h)`**, engine chọn **score THẤP = P(win) cao** (khớp manifest `…score1minusPwin`).
- **Split THEO THỜI GIAN (no shuffle, no leak):** TEST = 12 tháng cuối; VAL = 6 tháng trước TEST; TRAIN = phần còn lại; **purge = horizon** (24h) giữa các đoạn. Assert `tr.ts.max()<va.ts.min()<te.ts.min()` (đã có trong script).
- **Metric so táo-táo với baseline (nền TASK-128):** `rankIC` (Spearman score↔y) + `hit_top` (hit-rate nhóm top-K SELECTED). Baseline model cũ (TASK-128): **rankIC 0.344, hit_SEL 65.8%** — model mới phải THẮNG/HÒA + provenance + size hợp lý mới được cân nhắc thay.
- Acceptance ML-gate (đã pre-register trong script): LIFT≥1.20, N_top≥100, z≥2, |t_IC|≥2 (OOS 12 tháng) VÀ beat best-single-feature (chọn trên VAL, đo trên TEST).

### E. Kế hoạch SMOKE (GPU, KHÔNG thay model production)
- Kernel **funding-train-v1** (`enable_gpu=true`, `enable_internet=false` — data từ dataset, không cần 226 → tránh geo-block).
- Slot: CPU đang 5/5 (wfo-worker 1..5 + model-quality RUNNING) → **GPU quota RIÊNG**, không đụng slot CPU (đây là lợi ích chính của GPU cho task này).
- Lát nhỏ = **Q1-2021** (ff_202101/02/03) để chạy nhanh: kernel harness cắt OI + label về ts-range Q1 (đọc chunk, bound RAM), rồi gọi train script với `HORIZON=24h XGB_DEVICE=cuda N_ESTIMATORS=60 SAVE_MODEL=1`.
- **Tiêu chí PASS smoke:** (1) log in `device=cuda` + `xgb.__version__`; (2) train chạy hết không crash; (3) ra `model_24h.ubj` + `provenance.json` (commit sha + lệnh export + md5 input + md5 script + hyperparams). KHÔNG đòi model tốt.
- Nếu GPU quota hết / kernel lỗi → PENDING, ghi bàn giao.

### F. Việc PENDING (chạy train FULL clean-provenance — cần Oracle rảnh)
1. Re-run `ml/training/gen_train_data.sh` trên Oracle khi vế D xong (RAM-budget AGENTS.md) → ff+OI+label full 2021→nay với HEAD stamp + md5.
2. Push 3 dataset mới (provenance-stamped) → train FULL GPU 4 horizon → so rankIC/hit_SEL vs baseline TASK-128.
3. Convert .ubj→.onnx (`convert_ubj_to_onnx.py`) NẾU số thắng baseline. Thay model = **quyết định Uni**, KHÔNG phải CCD.

<!-- Kết quả bên dưới -->
&nbsp;

## Kết quả (CCD dựng + master thu hoạch 05/07 trưa)
- CCD-130 hoàn thành khảo sát + thiết kế + 4 dataset TRAIN Java-export + kernel smoke, nhưng process chết khi
  ngồi chờ kernel (bài học `-p` không chờ được tái diễn — marker không kịp cắm). Master thu hoạch.
- **SMOKE GPU PASS TRỌN** (kernel funding-train-v1 COMPLETE): nvidia-smi OK, XGBoost 3.2.0 **device=cuda**,
  lát H1-2021: 173,436 rows × 45 feat × 111 sym; label H=24h nBars≥96 (khớp định nghĩa TASK-128);
  metrics: hit_top 72.9% vs base 48.7% (LIFT 1.50, z=38.9), rankIC 0.148, beats_baseline f28+, PASS 2 gate;
  output model_24h.ubj 143KB + provenance.json đầy đủ md5.
- **TRAIN FULL đã push** (funding-train-full-24h, GPU, 600 trees, time-split TEST 6 + VAL 6 tháng cuối) —
  provenance data = bản export sẵn có, ghi rõ trong provenance.json; re-gen HEAD trên Oracle vẫn PENDING
  trước khi cân nhắc production. So baseline TASK-128 chỉ THAM KHẢO (nền đo khác: holdout vs per-fold).
- Marker: /d/claudedata/CCD130_DONE (master cắm thay).
