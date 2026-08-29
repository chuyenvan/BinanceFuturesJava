# CPCV AUTO-VALIDATION PIPELINE — KIỂM KÊ (dựng lại 2026-08-26)

> Mục đích pipeline: chạy validate Pha 2 **tự động, không người/LLM chạm số per-config** → chống leak
> tầng-chọn (governance §0.1). Người CHỈ nhận verdict PASS/FAIL. Đây là bản kiểm kê "tìm lại" toàn bộ
> mắt xích + chỗ còn thiếu. Luật gốc: DATA_GOVERNANCE_PROTOCOL.md · recipe: PHASE1_RECIPE_FROZEN_v1.md.

## 3 LỚP CỦA PIPELINE

### Lớp 1 — Java engine (ĐÃ commit, ĐÃ deploy Oracle `/home/ubuntu/java/cpcv.jar`)
- `src/.../ai_ml/wfo/CpcvBatchRunner.java` — 1 JVM nạp dataset 1 lần, đọc `CPCV_CELLS` (jsonl), chạy
  `backtestRange` mỗi cell, ghi `CPCV_OUT` (jsonl), **resume theo (seq|block)**. Set cứng cờ FROZEN v1
  trong main (DCA_GRID ON, OFF_FLAT_HARD, FILTER_MODE=A, BREAKER_MODE=OFF, APPLY_FUNDING).
- `src/.../wfo/framework/tasks/CpcvCellTask.java` — task `cpcv_v1`.
- `StrategyWfoTask.java` helper public: `geneNames/isIntGene/applyGenomeByName/backtestRange`.
- `HPOFitnessCalculatorV4.evaluateDetailedV2` — Calmar_mtm, cap 0.85, guard <5 lệnh.

### Lớp 2 — Python validation core (ĐÃ commit, canonical: `scripts/model_quality/cpcv/`)
- `run_cpcv_validation.py` — DRIVER/VERDICT. data_tiers → 8 block + gap14d → `sample_configs(SPACE, n=200,
  seed=42)` → cells.jsonl → gọi Java → results → **CPCV 28 path (inner argmax O trên train / outer chỉ đo)**
  → trial_ledger → DSR + PBO → `verdict.json`.
  - Objective: `O = median(Calmar_mtm) − 0.5·std`.
  - PASS = `pbo<0.20 AND dsr>0.95 AND pos_path_ratio>=0.80` (maxdd_mtm_cap 0.85).
- `cpcv_validation.py` — toán CPCV/DSR/PBO (self-test).
- `trial_ledger.py` — sổ trial append-only hash-chain (verify trước mọi lần tính DSR).
- `cpcv_harness.py` — vòng tự search (ma trận M×N).

### Lớp 3 — Orchestration Kaggle fanout (⚠️ CHƯA commit — chỉ ở `_wfotmp/`)
- `cpcv_baseline.sh` — baseline Oracle K=8, 16 cell → `baseline_oracle.jsonl` (mốc parity).
- `cpcv_fanout.sh` — MASTER: `STAGE = upload|kernels|parity|fanout|poll|verdict|all`. Upload jar+ds+cells lên
  Kaggle → build N=5 worker kernel → **PARITY GATE** (khớp baseline mới cho fanout) → fanout 1600 cell/5 kernel
  → gộp results → verdict.
- `run_cpcv_worker.py` — kernel worker Kaggle.
- `compare_parity.py` — so parity (trades KHỚP CHÍNH XÁC, note khớp, calmar/pnl reltol 1e-3).
- `ORCH_PARITY.md` — prompt/spec cho orchestrator chạy parity-gate (SCOPE cứng, bẫy chí mạng).
- `analyze_cpcv.py` — phân tích kết quả.

## TRÌNH TỰ CHẠY TỰ ĐỘNG (không người can thiệp giữa chừng)
1. `cpcv_baseline.sh` trên Oracle → `baseline_oracle.jsonl` (16 cell, K=8, tất định).
2. `cpcv_fanout.sh upload` → đẩy cpcv.jar + wfo-ds-val + shard cells lên Kaggle.
3. `cpcv_fanout.sh kernels && cpcv_fanout.sh parity` → PARITY GATE: Kaggle chạy 16 cell, so với baseline
   Oracle. **Lệch → DỪNG** (sim tất định phải khớp). Đây là chốt chặn chống môi-trường-lệch.
4. Parity MATCH → `cpcv_fanout.sh fanout && poll` → 1600 cell (200 config × 8 block) trên 5 kernel → gộp
   `results.jsonl`.
5. `cpcv_fanout.sh verdict` → `run_cpcv_validation.py` → CPCV 28 path + DSR/PBO → `verdict.json`.

## VÌ SAO "KHÔNG NGƯỜI/LLM → CHỐNG LEAK"
- Config KHÔNG do người chọn: `sample_configs(SPACE, seed=42)` tất định từ SPACE pre-registered (khớp recipe hash).
- INNER argmax chỉ nhìn block TRAIN; OUTER chỉ đo. Người không chỉnh giữa outer-fold.
- Người CHỈ thấy `verdict.json` (PASS/FAIL + DSR/PBO tổng), KHÔNG thấy số per-config/per-fold.
- Ngưỡng PASS chốt TRƯỚC khi chạy (freeze). FAIL → về DEV đẻ giả thuyết mới, KHÔNG vặn-rồi-chạy-lại VALIDATION.
- trial_ledger cộng dồn n_trials vĩnh viễn → mỗi lần chạm VALIDATION làm cửa DSR cao lên.

## ⚠️ CHỖ CÒN THIẾU / LỆCH (phải vá trước khi gọi là "đủ chạy")
1. **`parity_check.py` THIẾU.** `cpcv_fanout.sh` stage_parity gọi `python3 .../parity_check.py <cand> <oracle>`
   nhưng file không tồn tại — chỉ có `compare_parity.py` (khác TÊN và **khác thứ tự tham số**:
   `compare_parity.py <baseline> <candidate>`). Fanout sẽ chết ở bước parity.
2. **`run_cpcv_worker.py` SAI MODEL THỰC THI.** Bản hiện tại chạy `WfoWorker cpcv_v1` qua **jobstore Aerospike
   Oracle:3222** — nhưng ORCH_PARITY.md yêu cầu worker chạy **CpcvBatchRunner + shard file, KHÔNG jobstore,
   KHÔNG WFO_STATE_HOST**. Đây đúng là đường đã ra bug 168 trades vs 69 (quên SELECTOR_RANK_TOPK=8).
3. **Scheduled task orchestrator KHÔNG CÒN.** `trig_01ESLjZeiMaJecnW1LY4RnAc` không có trong account
   (list_triggers rỗng 2026-08-26). Driver auto "mỗi 2h" đã ngừng.
4. **Lớp 3 chưa commit git** (`_wfotmp/` untracked) → rủi ro mất.
5. **Pipeline hiện validate recipe v1** (objective median Calmar−0.5σ, cap 0.85, label triple-barrier 6%).
   Các quyết định mới trong hội thoại 2026-08-26 (fitness=PnL/gate maxDD 40%, label net_4h≥1.5%) **CHƯA**
   vào driver/Java → muốn chạy v2 phải pre-register v2 + sửa `PASS`/`objective_O` + fitness Java trước.

## HẠ TẦNG
- Oracle 161.118.212.3 ubuntu, key `~/.ssh/id_rsa_chuyennd_openssh` (qua desktop-commander/Git ssh, KHÔNG
  qua device_bash Linux VM — VM không có egress/key).
- Chạy đúng: `SELECTOR_RANK_TOPK=8` + `-Duser.timezone=Asia/Ho_Chi_Minh` + `TICKER_SOURCE=file`
  (ticker `/home/ubuntu/java/simulator/kaggle_data_hpo/daily/`). Thiếu 1 trong 3 = kết quả SAI recipe.
- Kaggle user chuyendinh, ticker sẵn: wfo-ticker-2024h1/h2/2025h1/h2.
- BẪY shell PowerShell→ssh: KHÔNG `&&`/`|`, dùng `;` + redirect file.
