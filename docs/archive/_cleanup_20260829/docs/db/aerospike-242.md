# db/aerospike-242 — SOURCE market (private)

> Đọc cùng [db/index](index.md). 242 = nguồn chính mọi market data; chỉ 226 tới được.

## Set MARKET (source ở 242, replicate sang 226 khi train cần)
- `kline_1m_opt` (realtime + historical) · `kline_15m_btceth` · `kline_4h_btceth`
- `funding_data` · `open_interest` (+ long/short, taker khi có) · `price_realtime` · `basis`/`premiumIndex` (nếu chốt dùng)

## Ghi 242
- LIVE: `BinanceDataIngestor` + `BinanceOrderTradingManager` chạy TRÊN 242, ghi realtime (`kline_1m_opt`, `funding_data`, `open_interest`, `price_realtime`). Forward `kline_15m/4h` (TASK-031).
- Cào lịch sử: job cào chạy TRÊN 226 (226 có internet + nối 242), **đích ghi = 242**. Tải nặng → Kaggle tải → 226 tạm → 226 đẩy 242 (Kaggle KHÔNG ghi 242 trực tiếp).

## Đã chốt (2026-06-14)
- **PHƯƠNG ÁN A: 242 giữ TẤT CẢ market kể cả historical sâu.** `kline_1m_opt`@242 = 22.25GB từ ~2021-01 → nay; disk 55% free, RAM 82% free → 242 ôm full historical, còn nửa ổ. KHÔNG tách historical sang 226.
- ⚠️ **Backup (repl=1):** 242 replication-factor=1, KHÔNG bản sao → set chỉ-sống-242 (`open_interest`/`price_realtime`/`funding_data`) MẤT nếu hỏng ổ. → 226 replicate làm BACKUP (TASK-034 DONE, tool `ReplicateSet242To226` `cc927e8` đã đẩy 3 set → 226).
- `funding_data_new` = MỒ CÔI (không code ghi/đọc) → có thể xoá khỏi 242 sau (user tay).

## Ranh giới
- ✅ Tác động DỮ LIỆU 242 (lấp gap/aggregate/backfill/replicate/backup) = CCD làm, chạy TRÊN 226 — job data, KHÔNG cần user tay.
- 🔒 Deploy code / restart 2 process live = CHỈ user tay (xem [CORE](../CORE.md)).
