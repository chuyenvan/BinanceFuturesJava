# WFO data validation + gap 19840→10502 (2026-08-22)

## ⭐ KẾT LUẬN CUỐI (rà kĩ, đã đính chính) — GAP = NGUỒN TICKER (44 ngày file thiếu phút), KHÔNG phải param/data
**Bằng chứng quyết định:**
- **CONFIG DIFF** baseline(ARM26K5DCAoff,19840) vs canary(TSGUARD_off,10502): `diff config.properties` = **ĐÚNG 1 DÒNG** `TICKER_SOURCE=aerospike` → `file`. Mọi param khác (arm, exit, SL, momentum, TS, budget, TOPK) GIỐNG HỆT.
- **predwf md5 IDENTICAL** (18 fold gate genomes, agg md5 8b23765d14e56798, per-fold SAME) giữa 2 tag.
- **Offline pred/market/funding IDENTICAL** (Agent B: pred.bin byte-identical với aerospike 0/2.76M; market 12/2.8M nhiễu; funding 18/18 md5). → "prediction drift" (giả thuyết ban đầu của tôi) **SAI**.
- **Ticker values IDENTICAL** vs Binance (validate 194k mẫu, 0 mismatch).
- → Khác biệt DUY NHẤT = ticker source. Cụ thể: **44 ngày file ticker THIẾU PHÚT (2024-03-01→04-15, aerospike đủ 1440, file 738-1439)** → file-mode SKIP nguyên ngày → mất trade ở window nặng 2024-2026 (baseline đóng góp lớn w15=5883...). Window sớm không chạm cụm 2024 nên khớp baseline (2-leg ratio 1.02); per-window lệch sớm = NON-DETERMINISM (Oracle 2-worker vs Kaggle), total vẫn khớp.

**ĐÃ FIX (Agent A):** re-export 44 ngày từ aerospike (nguồn đủ), sửa master + zip, **re-version wfo-ticker-2024h1** (ready, ticker_20240309.bin=19MB). 1 ngày 20260602 = gap nguồn thật (aerospike cũng thiếu 38'), không bịa.

**XÁC NHẬN đang chạy:** re-run canary Kaggle (guard PID 502372, 11:50 UTC) với ticker đã fix. Nút thắt: upload offline dataset 4.94GB → ~20-40'. Watcher /tmp/kaggle_canary_result.log. **Kỳ vọng FULL_new ≈ 19840** → chốt 100%.

**Bẫy config cần đưa vào runbook (Agent B):** nếu run quên `WFO_SET_PRED=ai_pred_market_gate_wfo` → rơi default `ai_pred_market_full_basket_v2` (lệch 99.9% predReturn15M) → đảo selection. drive_exp18/build scripts đang set đúng.

---
## (Nhật ký điều tra — giữ lại)

### Gap
- Baseline (Aug21, aerospike ticker): FULL=19840. Canary file-mode (Aug22): FULL=10502 (−49%).

### Đã fix trong ngày (hạ tầng, không phải gap)
1. Aerospike access-address 103.157.218.226→161.118.212.3 (worker hết InvalidNamespace).
2. Ticker 2021-01-24 0-byte → re-export + re-version wfo-ticker-2021.
3. exchange_info path sai → sửa configurable + dump 872 symbol + bundle java-run-lc.

### Validation dữ liệu (so Binance)
- Ticker: 610 symbol, 194,315 mẫu, 0 mismatch (căn GMT+7↔UTC). Full-sym tail (id 780-789) OK, maxId=789<1000 (không tràn mảng).
- Funding: ~350 mẫu, 0 mismatch.
- OI: chưa xong (Binance API 30 ngày; cần Vision cho lịch sử).
- **Completeness (chiều bị bỏ sót ban đầu):** file có 44 ngày <1440 phút (2024-03/04) — CHÍNH LÀ nguyên nhân gap.

### Topology aerospike
- 2 kho: local ns=test (kline_1m_opt 2,952,455) vs .226 ns=ticker (2,909,486). File export từ local ns=test; baseline aerospike đọc .226. Cả hai == Binance ở mẫu kiểm.
- file-mode & aerospike-mode dùng chung SimpleSymbolMapper + set kline_1m_opt.

### Hạ tầng
- SSH Oracle+242 qua desktop-commander Windows (Git ssh.exe C:\PROGRA~1\Git\usr\bin\ssh.exe, key id_rsa_chuyennd, pipe `"tr -d '\r'|bash -s" < file`). Scheduled sandbox KHÔNG ssh được → validate LIVE.
- Box Oracle 4-core/23GB: KHÔNG chạy nổi 2 WfoWorker × ~20g (heavy 2024 window OOM ở 8g) → full-18 local bất khả thi; dùng Kaggle (5 worker) cho canary.
- Tools: /home/ubuntu/tkval/{TickerValidate,TickerRandomCheck,FullSymCheck,FundingOICheck,MinuteCountCheck}.java.
