# WFO OPS RUNBOOK — luồng vận hành đang chạy trơn (2026-08-13)
Tài liệu vận hành để DÙNG LẠI + cải tiến. Ghi lại đúng luồng export→train→predict→fanout→verdict đang hoạt động ổn.

## 0. Topology (ai chạy ở đâu)
- **Kaggle GPU** (2 concurrent, ~13GB RAM): train selector (Stage A).
- **Kaggle CPU** (5 concurrent, ~30GB RAM): predict-only fine-grid (5 node) + wfo-worker fanout (5 node). → predict và fanout **phải tuần tự** (cùng tranh 5 slot).
- **Oracle** (4 core/23GB, IP 161.118.212.3): coordinator + Aerospike (ns=test, port 3222) + `drive_exp.sh` harness + build dataset (Java ExportWfoDataset) + kaggle CLI (`/home/ubuntu/kaggle_latest_venv/bin/kaggle`).
- **Điều khiển**: từ máy Windows qua Git-ssh + desktop-commander PowerShell + hàm `OrBash` (base64 → tránh lỗi quoting). System32 OpenSSH lỗi exit 255 → dùng `C:\Program Files\Git\usr\bin\ssh.exe`.

## 1. Luồng 4 bước

### Bước A — TRAIN selector (Kaggle GPU)
- Kernel `selector-15m-savemodel-net<thr>-gpu` (script Python, GPU, internet OFF).
- Input datasets: `funding-unf15-data` (features 15m .bin + labels funding_label_*.pb), `funding-oi-percoin` (OI + symbol_map), `sel1m-code` (gen_funding_wf_predictions_1m.py + tool1_col.py).
- Env chính (set trong .py TRƯỚC khi `exec()` gen script): `LABEL_MODE=net`, **`NET_THR=<thr>`** (ngưỡng label y=(retEnd_4h>thr)), `SELECTOR_GRID_MIN=15`, `FIRST_CUTOFF=20230101`, `OOS_MONTHS=3`, `PURGE_STEPS=288` (=72h purge), `XGB_DEVICE=cuda`, `HORIZONS=4h`, `MODEL_DIR=/kaggle/working`.
- Output: `model_f0..f13_4h.json` (14 model per-fold) + `predict_wf_<startdate>.bin` (dự đoán 15m mọi window).
- ⚠️ Dòng print "NET_THR=0.008" trong 1 số kernel là **chuỗi cứng cũ** — giá trị thật đọc từ `os.environ["NET_THR"]`. Xác minh bằng pos-rate/AUC/MD5, đừng tin print.
- ~40–50 phút.

### Bước B — ĐÓNG GÓI models → Kaggle dataset
- Pull output kernel Stage A → thư mục; copy `model_f*_4h.json` + `dataset-metadata.json` (title/id `sel-models-net<thr>`) → `kaggle datasets create -p . -r skip` → chờ status `ready`.

### Bước C — PREDICT-ONLY fine grid (Kaggle CPU, 5 node)  [chỉ khi cần lưới mịn]
- Kernel `selector-<grid>-predonly-c{0..4}-cpu`, NUM_NODES=5, NODE_IDX=0..4, `FOLD_IDX_LIST="0,1,...,9"` (win4–13; tránh 2025H2 OOM), **`PRED_GRID_MIN=<grid>`**.
- Cơ chế decouple: `TOOL1_GLOB`=15m .bin (train/cutoff), `PRED_TOOL1_GLOB`=1m .t1c (predict OOS), `MODEL_DIR`=discover `sel-models-net<thr>` (load model, SKIP train), `T1C_MEMMAP_OUT=/tmp` (giới hạn RAM decode).
- Output: `predict_wf_*.bin` chia theo node → pull gộp cả 5 vào 1 dir `predwf_<tag>`.
- ⚠️ Native-train (Phase 3 mới) sẽ thay bước này: train thẳng ở grid, không decouple.

### Bước D — FANOUT / SIM (Oracle `drive_exp.sh <tag> <hidx>`)
1. Chờ `predict_wf_*.bin` ≥12 trong `predwf_<tag>` (fine grid chỉ 10 → chờ hết 20′ rồi chạy tiếp — vô hại).
2. **Java ExportWfoDataset** (Xmx18g): build `wfo_ds_<tag>` (funding.bin/market.bin/pred.bin/manifest.txt) từ `WFO_FUNDING_PRED_DIR=predwf_<tag>` + market Aerospike. `WFO_SET_PRED=ai_pred_market_gate_wfo`, `WFO_SEL_HORIZON_IDX=<hidx>` (0=4h).
3. `kaggle datasets create ; datasets version` (vô điều kiện — để re-run cập nhật) → chờ `ready`.
4. Sed 5 `wfo-worker-*/kernel-metadata.json` trỏ dataset mới; `WfoCoordinator reset strategy_window`; push 5 worker.
5. **Worker** (Kaggle CPU, Xmx20g, `run_worker.py`): A6 preflight (exit3=BLOCK coverage<0.95) → `WfoWorker strategy_window` (sim thật, đọc wfo-ds) → report state về Aerospike Oracle:3222. Strategy env set trong `run_worker.py` env block: `SELECTOR_RANK_TOPK=8`, `SIM_MIN_MOMENTUM_15M=0.008`, `TS_GIVEBACK_FLOOR/TS_MIN_GAP`, `DCA_*`, `SIM_APPLY_FUNDING=true`, `SIM_BREAKER_MODE=OFF`, (`SIM_RATE_PROFIT_STOP_MARKET`=moveSL nếu set).
6. Poll `WfoCoordinator status` tới `DONE=16` (fine grid có win rỗng → bò từ từ 10→16). FAILED≥1 → ghi ERR.
7. `WfoCoordinator report` → `DONE_<tag>.txt`: per-window pnl (win4–15) + `TOTAL_12w` (Σ win4–15) + posRatio strict/lenient + maxDD.
- ~30–50 phút (upload dataset 4.3GB là nút cổ chai).

## 2. State & concurrency
- Aerospike ns=test port 3222: WfoCoordinator state (`strategy_window`) + market data (`kline_1m_opt` protobuf per-phút) + pred sets (`ai_pred_market_gate_wfo`...).
- 226 Aerospike (103.157.218.226) flaky → dùng jobstore LOCAL `WFO_STATE_HOST=127.0.0.1`.
- Kaggle GPU 2 / CPU 5. Train(GPU) ⟂ predict/fanout(CPU). Predict(5) và fanout(5) **serial**.
- ⚠️ jobstore dùng CHUNG namespace `wfo_jobs` + `__job_index__`, job-id không tách tag → **2 fanout song song = reset đè mất verdict**. Workaround: autosnap trước reset (đã vá). Fix gốc = `WFO_STATE_SET` per-tag (Phase 2, D2).

## 3. Verdict (đọc đúng)
- `WFO_HARNESS_FIX=true` (P0+P1): P0 ramp TOO_FEW dưới mọi reject; P1 OOS coi CAPITAL_LOCK/TOO_FEW/UNSTABLE là report-only, chỉ ZERO_TRADES/BURN/OVER_MAXDD disqualify.
- Verdict frozen = **%OOS-dương ≥70% + maxDD-OOS ≤50%** (BỎ WFE — vô nghĩa với frozen). Đọc qua `WfoCoordinator report` + gatecount.jar, KHÔNG dùng cache `wfo_report`/preflight jar (ra bản strict sai).
- Metric bổ sung tự tính từ DONE_*.txt (win4–13, apples-to-apples): Sharpe=mean/std, t=mean/(std/√10), %pos, maxDD từ equity cộng dồn, Profit Factor.

## 4. Gate (hiện tại)
- `AIRejectFilter`: **CHỈ** `predReturn15M ≥ MIN_MOMENTUM_15M` (worker set 0.008). risk4h BỎ hẳn 8/8 (leaky). Market-level (1 pred/timestamp). Data đủ 1m full range (`wfo_gate_pred.csv` 2.76M dòng, 60000ms).
- Per-symbol selection = selector rank-K8 (top-8/timestamp). Entry = gate ∩ selector-topK.

## 5. Bẫy hạ tầng (đừng lặp)
- **Jar stale**: build/bump Kaggle mà quên scp Oracle → chạy jar cũ (kết quả byte-identical baseline). → `verify_stage.py` đếm field Configs.class, PASS mới fanout.
- **RAM**: 3 batch chồng nhau = OOM → box treo (SSH banner timeout). `free -g` trước fanout; 1 batch/lần.
- **Kaggle env động**: không inject được → hardcode vào .py trước push.
- **Kernel status false-COMPLETE** ngay sau push (báo COMPLETE của version cũ) → sleep ~90s trước khi poll.
- **PowerShell nuốt quote** → OrBash base64. Multi-line here-string trong REPL cần gửi 1 dòng trống để flush.
- **drive_exp `datasets create`** không update dataset đã tồn tại → phải `create ; version` vô điều kiện.
- **Disk**: dọn định kỳ (predwf_*/wfo_ds_* của lưới đã bỏ an toàn xóa; giữ oi/sel_models/sel1m_code/funding_label/gate_pred).

## 6. Điểm cải tiến (đưa vào roadmap)
- `WFO_STATE_SET` per-tag → chạy song song nhiều fanout (bỏ giới hạn serial).
- `WFO_VERDICT_NO_WFE` → tool tự in PASS/FAIL, hết đọc tay.
- Native-grid feature export (5m) → bỏ decouple predict-only + lấp 2025H2 (hết OOM 1m).
- drive_exp: giảm chờ 20′ (ngưỡng ≥12 predict_wf) khi lưới chỉ 10 window.
- Manifest tự-validate + tên `wfo_ds_LF_*` → loader reject data không leak-free.
