# TASK-019: Fix funding LIVE — FundingFeeManager không refresh + FundingIngestor flush chậm [ƯU TIÊN]

- **status:** REVIEW — code DONE & committed (A lõi `f589309` + wiring+B `027830b`, refresh hết DEAD ở HEAD). Chờ gộp deploy 242 (016 + gỡ-crawl) + verify ts trên 242.
- **owner:** CCD #1 · **updated:** 2026-06-14
- **File:** `research/FundingFeeManager.java` + `websocket/FundingIngestor2AerospikeNew.java`. Production 242/live.

## ⚠️ AN TOÀN
- Live (242). Chỉ THÊM nhánh refresh / sửa nhịp flush; **KHÔNG đổi hành vi backtest** (sim determinism — luật "một bộ não"). SLF4J. Test riêng, KHÔNG tự deploy 242.

## Bối cảnh — một CHUỖI funding-live
`FundingIngestor` flush → Aerospike `funding_data` → `FundingFeeManager` cache → feature/model/trade. Hỏng ở 2 mắt: ingestor ghi chậm (B) + manager không reload (A). Sửa cache mà nguồn ghi chậm vẫn sai → làm CẢ HAI + verify nối chuỗi.

---

## PHẦN A — FundingFeeManager không refresh (isProductionMode dead)
### Bug (đã đọc code, xác nhận)
- `initData()` load TOÀN BỘ funding 1 lần lúc `getInstance()` → cache `symbol2FundingFee` (TreeMap time→rate).
- `isProductionMode` chỉ có `setProductionMode(...)`, **KHÔNG nơi nào ĐỌC** → không nhánh refresh.
- `getNearestFundingFee` dùng `floorEntry` trên cache TĨNH: live chạy lâu → funding mới (ingestor ghi) KHÔNG vào cache; `if (timestamp - entry.getKey() > 24h) return 0.0f` → **sau 24h funding trả 0** (mất hẳn).
- ⇒ feature funding (basketFundingAvg/Avg24H/Trend, B7) + funding classifier + trade live dùng funding cũ → 0. History train đúng → **train/serve mismatch**.

### Yêu cầu A
1. **Đọc `isProductionMode`** (hết dead). Khi `true` → refresh cache funding định kỳ.
   - **Đề xuất:** `setProductionMode(true)` khởi `ScheduledExecutorService` reload funding từ `funding_data` mỗi **N phút** (N ≤ chu kỳ funding; đề xuất 30–60′). Incremental nếu được (chỉ funding sau `lastLoadedTs`) để tránh `getAllFundingMap` nặng; nếu khó → reload per-symbol đang dùng. Atomic-swap per symbol (thread-safe).
   - **Hoặc lazy:** trong `getNearestFundingFee`, nếu production VÀ `floorEntry` quá cũ (> chu kỳ funding) → reload riêng symbol đó.
   - Chốt 1 cách + ghi lý do.
2. **Grep `setProductionMode(true)`** — đảm bảo luồng live THỰC SỰ gọi (đúng thứ tự, trước khi dùng funding). Nếu chưa → sửa. (Không set true thì nhánh refresh vẫn chết.)
3. **Backtest:** `isProductionMode=false` → KHÔNG schedule, load 1 lần như cũ; xác nhận sim cho kết quả y hệt (determinism).

---

## PHẦN B — FundingIngestor flush chậm (log ~1h thay vì 1 phút)
### Triệu chứng (log 2026-06-13 23:13→23:22)
- 9 phút KHÔNG có dòng nào từ `FundingIngestor2AerospikeNew` (trong khi Rest-Kline-Loop mỗi phút, OI-Forward mỗi ~5′). `startFlushLoop` đáng lẽ 60s/lần.

### Yêu cầu B
1. **Phân biệt bug-thật vs log-thưa TRƯỚC khi sửa:** đọc `funding_data` (Aerospike) vài symbol → `ts` mới nhất cách `now` bao lâu.
   - Cách `~vài phút` → flush vẫn ghi đúng, chỉ **log thưa** → sửa log cho phản ánh đúng, **KHÔNG động loop**.
   - Cách `~1h` → ghi chậm THẬT → tìm nguyên nhân: sleep sai đơn vị (phút↔giờ / `60*60*1000`), flush dùng chung thread với polling bị kéo dài, hay exception nuốt làm loop hụt nhịp. Đưa flush về đúng 60s.
2. KHÔNG đổi logic ghi `writeFundingMap` (guard chống mất lịch sử) — chỉ sửa NHỊP/log.

---

## Verify CHUỖI (sau A+B)
- `funding_data` cập nhật đúng nhịp (ts mới nhất gần `now`).
- `FundingFeeManager.getNearestFundingFee` ở production trả funding MỚI (không cũ/0) cho symbol vừa có funding.
- Backtest KHÔNG đổi.

## Deploy (gộp — KHÔNG tự chạy)
- Gộp **gỡ-`startHistoryCrawl`** (log xác nhận vẫn chạy 242 = jar 106baee) + **016** + **019** vào MỘT jar → restart 242 một lần (tránh nhiều lần gián đoạn ingest). Backup jar cũ + rollback. User duyệt thời điểm.

## Acceptance
- [x] A: `isProductionMode` được đọc (qua `setProductionMode`→`startProductionRefresh`); production refresh 30'; `setProductionMode(true)` gọi ở live `initData`; backtest determinism (không gọi → load-once).
- [x] B: xác định **log-thưa-by-design** (buffer rỗng→continue→im); sửa LOG (heartbeat idle), KHÔNG đổi nhịp 60s/`writeFundingMap`. (ts-check tuyệt đối cần 242.)
- [~] Verify chuỗi: logic đúng + compile pass; **chạy thật cần TRÊN 242** (máy dev firewall chặn 242).

## (Code điền)

### A — cách refresh + setProductionMode usage (DONE)
- `FundingFeeManager`: `setProductionMode(true)` → `startProductionRefresh()` (idempotent, `synchronized`, cờ `refreshStarted`) khởi `ScheduledExecutorService` (daemon, tên `FundingFee-Refresh`) chạy `refreshCache()` **mỗi 30'** (N ≤ chu kỳ funding 1h/4h/8h).
- `refreshCache()`: duyệt symbol ĐANG trong cache → `getFundingMap(symbol)` → **atomic-swap per symbol** (`ConcurrentHashMap.put`, thread-safe với reader); BỎ QUA symbol đọc ra rỗng (không xoá cache khi lỗi đọc tạm thời). Symbol mới vẫn lazy-load ở `getNearestFundingFee`. Chọn cách "reload per-symbol-in-cache" thay vì `getAllFundingMap` (nặng, scan toàn set) — chỉ tốn theo số symbol thực dùng.
- **Usage:** trước đây `setProductionMode` KHÔNG nơi nào gọi (dead). Thêm `FundingFeeManager.getInstance().setProductionMode(true)` ở đầu `DetectEntrySignal2TradeNormal.initData()`. Đường tới đây DUY NHẤT: `BinanceOrderTradingManager.main()` → `.start()` → `initData()` (live). Backtest dùng Simulator, KHÔNG đụng class này → `isProductionMode=false` → không scheduler → load 1 lần như cũ ⇒ **determinism**.
- KHÔNG đổi guard 24h trong `getNearestFundingFee` (là staleness-guard hợp lệ; với refresh thì funding luôn tươi nên không còn trả 0).

### B — funding_data ts + nguyên nhân + sửa gì (DONE — log-thưa)
- **Nguyên nhân (đọc code):** `startFlushLoop` ngủ đúng 60s, nhưng `if (fundingBuffer.isEmpty()) continue;` → KHÔNG log khi rỗng. `fundingBuffer` chỉ đầy khi polling phát hiện **settlement** (`nextFundingTime` nhảy mốc) — funding settle theo kỳ (1h/4h/8h), nên đa số phút buffer rỗng ⇒ im log. 9 phút không log (23:13→23:22) = **log-thưa BÌNH THƯỜNG**, KHÔNG phải ghi-chậm: nhịp 60s đúng (60000ms), không sai đơn vị, thread Flush riêng thread Polling, exception được catch-continue.
- **Sửa:** thêm **heartbeat idle** — đếm `idleCycles`, mỗi ~10 phút log `💤 Funding flush idle N phút … flush gần nhất X phút trước`. GIỮ NGUYÊN nhịp 60s + `writeFundingMap` (guard chống mất lịch sử). Reset `idleCycles` + cập nhật `lastFlushMs` khi có flush.
- ⚠️ Xác nhận tuyệt đối (đọc `funding_data.ts` vài symbol so `now`) phải chạy TRÊN 242 — máy dev bị firewall chặn 242:3222 (SocketTimeout). Nếu trên 242 thấy ts mới nhất cách `now` ~ chu kỳ funding → đúng log-thưa (đã sửa); nếu cách >>1 chu kỳ → còn bug-thật cần soi tiếp (loop hụt nhịp/exception).

### Verify chuỗi + backtest determinism
- **Compile:** `mvn -o compile` PASS toàn bộ.
- **Determinism backtest:** by construction — `setProductionMode` chỉ gọi ở live entry; backtest `isProductionMode=false` → load-once, không scheduler → kết quả y hệt.
- **Live (cần chạy trên 242, gộp deploy):** sau A, `getNearestFundingFee` ở production trả funding MỚI (cache refresh 30') thay vì cũ/0 sau 24h; sau B, log funding có heartbeat + dòng flush khi settle. CHƯA chạy thật (firewall).
