# VERDICT 10k-vs-20k: GIẢI DỨT ĐIỂM = Kaggle đọc ticker aerospike .226 qua WAN (Error -16) — 2026-08-23

## ⭐ ROOT CAUSE XÁC ĐỊNH (từ log kernel Kaggle) + ĐÃ FIX
Kaggle workers đọc ticker từ **AEROSPIKE .226 (ns=ticker) qua WAN**, KHÔNG từ file .bin:
- Log worker-3/5: `DataManagerAerospikeFloatSim [AEROSPIKE-READ] readDataFromAerospike1M lỗi ngày 20241001:
  batch read failed after 4 retries` + `[AEROSPIKE-RETRY] BatchRecords chunk keys=720 lần 4/4: Error -16`
  → `WfoWorker job strat-w15 FAIL`.
- Nguyên nhân: java-run-lc config trên Kaggle bị lật `TICKER_SOURCE=aerospike` + `AEROSPIKE_READ_CLUSTER=226`
  (re-upload Aug22 12:46). Dù run_worker.py stage .bin sẵn (comment còn ghi "TICKER_SOURCE=file"), config
  aerospike khiến worker đọc kline_1m qua WAN .226 → batch 720 key/chunk → Error -16 (timeout/conn) → fail.
⟹ Giải THÍCH CẢ HAI: (1) worker fail 12/16 = WAN read chập chờn; (2) 10k = đọc kho aerospike .226
  (ns=ticker, ~2.91M, coverage A6 0.971) KHÁC file corpus local (d521edb0, đủ) + nhiều fail → partial → ~10k.
LƯU Ý: content-compare ticker-file (1476/1477 identical) KHÔNG áp dụng khi aerospike-mode — workers bỏ qua .bin.

## FIX ĐÃ ÁP + VERIFY LIVE
- Sửa /home/ubuntu/claudedata/java-run-lc-dir/config.properties: TICKER_SOURCE=aerospike→**file** (backup .bak_ticker_*).
- Re-upload: kaggle datasets version java-run-lc → LIVE 2026-08-23 05:02. Verify tải lại: TICKER_SOURCE=file ✓.
- Từ giờ workers dùng .bin đã stage (từ Kaggle wfo-ticker-*, content ≈ local 1476/1477) → hết WAN read,
  hết Error -16, dùng đúng ticker → kỳ vọng fanout ~20k + DONE đủ (không fail hàng loạt).
- CHƯA verify bằng fanout thật (cần 1 fanout sạch để xác nhận DONE=16/16 + FULL~20k).

## Baseline THẬT = local 20240.8 (16w, 88% dương, deterministic, sealed). 
Đã loại: engine det, build funding/pred det, cache identical, ticker file content ok.
market.bin drift (aerospike market_data set trôi) vẫn là mục cần FREEZE trong seal (dùng ds_base fb4d62e4).

## Việc tiếp
1. [tuỳ chọn] 1 fanout sạch verify fix → DONE=16/16 FULL~20k (Oracle 1 job: build+coordinate; Kaggle compute).
   Dùng ds_base sealed reuse (tránh market rebuild-drift). Parity: 1 window local đối chứng.
2. Bổ sung parity-gate lâu dài: worker preflight checksum ticker+dataset == SEAL, lệch → EXIT fail-loud.
3. Sau đó phần chiến lược: SL/TP nuôi-lãi/chặn-lỗ, OOS 3mo/1mo (train 4yr expanding-capped=recompile), backtest live-config.

## Ops kỷ luật: Oracle CHỈ 1 job; KHÔNG 4yr-train/full-continuous local (thrash 23GB); local WFO an toàn
12mo-train+SMART_CACHE=0+-Xmx16g; coi chừng disk (đã full 100% do download 15GB). aerospike-wfo docker,
sau reboot ~10min load {test}.
