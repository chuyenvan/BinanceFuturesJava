# B0 CODE DIGEST

> Read-only gom code (không sửa file nào). Snippet trích nguyên khối + path + dòng.
> Repo: `BinanceFuturesJava` (branch `module`). Engine backtest: `SimulatorMarketLevelTicker1MStopLoss`.
> ⚠️ Lưu ý: chỗ "priceTP = priceSL" ĐÃ có kẹp `Math.min(priceSL, ticker.maxPrice)` trong code hiện tại
> (xem A3) — tức fix kẹp-theo-HIGH đã áp; PROMPT_fix nói "min(priceSL, bar.open)" thì KHÔNG có file (A8).

---

## A. Exit booking

### A1 — `calTp` và `calProfit` (TP/exit/PnL của 1 cụm)
`src/main/java/com/binance/chuyennd/research/OrderTargetInfoTest.java:200-220` (`calTp`), `:129-132` (`calProfit`)

```java
    public Float calProfit() {                                  // :129
        float profit = quantity * (lastPrice - priceEntry);
        return profit;
    }
    ...
    public Float calTp() {                                      // :200
        OrderTargetInfoTest orderInfo = this;
        if (orderInfo.priceTP == null) {
            return 0f;
        }
        Float tp = orderInfo.quantity * (orderInfo.priceTP - orderInfo.priceEntry)
                - orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
        if (orderInfo.side.equals(OrderSide.SELL)) {
            tp = orderInfo.quantity * (orderInfo.priceEntry - orderInfo.priceTP)
                    - orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
        }
        // 🔥 SLIPPAGE 2 chân
        if (Configs.APPLY_SLIPPAGE) {
            float slip = orderInfo.quantity * orderInfo.priceEntry * Configs.SLIPPAGE_RATE * 2f;
            tp = tp - slip;
        }
        tp = tp - calFundingFee();
        return tp;
    }
```
PnL realize của cụm = `qty*(priceTP - priceEntry) - fee - slippage(2 chân) - funding`. `priceTP` chính là **giá fill được book**. `calProfit` (unrealized) dùng `lastPrice` (giá close hiện tại), KHÁC `calTp`.

### A2 — Nhánh `STOP_MARKET_DONE` (trailing stop fill) trong close-path
`src/main/java/com/binance/chuyennd/research/OrderTargetInfoTest.java:161-175` (trong `updateStatusNew`, nhánh `priceSL != null`)

```java
        } else {
            // Nhánh này KHÔNG look-ahead: SL đã tồn tại từ nến trước, nến này chạm đáy thì khớp.
            if (minPrice <= priceSL) {
                if (priceSL > priceEntry) {
                    status = OrderTargetStatus.STOP_MARKET_DONE;
                } else {
                    status = OrderTargetStatus.STOP_LOSS_DONE;
                }
                // 🔴 BOOKING FIX (KHÔNG đụng trigger minPrice<=priceSL): kẹp giá chốt ≤ high nến khớp.
                //    priceSL là level set ở nến TRƯỚC; khi nến trigger GAP thủng xuống (high<priceSL) thì
                //    KHÔNG thể bán được priceSL — long-only => sell fill ≤ ticker.maxPrice. Ca thường
                //    (low≤priceSL≤high) min=priceSL nên KHÔNG đổi; chỉ ca gap mới bị kẹp (sửa PnL thổi).
                priceTP = Math.min(priceSL, ticker.maxPrice);
            }
        }
```
`STOP_MARKET_DONE` (priceSL>entry = chốt lãi) vs `STOP_LOSS_DONE` (priceSL≤entry). Trigger = `minPrice <= priceSL`.

### A3 — Chỗ set giá exit từ mức stop (đã KẸP)
`src/main/java/com/binance/chuyennd/research/OrderTargetInfoTest.java:173` (nhánh stop chính) và `:158` (nhánh look-ahead, bất hoạt khi `BLOCK_INTRABAR_LOOKAHEAD=true`)

```java
:158   priceTP = Math.min(priceSL, ticker.maxPrice);   // (look-ahead branch, bất hoạt)
:173   priceTP = Math.min(priceSL, ticker.maxPrice);   // (stop chính)
```
**Hiện tại ĐÃ kẹp về `ticker.maxPrice` (high nến trigger)** — KHÔNG còn book thẳng `priceSL`. Nghi vấn "book priceSL không kẹp" ĐÚNG với code TRƯỚC fix; code hiện tại đã sửa (kẹp theo HIGH, không phải `bar.open`).

### A4 — Chỗ THỰC SỰ book giá fill vào PnL (cụm → từng leg → allOrderDone)
`src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java:451-473` (`closeOrder`)

```java
    private void closeOrder(short symbolId, OrderTargetInfoTest orderMulti) {
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry[symbolId];
        if (orders != null) {
            for (OrderTargetInfoTest order : orders) {
                order.timeUpdate = orderMulti.timeUpdate;
                order.status = orderMulti.status;
                order.priceTP = orderMulti.priceTP;          // <-- BOOK giá fill (đã kẹp) cho từng leg
                order.minPrice = orderMulti.minPrice;
                order.maeLow = orderMulti.maeLow;
                order.lastPrice = orderMulti.lastPrice;
                allOrderDone.put(-order.timeUpdate - allOrderDone.size(), order);   // ghi vào sổ done
                BudgetManagerSimple.getInstance().updatePnl(order);                 // -> cộng calTp() vào profit
            }
        }
        symbol2OrdersEntry[symbolId] = null;
        symbol2OrderRunning[symbolId] = null;
        removeActiveRunningId(symbolId);
        BudgetManagerSimple.getInstance().marginRunning -= orderMulti.calMargin();
    }
```
`orderMulti.priceTP` (đã kẹp ở A3) được chép sang MỌI leg → `allOrderDone` → `updatePnl` cộng `calTp()`. Đây là nơi giá fill đi vào PnL.

### A5(a) — TRIGGER LOGIC (nến này có trigger không)
`src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java:421-440` (`startUpdateOldOrderTrading`) + điều kiện trigger trong `updateStatusNew` (A2: `minPrice <= priceSL`).

```java
    private void startUpdateOldOrderTrading(Long time, short symbolId, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning[symbolId];
        if (orderMulti != null) {
            if (orderMulti.timeStart <= ticker.startTime) {
                orderMulti.updatePriceByKlineSimple(ticker);
                if (ticker.maxPrice >= orderMulti.priceEntry * (1 + Configs.RATE_PROFIT_STOP_MARKET)
                        || orderMulti.priceSL != null) {                 // điều kiện vào xét trigger
                    Float predReturn15M  = getPredReturn15MForTradingStop(time);
                    orderMulti.updateStatusNew(predReturn15M , ticker);  // <-- TRIGGER + set priceTP (A2/A3)
                    if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                        closeOrder(symbolId, orderMulti);                // <-- CLOSE-PATH (A5b)
                    } else {
                        orderMulti.updateTPSL(predReturn15M , ticker);   // chưa trigger -> dời SL
                    }
                }
            }
        }
    }
```

### A5(b) — CLOSE-PATH SIM (sau trigger, book bao nhiêu)
= **A4** (`closeOrder:451-473`). Giá fill = `orderMulti.priceTP` (đã kẹp `min(priceSL, ticker.maxPrice)` lúc trigger ở A2/A3).

### A6 — Struct/class cụm position
`src/main/java/com/binance/chuyennd/research/OrderTargetInfoTest.java:38-68`

```java
    public OrderTargetStatus status;        // REQUEST / TAKE_PROFIT_DONE / STOP_MARKET_DONE / STOP_LOSS_DONE
    public OrderSide side;
    public Float priceEntry;                // giá vào (cụm = avg vol-weighted, xem mergeOrder)
    public Float lastEntry;
    public Float priceTP;                   // GIÁ EXIT đã book (dùng trong calTp)
    public Float priceSL;                   // mức trailing stop
    public Float quantity;                  // tổng qty cụm
    public Integer leverage;
    public String symbol;
    public short symbolId;
    public long timeStart;
    public long timeUpdate;                 // = thời điểm đóng khi close
    public Float profitMin = 0f;
    //    public Float maxPrice;
    public Float minPrice;                  // tham chiếu trailing (reset-lên) — KHÔNG phải đáy thật
    public Float maeLow;                    // đáy THẬT cụm (đo MAE, không reset)
    public Float lastPrice;
    public Float rateChange;
    public Float volume;
    public TreeMap<Long, Float> time2FundingFee = new TreeMap<>();
    public MarketDataObject marketData;
    public MarketLevelChange marketLevelChange;
    public KlineObjectSimple tickerOpen;
    public AiPredictionData predict;
    public Float symbolPred;
```

### A7 — Caller của close/calTp trong vòng lặp theo bar
- Vòng lặp bar gọi `startUpdateOldOrderTrading` cho mỗi cụm đang chạy MỖI phút:
  `src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java:102-111`
```java
                            if (activeRunningCount > 0) {
                                short[] currentIds = Arrays.copyOf(activeRunningIds, activeRunningCount);
                                for (short runningSymbolId : currentIds) {
                                    KlineObjectSimple ticker = symbol2Ticker[runningSymbolId];
                                    if (ticker != null) {
                                        startUpdateOldOrderTrading(time, runningSymbolId, ticker);  // -> closeOrder khi trigger
                                    }
                                }
```
- `calTp()` được gọi trong `BudgetManagerSimple.updatePnl(order)` (từ `closeOrder:463`):
  `src/main/java/com/binance/chuyennd/research/BudgetManagerSimple.java:64-73`
```java
    public void updatePnl(OrderTargetInfoTest orderInfo) {
        if (orderInfo != null) {
            if (orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) { totalSL++; }
            fee += calFee(orderInfo);
            totalFundingFee += orderInfo.calFundingFee();
            profit += orderInfo.calTp();           // <-- realize PnL
        }
    }
```
- `calProfit()` (unrealized) gọi trong `BudgetManagerSimple.calUnrealizedProfit` (vòng `updateBalance`). `calTp()` còn được dùng ở report: `EdgeAttributionReport`, `RunBreakerBacktest`, `ClassifyExitOutOfRange`.

### A8 — File ghi chú fix kẹp `min(priceSL, bar.open)`
**KHÔNG TÌM THẤY.** Glob `**/{PROMPT*,*exit*,*booking*}.md` → 0 file. Grep từ khóa `bar.open | PROMPT_fix | exit_booking | min(priceSL | kẹp | gap-fill` → chỉ khớp `priceOpen` trong code/proto, KHÔNG có file ghi chú fix nào. (Fix kẹp hiện có trong code dùng `ticker.maxPrice`, không phải `bar.open`.)

---

## B. Survivorship / delist handling

### B1 — `updateSymbolDeListed` (đóng cụm coin hết data >2 ngày tại lastPrice)
`src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java:388-397`

```java
    public void updateSymbolDeListed(short symbolId, Long time) {
        OrderTargetInfoTest order = symbol2OrderRunning[symbolId];
        if (order != null) {
            if (order.timeUpdate < time - 2 * Utils.TIME_DAY) {      // ngưỡng "2 ngày" = 2 * Utils.TIME_DAY
                order.status = OrderTargetStatus.STOP_LOSS_DONE;     // đóng = STOP_LOSS_DONE
                order.priceTP = order.lastPrice;                     // lastPrice = giá close cuối còn thấy
                closeOrder(symbolId, order);                         // đóng cụm + free margin (A4)
            }
        }
    }
```
- Ngưỡng "2 ngày": hằng `2 * Utils.TIME_DAY`, so với `order.timeUpdate` (lần cuối cụm được cập nhật giá).
- "hết data": gọi từ nhánh hourly khi `!Utils.isTickerAvailable(ticker)` (B1-caller).
- lastPrice: `order.lastPrice` (giá close cuối cùng cập nhật vào cụm).
- Đóng + free vốn: `closeOrder` (A4) trừ `marginRunning -= calMargin()`.

**B1-caller (job theo GIỜ):** `...SimulatorMarketLevelTicker1MStopLoss.java:234-243`
```java
                            } else {
                                if (time % (60 * Utils.TIME_MINUTE) == 0) {                 // mỗi giờ
                                    short[] currentIds = Arrays.copyOf(activeRunningIds, activeRunningCount);
                                    for (Short symbolId : currentIds) {
                                        KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                        if (!Utils.isTickerAvailable(ticker)) {             // ticker chết
                                            updateSymbolDeListed(symbolId, time);
                                        }
                                    }
                                    BudgetManagerSimple.getInstance().updateBalance(...);
                                }
                            }
```
⚠️ Nhánh này nằm trong `else` của block "có marketData+predict" — tức chỉ chạy phút nào KHÔNG ra `levelChange`. (Cần lưu ý khi đánh giá tần suất quét delist.)

**Điều kiện "hết data":** `src/main/java/com/binance/chuyennd/utils/Utils.java:457-463`
```java
    public static boolean isTickerAvailable(KlineObjectSimple ticker) {
        if (ticker != null) {
            return ticker.minPrice != ticker.maxPrice
                    || ticker.totalUsdt != 0;
        }
        return false;
    }
```
Coi là "hết data/chết" khi ticker null HOẶC (min==max VÀ volume==0).

### B2 — Nơi LOAD universe symbol (mapper)
`src/main/java/com/binance/chuyennd/ai_ml/data/SimpleSymbolMapper.java:68-91` (load từ set `symbol_mapper` qua `DataManagerAerospikeFloatSim.loadSymbolMapper()`)

```java
    public synchronized void init() {
        if (isInitialized) return;
        LOG.info("🔄 Initializing SimpleSymbolMapper (Singleton) from Aerospike...");
        Map<String, Short> dbMap = DataManagerAerospikeFloatSim.loadSymbolMapper();
        if (dbMap != null && !dbMap.isEmpty()) {
            strToId.putAll(dbMap);
            short maxId = 0;
            for (Map.Entry<String, Short> entry : dbMap.entrySet()) {
                idToStr.put(entry.getValue(), entry.getKey());
                if (entry.getValue() > maxId) { maxId = entry.getValue(); }
            }
            counter = maxId;
        }
        isInitialized = true;
        LOG.info("✅ SimpleSymbolMapper initialized. Total: {}, Next ID: {}", strToId.size(), counter + 1);
    }
```
Đây chỉ là MAP `symbol <-> short id` (log "Total: 751" = số symbol từng được cấp id). **KHÔNG có filter sống/chết/đang-listed** — chỉ là từ điển id. Nguồn: `loadSymbolMapper()` đọc set `symbol_mapper` (`DataManagerAerospikeFloatSim.java:100-122`, đọc qua `getReadClient()` → 226 nếu kaggle/hpo, else 242).

### B3 — Quyết định symbol có vào backtest hay không (entry universe)
`src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java:123-146` (`getTopSymbolArray`)

```java
    public static Set<Short> getTopSymbolArray(int period, KlineObjectSimple[] symbol2FinalTicker,
                                               Set<Short> symbolLocked, TreeMap<Float, Short> predict2Symbol) {
        Set<Short> symbols = new HashSet<>();
        if (predict2Symbol != null && !predict2Symbol.isEmpty()) {
            for (Map.Entry<Float, Short> entry : predict2Symbol.entrySet()) {
                Short symbolKey = entry.getValue();
                if (symbolLocked != null && symbolLocked.contains(symbolKey)) { continue; }
                KlineObjectSimple ticker = symbol2FinalTicker[symbolKey];
                if (ticker != null) { symbols.add(symbolKey); }   // CHỈ chọn symbol CÓ ticker phút này
                if (symbols.size() >= period) { break; }
            }
        }
        return symbols;
    }
```
Entry chỉ chọn symbol có `ticker != null` tại phút đó (ranked theo funding pred `predict2Symbol`). Thêm các filter trong `createOrderBUY` (`...Simulator...:505-547+`): `is50PercentOrderLoss`, `AIRejectFilter.checkSignal/checkSignalDynamic`, circuit breaker, `CoinRankManager` tier (TIER_3 chặn DCA). **Chỗ survivorship dễ lọt:** universe = bất kỳ symbol nào có ticker tại phút đó (không có danh sách "đang-listed" cứng); coin chết = không có ticker → không được chọn entry, còn cụm đang mở thì do B1 xử lý.

### B4 — Log/metric/counter sự kiện delist-close
**KHÔNG TÌM THẤY counter/log chuyên biệt.** `updateSymbolDeListed` (B1) KHÔNG log, KHÔNG tăng counter riêng. Delist-close gắn `status = STOP_LOSS_DONE` ⇒ chỉ được đếm gộp vào `BudgetManagerSimple.totalSL` (`BudgetManagerSimple.java:66-67`) và xuất hiện trong `allOrderDone` (status `STOP_LOSS_DONE`, `timeUpdate` = giờ đóng, `priceTP = lastPrice`). Grep `delist | deListed | DELIST | survivorship` → chỉ thấy hàm `updateSymbolDeListed` + caller, không có metric theo năm. ⇒ Muốn đếm delist-close theo năm phải THÊM (hoặc hậu xử lý `allOrderDone`: lọc cụm đóng kiểu delist = `timeUpdate` lệch xa nến cuối có data).

### B5 — Data-access truy lịch sử giá theo symbol/time (KHÔNG chạy query)
`src/main/java/com/binance/chuyennd/aerospike/DataManagerAerospikeFloatSim.java`
- `:475` `public static TreeMap<Long, KlineObjectSimple[]> readDataFromAerospike1M_ShortKey(long startTime)` — đọc 1 NGÀY giao dịch (07:00 GMT+7 + 1440'), key = phút (ms), value = mảng `KlineObjectSimple[]` index theo `symbolId`. Đọc qua `getReadClient()` (226 nếu kaggle/hpo).
- `:567` `public static TreeMap<Long, Map<String, KlineObjectSimple>> readDataFromAerospikeCustom(long startTime, int totalMinutes)` — đọc range phút tùy ý, value = `Map<symbol, kline>` mỗi phút.
- `:1924` `public static TreeMap<Long, long[]> getFundingPredsForTimestamps(String setName, long[] timestamps)` — funding pred theo set + list phút.

Truy cập là **THEO THỜI GIAN (key=phút)** rồi lấy symbol trong mảng/map của phút đó; "symbol có data phút này" = `Utils.isTickerAvailable` (B1). **KHÔNG có index first-seen/last-seen theo symbol sẵn** ⇒ muốn dựng bảng sinh-tử symbol theo năm phải QUÉT ticker theo thời gian và ghi nhận phút đầu/cuối có `isTickerAvailable` cho mỗi `symbolId` (chưa có hàm sẵn — phải thêm; chỉ trích cách truy data, không chạy).

---

## Index file path (các file đã trích)
- `src/main/java/com/binance/chuyennd/research/OrderTargetInfoTest.java`
- `src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java`
- `src/main/java/com/binance/chuyennd/research/BudgetManagerSimple.java`
- `src/main/java/com/binance/chuyennd/utils/Utils.java`
- `src/main/java/com/binance/chuyennd/ai_ml/data/SimpleSymbolMapper.java`
- `src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java`
- `src/main/java/com/binance/chuyennd/aerospike/DataManagerAerospikeFloatSim.java`

## Không tìm thấy
- **A8** file `PROMPT_fix_exit_booking.md` / ghi chú `min(priceSL, bar.open)`: KHÔNG TÌM THẤY. Glob `**/{PROMPT*,*exit*,*booking*}.md` = 0 file; grep `bar.open|PROMPT_fix|exit_booking|min(priceSL|kẹp|gap-fill` chỉ khớp `priceOpen` trong code/proto. (Code hiện kẹp theo `ticker.maxPrice`, không phải `bar.open`.)
- **B4** counter/metric delist-close theo năm: KHÔNG TÌM THẤY (chỉ gộp vào `totalSL` + `allOrderDone` status `STOP_LOSS_DONE`). Grep `delist|deListed|survivorship`.
- **B5** index first-seen/last-seen theo symbol: KHÔNG TÌM THẤY hàm sẵn (data truy theo phút, phải tự quét).
