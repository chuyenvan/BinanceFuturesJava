# WFO canary root cause: aerospike state-store access-address sai (2026-08-22)

## Kết luận ngắn
- **File-mode ticker migration: THÀNH CÔNG.** Worker log: `TICKER per-file symlinked 2051 files -> /kaggle/working/kaggle_data_hpo`, `TICKER total 2051 files`, dataset `WfoDataset: LOAD offline OK: market=2867134 pred=2760442 funding=2295903 (md5 verified)`. Không còn `No space`, không tràn /kaggle/working (symlink tốn ~0 disk). Aerospike EOF khi đọc ticker = HẾT.
- **Bug 1 (state-store): access-address sai** → worker `InvalidNamespace: Namespace not found in partition map: test`. ĐÃ FIX (xem dưới).
- **Bug 2 (data gap): ticker 2021-01-24 = file 0-byte** trong dataset wfo-ticker-2021 → window w00 FAIL-FAST `khong co ticker ngay 20210124 tu nguon file`. ĐÃ FIX (re-export + re-version).

## Bug 1 — access-address
Worker chết:
```
WfoJobStore: state Aerospike RIENG 161.118.212.3:3222 ns=test
com.aerospike.client.AerospikeException$InvalidNamespace: Error 20: Namespace not found in partition map: test
  at WfoJobStore.listAll(WfoJobStore.java:169) / WfoWorker.findAndClaim(WfoWorker.java:125)
```
Nguyên nhân: container `aerospike-wfo` (Oracle, docker, 3222) quảng bá `service-clear-std = 103.157.218.226:3222`. `103.157.218.226` = host `v103-157-218-226.3stech.vn` = cluster 226 (klines), **chỉ có ns=`ticker`, KHÔNG có `test`**. Worker connect `161.118.212.3:3222` bị Aerospike client redirect sang `.226` → không thấy ns=test. Coordinator nối `127.0.0.1` giữ seed connection nên vẫn đọc được → che bug. Public IP Oracle thật = `161.118.212.3` (máy chỉ có IP nội bộ `10.0.0.236`, NAT); lần "fix access-address" trước đặt nhầm `.226`.

Bằng chứng: `hostname -I`=`10.0.0.236 172.17.0.1`; `asinfo -h 103.157.218.226 -p3222 -v namespaces`=`ticker`; local=`test;ticker`, `set=wfo_jobs objects=20`; ns=test persist `storage-engine device file /opt/aerospike/data/test.dat` (restart không mất data); hairpin `161.118.212.3:3222` OPEN; lúc fix 0 java/0 ESTAB (không đụng live).

**Fix:** `/home/ubuntu/aerospike-wfo.conf` `access-address 103.157.218.226 → 161.118.212.3` (backup `.bak_afix_20260822_111421`), `sudo docker restart aerospike-wfo` ~04:14 UTC. Cold-reload ~25GB device file ~10-12'. Sau restart verify: `service-clear-std=161.118.212.3:3222`, `namespaces=test;ticker`, `wfo_jobs=20`, `kline_1m_opt=2952455` (data còn nguyên). Relaunch guard PID 473988 → worker claim được job (`DONE=6 RUNNING=5`, **0 InvalidNamespace**) → fix xác nhận.

## Bug 2 — ticker gap 2021-01-24 (0-byte)
Sau khi Bug 1 fix, w00 FAILED: `RuntimeException: FAIL-FAST: khong co ticker ngay 20210124 tu nguon file`. Trong dataset `wfo-ticker-2021`, `ticker_20210124.bin.gz` = **0 byte** (hàng xóm ~6MB). Master `.../kaggle_data_hpo/daily/ticker_20210124.bin.gz` cũng 0-byte, `gzip -t` = "unexpected end of file". Quét master: **đúng 1 lỗ duy nhất** (2050 file khác OK). = glitch ghi file lần build, KHÔNG phải aerospike thiếu data.

**Fix:** `cd /home/ubuntu/tickexport; java -cp full.jar com.binance.chuyennd.ai_ml.hpo.kaggle.ExportTickerDaily 20210124 20210125` → `ticker_20210124.bin`=5946110 (rong=0, aerospike có data). gzip → 2288796. Patch entry trong `up5/2021/ticker_2021.zip` bằng **python zipfile** (Oracle KHÔNG có zip/unzip CLI): rewrite zip copy 364 entry tốt + thay 0124 → 365 entry, 0 file 0-byte. Fix cả master (`daily/ticker_20210124.bin.gz`). `kaggle datasets version -p up5/2021 -m "fix..." -q` → version mới ready, `datasets files` xác nhận `ticker_20210124.bin=5946110`. Relaunch guard PID 477005 lúc 05:02 UTC.

## Trạng thái & việc còn lại (check-in 05:27 UTC — trig_01SDvNT2pYa1cEZ33hqQvGAW)
- Guard 477005 đang chạy: `drive_exp18.sh` tự `WfoCoordinator reset strategy_window` (18 PENDING) + push 5 worker (kéo ticker version mới).
- Chờ: canary `DONE=18 FAILED=0`, 0 InvalidNamespace, 0 "khong co ticker". FULL_ALL canary ~19840 (khoảng [18000,21500] OK; lệch nhiều = drift, cảnh báo).
- PASS → guard tự chạy A/B `TIME_STOP {off,120,168,240}` → đọc `sweep/wfoguard.log` ([PROP] TS120≠TS0), `wfo_stats` deflated-t (ntests=4), `DONE_TSGUARD_*.txt` (TOTAL_12w, posRatio, maxDD) → báo user.

## Ghi chú hạ tầng (QUAN TRỌNG cho phiên sau)
- SSH tới Oracle CHỈ qua **desktop-commander trên Windows**: `start_process` shell=cmd, `C:\PROGRA~1\Git\usr\bin\ssh.exe -i C:\Users\pc\.ssh\id_rsa_chuyennd ubuntu@161.118.212.3 "tr -d '\r' | bash -s" < C:\Users\pc\xxx.sh` (viết script bằng write_file, pipe stdin — TRÁNH inline `$`; MCP cap 60s → việc lâu thì nohup+poll hoặc list_sessions+read_process_output theo PID). `device_bash` (Linux VM sandbox) & cloud container KHÔNG có route tới Oracle.
- Oracle disk 95% (9.8G free) — cẩn thận khi build/upload.
- fanout drive_exp18.sh: line24 reset, line26 push 5 worker (LATEST dataset), line28 poll 90×30s, break sớm nếu FAILED>=1.
