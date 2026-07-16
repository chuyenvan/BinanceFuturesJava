---
id: 035
status: CANCELLED
depends_on: [013]
touches_live_process: true
writes_242_data: true
resource: heavy_226
checkpoint: false
max_retry: 1
report: docs/reports/035.md
require_review: true
---

# TASK-035: Migrate forward OI (007-C) sang chunk-tháng + ghi đủ LS/taker (đồng schema với 013)

- **status:** TODO. `depends_on: [013]` (schema chunk-tháng chốt ở 013). **`touches_live_process: true`** → sửa `BinanceDataIngestor` ⇒ build + restart = **USER TAY**, gộp đợt deploy.
- **Vì sao:** 013 backfill history ghi **chunk-tháng `SYMBOL_yyyyMM`** (5 set). Forward 007-C hiện ghi OI **1-record/symbol** (`open_interest`/bin `oi_data`) trên 242, và **CHƯA** ghi LS/taker. Lệch schema ⇒ reader (018/038) phải đọc 2 layout. User chốt: **MIGRATE forward sang chunk-tháng + ghi đủ 5 set** — một schema duy nhất.

## Việc
Sửa phần forward OI của 007-C trong `BinanceDataIngestor`, dùng CHUNG `OiMetricSets`/`DataManager...writeMetricMap242` (chunk-tháng) với 013 (một bộ não):
1. **OI**: đổi ghi từ 1-record/symbol → **chunk-tháng `SYMBOL_yyyyMM`** (như 013).
2. **THÊM 4 set LS/taker** từ API realtime, granularity 5m, chuẩn mốc 5m, merge-guard:
   - `oi_ls_toptrader_acc` ← topLongShortAccountRatio
   - `oi_ls_toptrader_pos` ← topLongShortPositionRatio
   - `oi_ls_global_acc` ← globalLongShortAccountRatio
   - `oi_taker_vol` ← takerlongshortRatio
3. **Cleanup key cũ:** 040 (sync history) sẽ phủ chunk-tháng lên 242; forward mới ghi tiếp chunk-tháng; key 1-record cũ (`open_interest` layout cũ) bỏ — dọn sau khi xác nhận reader chỉ đọc chunk-tháng.

## Cơ chế (chốt từ phân tích FundingIngestor/TickerIngestor — 2026-06-15)
- **Chu kỳ poll = ~30'** (không phải 5'). Lý do: 5 endpoint (OI + 4 LS/taker) × ~554 coin, REST **per-symbol** (3 metric này KHÔNG có WebSocket / endpoint all-symbol), throttle 250ms ⇒ 1 vòng quét ~11–12'. 30' để vòng quét nằm gọn + còn dư. Granularity gốc 5m ⇒ điểm mới nhất có thể trễ tới ~30'; chấp nhận vì selector dùng khung chậm (crowdedness), KHÔNG cần realtime. Nếu sau này feature cần OI tươi hơn → chỉ khả thi bằng cách thu hẹp phạm vi (chỉ coin có lệnh/watchlist).
- **Canh giây tránh va chạm:** khung **giây 2–10 đã bận** (TickerIngestor burst 554 kline + entry/DCA chạy giây 5–10). ⇒ ingest OI/LS/taker chỉ ghi ở **giây ~30–50** (trong vòng lặp, nếu đồng hồ ở giây 0–12 thì sleep tới ~13 mới ghi tiếp).
- **Buffer + flush tách thread** (học FundingIngestor): gom điểm theo symbol rồi flush ghi batch, thay vì read-merge-write từng điểm — giảm đọc lại chunk-tháng. Snapshot rồi clear buffer (chống phình RAM).
- **Guard ban GLOBAL** dùng chung `BinanceRestGuard` (như ticker/funding/OI hiện tại); `reportBan` cả khi body trả -1003; `awaitIfBanned` cap 60s/nhịp.
- **KHÔNG dùng settlement-detection** kiểu funding — OI/LS/taker là chuỗi 5m liên tục, ghi theo mốc 5m chuẩn.
- Phát hiện coin mới (pattern `globalSubscribedSymbols`) + heartbeat idle log để biết loop sống.


- `touches_live_process`: sửa Ingestor → **build + restart BinanceDataIngestor = USER TAY** (gộp deploy). KHÔNG auto. KHÔNG đụng BinanceOrderTradingManager.
- SLF4J. `main()` test forward 1 vòng trước. Throttle API (4 endpoint × ~nhiều symbol).

## Validate (require_review, sau deploy)
- Đọc 242 thấy `SYMBOL_yyyyMM` mới cho cả 5 set; LS/taker có data realtime; mốc 5m; ts tiến theo thời gian; KHÔNG đè history (merge-guard); khớp đơn vị với history 013.

## (Code / Kết quả điền)
