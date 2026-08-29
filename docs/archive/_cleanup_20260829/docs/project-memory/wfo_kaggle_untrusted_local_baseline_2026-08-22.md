# WFO: Kaggle fanout = nguồn untrusted; local baseline là trusted harness — 2026-08-22

## Finding then-chốt (tìm đúng vấn đề)
Sau khi PROVEN: engine deterministic (VerifyOneWindow ×2 byte-identical), build deterministic
(funding.bin md5 779e2f8e ×2 build), data complete (1613 ngày 0 incomplete) + ticker frozen local
(md5 d521edb0) — chạy reproducibility test qua Kaggle fanout ×2 (REPRO1/REPRO2) vẫn thấy per-window
LỆCH: w4 = 1208.6 vs 1212.4, w5 = 951.2 vs 957.5 (~0.3%), DÙ:
- funding.bin build md5 GIỐNG HỆT (779e2f8e) cả 2 leg,
- nSamples=1 cả 2 (coordinator reset set WFO_N_SAMPLES=1 vào job params),
- sample loop StrategyWfoTask là seeded Random(seed) + SEQUENTIAL → deterministic.

⟹ Input duy nhất KHÔNG được pin = **ticker mà Kaggle workers pull** (dataset_sources
"chuyendinh/wfo-ticker-*" KHÔNG có :version → kernels lấy LATEST; giữa 2 fanout Kaggle serve bản
khác nhau). Cộng thêm **Kaggle kernel flakiness** (REPRO1 FAILED=1 DONE=8; REPRO2 cuối cùng
DONE=7 FAILED=10). 

**KẾT LUẬN: lớp phân phối Kaggle là chỗ UNTRUSTED** (ticker unpinned drift + kernel chết), KHÔNG
phải engine/build/data. Đây đúng là gốc của "mỗi lần ra 1 số".

## Giải pháp: TRUSTED BASELINE chạy LOCAL trên Oracle (bỏ Kaggle)
Chạy WfoWorker LOCAL (đúng production path StrategyWfoTask.runJob, áp full env→Configs canary
DCA-off/K5/arm) tuần tự 18 window, với:
- WFO_DATA_DIR=/home/ubuntu/cmp/ds_base (funding md5 779e2f8e = đúng bản G015 fanout dùng),
- TICKER_SOURCE=file → frozen local corpus (md5 d521edb0, 1613 ngày đủ 1440'),
- WFO_N_SAMPLES=1, coordinator+worker trên 127.0.0.1:3222 ns=test.
→ Không Kaggle ⇒ không flaky, không ticker drift. Deterministic ⇒ reproducible (per-window det đã proven).
Script: C:\Users\pc\wfo_local_baseline.sh → Oracle ~/_localbase.sh. Output ~/localbase/RESULT.txt.
Genome log xác nhận "16 gene | dcaGrid=false" = canary config áp đúng.
LAUNCHED 2026-08-22 18:28 UTC (~60-90 phút, 18 window tuần tự @ -Xmx20g).

## Lưu ý VerifyOneWindow vs Worker (giải thích 2836 vs 3873 ở w10)
VerifyOneWindow main CHỈ áp ABLATION/BREAKER/SMART_CACHE/STATIC_RANK — KHÔNG áp DCA/K5/SIM_* env.
WfoWorker main áp FULL env→Configs (DCA_GRID, SELECTOR_RANK_TOPK=5, SIM_MIN_MOMENTUM_15M=0.008,
SIM_RATE_PROFIT_STOP_MARKET=0.05, TS_GIVEBACK_FLOOR, ...). Nên baseline phải chạy qua WfoWorker
(không phải VerifyOneWindow) để khớp strategy canary. VerifyOneWindow chỉ dùng để CHỨNG MINH
determinism (cùng config ×2 → byte-identical), KHÔNG để lấy số canary.

## Worker config canary (từ run_worker.py, DCA off do guard setcfg)
DCA_GRID_ENABLED=false DCA_TIER_MARGIN_ENABLED=false (canary) DCA_GRID_SCALAR=true DCA_GRID_L1=-0.30
DCA_GRID_STEP=0.20 DCA_GRID_LEGS=3 DCA_GRID_W_RATIO=1.0 DCA_GRID_SCALE=4 TS_GIVEBACK_FLOOR=true
TS_MIN_GAP=0.01 SIM_BREAKER_MODE=OFF SIM_APPLY_FUNDING=true SIM_MIN_MOMENTUM_15M=0.008
SELECTOR_RANK_TOPK=5 SIM_RATE_PROFIT_STOP_MARKET=0.05. WFO_SMART_CACHE=1 (khong doi so).

## Hardening pipeline (khuyến nghị)
1. TRUSTED baseline = local WfoWorker (script trên). Kaggle chỉ để chạy nhanh/thăm dò, KHÔNG để chốt số.
2. Nếu vẫn muốn Kaggle: (a) PIN version ticker dataset trong kernel-metadata (hoặc checksum-gate corpus
   trên worker + fail nếu != frozen d521edb0); (b) thêm retry-until-18/0 (WfoCoordinator chỉ có reset,
   nên retry = reset+push lại, intermittent nên vài lần là được).
3. wfo_trust_run.sh (đã soạn): manifest tự-mô-tả + preflight ticker md5 gate.
4. RETIRE canary band [18000,21500] (neo aerospike 19840 chưa verify). Re-anchor = FULL local baseline ±3%.
