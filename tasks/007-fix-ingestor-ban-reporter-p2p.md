# TASK-007: Live ingestor/log — fix REST-ban + Reporter(BTC,P2P) + OI ingest + gom log entry

- **status:** TODO (ops/live — ngoài mạch rebuild). Giao CCD.
- **owner:** _(điền khi claim — đồng bộ `docs/AGENTS.md`)_ · **updated:** _(điền)_
- **Gộp (theo yêu cầu):** A = fix vòng-lặp-giữ-ban REST (tách guard CHUNG); B = Reporter thêm giá BTC + 2 giá P2P + test in màn hình; C = ingest Open Interest FORWARD (vá T-1→now; history 2020+ = TASK-013) tích hợp `BinanceDataIngestor` chạy NGAY; D = gom log `DetectEntrySignal2TradeNormal` còn 1 dòng/phút.

## ⚠️ AN TOÀN — đọc trước
- `TickerIngestor2AerospikeNew` và `Reporter` chạy trên **PRODUCTION 242 (live)**. KHÔNG đổi logic nặn nến / ghi Aerospike / đặt lệnh / gửi Telegram khi test. Chỉ **THÊM** lớp guard (A) và **đọc + thêm field** (B).
- SLF4J (`LOG.*`), KHÔNG `System.out`.
- Build + test phần mới RIÊNG; KHÔNG tự ý deploy 242 — báo user trước.

---

## PHẦN A — Fix REST-ban ("đã lock, càng gọi lock càng tăng")

### Bối cảnh (đã đọc code — sự thật)
- `websocket/TickerIngestor2AerospikeNew.java`, 2 luồng REST + repair:
  - `Rest-Price-Loop`: GET `/fapi/v1/ticker/price` mỗi **3s** (1 request toàn thị trường, 2 weight).
  - `Rest-Kline-Loop`: mỗi phút (giây 2–10) GET `/fapi/v1/klines?...&limit=2` cho **~554 coin SONG SONG** (`ForkJoinPool(30)` trong `fetchKlinesForBatch`) = **burst lớn → nguồn ban chính**.
  - `startDataRepair` / `repairBatchOptimized`: gọi REST vá data.
- Khi Binance ban IP: HTTP 418/429 + body JSON `{"code":-1003,"msg":"...banned until <ms_epoch>. Please use the websocket..."}`.
- `utils/HttpRequest.getContentFromUrl`: với HTTP≥400 đọc `getErrorStream()` → **TRẢ BODY** (KHÔNG ném exception, KHÔNG trả status code); còn **tự retry tới 5 lần** khi lỗi kết nối → có thể khuếch đại số call lúc ban. ⇒ chỉ phát hiện ban được bằng **parse body**.
- Hiện tại: Price-Loop nhánh `response.startsWith("{")` **chỉ `LOG.warn` rồi `sleep(3000)` → gọi lại** ⇒ mỗi call khi đang ban GIA HẠN ban. Kline-loop/repair nuốt lỗi vẫn gọi ⇒ giữ ban.

### Yêu cầu (làm đúng, tránh code đơn giản mà lỗi)
1. **Cooldown GLOBAL theo IP — TÁCH class chung** `utils/BinanceRestGuard` (vì OI ingester ở phần C cũng phải tôn trọng cùng ban — ban theo IP nên cooldown phải DÙNG CHUNG một chỗ, không mỗi class một biến). Class chung gồm: `static AtomicLong BANNED_UNTIL_MS`, `parseBanUntilMs(body)`, `isBanned()`, `reportBan(body)`, `awaitIfBanned(capMs)`. Các hàm mục 2–6 dưới đây nằm trong guard này; MỌI REST caller (ticker price + kline + repair + funding + OI) gọi `BinanceRestGuard.*`.
2. **Parse ban an toàn** — `static long parseBanUntilMs(String body)`:
   - null/blank → `0`.
   - chứa `"-1003"` HOẶC `"banned until"`: regex `banned until (\d+)` lấy nhóm số → `parseLong` → return.
   - có `-1003` nhưng KHÔNG match số → return `now + DEFAULT_COOLDOWN_MS` (`DEFAULT_COOLDOWN_MS = 5*60_000`) (fallback, KHÔNG để lọt → gọi tiếp).
   - không phải ban → `0`.
   - ⚠️ regex phải anchor `banned until ` để KHÔNG bắt nhầm số trong IP (`103.157...`).
3. **Set cooldown** khi `>0`: `REST_BANNED_UNTIL_MS.updateAndGet(prev -> Math.max(prev, banUntil + SAFETY_BUFFER_MS))` (`SAFETY_BUFFER_MS = 10_000`). Atomic-max để nhiều luồng/nhiều response KHÔNG ghi đè bằng giá trị gần hơn. `LOG.warn` **một lần** khi giá trị mới > prev (tránh spam mỗi 3s).
4. **Guard TRƯỚC mọi REST call**:
   - Price-Loop: đầu mỗi vòng `while`, nếu `now < REST_BANNED_UNTIL_MS.get()` → `Utils.sleep(min(until-now, 60_000))` rồi `continue` (KHÔNG gọi endpoint). Cap 60s/nhịp để không kẹt thread + cho phép tái kiểm.
   - Kline-Loop: trước khi submit batch, nếu đang ban → skip phút đó (sleep ngắn rồi `continue`).
   - `fetchKlinesForBatch` (parallelStream): đầu mỗi coin `if (now < REST_BANNED_UNTIL_MS.get()) return;` (short-circuit khi dính ban giữa chừng).
   - `repairBatchOptimized`: tương tự trước mỗi coin.
5. **Phát hiện ban ở mọi nơi nhận response**:
   - Price-Loop nhánh `"{"`: gọi `parseBanUntilMs(response)` → set cooldown (thay vì chỉ log).
   - `fetchKlinesForBatch`: hiện nuốt lỗi/không xét body → THÊM kiểm `parseBanUntilMs(response)` → set cooldown (klines khi ban cũng trả body -1003).
6. **KHÔNG sửa `HttpRequest`** (dùng chung nhiều nơi) — xử toàn bộ ở tầng gọi trong `TickerIngestor2AerospikeNew`.
7. **Giữ nguyên** nặn nến / ghi Aerospike / repair khi KHÔNG ban — chỉ thêm guard + parse + cooldown.
8. Lưu ý: `banUntil` là **ms epoch UTC** → so trực tiếp `System.currentTimeMillis()`. Nếu `banUntil < now` (body cũ) → `now<until` tự false, không sleep.

### Test phần A
- Unit test `parseBanUntilMs` với mẫu THẬT từ log:
  - `...banned until 1781262464241. Please use...` → `1781262464241`.
  - body mảng giá `[...]` bình thường → `0`.
  - body có `-1003` không kèm số → fallback `now+5'`.
- Log quan sát: set cooldown in `🔒 REST banned, cooldown đến <yyyy-MM-dd HH:mm:ss>`; call đầu sau khi hết in `✅ Hết cooldown, resume REST`.

### (Phòng TÁI ban — KHÔNG làm trong task này, ghi để bàn sau)
Burst Kline 554 req/phút là nguồn ban gốc; tôn-trọng-ban chỉ chữa vòng-lặp-giữ-ban, KHÔNG giảm khả năng ban lại. Hướng sau (cần user duyệt vì đụng ingest core): throttle batch + sleep giữa, hoặc chuyển price/kline sang **websocket stream** (đúng khuyến nghị Binance trong msg). → DEFERRED/bàn riêng.

---

## PHẦN B — Reporter: thêm giá BTC (Aerospike) + 2 giá P2P

### Bối cảnh (đã đọc code)
- `trading/monitor/Reporter.java` → `buildReport()`: `calReportRunning` (Balance / marginRun / Running orders) + `LogMonitor.getStats(4)` → `Utils.sendSms2Telegram`. Chạy định kỳ (~30', scheduler ngoài — KHÔNG cần đụng scheduler).
- Giá realtime: `DataManagerAerospikeFloatSim.writePriceRealtime` ghi set **`price_realtime`** trên **242**, key = symbol UPPERCASE, bin `price` (Float) + bin `ts` (long ms). Chưa có hàm đọc 1 symbol (chỉ `getAllPriceRealtimeLegacy` scan toàn bộ).
- `client/BinanceP2PTracker.fetchP2PBestPrice(tradeType, transAmount)`: POST `p2p.binance.com/.../adv/search`, fiat VND, asset USDT, rows 10, `transAmount="5000000"`; mỗi item `data[i].adv.price` (String). BUY = mua USDT vào; SELL = bán USDT ra. Hiện CHỈ log, không trả dữ liệu.

### Yêu cầu
1. **Check logic Reporter** — đọc & nhận xét (KHÔNG sửa trừ khi rõ lỗi, báo trước): logic reset-by-15m, null-safety `umInfo`/`getAccountUMInfo`, cách tính `marginRunning`. Ghi vào (Code điền).
2. **Giá BTC từ Aerospike**:
   - Viết `DataManagerAerospikeFloatSim.getPriceRealtime(String symbol): Float` — đọc **242** (KHÔNG 226, vì price_realtime chỉ live ghi 242), key = `symbol.toUpperCase()`, bin `price`; null-safe; đọc kèm bin `ts` để tính tuổi data.
   - Reporter thêm dòng: `BTC: <price>$ (cập nhật <now-ts> trước)`; null → `BTC: N/A`.
3. **2 giá P2P** trong `BinanceP2PTracker`:
   - Refactor tách `static Double getLowestPrice(String tradeType, String transAmount)` — dùng LẠI payload/logic y hệt `fetchP2PBestPrice` (VND / USDT / rows 10 / transAmount), parse `data[].adv.price`, trả **MIN toàn list** (duyệt hết, KHÔNG dựa thứ tự sort của sàn). Empty/lỗi → `null`. Giữ nguyên `fetchP2PBestPrice` (bản log) cho `main`.
   - Reporter gọi `getLowestPrice("BUY","5000000")` (mua USDT thấp nhất) + `getLowestPrice("SELL","5000000")` (bán USDT thấp nhất), thêm dòng `P2P: mua thấp nhất <x> | bán thấp nhất <y>`. Bọc try-catch RIÊNG để lỗi P2P KHÔNG làm hỏng cả report (null → `N/A`).
4. **TEST IN MÀN HÌNH cho user view (quan trọng)**:
   - Viết main/test RIÊNG, in (LOG) 3 giá trị: giá BTC (Aerospike 242), P2P mua thấp nhất, P2P bán thấp nhất.
   - KHÔNG chạy full `buildReport()` khi test (tránh gửi Telegram thật + gọi account live). Test độc lập phần mới trước.
   - **Dán kết quả console vào (Code điền)** để user xem TRƯỚC khi ghép vào report chính thức.

---

## PHẦN C — Ingest Open Interest FORWARD (history → TASK-013) → BinanceDataIngestor

### Bối cảnh (đã đọc code)
- `BinanceDataIngestor.main` start `FundingIngestor2AerospikeNew` + `TickerIngestor2AerospikeNew`. Mẫu Funding: `startPollingLoop` (poll endpoint TOÀN SÀN 30s → buffer `Map<symbol,Map<Long,Float>>`) + `startFlushLoop` (mỗi phút `DataManagerAerospikeFloatSim.writeFundingMap` → set `funding_data`, Snappy Map<Long,Float>, có GUARD chống mất lịch sử: đọc cũ → merge → không ghi đè rỗng).
- Binance OI API:
  - Current per-symbol: `GET /fapi/v1/openInterest?symbol=` → `{openInterest, time}`.
  - History per-symbol: `GET /futures/data/openInterestHist?...` (≥2d gần, giới hạn Binance). ⚠️ **History sâu (2020+) KHÔNG lấy từ API này** mà từ dump `data.binance.vision/metrics` (**TASK-013**). 007-C chỉ dùng forward.
  - ⚠️ **OI KHÔNG có call toàn sàn** → phải gọi PER-SYMBOL (~554 calls) → **burst** → góp phần ban. BẮT BUỘC throttle + `BinanceRestGuard`.

### Yêu cầu
1. Class `websocket/OpenInterestIngestor2AerospikeNew` (khuôn theo FundingIngestor):
   - **History KHÔNG cào ở đây** → đã chuyển **TASK-013** (`data.binance.vision/metrics`, 2020→T-1, đầy đủ + có cả long/short & taker). 007-C CHỈ lo **FORWARD**.
   - **Forward poll:** vòng lặp **mỗi 5 phút** (OI đổi chậm) duyệt symbol gọi `openInterestHist period=5m limit=1` (hoặc `/fapi/v1/openInterest`), buffer → flush. THROTTLE tuần tự (hoặc pool ≤5 + sleep) — **KHÔNG** parallel 30-luồng kiểu kline. Guard ban trước mỗi call + `reportBan(response)`.
2. Lưu Aerospike: hàm mới `DataManagerAerospikeFloatSim.writeOpenInterestMap(String symbol, Map<Long,Float> oiByTs)` — set mới `open_interest`, Snappy Map<Long,Float> per symbol, **bắt chước `writeFundingMap`** (gồm guard chống mất lịch sử). Value = `sumOpenInterestValue` (USD notional — chuẩn hoá cross-coin tốt hơn contracts). Ghi **242**.
3. Tích hợp `BinanceDataIngestor.main`: thêm `new OpenInterestIngestor2AerospikeNew().start();` (thread riêng, KHÔNG đụng ticker/funding). Chạy NGAY để tích luỹ forward.
4. ⚠️ An toàn: OI thêm REST call → BẮT BUỘC qua `BinanceRestGuard` + throttle để KHÔNG góp ban (vừa fix ở phần A). KHÔNG đụng luồng ticker/funding.

### Ghi chú về sau (ADR-0011)
OI forward này là nguồn feature cho funding model version SAU (OI level / ΔOI / OI-price divergence / OI×funding). History ~30 ngày nên CHƯA đủ cho train 2021+ — phải tích luỹ dần. Long/short ratio cùng cơ chế, thêm sau nếu cần.

---

## PHẦN D — Gom log `DetectEntrySignal2TradeNormal` (mỗi phút 1 dòng)

### Bối cảnh (đã đọc code)
- `createOrderBuyRequest` được gọi trong vòng lặp CUỐI `checkMarketLevelChange2Trade` (duyệt TOÀN BỘ `sortedCandidates` với `PREDICT_SYMBOL_TRADE`) → in MỖI coin: `AI CHECK [sym] Pred:… -> Decision` + `❌ SKIP ORDER […] symbolPred:…` (hoặc `✅ AI PASS`). Mỗi phút = cả mớ dòng REJECT; market pred (return15M/24H/risk4H) GIỐNG NHAU mọi coin, chỉ `symbolPred` khác.

### Yêu cầu (CHỈ đổi LOG, KHÔNG đổi logic quyết định)
1. Thêm tham số `List<String> rejectCollector` (nullable) vào `createOrderBuyRequest`:
   - `levelChange == PREDICT_SYMBOL_TRADE` **và** `rejectCollector != null` **và** REJECT → KHÔNG log per-coin; `rejectCollector.add(String.format("%s(%.3f)", symShort, symbolPred))` (symShort = bỏ "USDT").
   - Các levelChange khác / collector null → GIỮ log cũ (AI CHECK + SKIP/PASS).
   - PASS (vào lệnh) → luôn GIỮ `✅ AI PASS` (ít, quan trọng).
2. Vòng lặp `PREDICT_SYMBOL_TRADE`: tạo `List<String> predictRejects = new ArrayList<>()` truyền vào; sau vòng lặp, nếu không rỗng + `predictData != null`:
   `LOG.info("🔕 [PREDICT fail {}] market[15M:{}% 24H:{}% Risk4H:{}%] Min15M:{}% | {}", predictRejects.size(), fmt(return15M*100), fmt(return24H*100), fmt(risk4H*100), fmt(MIN_MOMENTUM_15M*100), String.join(" ", predictRejects));`
   → 1 dòng: số fail + market pred (1 lần) + ngưỡng + list `SYM(symbolPred)`.
3. Các nơi gọi `createOrderBuyRequest` KHÁC (symbol2BUY, DCA) truyền `null` → log như cũ (kèo vào lệnh thật cần log rõ).
4. Null-safe: `predictData` có thể null (aiBrain null) → guard trước khi format dòng tổng hợp.

### Test phần D
Log live: 1 dòng `🔕 [PREDICT fail N] … SYM(0.320) SYM(0.327)…` thay mớ dòng cũ; lệnh vào thật vẫn `✅ AI PASS` + `Push redis order`.

---

## Acceptance
- [x] (A) Khi bị ban: KHÔNG còn gọi REST trong `banned until + buffer` (guard 4 chỗ qua BinanceRestGuard); log vào/ra cooldown; unit test `parseBanUntilMs` PASS 6/6.
- [x] (A) Không đổi hành vi ingest khi KHÔNG ban (chỉ thêm guard, nhánh không-ban giữ nguyên).
- [x] (B) Code BTC + P2P + null-safe từng phần XONG; **ĐÃ ghép buildReport** (user OK 2026-06-13): 2 dòng BTC + P2P thêm vào `calReportRunning`, try-catch riêng.
- [x] (B) Test in màn hình 3 giá trị + dán kết quả (P2P thật; BTC N/A do máy dev không reach 242).
- [~] (C) `OpenInterestIngestor` + `writeOpenInterestMap` + tích hợp `BinanceDataIngestor` XONG; per-symbol tuần tự+throttle qua `BinanceRestGuard`, KHÔNG đụng ticker/funding. **Ghi 242 chỉ verify được khi chạy trên 242** (máy dev firewall); endpoint+parser đã verify bằng curl.
- [x] (D) Gom log PREDICT_SYMBOL còn 1 dòng/phút; symbol2BUY/DCA giữ log cũ; logic quyết định KHÔNG đổi. (Verify dòng live cần chạy trên 242.)
- [x] Build `mvn -o compile` pass; SLF4J; KHÔNG deploy 242.

---

## (Code điền) — DONE (build `mvn -o compile` pass; SLF4J; CHƯA deploy 242)

> File mới: `utils/BinanceRestGuard.java`, `websocket/OpenInterestIngestor2AerospikeNew.java`,
> `websocket/ParseBanUntilTest.java`, `trading/monitor/ReportExtrasTest.java`.
> File sửa: `websocket/TickerIngestor2AerospikeNew.java`, `websocket/BinanceDataIngestor.java`,
> `aerospike/DataManagerAerospikeFloatSim.java`, `client/BinanceP2PTracker.java`,
> `trading/DetectEntrySignal2TradeNormal.java`.

### A — parseBanUntilMs + cooldown guard
- **TÁCH class chung `utils/BinanceRestGuard`** (theo yêu cầu A1 — OI/funding dùng chung 1 cooldown vì ban theo IP): `AtomicLong BANNED_UNTIL_MS`, `parseBanUntilMs(body)`, `isBanned()`, `reportBan(body)` (atomic-max + warn 1 lần), `awaitIfBanned(capMs)` (sleep cap rồi true). `DEFAULT_COOLDOWN_MS=5'`, `SAFETY_BUFFER_MS=10s`, regex anchor `banned until (\d+)`.
- `TickerIngestor2AerospikeNew` gỡ logic inline, gọi `BinanceRestGuard.*` ở **4 chỗ**: Price-Loop (đầu while `awaitIfBanned(60s)`→continue + cờ `wasBanned` để in `✅ Hết cooldown, resume REST` 1 lần; nhánh `"{"`→`reportBan`); Kline-Loop (`isBanned`→skip phút); `fetchKlinesForBatch` (đầu mỗi coin `isBanned`→return + `reportBan(response)`); `repairBatchOptimized` (đầu vòng `isBanned`→return). KHÔNG đụng HttpRequest, KHÔNG đổi logic nặn nến/ghi/repair khi không ban.

### A — unit test kết quả
`websocket/ParseBanUntilTest` (main, không JUnit) chạy từ jar — **PASS 6/6**:
```
✅ [ban-with-ts] got=1781262464241   ✅ [normal-price-array] got=0   ✅ [-1003-no-number] got=now+5'
✅ [null] got=0   ✅ [blank] got=0   ✅ [ip-no-ban] got=0 (KHÔNG bắt nhầm số trong IP)
KẾT QUẢ: pass=6 fail=0
```

### B — Reporter logic review (nhận xét, KHÔNG sửa)
- **reset-by-15m**: report kiêm watchdog — `now - LAST_TIME_CHECK_MARKET > 15'` → `Utils.reset()` RESTART process. Key thiếu → bỏ qua (an toàn). Ý đồ ổn, nên tách watchdog khỏi report.
- **null `umInfo`**: `getAccountUMInfo()` null → NPE `umInfo.getWalletBalance()`; bị buildReport try/catch nuốt → report bỏ phiên. Nên guard null.
- **marginRunning**: hiển thị 2 cách đo cạnh nhau (`calMarginRunning` vs `positionInitialMargin-unrealizedProfit`+`crossUnPnl`) — không sai, giữ nguyên.

### B — getPriceRealtime + getLowestPrice
- `DataManagerAerospikeFloatSim.getPriceRealtime(symbol):Float` + `getPriceRealtimeTs(symbol):Long` — đọc **242** (KHÔNG getReadClient/226), key UPPER, bin `price`/`ts`, null-safe.
- `BinanceP2PTracker.getLowestPrice(tradeType, transAmount):Double` — payload y hệt `fetchP2PBestPrice` (VND/USDT/rows10), duyệt HẾT `data[].adv.price` lấy **MIN**, empty/lỗi/HTTP≠200→null. `fetchP2PBestPrice` giữ nguyên cho `main`.

### B — TEST in màn hình (BTC + P2P mua/bán thấp nhất)
`trading/monitor/ReportExtrasTest` (main, KHÔNG gọi buildReport) chạy máy dev 2026-06-13:
```
BTC: N/A (không đọc được price_realtime từ 242)    ← máy dev firewall chặn 242 (SocketTimeout)
P2P: mua thấp nhất 26237.0 | bán thấp nhất 26200.0  ← dữ liệu THẬT từ Binance P2P
```
P2P verify OK. BTC code verify OK (null-safe, KHÔNG crash, P2P vẫn chạy sau → "lỗi từng phần không hỏng report"); giá BTC thật chỉ đọc được khi chạy TRÊN 242.
✅ **ĐÃ ghép vào `Reporter.calReportRunning`** (user OK 2026-06-13): 2 dòng `BTC: <price>$ (cập nhật <age> trước)` (null→N/A) + `P2P: mua thấp nhất <x> | bán thấp nhất <y>`, mỗi dòng try-catch RIÊNG (lỗi BTC/P2P không hỏng report). Test độc lập `ReportExtrasTest` vẫn giữ.

### C — OpenInterestIngestor + writeOpenInterestMap + tích hợp BinanceDataIngestor
- `DataManagerAerospikeFloatSim.writeOpenInterestMap(symbol, Map<Long,Float>)` + `getOpenInterestMap(symbol)` — set mới `open_interest` (242), bin `oi_data` Snappy Map<Long,Float>, **nhân bản writeFundingMap** gồm guard chống mất lịch sử (record có blob nhưng đọc rỗng → ABORT không ghi đè). Value = `sumOpenInterestValue` (USD notional).
- `websocket/OpenInterestIngestor2AerospikeNew`: gọi PER-SYMBOL **TUẦN TỰ + throttle 250ms** (KHÔNG ForkJoinPool kiểu kline), MỌI call qua `BinanceRestGuard` (`awaitIfBanned`/`reportBan`/`isBanned`), dùng `HttpRequest.getContentFromUrl` (public endpoint `openInterestHist`) để body -1003 vào guard. History: period 15m, page lùi theo `endTime`, lookback ~30 ngày; Forward: mỗi 5' period 5m limit=1.
- `BinanceDataIngestor.main` thêm `new OpenInterestIngestor2AerospikeNew().start();` (thread riêng, KHÔNG đụng ticker/funding).

### C — kết quả cào history + forward (số symbol, mốc, sample OI)
- Endpoint + parser verify bằng curl thật (field khớp): `GET openInterestHist?symbol=BTCUSDT&period=5m&limit=2` →
  `{"sumOpenInterestValue":"6351987591.07","timestamp":1781356500000}` (BTC OI notional ~$6.35B, 2026-06-13).
- ⚠️ **CHƯA chạy full forward/history thật**: ghi `open_interest` cần Aerospike **242** mà máy dev bị firewall chặn (SocketTimeout, giống BTC ở B) → chỉ chạy được khi `BinanceDataIngestor` chạy TRÊN 242. Code path (HTTP+parse) đã verify; phần ghi 242 verify khi deploy.

### D — gom log (diff createOrderBuyRequest + dòng tổng hợp)
- Thêm param `List<String> rejectCollector` (nullable) vào `createOrderBuyRequest`. `gather = (levelChange==PREDICT_SYMBOL_TRADE && rejectCollector!=null)`:
  - gather=true: KHÔNG log `AI CHECK`/`SKIP ORDER`; REJECT → `rejectCollector.add(String.format("%s(%.3f)", symShort, symbolPred))`. PASS → vẫn `✅ AI PASS`.
  - gather=false (symbol2BUY/DCA/collector null): GIỮ NGUYÊN log cũ.
- 3 caller symbol2BUY + 2×DCA truyền `null`; vòng `PREDICT_SYMBOL_TRADE` truyền `predictRejects`; sau vòng in 1 dòng:
  `🔕 [PREDICT fail {n}] market[15M:{}% Risk4H:{}%] Min15M:{}% | SYM(0.320) SYM(0.327)…`
- ⚠️ **Bỏ `24H` khỏi dòng tổng hợp** so với mẫu task: `PredictionResult` chỉ còn `return15M`+`riskDrawdown4H` (predReturn24H đã BỎ HẲN khỏi hệ — CLAUDE.md). Giữ 24H sẽ không compile.
- Logic quyết định KHÔNG đổi (chỉ đổi LOG). ⚠️ Verify dòng log live cần chạy TRÊN 242.
