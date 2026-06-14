# TASK-029: Sửa concurrency + position atomic (audit Cao #4/#5/#9)

- **status:** DOING. Nguồn: `docs/PRODUCTION_AUDIT.md` §2/§3. (Phần lớn phân tích TĨNH — verify repro khi sửa.)
- **owner:** CCD-024 · **updated:** 2026-06-14

## ⚠️ AN TOÀN
- Live (P1 ingest + P2 trade). Test riêng, **KHÔNG tự deploy**. SLF4J. Đây là sửa concurrency dễ gây regress — test kỹ trước.

## #4 — Race lost-update cùng key phút (`TickerIngestor:120/285` + `DataManager:151-155`) [P1]
- `Rest-Price-Loop` (3s) và `Rest-Kline-Loop` (chốt phút) cùng `writeMinuteBatch(curMin,...)`; hàm read (getExistingTickersMap) → putAll → put **KHÔNG atomic** → 2 luồng cùng `curMin` có thể mất nến.
- Sửa: khóa theo key phút, hoặc merge phía Aerospike (CDT/operate), hoặc gộp 1 luồng ghi. Repro bằng test ghi đồng thời cùng curMin trước/sau.

## #5 — ForkJoinPool(30) tạo MỚI mỗi batch (`TickerIngestor:225`) [P1]
- `new ForkJoinPool(30)` per-batch, lồng trong `restFetchService(15)` chạy nhiều batch/phút → bùng nổ luồng + tạo/hủy pool mỗi phút.
- Sửa: một pool dùng chung (field, shutdown khi stop), hoặc bỏ tầng batch-15 (đã parallelStream).

## #9 — updatePositionInfo: return không nhả lock + clear-then-fill không atomic (`BOTM:317-351`) [P2]
- Lock "UpdateAllPos" add (317); nhánh `positions==null` return (320-323) KHÔNG remove → kẹt tới timeout 3s. `symbol2Pos.clear()` (327) TRƯỚC putAll (351), không try-catch → exception giữa chừng làm trailing/SL/DCA **mất sạch position tạm thời**.
- Sửa: build map mới rồi **swap** (đừng clear-then-fill map đang đọc); try/finally nhả lock ở mọi đường ra.

## Acceptance
- [x] #4: ghi cùng key phút atomic (khóa/merge) — test đồng thời không mất nến. — striped lock (64) bọc read-modify-write `writeMinuteBatch`; test T1 32 luồng/cùng-phút giữ đủ 32 key PASS.
- [x] #5: pool dùng chung, không tạo/hủy mỗi batch. — field `klineFetchPool` (1 `ForkJoinPool(30)`), bỏ `new ...` per-batch + bỏ shutdown per-call.
- [x] #9: swap map (không clear-then-fill) + try/finally nhả lock. — build 5 map/set MỚI → swap reference; `removeLock` ở finally; test T3/T4 PASS.
- [x] Test riêng (đặc biệt #4/#9 — concurrency), không tự deploy. — `Task029ConcurrencyCheck` 4/4 PASS (không đụng Aerospike/Binance); javac11 PASS. KHÔNG deploy.

## (Code điền) — compile PASS javac11 · test 4/4 PASS · commit pending
- **#4 atomic key phút:** `DataManagerAerospikeFloatSim.writeMinuteBatch` — thêm striped lock 64 stripe theo hash key-phút; cùng phút → cùng stripe → tuần tự hoá `getExistingTickersMap → putAll → put` (atomic trong JVM ingest, 2 luồng Rest-Price/Rest-Kline không mất nến). Bounded, không phình.
- **#5 pool chung:** `TickerIngestor2AerospikeNew` — thêm field `klineFetchPool = new ForkJoinPool(30)` dùng chung; `fetchKlinesForBatch` bỏ tạo pool mỗi batch + bỏ `finally shutdown` (pool sống suốt vòng đời ingest). Trần luồng 30 thay vì đỉnh 15×30=450; hết churn tạo/hủy ~37 pool/phút.
- **#9 swap+finally:** `BinanceOrderTradingManager.updatePositionInfo` — bọc try/finally, `SymbolOrderLockingManager.removeLock(lockName)` ở finally (nhả lock cả nhánh `positions==null` return + exception). Build local `newSymbol2Pos/Margin/marginBig/symbolBuy/symbolSell` rồi SWAP reference (gán `symbol2Pos` CUỐI) — bỏ `clear()`-trước-`putAll` ⇒ reader song song (markPrice executor + processDynamicTP_SL) luôn thấy map đầy đủ, không cửa sổ rỗng. Thêm `removeLock` vào `SymbolOrderLockingManager`.
- **Test:** `trading/Task029ConcurrencyCheck.main()` — T1 striped-lock no-lost-update (32 luồng) · T2 stripe đúng (cùng key→cùng stripe, 1000 phút phủ 48/64) · T3 removeLock nhả sớm (CODE THẬT) · T4 swap không tạo cửa sổ rỗng (reader thấy min=50). **Method thật phụ thuộc Aerospike/Binance → verify runtime khi deploy live (không chạy offline).**
