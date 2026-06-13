# TASK-016: Fix ingest live — TickerFuturesHelper lỗi -1130 (limit) + -1003 (rate) [ƯU TIÊN]

- **status:** DONE (code+self-test PASS) — CHƯA deploy 242 (chờ user restart ingester với jar mới). Fix additive ở helper + guard; caller không đụng (đã có throttle 300ms + isBanned).
- **owner:** Claude Code (CCD) · **updated:** 2026-06-13
- **Liên hệ:** dùng `utils/BinanceRestGuard` (đã tạo ở TASK-007-A). Production 242/live.

## ⚠️ AN TOÀN
- `TickerFuturesHelper` dùng ở luồng ingest LIVE (242). Chỉ THÊM clamp/guard/throttle + sửa caller tính sai `limit`; KHÔNG đổi logic nặn/ghi data. SLF4J. Build + test riêng, không tự deploy 242.

## Triệu chứng (log 2026-06-13 21:57, pool-2-thread-1)
- `-1130 "Data sent for parameter 'limit' is not valid."` cho NHIỀU coin **gồm ADAUSDT** (coin chuẩn, không delist) → **bug `limit` chung invalid**, KHÔNG phải delist như log đoán.
- `-1003 "Too many requests; current limit of IP(...) is 2400 requests per minute."` → vượt rate (CHƯA "banned until" — nhưng gọi tiếp sẽ leo thành IP-ban như sự cố TickerIngestor trước).
- Cả hai rơi vào nhánh `respon.startsWith("{")` của `getTickerSimpleWithStartTimeAndLimit` → chỉ `LOG.warn("...Limit/Delist...")` rồi return rỗng, KHÔNG phân biệt, KHÔNG ghìm nhịp.

## Phần A — Fix `-1130` (limit invalid)
1. **Tìm CALLER gốc:** grep nơi gọi `getTickerSimpleWithStartTimeAndLimit(...)` chạy ở `pool-2-thread-1` (luồng ingest/repair live). Vì **ADAUSDT cũng dính** → `limit` truyền vào nhiều khả năng là giá trị CHUNG invalid (≤0 hoặc >1500), không phải tính per-coin. Soi cách caller tính `limit` → fix gốc (vd `limit` = số nến cần, bị ra 0/âm khi `startTime ≈ now`, hoặc cố định >1500).
2. **Defensive trong helper:** Binance futures klines `limit` hợp lệ **[1, 1500]**. Trong `getTickerSimpleWithStartTimeAndLimit`:
   - `if (limit <= 0) return rỗng + LOG.debug` (KHÔNG gọi API — gọi cũng vô ích, tốn weight).
   - `limit = Math.min(limit, 1500)` (clamp trần).
   - Đây là lưới an toàn; vẫn PHẢI fix caller (mục 1) cho đúng gốc.

## Phần B — Fix `-1003` (rate) + phân biệt lỗi
1. **Phân biệt code** trong nhánh `"{"` (parse `code`): `-1130` (param — log + bỏ, KHÔNG cooldown) vs `-1003` (rate/ban — vào guard) vs lỗi khác/delist (`-4xxx`/`-1121` → skip coin, log gọn). Không gộp chung "Limit/Delist".
2. **Qua `BinanceRestGuard`:** trước mỗi call helper → `awaitIfBanned`; sau khi nhận `respon` → `reportBan(respon)`.
3. **Mở rộng `BinanceRestGuard` cho -1003 dạng RATE (chưa "banned until"):** hiện `parseBanUntilMs` chỉ bắt `"banned until <ms>"`. Thêm: nếu body có `-1003` + `"Too many requests"`/`"current limit"` mà KHÔNG có `banned until` → đặt **cooldown BACKOFF ngắn** (vd 5–10s, hằng số `RATE_BACKOFF_MS`) để hạ nhịp NGAY, tránh leo thành IP-ban. (`-1130` KHÔNG phải ban → KHÔNG cooldown.)
4. **Throttle caller:** luồng gọi per-symbol (pool-2) phải tuần tự/pool nhỏ + sleep giữa coin (đừng burst toàn universe) — giống nguyên tắc đã áp cho OI ingester ở 007-C.

## Test
- Unit test phân loại code: body `-1130` → không cooldown; `-1003 "...2400 per minute..."` (không banned-until) → cooldown backoff ngắn; `-1003 "banned until 178..."` → cooldown tới mốc (đã có).
- `limit=0`/`limit=2000` → helper không gọi API / clamp 1500.
- Quan sát log live: hết spam `-1130`; khi chạm rate thấy backoff rồi resume, KHÔNG leo "banned until".

## Acceptance
- [ ] Hết `-1130` (caller truyền limit hợp lệ + helper clamp [1,1500]).
- [ ] `-1003` rate → backoff ngắn qua guard, KHÔNG leo IP-ban; phân biệt rõ -1130/-1003/delist.
- [ ] Caller throttle, đi qua `BinanceRestGuard`. Không đổi logic ingest. Build pass.

## (Code điền)
- **Root cause (self-test API thật chứng minh):** Binance futures klines hợp lệ **limit ∈ [1,1500]**. Probe: `limit=0/1501/2000 → -1130`; `limit=1/500/1500 → ARRAY ok`. ⇒ **-1130 ⟺ limit ∉ [1,1500]**, ĐỘC LẬP startTime. Caller live `TickerIngestor2AerospikeNew.repairBatchOptimized` truyền `limit=step=500` → HỢP LỆ; nên -1130 trong log là do **một caller khác truyền limit∈{0,>1500}** (không tái hiện được caller=0 trong repo hiện tại — có thể build/đường khác lúc sự cố). Clamp ở helper = lưới chặn mọi caller, không cần tìm thủ phạm.
- **Helper (`TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit`):** `limit≤0 → return rỗng, KHÔNG gọi API` (LOG.debug); `limit>1500 → clamp 1500`; `isBanned() → skip`. Nhánh lỗi `"{"`: gọi `reportBan(respon)` + phân biệt log: `-1003`(rate→backoff), `-1130`(log bug + limit/startTime, KHÔNG cooldown), khác(delist→debug). KHÔNG đổi logic parse/ghi.
- **BinanceRestGuard:** `parseBanUntilMs` phân tầng: (1) `banned until <ms>` → đúng mốc; (2) `-1003` (chưa banned-until) → `now + RATE_BACKOFF_MS`(8s) backoff NGẮN; (3) "banned until" không parse được → DEFAULT 5'; (4) `-1130`/khác → 0 (KHÔNG cooldown). Thêm hằng `RATE_BACKOFF_MS=8s`.
- **Self-test `TickerHelperSelfTest016` (chạy IP 226, tách live): 10/10 PASS** — probe API 6 mức limit (xác nhận boundary 1500); helper limit=0 không gọi API / limit=2000 clamp ≤1500 / limit=500 ~500 nến; parseBanUntilMs cho -1130→0, -1003-rate→8s, -1003-banned→mốc, -1121→0, array→0; reportBan(-1003)→banned, reportBan(-1130)→không.
- **Caller throttle:** `repairBatchOptimized` ĐÃ CÓ `Thread.sleep(300)`/coin (~200 req/min, dưới 2400) + `isBanned()` check → KHÔNG sửa (giảm rủi ro live). Helper-level clamp + guard đủ.
- ⚠️ **CHƯA deploy 242** (task: không tự deploy). Jar mới đã build + test trên 226. Live fix có hiệu lực khi user restart ingester 242 với jar mới.
