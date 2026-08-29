# PRODUCTION_AUDIT.md — Audit READ-ONLY 2 process live (TASK-020)

- **Owner:** CCD-audit · **Ngày:** 2026-06-14 · **Tính chất:** RÀ + LIỆT KÊ, **KHÔNG sửa code, KHÔNG đụng live.**
- **Phạm vi:** P1 `BinanceDataIngestor` (ingest → Aerospike 242) · P2 `BinanceOrderTradingManager` + `DetectEntrySignal2TradeNormal` (trade live) · Cross-cutting (guard/parity/host).
- **Phương pháp:** liệt kê mọi thread/loop từ `main`, soi theo 12 mục checklist của task; bằng chứng file:dòng. Các finding mức **Cao** được CCD spot-check trực tiếp trên source (đánh dấu ✔verify).
- **Quy ước cột Mức:** Cao = sai quyết định/mất dữ liệu/gia hạn ban; TB = sai biên/khó phát hiện; Thấp = noise/latent/đã-vá-xác-nhận.
- **Lưu ý đọc:** đây là DANH SÁCH để Desktop/user mở task sửa riêng — KHÔNG tự sửa từ file này. Một số finding TB/Thấp là phân tích tĩnh (race/edge) chưa repro runtime, đã ghi rõ.

> Mã dòng tham chiếu theo HEAD lúc audit (branch `module`). `FundingIngestor2AerospikeNew.java` đang có thay đổi chưa commit trong working tree — số dòng theo bản working tree.

---

## 1. Inventory thread/loop

### P1 — BinanceDataIngestor (`websocket/BinanceDataIngestor.java`)
`main()` chỉ start 3 ingestor; watchdog auto-restart **bị comment** (dòng 22).

| # | Thread/loop | Khởi từ | Nhịp |
|---|---|---|---|
| 1 | `Funding-Polling-Thread` | FundingIngestor2AerospikeNew:42 | 30s |
| 2 | `Funding-Sync/Flush` | FundingIngestor2AerospikeNew:94 | 60s (chỉ ghi khi có settlement) |
| 3 | `Rest-Price-Loop` | TickerIngestor2AerospikeNew:48 | 3s |
| 4 | `Rest-Kline-Loop` | TickerIngestor2AerospikeNew:144 | check 1s, chốt 1 lần/phút |
| 5 | `startDataRepair` (one-shot) + repair mã mới (on-demand) | TickerIngestor2AerospikeNew:320/348 | start + khi gặp coin mới |
| 6 | `restFetchService`(15) + `ForkJoinPool`(30) | TickerIngestor2AerospikeNew:33,168,225 | trong Rest-Kline-Loop |
| 7 | `OI-History-Crawl` (one-shot) + `OI-Forward-Loop` | OpenInterestIngestor2AerospikeNew:68/138 | start + 5 phút |
| — | `ThreadAutoRestartProgram` | BinanceDataIngestor:25 | **DEAD** (comment ở main:22) |

### P2 — BinanceOrderTradingManager (`trading/BinanceOrderTradingManager.java`)
`main()` → `DetectEntrySignal2TradeNormal.start()` + `BinanceOrderTradingManager.start()`.

| # | Thread/loop | Khởi từ | Nhịp |
|---|---|---|---|
| T1 | `ThreadDetectMarketLevel2Trader` (entry: pred + market level + DCA + breaker → Redis queue) | DetectEntry:89 | sleep 100ms, gate 1 lần/phút |
| T2 | `ThreadListenQueueOrder2ManagerNew` (blpop → processOrderNewMarketNew) | BOTM:119 | blocking |
| T3 | `ThreadManagerOrder` (updatePos, markPrice, trailing TP/SL, initSL, Reporter) | BOTM:72 | sleep 1s, cadence theo giây GMT+7 |
| T4 | `ThreadAutoRestartProgram` | BOTM:98 | 4h → Utils.reset |
| T5 | `ThreadUpdateBudgetByHour` | BudgetManager:70 | 1h |
| T6 | `FundingFee-Refresh` (production cache) | FundingFeeManager:58 | 30 phút |
| init | `initData` (load ONNX entry + funding model, warmup History 2000', bật FundingFeeManager production) | DetectEntry:570 | 1 lần |

---

## 2. Findings — P1 (ingest)

| Vị trí (file:dòng) | Phát hiện | Mức | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| FundingIngestor2AerospikeNew.java:49 | **Funding-Polling gọi REST KHÔNG qua BinanceRestGuard** — không `awaitIfBanned`/`isBanned` trước, không `reportBan` sau (chỉ LOG.warn body `{`). Đang ban IP (bởi process khác cùng IP) vẫn bắn 30s/lần → gia hạn ban; body `-1003` không vào cooldown global. Pattern y hệt bug guard-thiếu đã thấy. **✔verify** | **Cao** | dòng 47-52 không có guard nào; Ticker:57/131 & OI:147/153 đều có guard | Thêm `if(BinanceRestGuard.awaitIfBanned(...)) continue;` + `reportBan(response)`. |
| BinanceDataIngestor.java:22 (+25-56) | **Watchdog `ThreadAutoRestartProgram` DEAD** — comment ở main:22 nên P1 KHÔNG có auto-restart/giám sát nào. Hơn nữa nếu bật lại vẫn hỏng: `counterMinutes` (dòng 29) KHÔNG bao giờ ++ → điều kiện reset-12h (dòng 45) không bao giờ true; catch dùng `printStackTrace`. `checkAndComparePriceDiff` không caller live nào khác. **✔verify** | **Cao** | main:22 comment; dòng 29 không có `counterMinutes++`; dòng 43/50 printStackTrace | Quyết định: bật lại + fix counter/log, hoặc xóa code chết để khỏi hiểu nhầm là "có giám sát". |
| HttpRequest.java:218-220, 328 | **Exception nuốt câm toàn cục** — mọi REST của P1 đi qua hàm này; có `catch(Exception e){}` rỗng và retry chỉ `// ex.printStackTrace()` đã comment. Lỗi DNS/timeout/SSL/parse biến mất, trả `""`/`null` lẫn lộn → loop "chạy nhưng rỗng" không ai biết. | **Cao** | catch rỗng + printStackTrace bị comment | Log WARN trong catch, phân biệt timeout vs parse. (Vi phạm luật cấm nuốt exception câm — CLAUDE.md.) |
| TickerIngestor2AerospikeNew.java:120 & 285 + DataManagerAerospikeFloatSim.java:151-155 | **Race lost-update cùng key phút** — Rest-Price-Loop (3s) và Rest-Kline-Loop (chốt phút) cùng `writeMinuteBatch(curMin,...)`; hàm này read (getExistingTickersMap) → putAll → put KHÔNG atomic. 2 luồng ghi cùng `curMin` có thể mất nến. (phân tích tĩnh, chưa repro) | **Cao** | read-modify-write không khóa; 2 luồng cùng curMin | Khóa theo key, hoặc CDT map-operation / merge phía Aerospike. |
| TickerIngestor2AerospikeNew.java:225 | **`new ForkJoinPool(30)` tạo MỚI mỗi batch**, lồng trong `restFetchService`(15) chạy song song nhiều batch/phút → bùng nổ luồng + tạo/hủy pool mỗi phút. | **Cao** | dòng 225 trong hàm chạy per-batch; 168 submit nhiều batch | Một pool dùng chung, hoặc bỏ tầng batch-15 (đã parallelStream). |
| OpenInterestIngestor2AerospikeNew.java:67-91 | **`startHistoryCrawl` cào lại ~30 ngày × ~554 coin MỖI restart**, không kiểm DB đã có data (khác Ticker repair có `isSymbolMissingInPoints`) → tốn weight lớn mỗi lần khởi động. Pattern "startHistoryCrawl thừa". | **TB** | 75-85 luôn ghi đè full 30 ngày | Kiểm điểm cuối trong DB, chỉ cào phần thiếu. |
| Constants.java:52,58-65 | **`diedSymbol` load 1 lần static-init, KHÔNG refresh** — coin delist GIỮA phiên live (process chạy nhiều ngày) vẫn bị ingest → spam -4xxx, data rỗng. Mọi ingestor lọc `Constants.diedSymbol.contains`. | **TB** | static block chỉ chạy 1 lần, không reload | Reload định kỳ từ config/exchangeInfo, hoặc auto-add khi gặp code delist. |
| TickerIngestor2AerospikeNew.java:126 (+helper clamp 172) | **Repair mã mới: range 1800 phút (30h) nhưng limit bị clamp ≤1500** → 300 phút đầu KHÔNG repair, im lặng (chỉ log DEBUG). | **TB** | limit=1800 → helper clamp 1500 | Phân trang ≤1500 hoặc giảm range cho khớp. |
| TickerIngestor2AerospikeNew.java:267-269 | **Nuốt exception per-coin câm** trong kline fetch (`catch{ // Ignore }`) — coin parse lỗi/-1130 biến mất. (repair 372-374 đã log → bất nhất). | **TB** | comment "Ignore" | Log WARN như repairBatchOptimized. |
| TickerIngestor2AerospikeNew.java:383-384 | **`initNewSymbolConfig` nuốt exception** — `changeInitialLeverage` fail (coin lạ) → catch rỗng nhưng coin VẪN được subscribe (dòng 107) → có thể vào order với leverage mặc định SAI. | **TB** | catch rỗng; add subscribe bất kể set leverage | Log lỗi; cân nhắc không subscribe nếu set leverage fail. |
| FundingIngestor2AerospikeNew.java:64 | **`getFloat("lastFundingRate")` không guard field** — coin mới list trả field rỗng → JSONException rơi vào catch ngoài (86) BỎ NGUYÊN vòng poll đó (mất các symbol còn lại). | **TB** | catch ở 86 bọc cả vòng for | try-catch per-symbol. |
| FundingIngestor2AerospikeNew.java:71-76 | **Mất kỳ settlement đầu sau restart** — `lastSeenNextFundingTime` là RAM, vòng đầu `prevNext==null` chỉ set baseline; restart đúng quanh giờ settle → mất kỳ đó (HistoricalFundingCrawler vá sau). | **TB** | chỉ ghi khi `prevNext!=null` | Chấp nhận, hoặc seed từ DB lúc start. |
| HttpRequest.java:280-283, 299 | **Buffer đọc cấp theo `Content-Length` header** — server trả `-1` (chunked) → cấp `char[8MB]` mỗi call; với price 3s + kline ~554 coin/phút → rác lớn. | **TB** | 281-283 ép 8MB khi ==-1; 299 `new char[...]` | Buffer cố định nhỏ + đọc lặp. |
| OpenInterestIngestor2AerospikeNew.java:167-169 | Nuốt exception per-coin câm (`// bỏ qua lỗi 1 coin`). | Thấp | catch comment rỗng | Log WARN. |
| OpenInterestIngestor2AerospikeNew.java:100-127 | OI history `endTime = minTs-1` không guard `minTs==0` → có thể gửi `endTime=-1` (rủi ro -1130); hiện chặn gián tiếp bởi break theo PAGE_LIMIT. | Thấp | 127 không kiểm endTime>0 | Guard `if(endTime<=boundary) break`. |
| TickerIngestor2AerospikeNew.java:280 | `lastMin = curMin - 60000` magic number thay `Utils.TIME_MINUTE`. | Thấp | so với 328/363 dùng hằng | Dùng hằng. |
| FundingIngestor2AerospikeNew.java:104-127 | **(xác nhận ĐÃ tốt)** Flush 60s nhưng chỉ ghi khi có settlement (`isEmpty→continue`); clear sau snapshot. Bug "flush ~1' thay ~1h" KHÔNG còn. | Thấp (đã vá) | 105-120 | Không cần sửa. |

---

## 3. Findings — P2 (trade)

| Vị trí (file:dòng) | Phát hiện | Mức | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| onnx/entry/OnnxInferenceManager.java:50-55 | **Train/serve parity: model Return15M chạy nhầm feature set.** `p15M.predict(featuresV3)` (33 feat V3) trong khi `extractFeaturesV4Sideway` (comment "Cho Return", "Khớp Python V4 Final") bị comment dead (dòng 50). Nếu model Return15M train với V4 → serve đưa V3 → scaler/thứ tự sai → `predReturn15M` rác, mà đây là gate chính của MỌI entry. **✔verify** (xác nhận code state; cần đối chiếu Python xác định model train V3 hay V4) | **Cao** | dòng 50 V4 comment-out, 54 dùng V3; `extractFeaturesV4Sideway` không caller | Đối chiếu số feature model Return15M lúc train. Nếu V4 → gọi đúng extractor cho p15M; nếu thật V3 → xóa V4 cho hết mơ hồ. |
| DetectEntrySignal2TradeNormal.java:494 | **Entry/quantity tính trên nến đã ĐÓNG, không dùng price_realtime tươi.** `priceEntry = ticker.priceClose` (nến 1m đóng cuối). `getPriceRealtime` (set price_realtime 242) tồn tại nhưng KHÔNG gọi trong path entry → quantity/budget tính trên giá cũ tới ~1-2 phút, sai size khi coin biến động mạnh trong phút. | **Cao** | :121-124 đọc tới now-1min; :494 priceClose; getPriceRealtime chỉ ở Reporter | Đọc `getPriceRealtime(symbol)` + check tuổi `getPriceRealtimeTs` lúc tính quantity. |
| DetectEntry initData:604 + :412 | **`aiBrain` load fail → bot NGỪNG vào lệnh hoàn toàn, không alert.** initData catch nuốt (LOG.error, không rethrow); nếu aiBrain==null thì mọi createOrderBuyRequest return ở :413 chỉ log info per-coin. | **Cao** | initData:604 catch không rethrow; :205 `if(aiBrain!=null)`; :412 return | aiBrain==null sau init → Telegram alert + fail-fast, đừng chạy câm. |
| BOTM updatePositionInfo:317-351 | **Return giữa chừng không nhả lock + clear-then-fill không atomic.** Lock "UpdateAllPos" add (317) nhưng nhánh `positions==null` return (320-323) KHÔNG remove → kẹt tới timeout 3s. `symbol2Pos.clear()` (327) TRƯỚC putAll (351), không try-catch → exception giữa chừng làm trailing/SL/DCA mất sạch position tạm thời. (phân tích tĩnh) | **Cao** | 317 addLock; 320-323 return không remove; 327 clear trước 351 | Build map mới rồi swap (đừng clear-then-fill map đang đọc); try/finally nhả lock. |
| FundingFeeManager.java:121 | **Funding stale → trả `0.0f` âm thầm sau 24h** (không phải null) → coin thiếu funding mới được coi funding=0, lọt vào feature `coinFundingRate/fundingRateAvg24H` → pred sai không log. | **TB** | `if(timestamp-entry.getKey()>24h) return 0.0f;` | Log WARN + đếm symbol stale; cân nhắc reject entry thay vì giả định 0. |
| OnnxInferenceManager.java:58-60 + BOTM:269,378 | **Pred lỗi inference lưu `(0,0)` như pred hợp lệ.** Khi infer throw trả PredictionResult(0,0) → lưu Aerospike → trailing/initSL đọc lại pred=0 → dùng giá trị degraded mà không biết (entry thì vô tình bị reject do momentum<MIN). | **TB** | OnnxInferenceManager:60; BOTM đọc getAiPredictionAtTime | Dùng sentinel phân biệt "pred lỗi" vs pred=0 thật; đừng lưu (0,0) khi throw. |
| BOTM processManagerPosition:201-212 | **Cadence so sánh BẰNG giây (`==10`, `%30==0`) + loop có thể trôi nhịp** (updatePositionInfo lock 3s + REST) → giây mốc bị nhảy qua → bỏ cả vòng update vị thế / re-read ticker 30s. | **TB** | 201/212 so sánh bằng; loop sleep 1s; updatePos lock 3s | Dùng "đã-chạy-trong-cửa-sổ" flag (như isTimeProcessData) thay so sánh bằng. |
| BOTM:261 | **Điều kiện thời gian luôn-true:** `position.getUpdateTime() < startTime + 30*TIME_MINUTE` (startTime=now) → gần như luôn true → nhánh else dọn `symbol2Level` gần như không chạy. Có vẻ ý đồ là `> now - 30'`. | **TB** | dòng 261 | Xem lại dấu so sánh. |
| BOTM:373,463,472 | **So sánh float bằng `!=`/`==`** cho priceEntry/stopPrice/priceSL → sai số → ghi đè liên tục (373, noise) hoặc SL cũ không nhận diện được (463/472, có thể tạo trùng/không cancel đúng). | **TB** | 373/463/472 | Dùng epsilon hoặc BigDecimal.compareTo. |
| BudgetManager:36,57-68 + DcaUtils:59 | **budget=0 → chia Infinity → DCA cực mạnh.** `BUDGET_PER_ORDER=0f` khởi tạo; nếu `updateBudget` fail lần đầu (REST, catch nuốt) giữ 0 → `margin/budget`=Infinity → marginRatio≥3 → rateLoss -0.99. | **TB** | BudgetManager:36/57-68; DcaUtils:59 | Guard `budget<=0 → skip` trước khi chia. |
| DetectEntry:122-124 | **NPE nếu BTC thiếu data** — `btcTickers.get(size-1)` không null-check → cả phút không trade, rơi catch in stacktrace (im lặng). Edge khi 242 thiếu BTC. | **TB** | 123-124 không null-check | Null-check + alert (fatal-skip có cảnh báo). |
| BOTM:155-157 vs :187 | **`symbol2Processing` không dọn khi return sớm** (isLockReduceOnly return ở 157 trước remove ở 187) → symbol kẹt 2' dù lệnh bị bỏ. 2 cơ chế lock (symbol2Processing + SymbolOrderLockingManager) chồng nhau không nhất quán. | **TB** | 155-157 return không remove | try/finally remove ở mọi đường ra. |
| CoinRankManager:66,70,125 + DetectEntry:479-487 | **Sau restart, tier mặc định TIER_3 cho mọi coin** tới khi T1 tick đầu build ranking → budget×0.5 + chặn DCA toàn bộ ngay sau restart. initData warmup History nhưng không gọi updateRanking. | **TB** | symbolTiers.isEmpty()→build; default TIER_3 | Gọi `getTopCoin(now)` cuối initData để warm tier. |
| BOTM:174-186 | **Re-queue order lỗi không kiểm vị thế thực** → có thể double order (kết hợp symbol2Processing đã remove ở 187). | **TB** | 174-186 | Kiểm vị thế REST trước re-push. |
| BOTM:226-240 vs trailing | markPrice cập nhật song song (executor) với processDynamicTP_SL đọc cùng `position.getMarkPrice()` → race đọc giá nửa-update. | **TB** | 206-208 submit song song; cùng đụng symbol2Pos | Tính SL trên snapshot giá tại chỗ, đừng mutate shared PositionRisk. |
| BOTM (nhiều dòng) | **`e.printStackTrace()` + log nhầm class** (`Logger.getLogger(DetectEntrySignal...)` trong BOTM) → exception ra stdout không vào log/alert. | Thấp | 80,92,106,141,184,238... | Thống nhất LOG.error + alert. |
| FundingFeeManager.java:58-89 + DetectEntry:574 | **(xác nhận ĐÃ vá - lỗi 019)** refresh scheduler 30' production được kích hoạt ở initData:574; bug "cache không refresh" đã vá (còn sót nhánh stale-24h→0 ở trên). | Thấp (đã vá) | 58-89; 574 | Theo dõi log "refresh cập nhật N symbol" để chắc N>0. |

---

## 4. Findings — Cross-cutting (guard / parity / host)

| Vị trí (file:dòng) | Phát hiện | Mức | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| SimulatorMarketLevelTicker1MStopLoss.java:517 (sim) vs DetectEntry:412 (live) | **Vi phạm "một bộ não": gate AI lệch khi pred==null.** SIM: pred==null → BỎ filter, VẪN vào lệnh. LIVE: pred==null → return, KHÔNG vào lệnh. Backtest tính lãi cho lệnh mà live bỏ → P&L sim ≠ live ở edge thiếu pred. | **Cao** | sim:517 `if(predict!=null && !BIG_DOWN)`; live:412 `if(prediction==null) return` | Gom về 1 hàm lõi (ROADMAP bước 5); rõ luật khi pred null. |
| config.properties:25 | **DIED_SYMBOLS repo = 30 symbol, KHÔNG phải 129 mà TASK-008 chốt.** Nếu deploy từ repo này, ingest+trade KHÔNG skip ~99 coin chết 008 đã quyết. **✔verify** (đếm 30; nhưng 008 apply trên box 226 — config production có thể sống ngoài repo, CẦN xác nhận owner). | **Cao** (cần xác nhận) | dòng 25 đếm 30 vs tasks/008:73,108 (129) | Đồng bộ config.properties = chuỗi 129, hoặc ghi rõ "config production ngoài repo". |
| DataManagerAerospikeFloatSim.getReadClient():2021-2026 + Configs.java:57 | **Live đọc qua getReadClient → lỡ trỏ 226 (kho backtest) nếu `IS_KAGGLE_MODE=true` trên box live, không fail-fast.** Hiện config không có key → false (an toàn). Nhưng GHI vẫn 242 → nếu bật nhầm, bot quyết trên data 226 cũ mà không báo. Live đọc qua đây: ticker readDataForSymbols:798, funding getFundingMap:386/431, mapper:105. | **Cao** | getReadClient:2022 chọn 226 khi KAGGLE/HPO; Configs:57 mặc định false | Fail-fast: live khẳng định IS_KAGGLE_MODE=false lúc start; hoặc client đọc-live cứng 242. |
| DataManagerAerospikeFloatSim.java:1298, 2045 | **`getFundingPredictionAtTime`/`getFundingPredsForTimestamps` HARDCODE `getClient226()`** — hiện không nằm trong path live (callers chỉ test/validator), nhưng là bom hẹn giờ nếu live mai mốt đọc pred-set từ đây. | **TB** | 1298/2045 getClient226() | Đổi sang getReadClient() / tham số host rõ ràng. |
| MarketBigChangeDetector.java:213 (sim) vs 248-253 (prod) | Circuit breaker lõi CHUNG `evaluateCircuitBreakerCore` (tốt), nhưng input `isProfitable` khác: sim luôn false, prod suy từ priceTP>priceEntry → cùng tình huống có thể ra quyết định khác. | **TB** | 213 vs 248-253 | Chuẩn hóa cách tính isProfitable cho 2 môi trường. |
| createOrderBuyRequest (live) vs createOrderBUY (sim) | LIVE thiếu khối `BREAKER_MODE` (MARGIN/DCA cap) mà sim có; mặc định OFF nên hiện vô hại, nhưng bật để đo thì sim≠live. SIM còn loại trừ BIG_DOWN khỏi filter, live không có nhánh tương ứng. | **TB** | sim:531-553 breaker; sim:518 `!BIG_DOWN` | Đưa breaker + nhánh BIG_DOWN vào hàm lõi chung. |
| TickerFuturesHelper.java:53,72,100,113,125 | Một số helper REST trần (`getTickerSimpleWithStartTime`, `getFundingFeeWithStartTime`, `getAllSymbol/getSymbolVolumeLower/getSymbolPrice` — `ticker/24hr` weight cao) KHÔNG guard/reportBan. Khác với `getTickerSimpleWithStartTimeAndLimit` (177/195 có guard đủ). | **TB** | 53/72/100/113/125 trần | Kiểm caller live; thêm guard nếu dùng trong luồng live. |
| Constants.java:52 | (trùng P1) `diedSymbol` nạp 1 lần không refresh. Ingest (Ticker/Funding/OI) + Trade (DetectEntry:134) dùng CHUNG `Constants.diedSymbol` → **logic NHẤT QUÁN** (sạch). | Thấp (sạch) | DetectEntry:134 == ingest | Chỉ vấn đề refresh runtime (đã nêu P1). |

---

## 5. Tổng kết mức Cao (Desktop/user mở task sửa)

**P1 ingest**
1. `FundingIngestor2AerospikeNew.java:49` — Funding-Polling KHÔNG qua BinanceRestGuard (thiếu await + reportBan) → gia hạn ban. **✔verify**
2. `BinanceDataIngestor.java:22` — watchdog auto-restart DEAD (và logic 12h hỏng nếu bật); P1 không có giám sát. **✔verify**
3. `HttpRequest.java:218/328` — exception nuốt câm toàn cục cho mọi REST ingest.
4. `TickerIngestor:120/285 + DataManager:151-155` — race lost-update cùng key phút.
5. `TickerIngestor:225` — ForkJoinPool(30) tạo mới mỗi batch, lồng pool → bùng nổ luồng.

**P2 trade**
6. `OnnxInferenceManager.java:50-55` — model Return15M chạy nhầm feature V3 thay V4 (cần đối chiếu Python). **✔verify code state**
7. `DetectEntry:494` — entry/quantity trên nến đã đóng, không dùng price_realtime tươi.
8. `DetectEntry initData:604 + :412` — aiBrain load fail → bot ngừng vào lệnh, không alert.
9. `BOTM updatePositionInfo:317-351` — return không nhả lock + clear-then-fill không atomic.

**Cross-cutting**
10. `Simulator...:517` vs `DetectEntry:412` — gate AI lệch khi pred==null ("một bộ não").
11. `config.properties:25` — DIED_SYMBOLS 30 vs 129 của TASK-008 (cần xác nhận config production). **✔verify**
12. `getReadClient():2021 + Configs:57` — live có thể lỡ đọc 226 nếu IS_KAGGLE_MODE bật, không fail-fast; + 2 hàm hardcode 226.

## 6. Đã kiểm & XÁC NHẬN tốt (loại nghi ngờ ban đầu của task)
- **Model pred KHÔNG precompute stale:** live infer realtime mỗi phút (DetectEntry:211-221, predictAllCandidates:374-393). Set `funding_pred_1m_v5`/`ai_pred_market` chỉ dùng tooling/HPO, không đọc trong entry path live. → lo ngại "time2SymbolPred precompute STALE" KHÔNG đúng với code hiện tại.
- **price_realtime đọc đúng 242** (getPriceRealtime ép getClient242). GHI live nhất quán 242 (writeMinuteBatch/Price/Funding/OI/saveAiPrediction). Không lẫn 226 trong path mặc định.
- **FundingFeeManager refresh (lỗi 019) đã vá** (scheduler 30' production, bật ở initData:574). Còn sót: nhánh stale-24h→0 (đã liệt mục 3 TB).
- **HistoryManager CÓ được nuôi live** mỗi phút qua extractAllFeatures → updateMarketHistory, không rỗng.
- **DIED_SYMBOLS dùng nhất quán** giữa ingest và trade (cùng `Constants.diedSymbol`).
- **TickerFuturesHelper clamp limit [1,1500] + phân biệt -1003/-1130** (bug -1130 TASK-016 đã vá đúng); Funding flush 60s chỉ-ghi-khi-settlement (bug flush ~1' đã vá).

---
*Phương pháp: 3 agent đọc song song (P1/P2/cross-cutting) + CCD spot-check trực tiếp các finding mức Cao. Finding TB/Thấp dạng race/edge là phân tích tĩnh, chưa repro runtime — ưu tiên xác minh khi mở task sửa.*
