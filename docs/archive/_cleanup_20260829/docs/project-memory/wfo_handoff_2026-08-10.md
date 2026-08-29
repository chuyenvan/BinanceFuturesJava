# WFO HANDOFF — 2026-08-10 (sang session mới)

Mục đích: session sau đọc file này là đủ tiếp tục, không cần đọc lại toàn bộ lịch sử.

---

## 1. TL;DR trạng thái

- Dataset canonical leak-free **đã build + validate PASS + sign**: `wfo_ds_canon_1m_h4h` (trên Oracle).
- Fanout **N=1 frozen (genome loose_k8) đã chạy xong**: **14 DONE + 2 FAILED (OOM)**.
- **VERDICT: ❌ FAIL/REVIEW** — WFE median 0.275 (ngưỡng ≥0.5), posRatio lenient 50% (7/14; bỏ 4 window 2022 rỗng → 7/10), maxDD worst 38.4%. Chi tiết: `claude/wfo_fanout_verdict_canon_k8_2026-08-10.md`.
- Kết luận: **xác nhận thesis project "ăn ít đuôi lớn"**; edge OOS yếu + overfit. Nhưng CHƯA so được apples-to-apples với run 15m cũ (14/16) vì đổi cùng lúc 4 biến (xem mục 4).

---

## 2. Dữ liệu WFO đang dùng (2 lớp — đừng gộp)

**Lớp 1 — prediction (leak-free "predict sẵn"):**
- Selector: chạy Kaggle, canonical, `FIRST_CUTOFF=2023-01-01`, 14 fold, universe **filtered top-10%** (EntrySignalFilter), OI full-native 5m, block_lo=c, purge 72h, WFO_SEL_HORIZON_IDX=0 (4h), WIN=0.06. Output = file `predict_wf` → `/home/ubuntu/claudedata/predwf_canon` trên Oracle.
- Gate: train+predict trên Oracle → Aerospike set `ai_pred_market_gate_wfo`. Coverage 2023+ đo được 99.98%.

**Lớp 2 — strategy WFO (fanout):**
- Dataset `wfo_ds_canon_1m_h4h` = `market.bin + pred.bin + funding.bin + manifest`, build bằng `ExportWfoDataset` (đọc `market_data` 1-phút từ Aerospike + gate + selector predict_wf).
- Manifest: codeGitSha=8741f85154e04d57c48da9c55472cea7e55eed2a, leakFreeFrom=2023-01-01, horizonIdx=0, foldCount=14.
- Số liệu build: market=2,774,140 | gate pred=2,760,442 | funding=1,752,741. Features 59,440,991 rows / 776 symId. Base rate 4h ≈ 0.15.

**Vì sao KHÔNG chạy sim trên Kaggle:** simulator lớp 2 cần `market.bin` = OHLCV 1-phút raw toàn bộ coin 2022–2026, nằm trong Aerospike, Kaggle không có. Kaggle chỉ đủ cho selector (lớp 1). Phân công đúng: Kaggle=selector, Oracle=build_ds+sim.

---

## 3. VERDICT chi tiết (14 DONE)

Bảng OOS_pnl 10 window thực (2023-01..2025-07): +764, +2196, +806, +1326, **+7256**(2024Q1), −280, +1178, −38, **−9905**(2025Q1), +310. Tổng ≈ **+3613 / 100k (~+3.6%)** qua 2.5 năm.
- 7 window `TOO_MUCH_CAPITAL_LOCK` (ăn nhỏ, khóa vốn) + 3 window `BURN_ACCOUNT` (w9/w11/w12 lỗ).
- 4 window 2022 (w0–w3) = **ZERO_TRADES** vì selector không có predict trước 2023-01-01 (KHÔNG phải do lưới thô — lưới mịn không tạo lệnh ở nơi không có predict).
- 2 window OOM (w14/w15 = 2025 H2): lỗi kỹ thuật `readDataFromAerospike1M: Java heap space` ngày 2025-09-21. Oracle còn ~21GB RAM trống → chỉ cần bump `-Xmx` worker rồi rerun 2 window đó.

---

## 4. Câu hỏi mở QUAN TRỌNG: "sao 1m tệ hơn 15m (14/16)?"

CHƯA trả lời được chắc chắn — 4 biến đổi cùng lúc giữa 2 run:
1. **Selector khác**: run 15m cũ non-canonical (FIRST_CUTOFF 2022, **fold-0 leak** đã sửa 2026-08-03, OI 15m, universe **unfiltered**). Run 1m mới leak-free + filtered. → Giả thuyết mạnh: **edge 88% cũ một phần là ảo do leak** (đúng câu hỏi project "edge có thực không").
2. **Genome mismatch**: loose_k8 tune trên 15m, áp frozen lên 1m → threshold (MIN_MOMENTUM_15M, TS, DCA grid) không transfer, nhiễu 1m dày → whipsaw + DD tăng.
3. Khác date-range + universe.

**VIỆC CẦN LÀM để phân định:** kéo report run 15m cũ ra diff từng config. Nếu "tệ hơn" do bỏ leak → tin tốt (biết sự thật). Nếu do genome mismatch → phải re-tune genome cho 1m, không dùng loose_k8 frozen.

---

## 5. Việc cần sửa / quyết định (cho session sau)

**Sửa ngay (fragility tôi để lọt):**
- [ ] **Jobstore đang ở 226 (retire-pending)** → move `WFO_STATE_HOST=127.0.0.1` (Aerospike Oracle-local, đã confirm alive). 226 chết giữa run = mất state coordination.
- [ ] **Window scope sinh từ 2022** (default orchestrator) → set để bắt đầu **2023** cho khớp selector coverage, bỏ 4 window rỗng. Riêng việc này nâng posRatio 7/14 → 7/10.

**Quyết định hướng đi (Uni chưa chốt — 3 lựa chọn):**
- (A) **Pivot redesign chiến lược** (đúng nội dung project): tách scalp/hold, sửa asymmetry SL/TP "chặn lỗ khi lãi, nuôi lãi", thiết kế lại selector+gate. Giá trị nhất lúc này.
- (B) **Fix OOM + hoàn tất 2025 H2** (rerun w14/w15 với heap lớn hơn) — rẻ nhưng khó đổi kết luận WFE 0.275.
- (C) **N=30 per-window HPO** — tốn token, N=1 đã FAIL nên rủi ro phí công.
- Ưu tiên đề xuất: làm mục (4) diff 15m-vs-1m TRƯỚC để biết nguyên nhân, rồi mới chọn A/B/C.

**Câu hỏi mở khác:** universe train = filtered top-10% (run này) vs unfiltered như 08-02 — Uni chưa xác nhận nên giữ cái nào.

---

## 6. Plumbing / mechanics (SSH, paths, commands)

**SSH Oracle (161.118.212.3):** dùng Git ssh qua wrapper `C:\Users\pc\_ora2.bat "<remote cmd>"` (shell=cmd). Windows OpenSSH fail dưới bridge (exit 255). nohup phải kèm `</dev/null`.

**wfo_status:**
```
_ora2.bat "export CE_RUN_DIR=/home/ubuntu/claudedata/.run/ce_run CE_LOCKS_DIR=/home/ubuntu/claudedata/.run/ce_locks; cd /home/ubuntu/claudedata/.run; python3 mcp_tools-v3.py wfo_status"
```

**Đọc verdict/report:**
```
_ora2.bat "cd /home/ubuntu/claudedata/.run/oracle_worker_cwd && WFO_STATE_HOST=103.157.218.226 WFO_STATE_PORT=3222 WFO_STATE_NS=ticker WFO_HARNESS_FIX=true java -cp /home/ubuntu/java/simulator/gatecount.jar com.binance.chuyennd.ai_ml.wfo.framework.WfoCoordinator report strategy_window"
```
Report file: `/home/ubuntu/claudedata/.run/oracle_worker_cwd/docs/reports/wfo_strategy_window.md`.

**Launch fanout:** `C:\Users\pc\launch_fanout.sh` (scp lên Oracle). ENV frozen loose_k8 + WFO_HARNESS_FIX=true. build_ds: `C:\Users\pc\build_ds.sh` (chạy từ cwd `oracle_worker_cwd` có config.properties; cần WFO_CODE_SHA).

**Gotchas đã gặp:** fanout cần `CE_RUN_DIR`/`CE_LOCKS_DIR` set (mặc định /workspace → PermissionError). Kaggle: /tmp là tmpfs (RAM) → MMAP_DIR=/kaggle/working. Kaggle cap 5 session, CLI không cancel (`echo y| kaggle kernels delete <slug>`). Oracle heap: worker fanout OOM ở window lớn → cần tăng -Xmx.

**Hosts:** Oracle 161.118.212.3 (build+sim, 23GB RAM). Jobstore/state hiện 226:3222 ns=ticker (RETIRE PENDING — nên chuyển). Aerospike Oracle-local 127.0.0.1:3222 (alive).

**Code selector:** `C:\Users\pc\sel1m_code\gen_funding_wf_predictions_1m.py` (memmap version, verified == full). Kernel base `C:\Users\pc\sel1m_kernel\sel_kernel.py`. Node-split `gen5nodes.py` (NUM=4).

**Docs liên quan trong project:** `wfo_fanout_verdict_canon_k8_2026-08-10.md`, `wfo_fresh_export_exec_2026-08-09.md`, `wfo_data_flow_architecture.md`, `WFO_DATA_PIPELINE_MASTER.md` (repo `E:\educa\...\BinanceFuturesJava\docs`, v1.1.2 = nguồn params canonical).
