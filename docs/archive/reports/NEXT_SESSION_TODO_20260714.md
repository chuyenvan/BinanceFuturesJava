# HANDOFF — việc làm nốt session sau (2026-07-14)

## Trạng thái hiện tại (ĐÃ XONG)
- **Bug gốc funding forward-fill 15p→phút: ĐÃ FIX** (`WfoDataset.forwardFillToGrid`), dataset `_ff` re-export (funding 175k→2.55M/model), BIG_DOWN hồi 9→145/136. Test 4/4 PASS.
- **3 bug metric WFO: ĐÃ FIX** — WFE median chỉ tính SUCCESS, reset purge orphan, cap OOS≤2026 (`WFO_MAX_OOS_DATE`).
- **Validator A6CountByCadenceValidator: ĐÃ THÊM** (BLOCK coverage<0.95) — tự bắt lỗi thiếu-phút.
- **Kaggle master-worker fan-out: CHẠY ĐƯỢC** — 7 node (2 Oracle + 5 Kaggle) join jobstore REAL 226:3222 ns=ticker. Ticker (`hpo-ticker-daily` v6, 1826 file .bin) + `_ff` ret2 (`wfo-ds-ret2-4h-ff`) + jar (`java-run-lc`) đã trên Kaggle. Launcher 1 lệnh `launch_fanout.sh`. kaggle CLI dùng `~/kaggle_latest_venv` (1.7.4.5) — bug 'type' cũ do venv xgb-env lỗi dep, KHÔNG phải version.
- **Verify Kaggle không lệch: genome tất định 18/18 trùng khít** (tầng-2 w10). Kaggle KHÔNG chậm hơn Oracle cùng nguồn file.
- **Genome: ĐÃ SỬA nguồn còn 17 gene** (bỏ DCA_TIME_BIG_Up chết) — compile RC=0. NHƯNG **CHƯA rebuild/deploy** (jar deploy vẫn 18-gene).
- **Verdict WFO sạch (Oracle aerospike, 18-gene, data _ff):** maxfav3 %OOS 50%/WFE 0.596 > ret2 %OOS 43.8%/WFE 0.307. **maxfav3 nhỉnh hơn ret2.** Cả 2 FAIL vì %OOS<70%.

## VIỆC LÀM NỐT (ưu tiên)

### 1. Sync CONFIG-DRIFT (ƯU TIÊN CAO — số fan-out mới khớp Oracle)
Kernel Kaggle bundle `config.properties` KHÁC Oracle-worker → lệch ~4% pnl (tầng-2: oosPnl 883→847, trades 158→142). Khác biệt:
- `DIED_SYMBOLS`: Kaggle 30 coin survivorship vs Oracle `BTCDOM,USDC` (2).
- Kaggle THIẾU: `NUMBER_ENTRY_EACH_SIGNAL` (Oracle=4, default=2 → nửa entry), `NUMBER_HOUR_FUNDING_CAL`, `FUNDING_MAX/MIN_TRADE`, `BTC_TREND_REVERSE_*`.
**Làm:** sửa `gen_kernels.sh`/`launch_fanout.sh` (trong `~/claudedata/.run/`) để bundle ĐÚNG config.properties = Oracle-worker (đừng dùng bản stale). **Verify:** rerun w10 Oracle với config Kaggle → phải tái lập 883.66/158 (chốt config là nguyên nhân duy nhất). Chi tiết: `docs/reports/KAGGLE_DATA_VERIFY_METHODS.md` mục tầng-2.

### 2. Rework RAM-cache ticker cho VỪA RAM (tốc độ — mỗi window ~77')
Code đã viết (compile RC=0) nhưng cache exact-object **16-24GB > Oracle 23GB → OOM**. Files đã đụng: `HPOSmartCache.java` (FILE_STORE + getDataShortFromFile/clearFileCache), `SimulatorMarketLevelTicker1MStopLoss.java` (nhánh file dùng cache khi USE_SMART_CACHE), `StrategyWfoTask.java` (clearFileCache sau train), entrypoint `VerifyOneWindow`, test `HPOSmartCacheFileCacheTest`.
**Làm:** rework sang **compact-lossless** — giữ `totalUsdt` (thứ CompactDayData cũ làm mất, khiến `isTickerAvailable` sai) trong dạng nén ~4.5GB thay vì raw 16GB. Rồi: `mvn -o test -Dtest=HPOSmartCacheFileCacheTest` → build jar riêng → đo before/after 1 window (`VerifyOneWindow`) trên Oracle: THỜI GIAN giảm + số oosPnl/trades TRÙNG (cache không đổi kết quả). Đo read% thật để biết mức lợi. Runbook: `docs/reports/ramcache_ticker_142.md`.

### 3. Rebuild + deploy 17-gene + chạy 1 vòng fan-out SẠCH
Sau (1)+(2): `mvn -o package` → scp jar Oracle (`/home/ubuntu/java/simulator/binance-futures-preflight.jar`) + upload `java-run-lc` Kaggle. Chạy `launch_fanout.sh` cho **CẢ maxfav3 VÀ ret2** (data _ff, config-synced, ram-cache, 17-gene, WFO_MAX_OOS_DATE=20260101) → verdict sạch + wall-clock. So maxfav3 vs ret2 lần cuối.

### 4. (Bức tranh lớn) Quyết model + tối ưu
maxfav3 đang dẫn nhưng cả 2 FAIL %OOS<70%. Sau khi fan-out sạch: chốt maxfav3 vs ret2, rồi tối ưu (Kaggle distributed — giờ đã nhanh) đẩy %OOS qua 70% + giữ WFE≥0.5, maxDD≤50%.

## Runbook fan-out (tái dùng)
```
# Ticker: chỉ upload lại khi kline đổi (tar → Kaggle tự bung)
cd ~/claudedata/ticker_regen/kaggle_data_hpo && tar cf ~/claudedata/ticker_archive/ticker_all.tar .
source ~/kaggle_latest_venv/bin/activate && kaggle datasets version -p ~/claudedata/ticker_archive -m "..." -r skip
# Mỗi run WFO:
WFO_MAX_OOS_DATE=20260101 bash ~/claudedata/.run/launch_fanout.sh <ds_ff_dir> 2 1 30 ~/claudedata/ticker_regen
nohup bash ~/claudedata/.run/report_watch.sh &   # tự report khi 16 window terminal
```

## Tài liệu liên quan
- `docs/reports/BUGHUNT_WFO_20260713.md` — 4 bug + fix.
- `docs/reports/KAGGLE_FANOUT_PHASE1.md` + `KAGGLE_FANOUT_RESULT.md` — hạ tầng + kết quả.
- `docs/reports/KAGGLE_DATA_VERIFY_METHODS.md` — 3 tầng verify (tầng-2 đã chạy, tầng-3 chưa).
- `docs/reports/ramcache_ticker_142.md` — runbook RAM-cache.
- `docs/reports/DATA_FLOW_AUDIT_20260713.md` — audit luồng dữ liệu.

## Lưu ý
- Monitor nền cũ (bjf6lhntp, byf1fccwl...) có thể còn treo — dọn khi vào session mới.
- KHÔNG mở port Aerospike ra internet (đã phân tích: không an toàn + aerospike-net cap ~2 reader). Giữ ticker = file dataset Kaggle.
- Deploy/restart 2 process live = NGƯỜI tay (CORE.md).
