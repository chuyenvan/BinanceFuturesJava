# WFO ticker → file-mode migration (root-cause fix for Aerospike WAN EOF)

Date: 2026-08-21. Owner: live/WFO pipeline (box 242 live; Oracle 161.118.212.3 = backtest coordinator + aerospike-wfo docker).

## Vấn đề gốc (đã xác minh, không suy đoán)
WFO Kaggle workers đọc 1m ticker từ Aerospike qua WAN → `readDataFromAerospike1M failed: EOFException` (connection rớt dưới tải concurrent). Chuỗi lớp:
1. **Slug bug** (đã fix): tag `TSGUARD_off` có `_` → slug Kaggle invalid → 403. Fix: sanitize slug trong `drive_exp18.sh` (`SLUG=$(printf %s "$TAG"|tr 'A-Z_' 'a-z-')`). Backup `drive_exp18.sh.bak_slugfix`.
2. **Aerospike advertise private IP** (đã fix, user duyệt): `asinfo -v service` trả `10.0.0.236` (private) → client Kaggle không route được. Fix: thêm `access-address 103.157.218.226` vào `/home/ubuntu/aerospike-wfo.conf` (network.service) + restart docker. Backup `aerospike-wfo.conf.bak_accessaddr_20260821`. Verify: service=`103.157.218.226:3222`. LƯU Ý cold-start replay ns=test (34M obj) mất ~10-16 phút mỗi restart.
3. **Nguyên nhân THẬT**: `TICKER_SOURCE=aerospike` trong `/home/ubuntu/claudedata/java-run-lc-dir/config.properties` (config nhét vào dataset java-run-lc mà kernel dùng). Đọc Aerospike WAN vốn fragile. Nên chuyển `TICKER_SOURCE=file`.

## Vì sao đang để aerospike (không phải vô tình)
Bộ ticker file (`ticker_YYYYMMDD.bin(.gz)`) chỉ phủ **2021-01-01 → 2026-03-01** (1886 file, local `/home/ubuntu/kaggle_data_hpo`, và Kaggle dataset `chuyendinh/hpo-ticker-daily` = 1 file `ticker_bundle.dat` 14GB). WFO fold cuối OOS từ `20260401` tới `WFO_MAX_OOS_DATE=20261001` → file-mode fail các window 2026-04→nay vì thiếu ticker. Aerospike có data tươi nên bị để = aerospike.

## Kiến trúc đã hỗ trợ file-mode (không cần sửa code sim)
- `SimulatorMarketLevelTicker1MStopLoss` (dòng 165-188) dispatch theo `Configs.TICKER_SOURCE`: `aerospike`→`readDataFromAerospike1M`; `file`→`HPOSmartCache.getDataShortFromFile()`→`KaggleDataLoader.loadDailyTickersShort` đọc `kaggle_data_hpo/ticker_YYYYMMDD.bin(.gz)`.
- `run_worker.py` (wfo-worker-1..5) ĐÃ wire: kernel-metadata `dataset_sources` đã có `chuyendinh/hpo-ticker-daily`; run_worker giải nén `ticker_bundle.dat`/`ticker_all.tar` → `kaggle_data_hpo/` (đòi ≥1800 file), HOẶC symlink per-file. WFO_STATE dùng Oracle 161.118.212.3:3222 (state nhẹ, không phải bulk ticker).
- 1m klines thật: `ns=test / set=kline_1m_opt` = 2.95M objects trên Oracle aerospike (phủ ~2021→2026). `AEROSPIKE_SET_NAME_TICKER="kline_1m_opt"`. Export phải chạy với `AEROSPIKE_NAMESPACE=test`.

## Quyết định user: chuyển hẳn file-mode, đóng gói **THEO NĂM**
Lý do: 1886 file lẻ = quá nhiều file (Kaggle mount chậm); 1 bundle 14GB = quá lớn (lag). → ~6 archive `ticker_2021.tar`…`ticker_2026.tar` (mỗi ~2-3GB).

## KẾ HOẠCH THỰC THI (việc nhỏ, verify từng bước)
1. **Export gap 2026-03-02→nay**: jar full build có sẵn trên Windows `E:\...\BinanceFuturesJava\target\binance-java-sdk-1.2.4.jar` (95MB, 2026-08-21, có `ExportTickerDaily.class`). Copy sang Oracle → chạy `ExportTickerDaily 20260302 <today+1> <outDir>` với CWD config `AEROSPIKE_NAMESPACE=test, AEROSPIKE_READ_CLUSTER=226, AEROSPIKE_HOST_226=127.0.0.1` (đọc local, nhanh). Ghi `ticker_YYYYMMDD.bin` (uncompressed).
2. **Gộp + gzip** gap files với 1886 file cũ (2021→2026-03). Chuẩn hoá `.bin.gz`.
3. **Đóng gói theo năm**: `ticker_2021.tar`..`ticker_2026.tar` (mỗi tar chứa .bin.gz của năm đó).
4. **Sửa `run_worker.py`** (5 kernel): giải nén TẤT CẢ `ticker_*.tar` (loop) vào `kaggle_data_hpo/`, không chỉ file đầu. Guard: đếm file ≥ kỳ vọng.
5. **Upload Kaggle**: dataset mới (vd `wfo-ticker-yearly`) gồm 6 tar; update kernel-metadata `dataset_sources` thay `hpo-ticker-daily` bằng dataset mới. Verify `datasets status`=ready.
6. **Flip config**: `java-run-lc-dir/config.properties` → `TICKER_SOURCE=file`; re-push dataset `java-run-lc`. (Giữ backup config aerospike.)
7. **Retest canary file-mode**: relaunch `wfo_guard_run.sh`. Verify: log worker in "TICKER per-file/extract", 0 `readDataFromAerospike1M`, DONE=18 FAILED=0 gồm cả OOS 2026, canary FULL∈[18000,21500].

## Guard/kiểm bắt buộc
- Coverage: sau gộp, phải có đủ ngày tới `<today>`; không gap giữa. WFO windows cần tới ~2026-08 (data thật hết ở đó; WFO_MAX_OOS_DATE=20261001 chỉ là cap).
- `symbol_mapper` + `symbol_lifecycle` snapshot phải có cho file-mode (KaggleDataLoader.loadSymbolMapper/Lifecycle). HPO chạy file-mode OK nên aux đang có ở đâu đó — verify nằm trong dataset attach.
- Không confound canary aerospike đang chạy (PID 438851) bằng cách chạy export nặng cùng lúc trên Oracle.

## Trạng thái nhánh song song
- Canary aerospike-mode + access-address: PID 438851, đang chạy để đo access-address có hết EOF không (Plan B / cho ra số A/B TIME_STOP hôm nay). Check ~14:51 UTC.
