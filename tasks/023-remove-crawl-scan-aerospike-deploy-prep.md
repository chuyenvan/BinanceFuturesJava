# TASK-023: Gỡ startHistoryCrawl + scan Aerospike điền số thật + chuẩn bị deploy gộp [CCD#1]

- **status:** TODO — tiếp nối recon 021. Giao CCD #1 (nắm live + vừa recon).
- **owner:** CCD #1 · **status:** DONE (P1 gỡ-crawl `b231b6d`; P2 scan `ff579a6` đo CẢ 226+242 — chạy TRÊN 226 2026-06-14 10:40; P3 runbook `docs/DEPLOY_242.md`). 242: funding/OI forward ghi live OK, kline historical@242 có, lifecycle rỗng. Deploy gộp = việc user duyệt. · **updated:** 2026-06-14
- **Liên hệ:** recon `docs/STATUS_RECON.md` §3 (crawl chưa gỡ) + §4.6 (số Aerospike chưa đo). 019 đã commit `027830b`, 016 `3704b6e` — chờ gộp deploy.

## Phần 1 — GỠ startHistoryCrawl (recon xác nhận VẪN trong code)
- `OpenInterestIngestor2AerospikeNew.java`: bỏ gọi `startHistoryCrawl()` (~dòng 49) + xóa/vô hiệu định nghĩa (~dòng 67, thread `OI-History-Crawl`). History OI → TASK-013 (metrics). Forward-poll giữ nguyên.
- Commit. Lý do: tránh tải thừa + lệch đơn vị trước khi 013 backfill.

## Phần 2 — SCAN Aerospike điền số thật (đọc-only, chạy TRÊN 226)
Recon không đo được từ dev (242 firewall, không CLI). Chạy 1 tool Java scan đọc-only trên 226 (226 thấy cả 242), ghi kết quả vào **`docs/STATUS_RECON.md`** (mục mới "§5 Aerospike thực đo") hoặc file `docs/aerospike_state.md`:
- **009:** ts mới nhất `kline_15m_btceth` / `kline_4h_btceth` trên **242** (live) và 226 → forward-rolling đã bật chưa (ts có tiến quá 2026-06-07 không).
- **007-C/013:** set `open_interest` trên 242 — có data? #record + range ts (forward poll 007-C đã ghi gì).
- **010:** set `symbol_lifecycle` (226+242) — rỗng hay có? (builder chưa chạy → kỳ vọng rỗng; xác nhận).
- **019:** `funding_data` trên 242 — ts mới nhất vài symbol (funding live có tươi không sau khi 019 wiring vào HEAD — nhưng CHƯA deploy nên kỳ vọng vẫn cũ; đo để biết mốc trước deploy).
- ⚠️ Scan đọc-only, nhẹ; KHÔNG ghi/sửa set. Điều phối 226 (đừng đụng job nặng khác).

## Phần 3 — Chuẩn bị runbook deploy GỘP (KHÔNG tự chạy)
Gộp **016 + 019 + gỡ-crawl (Phần 1)** vào một jar. Runbook `docs/DEPLOY_242.md`:
- Backup jar đang chạy (rollback).
- Build jar mới (gồm 3) + scp lên 242.
- Restart ingester 242 theo **pid-file** (không pkill/killall java).
- **Verify sau restart:** log hết `-1130`; **hết `OI-History-Crawl`** (xác nhận gỡ); thấy log `FundingFee-Refresh` 30′ + heartbeat funding idle; `price_realtime` BTC + `open_interest` ghi 242 (007-B/C lần đầu verify được); Reporter/Telegram còn chạy.
- Rollback nếu ingest gap bất thường.
- User duyệt thời điểm + bấm chạy.

## An toàn
- Phần 1 sửa code + commit (chỉ gỡ crawl, không đụng forward/ghi). Phần 2 đọc-only. Phần 3 viết runbook, KHÔNG tự deploy. SLF4J.

## Acceptance
- [x] startHistoryCrawl gỡ + commit; build pass. → `b231b6d` (javac 11 PASS).
- [x] Số Aerospike thật điền vào recon (`STATUS_RECON.md §5`): **226 + 242 đo thật xong** (chạy tool TRÊN 226 lúc 2026-06-14 10:40). 242: funding 5974đ ts 06-14 07:00 (tươi), OI 622 sym ts ~5-10m, kline historical@242 tới 06-07, lifecycle rỗng.
- [x] `docs/DEPLOY_242.md` đủ backup/scp/restart-pid/verify/rollback.
- [x] KHÔNG tự deploy.

## (Code điền)
- **Phần 1 commit gỡ crawl:** `b231b6d` — bỏ gọi `startHistoryCrawl()` + xoá method + helper `crawlHistoryForSymbol` + 2 hằng `HISTORY_LOOKBACK_MS`/`PAGE_LIMIT`; forward poll giữ nguyên; tiện thể fix `catch` nuốt-câm trong forward → `LOG.warn` kèm symbol. Compile javac 11 PASS.
- **Phần 2 số Aerospike thật:** tool `ai_ml/validation/data/AerospikeStateScan.java` (commit `ff579a6`, đọc-only, scan 242+226). **Đo 2026-06-14 08:45 GMT+7 từ dev** → 242 client null (firewall), **226 đo thật** (xem `STATUS_RECON.md §5`):
  - `funding_data@226` BTC/ETH 5954 điểm, ts-cuối 2026-06-07 15:00 (226 snapshot đứng yên — đúng).
  - `open_interest@226` = **0 record** (226 không có OI; forward ghi 242).
  - `kline_15m/4h_btceth@226` mỗi set 132 key-tháng, BTCUSDT startMs-cuối 2026-06-07 (forward chưa bật — khớp 009).
  - `symbol_lifecycle@226` = **0 record → RỖNG** (xác nhận builder 010 CHƯA chạy).
  - **242 (live) còn trống** → chạy lệnh trong `STATUS_RECON.md §5` TRÊN 226 để điền (funding tươi/OI forward/kline forward/lifecycle).
- **Phần 3 runbook path:** `docs/DEPLOY_242.md` — gộp `3704b6e`(016)+`027830b`(019)+`b231b6d`(gỡ-crawl); restart CẢ ingest+trading theo pid-file (019-A ở trading); verify hết -1130/hết OI-History-Crawl/thấy FundingFee-Refresh+heartbeat/242 ghi được; rollback theo `.bak`.
