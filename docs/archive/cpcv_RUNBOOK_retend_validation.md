# RUNBOOK — CPCV label-swap validation (maxFav → retEnd-0.015)

> Mục đích: đổi label model rồi chạy lại toàn bộ CPCV validation để ra verdict, **giữ nguyên mọi thứ khác** (data, DD gate 40%, fitness Cách 2). Doc này để lần sau không phải đi tìm lại. Cập nhật theo từng bước ĐÃ verify.
>
> Cập nhật gần nhất: 2026-08-26. Chủ đề hiện tại: `retEnd-0.015` (4h), thay cho `maxFav-0.06`.

## 0. Hạ tầng & lối vào

- **Oracle** (master + data): `ssh -i /root/.ssh/id_rsa_chuyennd -o StrictHostKeyChecking=no ubuntu@161.118.212.3`
  - Key nằm ở `/root/.ssh/id_rsa_chuyennd` trên env desktop-commander (KHÔNG phải `/c/Users/...`).
- **Kaggle** (workers + GPU predict): auth `~/.kaggle/kaggle.json`, CLI trong `~/envs/xgb-env`. `source ~/envs/xgb-env/bin/activate` trước khi gọi `kaggle`.
- **GOTCHA bridge desktop-commander**: nó **pre-expand mọi `$VAR` và `$(...)`** trong command string VÀ trong `write_file` → biến rỗng, script hỏng (`mkdir -p ""`). 
  - Cách an toàn tạo file trên Oracle: viết local → `base64` → `ssh "... | base64 -d > file"` (base64 không có ký tự đặc biệt). HOẶC `cat <<'EOF'` với nội dung **hardcode, không có `$` nào**.
- **MCP tool cap 60s**: lệnh chạy lâu phải `nohup ... &` rồi poll ở ssh riêng; đừng nối `; sleep` sau nohup trong cùng 1 ssh (background bị kill).

## 1. Data tiers (frozen 2026-08-24, `configs/data_tiers.json`)

| Tier | Range | Ghi chú |
|---|---|---|
| DEV | 2021-01-01 → 2024-06-30 | R&D zone, leak được phép |
| GAP_1 | 2024-07-01 → 14 | purged |
| VALIDATION | 2024-07-15 → 2025-12-31 | machine_only, contaminated → verdict là CẬN TRÊN |
| HOLDOUT | 2026-01-01 → 2026-08-13 | SEALED, chạm 1 lần sau khi PASS |

## 2. Pipeline end-to-end (3 tầng)

### Tầng A — Train model → predict_wf (Python, CÓ THỂ OOM)
- Script gốc: `/home/ubuntu/claudedata/gen_funding_wf_predictions_1m.py` (maxFav, `WIN=0.06`).
- Bản retEnd: `/home/ubuntu/cpcv/gen_retend.py` = copy đã patch: `maxFav_{h}`→`retEnd_{h}`, `WIN=float(os.environ["NET_THR"])` (default 0.015). Label `y=(retEnd_4h>=0.015)`.
- Walk-forward, expanding train, purge=72h (PURGE_STEPS=288 @1m), FIRST_CUTOFF hoặc CUTOFFS (env), OOS_MONTHS=3, HORIZONS=4h. Leak guard: assert `ts_max_train < cutoff`.
- Output: `predict_wf_YYYYMMDD.bin`, format `>q h 4f` (26B: ts i64-BE, symId i16, 4×f32 = [4h,12h,24h,72h]; HORIZONS=4h → chỉ slot 0 có giá trị).
- **OOM**: builder memmap gộp TẤT CẢ năm 1 lần, tune cho box 30GB (Kaggle). Box Oracle 23GB → đọc feature 2025 (15M dòng) đẩy peak 21GB → oom-killer (Aerospike co-resident càng chật).
  - Range 2021→2024 (DEV): peak ~16-17GB → **chạy Oracle OK**.
  - Range có 2025+ (VALIDATION): **phải chạy Kaggle GPU** (`sel1m_code/gen_wf_pred_stream_gpu.py`) — đây là lý do maxFav sinh predict_wf trên Kaggle.

### Tầng B — Bake predict_wf vào dataset offline (Java, memory-bounded, Oracle OK)
- Script: `/home/ubuntu/build_ds.sh` → Java `com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset`, `-Xmx18g`.
- Env quan trọng:
  - `WFO_FUNDING_PRED_DIR=<dir chứa predict_wf_*.bin>` (maxFav dùng `/home/ubuntu/claudedata/predwf_canon`)
  - `WFO_SEL_HORIZON_IDX=0`  → **0 = 4h** (production là 4h; đừng nhầm với `build_funding_bin.py` HZ_IDX=2=24h — file đó STALE, không dùng)
  - `WFO_SET_PRED=ai_pred_market_gate_wfo`
- Nạp market data từ Aerospike + ticker daily bundles `/home/ubuntu/java/simulator/kaggle_data_hpo/daily/ticker_YYYYMMDD.bin.gz` (2021→2026, per-day, low-mem).
- Output: dataset `/home/ubuntu/claudedata/wfo_ds_canon_1m_h4h` (+ manifest.txt, md5). Đây là thứ Java validation nạp ("LOAD offline OK: market/pred/funding md5 verified").

### Tầng C — Campaign CPCV → verdict (Oracle master + Kaggle workers)
- JAR: `/home/ubuntu/java/cpcv.jar` (= `/home/ubuntu/cpcv/kg/ds_jar/cpcv.jar`, md5 phải khớp).
- Master/coordinator: `java -cp cpcv.jar com.binance.chuyennd.ai_ml.wfo.framework.WfoCoordinator status|report <campaign>` (vd campaign `cpcv_v1`).
- Worker (Oracle): `java -cp cpcv.jar com.binance.chuyennd.ai_ml.wfo.framework.WfoWorker <campaign>`.
- Worker (Kaggle): kernels `chuyendinh/wfo-worker-1..5` (`/home/ubuntu/claudedata/.run/kernels/wfo-worker-*/run_worker.py`), đẩy bằng kaggle CLI. Job store qua Aerospike.
- Batch runner (1 JVM nạp dataset 1 lần, chạy cells.jsonl): `java -cp cpcv.jar com.binance.chuyennd.ai_ml.wfo.CpcvBatchRunner` (chạy từ `/home/ubuntu/cpcv/run`, cần config.properties).
- Driver Python (frozen v1): `/home/ubuntu/cpcv/run_cpcv_validation.py <tiers.json> <workdir> --java-cmd "..." --n 200`.
- Verdict: `verdict_v2.py` (đọc `wf_v2/results_jobstore.jsonl` → ma trận Calmar → PBO/DSR/%path+). Gate frozen v1: PBO<0.20, DSR>0.95, %path+≥0.80. Fitness Cách 2: totalPnL thuần, DD gate hard = 40%.

## 3. Trạng thái retEnd-0.015 hiện tại (2026-08-26)

- **6 fold DEV** đã train (cutoff 2023-01 → 2024-04), leak-free, tại `/home/ubuntu/cpcv/retend_dev_out/predict_wf_*.bin`.
  - Script: `/home/ubuntu/cpcv/run_dev.sh` (glob `features_202[1234]*`, CUTOFFS 6 fold, log `retend_dev.log`).
  - Eval: `/home/ubuntu/cpcv/eval_auc_all.py` → **pooled OOS AUC = 0.657**, per-fold 0.61–0.67, lift pred≥0.6 = 1.6–2.4x.
- **CÒN THIẾU**: ~8 fold phủ 2024-07 → 2025-12 (VALIDATION) → phải sinh trên **Kaggle GPU** (Oracle OOM ở 2025).

## 4. TODO để ra verdict retEnd
1. [ ] Sinh predict_wf retEnd fold 2024-07→2025-12 trên Kaggle GPU (gen_wf_pred_stream_gpu, NET_THR=0.015, horizon 4h).
2. [ ] Gom đủ ~14 fold retEnd vào 1 dir → chạy `build_ds.sh` (WFO_FUNDING_PRED_DIR trỏ dir đó, HORIZON_IDX=0).
3. [ ] Push dataset + jar lên Kaggle, chạy campaign `WfoCoordinator` (workers) trên VALIDATION.
4. [ ] `verdict_v2.py` với fitness Cách 2 (DD 40%) → PASS/FAIL + PBO/DSR/%path+.
5. [ ] KHÔNG đụng HOLDOUT tới khi PASS.

---

## 5. PHÁT HIỆN 2026-08-26: net015 ĐÃ ĐƯỢC VALIDATE TRƯỚC ĐÓ (13–15/08)

**Không cần build lại từ đầu.** retEnd-0.015 (net015, 4h) đã chạy end-to-end nhiều lần qua `drive015.sh` → `drive_exp.sh <TAG> <HIDX>`.

### drive_exp.sh (driver "như cũ", 1 lệnh)
- Chờ `predwf_<TAG>` có ≥12 fold → Java `ExportWfoDataset` (build_ds, `WFO_SEL_HORIZON_IDX=<HIDX>`, `-Xmx18g`) → dataset `wfo_ds_<TAG>` → upload Kaggle `chuyendinh/wfo-ds-<TAG>` → `WfoCoordinator reset strategy_window` → push 5 worker `wfo-worker-1..5` → poll tới `DONE=16` → `report strategy_window` → ghi `claudedata/sweep/DONE_<TAG>.txt`.
- Verdict kiểu: **walk-forward fanout 16 window** (2022→2026-01), per-window PnL + `TOTAL_12w` + posRatio(strict/lenient) + WFE. **KHÁC** CPCV 28-path PBO/DSR/%path+.
- `WFO_MAX_OOS_DATE=20260101` (không chạm HOLDOUT).

### Kết quả net015 đã có (`claudedata/sweep/DONE_*015*.txt`)
| TAG | TOTAL_12w PnL | posRatio lenient | ghi chú |
|---|---|---|---|
| B015 (net015 thuần, 4h) | 14,085.6 | 81% (13/16) | thua đậm win12 2025Q1 −1984.7 |
| B015K5 (+ selector topK5) | 18,139.5 | 94% (15/16) | tốt nhất nhóm B; thua nhẹ 2025Q1 −1354 |
- Còn sweep: `G015K5/K8/K10/K12/K15 v26b`, `G015sl05/sl08`, `G015x26/x26q2...` (topK + stoploss + range 2026 variants).
- Prediction sets: `claudedata/predwf_G015*` (~22 dir), mỗi dir ~15 fold predict_wf.

### Chưa có (theo tìm được)
- **CPCV rigorous (PBO/DSR/%path+, verdict_v2.py, campaign cpcv_v1)** cho net015 — bộ đó session này siết cho maxFav-6%. net015 mới chỉ qua fanout 16-window, chưa qua CPCV 28-path.

### Ghi chú lệch hướng
- gen_retend 6-fold DEV (mục 3) là tôi tự dựng lại 1 lát nhỏ — thừa so với hạ tầng có sẵn, nhưng xác nhận label chạy đúng (AUC 0.657). Lần sau: dùng thẳng `drive_exp.sh`/`predwf_G015*`, đừng dựng lại.
