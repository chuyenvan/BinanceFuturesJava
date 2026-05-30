package com.binance.chuyennd.research;

import ai.onnxruntime.OrtException;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager15M;
import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
import com.binance.chuyennd.bigchange.test.TraceOrderDone;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.*;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.text.ParseException;
import java.util.*;

public class SimulatorMarketLevelTicker1MStopLoss {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorMarketLevelTicker1MStopLoss.class);
    public static final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone15M.data";
    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;

    // 🔥 Dùng MarketDataObject15M thay cho 1M
    public TreeMap<Long, MarketDataObject15M> time2MarketData;
    public TreeMap<Long, AiPredictionData> predictionMap;
    public TreeMap<Long, long[]> time2SymbolPred;

    public AIRejectFilter aiRejectFilter;
    public Boolean is50PercentOrderLoss = null;

    @SuppressWarnings("unchecked")
    public List<OrderTargetInfoTest>[] symbol2OrdersEntry = new ArrayList[5000];
    public OrderTargetInfoTest[] symbol2OrderRunning = new OrderTargetInfoTest[5000];

    public short[] activeRunningIds = new short[5000];
    public int activeRunningCount = 0;

    public void setConfig(BotTradingConfig config) {
        Configs.BASE_DOWN = config.baseDown;
        Configs.RATIO_DOWN = config.ratioDown;
        Configs.BASE_UP = config.baseUp;
        Configs.RATIO_UP = config.ratioUp;

        Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = config.aiPredictRateMaxThreshold;
        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = config.aiPredictRateDown15m;
        Configs.PREDICT_SYMBOL_RATE_UP_AVG = config.aiPredictRateUpAvg;
        Configs.PREDICT_SYMBOL_RATE_DOWN_AVG = config.aiPredictRateDownAvg;

        Configs.MS_UP_BIG_THRES = config.msUpBigThres;
        Configs.MS_DOWN_BIG_AVG = config.msDownBigAvg;
        Configs.MS_UP_MED_THRES = config.msUpMedThres;
        Configs.MS_DOWN_MED_AVG = config.msDownMedAvg;
        Configs.MS_UP_SMALL_THRES = config.msUpSmallThres;
        Configs.MS_DOWN_SMALL_AVG = config.msDownSmallAvg;
        Configs.MS_DOWN_15M_SMALL_ONLY = config.msDown15mSmallOnly;

        Configs.RATE_PROFIT_STOP_MARKET = config.rateProfitStopMarket;

        Configs.number_order_budget = config.numberOrderBudget;
        Configs.BUDGET_MARGIN_RATIO_1 = config.budgetMarginRatio1;
        Configs.BUDGET_DIVIDER_1 = config.budgetDivider1;
        Configs.BUDGET_MARGIN_RATIO_2 = config.budgetMarginRatio2;
        Configs.BUDGET_DIVIDER_2 = config.budgetDivider2;

        Configs.LEVERAGE_ORDER = config.leverageOrder;
        Configs.NUMBER_ENTRY_EACH_SIGNAL = config.numberEntryEachSignal;
        Configs.MAX_CONCURRENT_ORDERS = config.maxConcurrentOrders;
    }

    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        LOG.info("Start with kaggle mode: {} ", Configs.IS_KAGGLE_MODE);
        SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
        test.initData();
        test.simulatorWithInitEntry(startTime, System.currentTimeMillis());
        Thread.sleep(5000);
        System.exit(1);
    }

    public void simulatorWithInitEntry(Long startTime, Long endTime) throws ParseException {
        long timeSimulator = System.currentTimeMillis();
        LOG.info("=== 🚀 BẮT ĐẦU SIMULATE HỆ 15M TỪ {} ĐẾN {} ===", Utils.normalizeDateYYYYMMDDHHmm(startTime), Utils.normalizeDateYYYYMMDDHHmm(endTime));

        // 🔥 FIX VÒNG LẶP: Nhảy mỗi ngày để đọc batch, mỗi batch 96 nến (15 phút/nến)
        int chunkBlocks15m = 96;

        while (startTime <= endTime) {
            TreeMap<Long, Map<Short, KlineObjectSimple>> time2Tickers;
            try {
                // 🔥 Đọc dữ liệu nến 15 phút từ Aerospike
                if (Configs.IS_HPO_MODE) {
                    time2Tickers = KaggleDataLoader.loadDailyTickersRaw(startTime);
                } else {

                    time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(startTime, chunkBlocks15m);
                }
                if (time2Tickers == null || time2Tickers.isEmpty()) {
                    LOG.info("File data error or not found for time: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                }

                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<Short, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey(); // Thời gian nhảy 15 phút một lần
                        try {
                            long startTimeRun = System.currentTimeMillis();
                            Map<Short, KlineObjectSimple> symbol2TickerMap = entry.getValue();

                            // Chuyển Map sang mảng để dùng code O(1) cũ
                            KlineObjectSimple[] symbol2Ticker = new KlineObjectSimple[5000];
                            for (Map.Entry<Short, KlineObjectSimple> klineEntry : symbol2TickerMap.entrySet()) {
                                symbol2Ticker[klineEntry.getKey()] = klineEntry.getValue();
                            }

                            // Cập nhật History 15M
                            HistoryManager15M.getInstance().updateHistoryArray(symbol2Ticker);

                            // --- TỐI ƯU CẬP NHẬT LỆNH ---
                            if (activeRunningCount > 0) {
                                for (int i = activeRunningCount - 1; i >= 0; i--) {
                                    short runningSymbolId = activeRunningIds[i];
                                    KlineObjectSimple ticker = symbol2Ticker[runningSymbolId];
                                    if (ticker != null) {
                                        startUpdateOldOrderTrading(time, runningSymbolId, ticker);
                                    }
                                }
                            }

                            logByProcessTime(startTimeRun, "Done update order", time);
                            startTimeRun = System.currentTimeMillis();

                            // =========================================================
                            // 🔥 KHÔNG CẦN FALLBACK FLOOR TIME NỮA VÌ ĐÂY LÀ HỆ NATIVE 15M
                            // =========================================================
                            MarketDataObject15M marketData = time2MarketData.get(time);
                            AiPredictionData predict = predictionMap.get(time);

                            Set<Short> symbolLocked = new HashSet<>();
                            MarketLevelChange levelChange = null;

                            if (predict != null && marketData != null) {
                                // GỌI BIG CHANGE CHO 15M
                                levelChange = MarketBigChangeDetector.getMarketStatus1M(marketData.rateDownAvg, marketData.rateUpAvg, marketData.rateDown4HAvg);

                                if (levelChange != null) {
                                    Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;

                                    for (int i = 0; i < activeRunningCount; i++) symbolLocked.add(activeRunningIds[i]);

                                    if (levelChange.equals(MarketLevelChange.SMALL_DOWN) || levelChange.equals(MarketLevelChange.SMALL_UP) || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M) || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)) {
                                        numberOrder = numberOrder / 2;
                                    }

                                    Set<Short> symbol2BUY = new HashSet<>();
                                    long[] currentSymbolPreds = time2SymbolPred.get(time);

                                    TreeMap<Float, Short> predict2Symbol = extractPredict2Symbol(currentSymbolPreds);

                                    symbol2BUY.addAll(MarketBigChangeDetector.getTopSymbolArray(numberOrder,
                                            symbol2Ticker, symbolLocked, predict2Symbol));

                                    Map<Short, OrderTargetInfoTest> activeOrderMap = getActiveOrderMap();
                                    List<Short> symbolDcaLevel = DcaProcessor.getDCA(levelChange, time, BudgetManagerSimple.getInstance().getBudget(), activeOrderMap);

                                    for (short symbolId : symbol2BUY) {
                                        KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                        if (Utils.isTickerAvailable(ticker)) {
                                            createOrderBUY(symbolId, ticker, levelChange, marketData, null);
                                        }
                                    }
                                    for (short symbolId : symbolDcaLevel) {
                                        KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                        if (Utils.isTickerAvailable(ticker)) {
                                            createOrderBUY(symbolId, ticker, MarketLevelChange.DCA_LEVEL1, marketData, null);
                                        }
                                    }
                                }
                            }

                            logByProcessTime(startTimeRun, "Done market data", time);
                            startTimeRun = System.currentTimeMillis();

                            if (marketData != null) {
                                // DCA Altcoin (Dùng hàm 15M nếu có, tạm giữ nguyên tên)
                                if (MarketBigChangeDetector.isDcaAlt(marketData.rateDown4HAvg, marketData.rateDownAvg, marketData.rateUpAvg)) {
                                    List<Short> symbolDcaLossBig = DcaProcessor.getDCA(null, time, BudgetManagerSimple.getInstance().getBudget(), getActiveOrderMap());
                                    for (short symbolId : symbolDcaLossBig) {
                                        KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                        if (Utils.isTickerAvailable(ticker)) {
                                            createOrderBUY(symbolId, ticker, MarketLevelChange.DCA_LEVEL1, marketData, null);
                                        }
                                    }
                                    logByProcessTime(startTimeRun, "Done dca big", time);
                                    startTimeRun = System.currentTimeMillis();
                                }

                                // 🔥 FUNDING FEE THEO 15 PHÚT TỰ NHIÊN
                                long[] symbol2Pred = time2SymbolPred.get(time);
                                if (symbol2Pred != null) {
                                    float maxThres = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * Configs.AI_DYNAMIC_MAX;

                                    for (long encodedData : symbol2Pred) {
                                        float symbolPred = Float.intBitsToFloat((int) encodedData);
                                        if (symbolPred > maxThres) break;

                                        short targetId = (short) (encodedData >> 32);

                                        if (!isSymbolRunning(targetId)) {
                                            KlineObjectSimple ticker = symbol2Ticker[targetId];
                                            if (Utils.isTickerAvailable(ticker)) {
                                                createOrderBUY(targetId, ticker, MarketLevelChange.PREDICT_SYMBOL_TRADE, marketData, symbolPred);
                                            }
                                        }
                                    }
                                }
                            }

                            logByProcessTime(startTimeRun, "Done funding fee", time);
                            startTimeRun = System.currentTimeMillis();

                            // XỬ LÝ CHỐT SỔ NGÀY/GIỜ (Phải tính toán thời gian chẵn ngày/giờ)
                            if (Utils.isStartOfDay(time)) { // Viết thêm hàm isStartOfDay(time) trong Utils nếu chưa có, tương đương time % Utils.TIME_DAY == 0
                                if (Configs.IS_HPO_MODE) {
                                    if (Utils.isMidnightFirstDay(time)) {
                                        BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, getActiveIdSet(), symbol2OrderRunning, symbol2OrdersEntry, true);
                                    } else {
                                        BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, getActiveIdSet(), symbol2OrderRunning, symbol2OrdersEntry, false);
                                    }
                                } else {
                                    if (Utils.isFirstDayOfYear(time)) {
                                        System.gc();
                                    }
                                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, getActiveIdSet(), symbol2OrderRunning, symbol2OrdersEntry, true);
                                }
                            } else {
                                if (Utils.isStartOfHour(time)) { // Tương đương time % (60 * Utils.TIME_MINUTE) == 0
                                    for (int i = activeRunningCount - 1; i >= 0; i--) {
                                        short symbolId = activeRunningIds[i];
                                        KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            updateSymbolDeListed(symbolId, time);
                                        }
                                    }
                                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, getActiveIdSet(), symbol2OrderRunning, symbol2OrdersEntry, false);
                                }
                            }
                            logByProcessTime(startTimeRun, "Done budget data", time);
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                        is50PercentOrderLoss = null;
                    }
                } else {
                    LOG.info("Date data error: {}", Utils.normalizeDateYYYYMMDD(startTime));
                }
                time2Tickers = null;
            } catch (Exception e) {
                e.printStackTrace();
            }

            Long finalStartTime1 = startTime;
            startTime += Utils.TIME_DAY; // Nhảy 1 ngày

            if (startTime > endTime) {
                BudgetManagerSimple.getInstance().updateBalance(finalStartTime1, allOrderDone, getActiveIdSet(), symbol2OrderRunning, symbol2OrdersEntry, false);
                break;
            }
        }

        // KẾT THÚC VÀ ĐÓNG LỆNH
        for (int i = 0; i < activeRunningCount; i++) {
            short id = activeRunningIds[i];
            List<OrderTargetInfoTest> orderRunningList = symbol2OrdersEntry[id];
            if (orderRunningList != null) {
                for (OrderTargetInfoTest orderInfo : orderRunningList) {
                    orderInfo.lastPrice = symbol2OrderRunning[id].lastPrice;
                    orderInfo.priceTP = orderInfo.lastPrice;
                    orderInfo.minPrice = symbol2OrderRunning[id].minPrice;
                    orderInfo.timeUpdate = symbol2OrderRunning[id].timeUpdate;
                    orderInfo.updateFundingFee();
                    allOrderDone.put(-orderInfo.timeUpdate - allOrderDone.size(), orderInfo);
                }
            }
        }

        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);
        int finalYear = cal.get(Calendar.YEAR);
        BudgetManagerSimple.getInstance().balanceIndex.year2UnrealizedPnl.put(finalYear, 0f);

        if (!Configs.IS_KAGGLE_MODE) {
            try {
                Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
                Storage.writeObject2File("storage/BalanceIndex.data", BudgetManagerSimple.getInstance().balanceIndex);
                TraceOrderDone.printOrderTestDone("storage/printDone15M.csv", allOrderDone); // Tách file log
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        Utils.printMemoryUse(System.currentTimeMillis() - timeSimulator);
    }

    // Các hàm O(1) giữ nguyên
    private void addActiveRunningId(short id) {
        for (int i = 0; i < activeRunningCount; i++) {
            if (activeRunningIds[i] == id) return;
        }
        if (activeRunningCount < activeRunningIds.length) {
            activeRunningIds[activeRunningCount++] = id;
        }
    }

    private void removeActiveRunningId(short id) {
        for (int i = 0; i < activeRunningCount; i++) {
            if (activeRunningIds[i] == id) {
                activeRunningIds[i] = activeRunningIds[activeRunningCount - 1];
                activeRunningCount--;
                return;
            }
        }
    }

    private boolean isSymbolRunning(short id) {
        for (int i = 0; i < activeRunningCount; i++) {
            if (activeRunningIds[i] == id) return true;
        }
        return false;
    }

    private Set<Short> getActiveIdSet() {
        Set<Short> set = new HashSet<>();
        for (int i = 0; i < activeRunningCount; i++) set.add(activeRunningIds[i]);
        return set;
    }

    private Map<Short, OrderTargetInfoTest> getActiveOrderMap() {
        Map<Short, OrderTargetInfoTest> activeMap = new HashMap<>();
        for (int i = 0; i < activeRunningCount; i++) {
            short id = activeRunningIds[i];
            activeMap.put(id, symbol2OrderRunning[id]);
        }
        return activeMap;
    }

    private List<OrderTargetInfoTest> getActiveOrderList() {
        List<OrderTargetInfoTest> list = new ArrayList<>(activeRunningCount);
        for (int i = 0; i < activeRunningCount; i++) {
            list.add(symbol2OrderRunning[activeRunningIds[i]]);
        }
        return list;
    }

    private Integer counterOrderRunning() {
        int counter = 0;
        for (int i = 0; i < activeRunningCount; i++) {
            short id = activeRunningIds[i];
            if (symbol2OrdersEntry[id] != null) {
                counter += symbol2OrdersEntry[id].size();
            }
        }
        return counter;
    }

    private TreeMap<Float, Short> extractPredict2Symbol(long[] encodedDataArray) {
        TreeMap<Float, Short> predict2Symbol = new TreeMap<>();
        if (encodedDataArray != null) {
            for (long encodedData : encodedDataArray) {
                short symbolId = (short) (encodedData >> 32);
                float pred = Float.intBitsToFloat((int) encodedData);
                predict2Symbol.put(pred, symbolId);
            }
        }
        return predict2Symbol;
    }

    private void logByProcessTime(Long startTimeRun, String msg, Long time) {
        long duration = (System.currentTimeMillis() - startTimeRun);
        if (duration > 20) {
            LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), msg, duration);
        }
    }

    public void updateSymbolDeListed(short symbolId, Long time) {
        OrderTargetInfoTest order = symbol2OrderRunning[symbolId];
        if (order != null) {
            if (order.timeUpdate < time - 2 * Utils.TIME_DAY) {
                order.status = OrderTargetStatus.STOP_LOSS_DONE;
                order.priceTP = order.lastPrice;
                closeOrder(symbolId, order);
            }
        }
    }

    public void initData() throws IOException, ParseException {
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();

        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        int numberMinutes = System.currentTimeMillis() - startTime > 0 ? (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_MINUTE) : 0;

        LOG.info("📥 Đang tải dữ liệu HỆ 15M vào RAM...");

        // Đổi hàm load để gọi bản 15M của Database (Cần đảm bảo hàm này có sẵn trong DataManagerAerospikeFloatSim)
        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketData15MFromAerospike();

        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike(); // Market Pred
        time2SymbolPred = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, numberMinutes); // Funding Pred

        preprocessFundingData(time2SymbolPred);
        aiRejectFilter = new AIRejectFilter();

        SimpleSymbolMapper.getInstance().init();

        Utils.printMemoryUsage("Load time2FundingPre (time2SymbolPred)");
        LOG.info("✅ TẤT CẢ DỮ LIỆU ĐÃ SẴN SÀNG. BẮT ĐẦU SIMULATE 15M...");
    }

    public void initDataReady(TreeMap<Long, MarketDataObject15M> t2MarketData,
                              TreeMap<Long, AiPredictionData> t2Predict, TreeMap<Long, long[]> t2FundingPre,
                              AIRejectFilter aiRejectFilter) throws OrtException {
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();
        SimpleSymbolMapper.getInstance().init();

        this.time2MarketData = t2MarketData;
        this.predictionMap = t2Predict;
        this.time2SymbolPred = t2FundingPre;
        preprocessFundingData(this.time2SymbolPred);

        this.aiRejectFilter = aiRejectFilter;
    }

    private void preprocessFundingData(TreeMap<Long, long[]> time2FundingPre) {
        if (time2FundingPre == null) return;
        LOG.info("⚙️ Bắt đầu Pre-calculate (Sort sẵn) dữ liệu Funding Fee...");
        long start = System.currentTimeMillis();
        for (long[] preds : time2FundingPre.values()) {
            if (preds == null || preds.length == 0) continue;

            Long[] boxed = new Long[preds.length];
            for (int i = 0; i < preds.length; i++) {
                boxed[i] = preds[i];
            }

            Arrays.sort(boxed, (a, b) -> {
                float valA = Float.intBitsToFloat(a.intValue());
                float valB = Float.intBitsToFloat(b.intValue());
                return Float.compare(valA, valB);
            });

            for (int i = 0; i < preds.length; i++) {
                preds[i] = boxed[i];
            }
        }
        LOG.info("✅ Pre-calculate hoàn tất trong {} ms.", (System.currentTimeMillis() - start));
    }

    private void startUpdateOldOrderTrading(Long time, short symbolId, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning[symbolId];
        if (orderMulti != null) {
            if (orderMulti.timeStart <= ticker.startTime) {
                orderMulti.updatePriceByKlineSimple(ticker);
                if (ticker.maxPrice >= orderMulti.priceEntry * 1.007 || orderMulti.priceSL != null) {
                    Float maxChangeIn90M = getMaxRateIn90MForTradingStop(time);
                    orderMulti.updateStatusNew(maxChangeIn90M, ticker);
                    if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                        closeOrder(symbolId, orderMulti);
                    } else {
                        orderMulti.updateTPSL(maxChangeIn90M, ticker);
                    }
                }
            }
        }
    }

    private Float getMaxRateIn90MForTradingStop(Long time) {
        AiPredictionData predict = predictionMap.get(time); // Ko cần fallback 15m nữa
        if (predict == null) return 0f;
        return predict.predReturn1H;
    }

    private void closeOrder(short symbolId, OrderTargetInfoTest orderMulti) {
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry[symbolId];
        if (orders != null) {
            for (OrderTargetInfoTest order : orders) {
                order.timeUpdate = orderMulti.timeUpdate;
                order.status = orderMulti.status;
                order.priceTP = orderMulti.priceTP;
                order.minPrice = orderMulti.minPrice;
                order.lastPrice = orderMulti.lastPrice;

                allOrderDone.put(-order.timeUpdate - allOrderDone.size(), order);
                BudgetManagerSimple.getInstance().updatePnl(order);
            }
        }

        symbol2OrdersEntry[symbolId] = null;
        symbol2OrderRunning[symbolId] = null;
        removeActiveRunningId(symbolId);

        BudgetManagerSimple.getInstance().marginRunning -= orderMulti.calMargin();
    }

    private OrderTargetInfoTest mergeOrder(List<OrderTargetInfoTest> orders, KlineObjectSimple ticker) {
        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        float quantity = 0f;
        float margin = 0f;
        for (OrderTargetInfoTest orderInfo : orders) {
            time2Order.put(orderInfo.timeStart, orderInfo);
            margin += orderInfo.priceEntry * orderInfo.quantity;
            quantity += orderInfo.quantity;
        }
        float entry = margin / quantity;

        OrderTargetInfoTest orderResult = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity, Configs.LEVERAGE_ORDER,
                time2Order.lastEntry().getValue().symbol, time2Order.lastEntry().getKey(), time2Order.lastEntry().getKey(), orders.get(0).side);

        orderResult.minPrice = ticker.priceClose;
        orderResult.lastPrice = ticker.priceClose;
        orderResult.lastEntry = orders.get(orders.size() - 1).lastEntry;
        orderResult.rateChange = orders.get(orders.size() - 1).rateChange;

        // Cần đảm bảo hàm này chấp nhận MarketDataObject15M (nếu không, hãy cập nhật trong OrderTargetInfoTest)
        // orderResult.tickerOpen = time2Order.lastEntry().getValue().tickerOpen;
        orderResult.marketLevelChange = time2Order.lastEntry().getValue().marketLevelChange;

        return orderResult;
    }

    public void createOrderBUY(short symbolId, KlineObjectSimple ticker, MarketLevelChange levelChange,
                               MarketDataObject15M marketData, Float symbolPred) { // Đổi sang MarketDataObject15M

        if (levelChange != MarketLevelChange.DCA_LEVEL1) {
            if (is50PercentOrderLoss == null)
                is50PercentOrderLoss = MarketBigChangeDetector.is50PercentOrderLoss(getActiveOrderList(), ticker.startTime);
            if (is50PercentOrderLoss) {
                return;
            }
        }

        AiPredictionData predict = predictionMap.get(ticker.startTime);

        if (predict != null && !levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            AIRejectFilter.FilterResult filterResult = null;
            if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) {
                if (symbolPred != null) {
                    filterResult = aiRejectFilter.checkSignalDynamic(predict, symbolPred);
                }
            }
            if (filterResult == null)
                filterResult = aiRejectFilter.checkSignal(predict);

            if (filterResult.decision == AIRejectFilter.FilterDecision.REJECT) {
                return;
            }
        }

        Float entry = ticker.priceClose;
        Integer leverage = Configs.LEVERAGE_ORDER;

        long currentTs = ticker.startTime;
        CoinRankManager15M.CoinTier myTier = CoinRankManager15M.getInstance().getCoinTierShort(symbolId, currentTs);
        if (myTier == CoinRankManager15M.CoinTier.TIER_3_SHITCOIN) {
            if (levelChange == MarketLevelChange.DCA_LEVEL1) {
                return;
            }
        }

        Float marginRunning = BudgetManagerSimple.getInstance().marginRunning;
        Float balanceBasic = BudgetManagerSimple.getInstance().balanceBasic;
        Float budget = BudgetManagerSimple.getInstance().getBudget();

        budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange);

        if (budget == null) {
            return;
        }

        float tierMultiplier = CoinRankManager15M.getInstance().getBudgetMultiplier(symbolId);
        budget *= tierMultiplier;

        String symbolStr = SimpleSymbolMapper.getInstance().getSymbol(symbolId);
        Float quantity = Utils.calQuantityTest(budget, leverage, entry, symbolStr);

        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry,
                null, quantity, leverage, symbolStr, ticker.startTime,
                ticker.startTime, OrderSide.BUY);

        order.minPrice = entry;
        order.lastEntry = entry;
        order.lastPrice = entry;
        order.tickerOpen = ticker;
        order.marketLevelChange = levelChange;

        // Cần đảm bảo order.marketData hỗ trợ MarketDataObject15M, có thể cần cast hoặc đổi biến trong class đó.
        if (marketData != null) {
            order.marketData = marketData;
        }
        order.predict = predict;
        order.symbolPred = symbolPred;

        List<OrderTargetInfoTest> orders = symbol2OrdersEntry[symbolId];
        if (orders == null) {
            orders = new ArrayList<>();
            symbol2OrdersEntry[symbolId] = orders;
        }
        orders.add(order);

        BudgetManagerSimple.getInstance().counterOrderCreated.incrementAndGet();

        symbol2OrderRunning[symbolId] = mergeOrder(orders, ticker);
        addActiveRunningId(symbolId);

        BudgetManagerSimple.getInstance().updateMaxOrderRunning(counterOrderRunning());
        BudgetManagerSimple.getInstance().marginRunning += order.calMargin();
    }
}