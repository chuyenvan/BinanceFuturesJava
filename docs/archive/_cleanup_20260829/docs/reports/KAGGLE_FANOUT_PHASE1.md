# KAGGLE_FANOUT_PHASE1 — Hạ tầng fan-out WFO (Oracle 4-core + Kaggle 5 node)

> Ngày: 2026-07-13. Mục tiêu: mỗi lần chạy WFO vắt hết tài nguyên (Oracle + 5 Kaggle node) thay vì
> 1 node cày vài tiếng. Hạ tầng TÁI DÙNG, jobstore đặt trên REAL 226 để cả Oracle lẫn Kaggle cùng join.
> Mọi script: `/home/ubuntu/claudedata/.run/` (Oracle). Bản A6-only runner: repo `RunA6Check.java`.

## 0. Kiến trúc chốt (isolation + jobstore)

- **Jobstore phân tán = REAL 226** `103.157.218.226:3222 ns=ticker set=wfo_jobs`
  (env `WFO_STATE_HOST/PORT/NS`). Kaggle tới được 226:3222 (KAGGLE_RULES §3) → cả Oracle lẫn Kaggle join CÙNG store.
- **Tách hoàn toàn với run local**: `wfo_final` (task #24) chạy trên **Oracle-local** Aerospike
  (`getClient226()` → config `AEROSPIKE_HOST_226=127.0.0.1` ns=`test`). Hai Aerospike VẬT LÝ khác nhau
  ⇒ dùng chung type `strategy_window` KHÔNG đụng nhau. `wfo_final` đã **DONE 11:35** (verdict FAIL/REVIEW cả 2).
- **Real 226 chỉ có 1 namespace = `ticker`** (không có `test`) ⇒ bắt buộc `WFO_STATE_NS=ticker`.
- **Ticker nguồn**: mọi node dùng `TICKER_SOURCE=file` (nhất quán, loại confound file≠aerospike).
  Dataset _ff (market/pred/funding.bin) offline + md5-verify; ticker file riêng `ticker_YYYYMMDD.bin[.gz]`.

## 1. Regen ticker sạch + upload Kaggle

- **Tool: đã có sẵn — `com.binance.chuyennd.ai_ml.hpo.kaggle.ExportHpoDataKaggle`** (TÁI DÙNG, không viết mới).
  Args `START END ticker` → ghi `kaggle_data_hpo/ticker_YYYYMMDD.bin.gz`, đúng format
  `KaggleDataLoader.loadDailyTickersShort` (`TreeMap<Long,Map<String,KlineObjectSimple>>`).
  Đọc `kline_1m_opt` qua `getReadClient()` = Oracle-local (ĐÃ ghost-clean 07-07 → nguồn sạch hiện tại).
- ⚠️ **Bẫy**: `ExportHpoDataKaggle.main()` KHÔNG có `System.exit(0)` → ghi xong hết file rồi TREO
  (Aerospike thread giữ JVM). Wrapper `regen_ticker.sh` poll marker `"All data exported"` rồi kill đúng PID.
- **Tốc độ đo thật ~0.4s/ngày** ⇒ full range `20210101..20260301` (~1886 ngày) ≈ **~13 phút export, ~11GB**.
- **Đã regen + verify**: subset smoke `20210101..20220331` = **455 file, 1.4GB** (`/home/ubuntu/claudedata/ticker_smoke/kaggle_data_hpo`).
  Full regen `20210101..20260301` → `/home/ubuntu/claudedata/ticker_regen/kaggle_data_hpo` đang chạy nền.
- **Slug ticker Kaggle: `chuyendinh/hpo-ticker-daily`** (bản cũ 11.4GB sinh 07-04 TRƯỚC ghost-clean → stale).
  Regen mới upload bằng: `bash .run/regen_ticker.sh 20210101 20260301 /home/ubuntu/claudedata/ticker_regen 1`
  (arg cuối `1` = version lên hpo-ticker-daily). Upload 11GB chạy nền (chưa hoàn tất trong phiên này).

## 2. Auto-sync dataset _ff lên Kaggle

- **Script: `.run/sync_ff_kaggle.sh <DS_DIR> <SLUG>`** (tạo dataset nếu chưa có, else version). TÁI DÙNG mỗi lần re-export.
- **Đã chạy ret2**: `sync_ff_kaggle.sh /home/ubuntu/claudedata/wfo_ds_ret2wf_4h_ff chuyendinh/wfo-ds-ret2-4h-ff`
  → dataset **`chuyendinh/wfo-ds-ret2-4h-ff`** đã tạo: `funding.bin 437MB, market.bin 55MB, pred.bin 43MB, manifest.txt`.
- maxfav3: cùng script — `sync_ff_kaggle.sh /home/ubuntu/claudedata/wfo_ds_maxfav3_4h_ff chuyendinh/wfo-ds-maxfav3-4h-ff` (chưa chạy).

## 3. Jar + 5 kernel + launcher 1-lệnh

- **Jar**: rebuild HEAD 07-13 (đã có A6 + StrategyWfoTask BUG1/2 fix) + **thêm class mới `RunA6Check`**
  (A6-only fail-fast, KHÔNG cần Aerospike — vì full gate 22 validator cần source-set không có trên Kaggle).
  PrivateConfig = placeholder `SANITIZED_*` (0 secret). Upload **`chuyendinh/java-run-lc`** (99,399,422 B).
  `config.properties` trong dataset đã sẵn `TICKER_SOURCE=file` + `AEROSPIKE_HOST_226=103.157.218.226`.
- **5 kernel `wfo-worker-{1..5}`**: `.run/kernels/wfo-worker-N/{run_worker.py,kernel-metadata.json}`
  (sinh bằng `.run/gen_kernels.sh`). `run_worker.py`: glob (jar/_ff/ticker) → copy config + symlink ticker
  vào `kaggle_data_hpo` → **A6 fail-fast (RunA6Check, exit3=BLOCK)** → `WfoWorker strategy_window`
  (env `WFO_STATE_HOST=103.157.218.226 PORT=3222 NS=ticker`) → `sys.exit`. `enable_internet=true`,
  `dataset_sources=[java-run-lc, wfo-ds-ret2-4h-ff, hpo-ticker-daily]`.
- **Launcher 1-lệnh: `.run/launch_fanout.sh <DS_DIR> <N_ORACLE> <PUSH_KAGGLE> <N_SAMPLES> <TICKER_BASE>`**
  Chuỗi: (a) A6 fail-fast dataset (abort nếu BLOCK, không phí Kaggle) → (b) `WfoCoordinator reset` nạp job
  vào 226/ticker (purge orphan) → (c) bật N worker Oracle (`TICKER_SOURCE=file`) → (d) push kernel Kaggle
  theo slot trống (≤5) → (e) in status + lệnh poll/report.
  Ví dụ full ret2: `bash .run/launch_fanout.sh /home/ubuntu/claudedata/wfo_ds_ret2wf_4h_ff 2 1 30 /home/ubuntu/claudedata/ticker_regen`

## 4. Smoke test (an toàn, không đụng wfo_final)

Window ngắn: default 12m train + 3m OOS, **chỉ window 0** (OOS 2022-Q1 — có pred, vì pred/gate bắt đầu ~2021-04;
market/funding từ 2021-01), N=5. Store 226/ticker (khác Oracle-local).

- **A6 fail-fast: PASS cả 2 nhánh.**
  - ret2 _ff: market coverage=0.9715, gate=1.0, funding=0.9714 → **WARN** (≥0.95 BLOCK, <0.99 WARN) → **exit 0** (cho chạy).
  - Ép `WFO_COUNT_BLOCK_BELOW=0.98` → market 0.9715<0.98 → **BLOCK → exit 3** (dừng, không cày). ✅
- **Oracle 1 window = 407s** (runJob 381s; N=5, 12m/3m, file ticker). Worker join 226 → claim `strat-w00`
  → backtest train 2021 (SUCCESS, 1931 trades, pnl≈2911) → report DONE về 226 → coordinator report OK.
  (WIN0 OOS=sentinel do 2022-Q1 — không ảnh hưởng kết luận CƠ CHẾ.)
- **Kaggle: JOIN 226 XÁC NHẬN ✅.** Kernel `wfo-worker-1` push OK (v14) → mount 3 dataset (11GB ticker ~3-4')
  → qua A6 fail-fast → `WfoWorker` join REAL 226:3222/ticker → **claim `strat-w00` RUNNING owner=`4f78e0fabad0/33`**
  (hostname container Kaggle, KHÁC Oracle `instance-20260622-1647`) + heartbeat lease. Tức là cả 4 mục smoke Kaggle
  đạt: (i) join 226, (ii) A6 chạy trước worker, (iii) claim+lease job, (iv) đang cày window → report DONE về 226.

**So sánh thời gian 1 window** (cùng window0, N=5, 12m/3m, file ticker): **Oracle = 407s** (runJob 381s).
**Kaggle ≈ ~7 phút** (claim ~12:14 → job **DONE 226** ~12:21) — chậm hơn Oracle chút (đọc ticker từ dataset
mount 11GB chậm hơn SSD local + CPU Kaggle nhỉnh chậm). **Kernel COMPLETE, job DONE về 226 → smoke Kaggle TRỌN VẸN.**
Suy ra full N=30 ≈ ~6× train ≈ **~35–40 phút/window** (Oracle; Kaggle nhỉnh hơn)
(chậm hơn aerospike+SMART_CACHE ~15 phút/window vì file-ticker KHÔNG cache — đọc+gunzip lại mỗi sample).
Lợi ích fan-out đến từ SỐ NODE (7 worker vs 2): 16 window / 7 ≈ 2–3 window/worker ≈ ~1.5–2h wall-clock.

## 5. Checklist còn thiếu để chạy FULL fan-out ret2

- [ ] **Full ticker regen xong + upload 11GB** lên `hpo-ticker-daily` (export ~13' đang chạy; upload 11GB là nút chậm).
      Verify: `kaggle datasets files chuyendinh/hpo-ticker-daily` (số file ~1886, ngày mới).
- [x] Kaggle join 226 CONFIRMED (owner=4f78e0fabad0). [ ] Chờ kernel COMPLETE → job DONE + đo thời gian 1 window Kaggle
      (Verify: `WfoCoordinator status strategy_window` = DONE; `kaggle kernels status chuyendinh/wfo-worker-1` = COMPLETE).
- [ ] (nếu cần) TICKER_BASE cho Oracle worker = `ticker_regen` (full) thay vì `ticker_smoke`.
- [ ] Chạy `launch_fanout.sh` với N=30, cấu hình full window (bỏ `WFO_MAX_WINDOWS`), `WFO_MAX_OOS_DATE=20260101`.
- [ ] Poll tới đủ DONE (16 window) → `WfoCoordinator report strategy_window` → verdict + wall-clock.
- [ ] Dọn: job smoke nằm ở 226/ticker/wfo_jobs — `launch_fanout.sh` dùng `reset` sẽ ghi đè, không cần dọn tay.

### Cải tiến đề xuất (ghi nhận, không bắt buộc Phase 1)
- **File-ticker RAM cache** (tương tự `HPOSmartCache` cho Aerospike): hiện file-ticker đọc+gunzip lại mỗi
  sample → per-window chậm ~2–2.5× so với aerospike-cache. Thêm cache theo ngày cho nguồn file → vừa nhanh vừa fan-out.
- **Type riêng** (`WFO_JOB_TYPE`): hiện dùng chung `strategy_window` (an toàn nhờ tách store vật lý). Nếu muốn chạy
  ĐỒNG THỜI ret2 + maxfav3 trên CÙNG 226/ticker thì cần type/id-prefix riêng (đổi nhỏ `StrategyWfoTask`).
- **maxfav3 _ff** chưa sync (chỉ ret2 cho benchmark) — 1 lệnh `sync_ff_kaggle.sh` khi cần.

## Phụ lục — đường dẫn script (Oracle)
```
/home/ubuntu/claudedata/.run/regen_ticker.sh      # regen ticker + (opt) upload hpo-ticker-daily
/home/ubuntu/claudedata/.run/sync_ff_kaggle.sh     # sync _ff dataset lên Kaggle
/home/ubuntu/claudedata/.run/gen_kernels.sh        # sinh 5 kernel folder
/home/ubuntu/claudedata/.run/kernel_run_worker.py  # template kernel worker (A6 + WfoWorker)
/home/ubuntu/claudedata/.run/kernels/wfo-worker-{1..5}/
/home/ubuntu/claudedata/.run/launch_fanout.sh      # 1-lệnh fan-out
/home/ubuntu/claudedata/.run/smoke_fanout.sh       # smoke 1 window an toàn
```
Repo: `src/main/java/com/binance/chuyennd/ai_ml/validation/preflight/RunA6Check.java` (A6-only fail-fast).
