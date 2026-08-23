# WFO train code — provenance, Kaggle versions, grid re-test (2026-08-16)

## 1. Ba bản code train — bản nào làm ra 18 fold
| Bản | Path | Trạng thái | Grid | Guard |
|---|---|---|---|---|
| **CANON** ✅ | `BinanceFuturesJava/ml/training/gen_funding_wf_predictions.py` (05/08) | ĐÚNG BÀI | grid-agnostic `SELECTOR_GRID_MIN` (mặc định 15); `H_STEPS = H_BASE_MIN // GRID_MIN` | CÓ: validate `LABEL_CSV.meta.json` stepMinutes == GRID_MIN, throw nếu lệch; label = **CSV**; `CHUNK_YEARS=1` merge OI theo năm (RAM-safe); FIRST_CUTOFF |
| BAK2 (=_1m gốc) | `sel1m_code/gen_funding_wf_predictions_1m.py.bak2` | nhánh 1m experiment, HỎNG | 1m hardcode (`H_STEPS={240,720,1440,4320}`, GRID_MS=1m) | MẤT guard; label = **.pb**; không CHUNK_YEARS |
| CURRENT (_1m tôi vá) | `sel1m_code/gen_funding_wf_predictions_1m.py` | tôi vá tạm về 15m + symId + stream OI | 15m | vá chắp vá, KHÔNG nên dùng |

- **Kernel `selector-15mtr-pred15-net015-gpu` exec `_1m`** (không phải CANON). Đã lưu bản CANON vào `claude/code/gen_funding_wf_predictions_CANON.py`.
- **18 fold `predwf_G015x26e` (mtime 14/08 15:03-15:05)**: expanding, OOS 2022Q1→2026Q2 tuần tự, chỉ 4h (12h/24h/72h NaN — WFO chỉ đọc idx0=4h). Logic 18-fold của CANON verify ĐÚNG (gen_cutoffs FIRST_CUTOFF=20220101 + OOS 3m + disjoint + expanding + per-fold write). Run 14/08 là một variant **chỉ-4h** của pipeline này.

## 2. ROOT CAUSE grid-mismatch — giải thích vì sao 1m & 5m train cũng fail (user xác nhận)
- Bản `_1m` (và các nhánh experiment) **hardcode H_STEPS/GRID theo 1 lưới cố định**. Khi data (feature+label) ở lưới KHÁC → filter `nBars >= need` giết sạch label (0 dòng) → train bỏ → fold NaN/fail. Đúng cái làm chuỗi regen v11–v20 của tôi vỡ, VÀ (theo user) làm **train lưới 1m và lưới 5m trước đây cũng fail**.
- **CANON không dính lỗi này**: `H_STEPS` suy từ `SELECTOR_GRID_MIN` + validate `label.meta.json` (throw nếu feature-grid ≠ label-grid). ⇒ Đổi lưới an toàn NẾU có feature+label đúng lưới đó + set `SELECTOR_GRID_MIN` khớp.

## 3. ⚠️ CẦN TEST LẠI: lưới 5m và 1m (hypothesis user: 5m > 15m hiện tại)
- **Data 5m ĐÃ CÓ trên Kaggle:** `funding-tool1-5m` (4.9GB), `funding-label-5m` (2.5GB). Data 1m: cần xác nhận (`funding-tool1-features-1m` / label 1m — theo data_flow doc).
- **Cách chạy đúng (dùng CANON, KHÔNG dùng _1m):** kernel exec CANON, set `SELECTOR_GRID_MIN=5`, TOOL1_GLOB→tool1-5m, LABEL_CSV→label-5m (kèm `.meta.json` stepMinutes=5), OI như cũ. CANON tự đặt H_STEPS={4h:48,12h:144,24h:288,72h:864}, purge 72h=864 bước. Guard sẽ throw nếu label 5m thiếu meta/ lệch — an toàn.
- RAM: 5m ~3x số dòng của 15m. CANON có `CHUNK_YEARS=1` (merge OI theo năm) để chịu. Nếu vẫn nặng: train chỉ 4h (WFO chỉ dùng 4h) để giảm ~4x — chỉnh H_LIST=["4h"] hoặc lọc theo HORIZONS (hiện CANON KHÔNG lọc theo HORIZONS → cần thêm 1 dòng).
- **Giả thuyết cần kiểm:** data gốc 5m → train lưới 5m có thể sắc hơn 15m (đỡ mất tín hiệu do downsample). 1m mịn nhất nhưng RAM nặng + nhiễu microstructure. So bằng cùng K-sweep/WFO như 15m canonical (K5, moveSL0.05, thr015) rồi đối chiếu total/quý dương/DD.

## 4. Kaggle inventory (private) — version note
- **Kernels selector (nhiều nhánh experiment):** selector-15mtr-pred15-net015-gpu (canonical 15m — ĐANG là bản tôi push tới v20, state ERROR do regen), selector-1m-net-gpu, selector-net-t015-cpu, selector-net-t020-cpu (thử threshold), selector-maxfav-w5-gpu, selector-unf15-net72-gpu, selector-wfo-pred-1m… → các nhánh 1m/5m/threshold/window trước đây, phần nhiều fail do grid-mismatch mục 2.
- **Datasets nguồn:** funding-tool1-15m (1.75GB, upd 16/08), funding-tool1-5m (4.9GB), funding-label-15m (906MB), funding-label-5m (2.5GB), funding-oi-percoin (3.2GB, oi_percoin_full.bin raw), hpo-ticker-daily (13.7GB, worker source — ĐỪNG xóa), java-run-lc (worker source — ĐỪNG xóa).
- **sel1m-code dataset (chứa gen code kernel exec):** version hiện tại (16/08 08:37) chứa gen_funding_wf_predictions_1m.py + .bak2. CÁC version tôi push phiên này (v12–v20): stream-OI raw+gzip, merge-peak fix, train-stage numpy/del, grid 15m revert, labels symId-int, labels window-filter — TẤT CẢ trên nhánh `_1m` (nhánh cụt). Bản 14/08 (làm 18 fold) là version sel1m-code TRƯỚC khi tôi recreate.

## 5. Khuyến nghị
1. **Bỏ nhánh `_1m`** cho việc regen; nếu cần regen bất kỳ fold nào → dùng **CANON** + `SELECTOR_GRID_MIN` đúng lưới. Kernel nên trỏ exec CANON, không phải _1m.
2. **2026Q2 KHÔNG cần regen** (fold đã có, hợp lệ). Blocker thật = market/funding coverage tới 2026-07-01 + nới buildJobs (xem doc recipe).
3. **Re-test 5m & 1m** bằng CANON như mục 3 để kiểm hypothesis 5m>15m — chạy song song, so bằng K-sweep canonical.
