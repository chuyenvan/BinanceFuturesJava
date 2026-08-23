# WFO file-mode migration — TIẾN ĐỘ & phát hiện (2026-08-21, nối tiếp plan)

## Đã xong
- **Fix slug** (drive_exp18.sh sanitize) + **access-address 103.157.218.226** (aerospike-wfo.conf, restart, verified). Cả 2 có backup.
- Canary aerospike-mode đã KILL (chuyển hướng file-mode).
- Jar full build: copy từ Windows `target/binance-java-sdk-1.2.4.jar` → Oracle `/home/ubuntu/tickexport/full.jar` (có ExportTickerDaily).
- **Export gap DONE**: `/home/ubuntu/tickexport/gapout/` — 165 file `ticker_YYYYMMDD.bin`, phủ **2026-03-02 → 2026-08-13**, 8 ngày rỗng (aerospike KHÔNG có data sau 2026-08-13 → đó là mốc mới nhất khả dụng). Đang gzip nền để giải phóng disk.

## Nguồn ticker & coverage
- File cũ: `/home/ubuntu/kaggle_data_hpo` = symlink → `/home/ubuntu/java/simulator/kaggle_data_hpo/daily` = 1886 file `.bin.gz`, phủ **2021-01-01 → 2026-03-01**. (~9MB/ngày gz)
- Sau gộp: ~2051 ngày, **2021-01-01 → 2026-08-13**, liền mạch. Đủ cho WFO (OOS cuối cần tới ~2026-08).

## RỦI RO / cần xử
1. **Disk Oracle 95% đầy (~11-12G free)**. Đóng 6 tar (~14GB) sẽ không đủ chỗ nếu làm cùng lúc → phải build+upload+xóa TỪNG NĂM.
2. **Aux snapshots cho file-mode**:
   - `core_symbol_mapper`: `SimpleSymbolMapper.init()` LUÔN đọc Aerospike (`loadSymbolMapper()`), KHÔNG branch file. Nhưng đây là 1 read NHỎ (~1000 symbol), không phải bulk → không gây EOF; access-address làm nó tin cậy. → file-mode vẫn cần 1 aerospike read nhỏ lúc init (chấp nhận được).
   - `core_symbol_lifecycle`: `SymbolLifecycleManager` CÓ branch file → đọc `core_symbol_lifecycle` snapshot; thiếu → "cache rong" (WARNING, không crash) nhưng ẢNH HƯỞNG PARITY (lọc symbol theo lifecycle). Nên cấp snapshot để khớp backtest aerospike-mode cũ.
   - Sinh bởi `ExportKaggleBootstrapSnapshots` (đọc Aerospike). `unzip -l | grep` báo không thấy trong jar NHƯNG grep này KHÔNG tin cậy (ExportTickerDaily cũng grep=0 mà vẫn chạy được) → phải THỬ chạy để biết. Hoặc extract từ ticker_bundle.dat hiện có (HPO đang dùng, chắc chắn chứa aux).
3. **Bảo vệ HPO**: KHÔNG sửa dataset `hpo-ticker-daily` (HPO đang dùng ticker_bundle.dat). Tạo dataset MỚI per-year cho WFO, chỉ đổi `dataset_sources` của wfo-worker.

## Còn lại (thứ tự)
1. Xong gzip gap. 2. Sinh/extract aux (core_symbol_mapper + core_symbol_lifecycle). 3. Gộp gap+old → đóng `ticker_2021.tar`..`ticker_2026.tar` (mỗi tar = .bin.gz năm đó; kèm aux vào tar 1 hoặc file lẻ). 4. Sửa `run_worker.py` (5 kernel): loop giải nén MỌI `ticker_*.tar`. 5. Tạo Kaggle dataset mới (per-year) + đổi dataset_sources wfo-worker (bỏ hpo-ticker-daily, thêm dataset mới). 6. Flip `TICKER_SOURCE=file` ở java-run-lc-dir/config.properties + re-push java-run-lc. 7. Retest canary file-mode: verify 0 `readDataFromAerospike1M` bulk, DONE=18 FAILED=0 gồm OOS 2026, FULL∈[18000,21500]. BÁO USER dung lượng mỗi tar TRƯỚC khi upload.
