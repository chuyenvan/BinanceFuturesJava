/*
 */
package com.binance.chuyennd.research;

import ai.onnxruntime.OrtException;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.BacktestIntegrityGuard;
import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.bigchange.test.TraceOrderDone;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.*;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.text.ParseException;
import java.util.*;

/**
 * @author pc
 */
public class SimulatorMarketLevelTicker1MStopLoss {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorMarketLevelTicker1MStopLoss.class);
    public static final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";
    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;
    public TreeMap<Long, MarketDataObject> time2MarketData;
    public TreeMap<Long, AiPredictionData> predictionMap;
    public TreeMap<Long, long[]> time2SymbolPred;
    public AIRejectFilter aiRejectFilter;
    public Boolean is50PercentOrderLoss = null;

    // Đếm số lần circuit breaker kích hoạt (reset theo mỗi instance Simulator). Runner đọc để báo cáo.
    public long breakerMarginHaltCount = 0;
    public long breakerDcaCapCount = 0;

    // =================================================================
    // 🔥 SỬ DỤNG MẢNG CỐ ĐỊNH O(1) ĐỂ LOẠI BỎ AUTOBOXING RÁC CỦA HASHMAP
    // =================================================================
    @SuppressWarnings("unchecked")
    public List<OrderTargetInfoTest>[] symbol2OrdersEntry = new ArrayList[1000];
    public OrderTargetInfoTest[] symbol2OrderRunning = new OrderTargetInfoTest[1000];

    // 🔥 TỐI ƯU TUYỆT ĐỐI: Dùng mảng nguyên thủy thay cho HashSet<Short>
    // Loại bỏ hoàn toàn Autoboxing khi gọi add(), remove() hay contains()
    public short[] activeRunningIds = new short[1000]; // Tối đa 100 lệnh chạy cùng lúc
    public int activeRunningCount = 0;

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
        // 🔒 NÚT CHẶN LIÊM CHÍNH DUY NHẤT: mọi backtest (HPO master, WFO, 7 engine khác,
        // hay chạy main() trực tiếp) đều đi qua hàm này. Đặt guard ở đây nên KHÔNG engine
        // nào bypass được — không cần ai nhớ gọi assert ở từng engine.
        BacktestIntegrityGuard.assertProductionGrade();

        long timeSimulator = System.currentTimeMillis();
        LOG.info("=== 🚀 BẮT ĐẦU SIMULATE TỪ {} ĐẾN {} ===", Utils.normalizeDateYYYYMMDDHHmm(startTime), Utils.normalizeDateYYYYMMDDHHmm(endTime));

        while (true) {
            TreeMap<Long, KlineObjectSimple[]> time2Tickers;
            try {
                if (Configs.IS_KAGGLE_MODE) {
                    time2Tickers = KaggleDataLoader.loadDailyTickersShort(startTime);
                } else {
                    time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(startTime);
                }

                if (time2Tickers == null) {
                    LOG.info("File data error or not found for time: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                }

                if (time2Tickers != null && time2Tickers.size() >= 1440) {
                    for (Map.Entry<Long, KlineObjectSimple[]> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        try {
                            long startTimeRun = System.currentTimeMillis();
                            KlineObjectSimple[] symbol2Ticker = entry.getValue();

                            HistoryManager.getInstance().updateHistoryArray(symbol2Ticker);

                            // --- BƯỚC 2: UPDATE ACTIVE ORDERS THEO ARRAY NGUYÊN THỦY O(1) ---
                            if (activeRunningCount > 0) {
                                // Copy mảng để tránh lỗi ConcurrentModification khi dời mảng vì lệnh chốt
                                short[] currentIds = Arrays.copyOf(activeRunningIds, activeRunningCount);

                                for (short runningSymbolId : currentIds) {
                                    KlineObjectSimple ticker = symbol2Ticker[runningSymbolId];
                                    if (ticker != null) {
                                        startUpdateOldOrderTrading(time, runningSymbolId, ticker);
                                    }
                                }

                                // 🔎 maxDD THẬT (ĐO LƯỜNG, KHÔNG quyết định): MỖI TICK tính tổng unrealized
                                //    danh mục theo bar.low của từng cụm đang chạy rồi theo dõi đáy. Dùng bar.low
                                //    để bắt đáy trong nến — đây là METRIC nên KHÔNG phải look-ahead. Chạy SONG
                                //    SONG unProfitMin cũ (xây từ profitMin/minPrice, lấy mẫu theo giờ), không thay thế.
                                float unrealAtLow = 0f;
                                for (int i = 0; i < activeRunningCount; i++) {
                                    short id = activeRunningIds[i];
                                    OrderTargetInfoTest cluster = symbol2OrderRunning[id];
                                    KlineObjectSimple tk = symbol2Ticker[id];
                                    if (cluster != null && cluster.priceEntry != null && cluster.quantity != null
                                            && tk != null && tk.minPrice > 0) {
                                        unrealAtLow += cluster.quantity * (tk.minPrice - cluster.priceEntry);
                                    }
                                }
                                BudgetManagerSimple.getInstance().updateTrueUnrealizedMin(unrealAtLow, time);
                            }

                            logByProcessTime(startTimeRun, "Done update order", time);
                            startTimeRun = System.currentTimeMillis();

                            MarketDataObject marketData = time2MarketData.get(time);
                            Set<Short> symbolLocked = new HashSet<>();
                            MarketLevelChange levelChange = null;
                            AiPredictionData predict = predictionMap.get(time);

                            if (predict != null && marketData != null) {
                                levelChange = MarketBigChangeDetector.getMarketStatus1M(marketData.rateDownAvg, marketData.rateUpAvg, marketData.rateDown15MAvg);

                                if (levelChange != null) {
                                    Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;

                                    // Chép ID đang chạy vào Set để khóa
                                    for (int i = 0; i < activeRunningCount; i++) symbolLocked.add(activeRunningIds[i]);

                                    if (levelChange.equals(MarketLevelChange.SMALL_UP) ||
                                            levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)) {
                                        numberOrder = numberOrder / 2;
                                    }

                                    Set<Short> symbol2BUY = new HashSet<>();
                                    TreeMap<Float, Short> predict2Symbol = extractPredict2Symbol(time2SymbolPred.get(time));

                                    symbol2BUY.addAll(MarketBigChangeDetector.getTopSymbolArray(numberOrder,
                                            symbol2Ticker, symbolLocked, predict2Symbol));

                                    Map<Short, OrderTargetInfoTest> activeOrderMap = getActiveOrderMap();
                                    List<Short> symbolDcaLevel = DcaProcessor.getDCA(levelChange, time,
                                            BudgetManagerSimple.getInstance().getBudget(), activeOrderMap);

                                    for (short symbolId : symbol2BUY) {
                                        KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                        if (Utils.isTickerAvailable(ticker)) {
                                            createOrderBUY(symbolId, ticker, levelChange, time2MarketData.get(time), null);
                                        }
                                    }
                                    for (short symbolId : symbolDcaLevel) {
                                        KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                        if (Utils.isTickerAvailable(ticker)) {
                                            createOrderBUY(symbolId, ticker, MarketLevelChange.DCA_LEVEL1, time2MarketData.get(time), null);
                                        }
                                    }
                                }
                            }

                            logByProcessTime(startTimeRun, "Done market data", time);
                            startTimeRun = System.currentTimeMillis();

                            if (marketData != null) {
                                if (MarketBigChangeDetector.isDcaAlt(marketData.rateDown15MAvg, marketData.rateDownAvg, marketData.rateUpAvg)) {
                                    List<Short> symbolDcaLossBig = DcaProcessor.getDCA(null, time, BudgetManagerSimple.getInstance().getBudget(), getActiveOrderMap());
                                    for (short symbolId : symbolDcaLossBig) {
                                        KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                        if (Utils.isTickerAvailable(ticker)) {
                                            createOrderBUY(symbolId, ticker, MarketLevelChange.DCA_LEVEL1, time2MarketData.get(time), null);
                                        }
                                    }
                                    logByProcessTime(startTimeRun, "Done dca big", time);
                                    startTimeRun = System.currentTimeMillis();
                                }

                                // 🔥 BƯỚC 3: FUNDING FEE SIÊU TỐC (ĐÃ PRE-CALCULATE SORT SẴN) 🔥
                                long[] symbol2Pred = time2SymbolPred.get(time);
                                if (symbol2Pred != null) {
                                    float maxThres = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * Configs.AI_DYNAMIC_MAX;

                                    for (long encodedData : symbol2Pred) {
                                        float symbolPred = Float.intBitsToFloat((int) encodedData);

                                        // 🚀 ĐIỂM ĂN TIỀN: Vì mảng đã được sort chuẩn từ thấp đến cao lúc load file.
                                        // Gặp thằng vượt ngưỡng là CẮT LUÔN VÒNG LẶP, không cần kiểm tra phần sau!
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

                            if (time % Utils.TIME_DAY == 0) {
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
                                if (time % (60 * Utils.TIME_MINUTE) == 0) {
                                    short[] currentIds = Arrays.copyOf(activeRunningIds, activeRunningCount);
                                    for (Short symbolId : currentIds) {
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
            startTime += Utils.TIME_DAY;

            if (startTime > endTime) {
                BudgetManagerSimple.getInstance().updateBalance(finalStartTime1, allOrderDone, getActiveIdSet(), symbol2OrderRunning, symbol2OrdersEntry, false);
                break;
            }
        }

        // add all order running to done
        for (int i = 0; i < activeRunningCount; i++) {
            short id = activeRunningIds[i];
            List<OrderTargetInfoTest> orderRunningList = symbol2OrdersEntry[id];
            if (orderRunningList != null) {
                for (OrderTargetInfoTest orderInfo : orderRunningList) {
                    orderInfo.lastPrice = symbol2OrderRunning[id].lastPrice;
                    orderInfo.priceTP = orderInfo.lastPrice;
                    orderInfo.minPrice = symbol2OrderRunning[id].minPrice;
                    orderInfo.maeLow = symbol2OrderRunning[id].maeLow;   // 🔎 đáy THẬT cụm (đo MAE)
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
                TraceOrderDone.printOrderTestDone("storage/printDone.csv", allOrderDone);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        Utils.printMemoryUse(System.currentTimeMillis() - timeSimulator);
    }

    // =========================================================================
    // 🔥 CÁC HÀM XỬ LÝ MẢNG NGUYÊN THỦY O(1) SIÊU TỐC KHÔNG SINH OBJECT RÁC
    // =========================================================================
    private void addActiveRunningId(short id) {
        // Kiểm tra tránh trùng
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
                // Đổi vị trí với phần tử cuối để xóa O(1)
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

    // =========================================================================

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
        // Log per-tick (>20ms) đã TẮT: gọi 5 lần/tick × hàng triệu tick + GC spike trong HPO = spam nặng.
        // Cần profiling thì mở lại dòng dưới (hoặc nâng ngưỡng lên vài giây để chỉ bắt tick treo thật).
        // long duration = (System.currentTimeMillis() - startTimeRun);
        // if (duration > 5000) LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), msg, duration);
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

        LOG.info("📥 Đang tải dữ liệu vào RAM...");
        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
//        time2SymbolPred = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, numberMinutes);
        time2SymbolPred = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        // 3. CHẠY PRE-CALCULATE (SORT SẴN FUNDING FEE MỘT LẦN DUY NHẤT)
        preprocessFundingData(time2SymbolPred);
        aiRejectFilter = new AIRejectFilter();

        SimpleSymbolMapper.getInstance().init();

        Utils.printMemoryUsage("Load time2FundingPre (time2SymbolPred)");
        LOG.info("✅ TẤT CẢ DỮ LIỆU ĐÃ SẴN SÀNG. BẮT ĐẦU SIMULATE...");
    }

    private void startUpdateOldOrderTrading(Long time, short symbolId, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning[symbolId];
        if (orderMulti != null) {
            if (orderMulti.timeStart <= ticker.startTime) {
                orderMulti.updatePriceByKlineSimple(ticker);
                if (ticker.maxPrice >= orderMulti.priceEntry * (1 + Configs.RATE_PROFIT_STOP_MARKET)
                        || orderMulti.priceSL != null) {
                    Float predReturn15M  = getPredReturn15MForTradingStop(time);
                    orderMulti.updateStatusNew(predReturn15M , ticker);
                    if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                        closeOrder(symbolId, orderMulti);
                    } else {
                        orderMulti.updateTPSL(predReturn15M , ticker);
                    }
                }
            }
        }
    }

    private Float getPredReturn15MForTradingStop(Long time) {
        AiPredictionData predict = predictionMap.get(time);
        if (predict == null) {
            return 0f;
        } else {
            return predict.predReturn15M;
        }
    }

    private void closeOrder(short symbolId, OrderTargetInfoTest orderMulti) {
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry[symbolId];
        if (orders != null) {
            for (OrderTargetInfoTest order : orders) {
                order.timeUpdate = orderMulti.timeUpdate;
                order.status = orderMulti.status;
                order.priceTP = orderMulti.priceTP;
                order.minPrice = orderMulti.minPrice;
                order.maeLow = orderMulti.maeLow;   // 🔎 chép đáy THẬT cụm sang từng leg (đo MAE)
                order.lastPrice = orderMulti.lastPrice;

                allOrderDone.put(-order.timeUpdate - allOrderDone.size(), order);
                BudgetManagerSimple.getInstance().updatePnl(order);
            }
        }

        // Xóa sổ lệnh khỏi mảng O(1)
        symbol2OrdersEntry[symbolId] = null;
        symbol2OrderRunning[symbolId] = null;
        removeActiveRunningId(symbolId);

        BudgetManagerSimple.getInstance().marginRunning -= orderMulti.calMargin();
    }

    private OrderTargetInfoTest mergeOrder(List<OrderTargetInfoTest> orders, KlineObjectSimple ticker,
                                           OrderTargetInfoTest prevRunning) {
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
        // 🔎 maeLow: KHÔNG reset-lên khi nhồi. Mang theo đáy THẬT của cụm cũ (nếu có), lần đầu = giá vào
        //    leg đầu, rồi hạ thêm nếu nến hiện tại thủng sâu hơn. Bảo toàn đáy từ leg đầu để MAE chuẩn.
        float firstLegEntry = time2Order.firstEntry().getValue().priceEntry;
        float carriedLow = (prevRunning != null && prevRunning.maeLow != null) ? prevRunning.maeLow : firstLegEntry;
        orderResult.maeLow = Math.min(carriedLow, ticker.minPrice);
        orderResult.lastPrice = ticker.priceClose;
        orderResult.lastEntry = orders.get(orders.size() - 1).lastEntry;
        orderResult.rateChange = orders.get(orders.size() - 1).rateChange;
        orderResult.tickerOpen = time2Order.lastEntry().getValue().tickerOpen;
        orderResult.marketLevelChange = time2Order.lastEntry().getValue().marketLevelChange;

        return orderResult;
    }

    public void createOrderBUY(short symbolId, KlineObjectSimple ticker, MarketLevelChange levelChange,
                               MarketDataObject marketData, Float symbolPred) {

        if (levelChange != MarketLevelChange.DCA_LEVEL1) {
            if (is50PercentOrderLoss == null)
                is50PercentOrderLoss = MarketBigChangeDetector.is50PercentOrderLoss(getActiveOrderList(), ticker.startTime);
            if (is50PercentOrderLoss) {
                return;
            }
        }


        AiPredictionData predict = predictionMap.get(ticker.startTime);
        // 🧠 #10 PARITY (TASK-030, một bộ não): LIVE createOrderBuyRequest reject khi prediction==null
        // (DetectEntrySignal2TradeNormal). TRƯỚC ĐÂY sim bỏ qua filter khi predict==null → VẪN vào lệnh "mù"
        // → P&L sim≠live ở mốc thiếu pred. Nay sim cũng reject pred==null. (CONFIG_VERSION v8→v9.)
        if (predict == null) {
            return;
        }
        if (!levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            AIRejectFilter.FilterResult filterResult = null;
            if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) {
                filterResult = aiRejectFilter.checkSignalDynamic(predict, symbolPred);
            }
            if (filterResult == null)
                filterResult = aiRejectFilter.checkSignal(predict);

            if (filterResult.decision == AIRejectFilter.FilterDecision.REJECT) {
                return;
            }
        }

        // 🛑 CIRCUIT BREAKER — chỉ tác động khi BREAKER_MODE != OFF. Tác động tầng DCA/margin,
        // KHÔNG đụng entry filter, KHÔNG force-close (long-only): chỉ DỪNG MỞ / DỪNG NHỒI.
        if (!"OFF".equals(Configs.BREAKER_MODE)) {
            // (a) MARGIN halt: chặn MỌI lệnh mới (entry + DCA) khi tổng margin/vốn >= ngưỡng
            if ("MARGIN".equals(Configs.BREAKER_MODE) || "BOTH".equals(Configs.BREAKER_MODE)) {
                float bal = BudgetManagerSimple.getInstance().balanceBasic;
                if (bal > 0 && BudgetManagerSimple.getInstance().marginRunning / bal >= Configs.BREAKER_MARGIN_HALT) {
                    breakerMarginHaltCount++;
                    return;
                }
            }
            // (b) DCA depth cap: symbol ĐÃ có cụm mở và cụm đang lỗ sâu => ngừng NHỒI (giữ cụm)
            if ("DCA".equals(Configs.BREAKER_MODE) || "BOTH".equals(Configs.BREAKER_MODE)) {
                OrderTargetInfoTest running = symbol2OrderRunning[symbolId];
                if (running != null && running.priceEntry != null && running.priceEntry > 0) {
                    float clusterDd = (ticker.priceClose - running.priceEntry) / running.priceEntry;
                    if (clusterDd <= Configs.BREAKER_CLUSTER_DD_MAX) {
                        breakerDcaCapCount++;
                        return;
                    }
                }
            }
        }

        Float entry = ticker.priceClose;
        Integer leverage = Configs.LEVERAGE_ORDER;

        long currentTs = ticker.startTime;
        CoinRankManager.CoinTier myTier = CoinRankManager.getInstance().getCoinTier(symbolId, currentTs);
        if (myTier == CoinRankManager.CoinTier.TIER_3_SHITCOIN) {
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

        float tierMultiplier = CoinRankManager.getInstance().getBudgetMultiplier(symbolId);
        budget *= tierMultiplier;

        String symbolStr = SimpleSymbolMapper.getInstance().getSymbol(symbolId);
        Float quantity = Utils.calQuantityTest(budget, leverage, entry, symbolStr);

        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry,
                null, quantity, leverage, symbolStr, ticker.startTime,
                ticker.startTime, OrderSide.BUY);

        order.minPrice = entry;
        order.maeLow = entry;   // 🔎 đáy THẬT khởi tạo = giá vào leg (đo lường MAE)
        order.lastEntry = entry;
        order.lastPrice = entry;
        order.tickerOpen = ticker;
        order.marketLevelChange = levelChange;

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

        symbol2OrderRunning[symbolId] = mergeOrder(orders, ticker, symbol2OrderRunning[symbolId]);
        addActiveRunningId(symbolId); // Thêm ID vào mảng O(1)

        BudgetManagerSimple.getInstance().updateMaxOrderRunning(counterOrderRunning());
        BudgetManagerSimple.getInstance().marginRunning += order.calMargin();
    }

    public void initDataReady(TreeMap<Long, MarketDataObject> time2MarketData,
                              TreeMap<Long, AiPredictionData> predictionMap, TreeMap<Long, long[]> time2FundingPre,
                              AIRejectFilter aiRejectFilter) throws OrtException {

        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();

        // Khởi tạo Mapper để cache sẵn danh sách symbol
        SimpleSymbolMapper.getInstance().init();

        this.time2MarketData = time2MarketData;
        this.predictionMap = predictionMap;
        this.time2SymbolPred = time2FundingPre;
        // 3. CHẠY PRE-CALCULATE (SORT SẴN FUNDING FEE MỘT LẦN DUY NHẤT)
        preprocessFundingData(this.time2SymbolPred);
        this.aiRejectFilter = aiRejectFilter;
    }

    // 🔥 HÀM PRE-CALCULATE: Sort mảng theo điểm Float đảm bảo logic 100% như cũ
//    public static void preprocessFundingData(TreeMap<Long, long[]> time2FundingPre) {
//        LOG.info("⚙️ Bắt đầu Pre-calculate (Sort sẵn) dữ liệu Funding Fee...");
//        long start = System.currentTimeMillis();
//        for (long[] preds : time2FundingPre.values()) {
//            if (preds == null || preds.length == 0) continue;
//
//            // Ép sang Object Long để sort bằng Comparator đảm bảo logic không lệch 1 ly
//            Long[] boxed = new Long[preds.length];
//            for (int i = 0; i < preds.length; i++) {
//                boxed[i] = preds[i];
//            }
//
//            Arrays.sort(boxed, (a, b) -> {
//                float valA = Float.intBitsToFloat(a.intValue());
//                float valB = Float.intBitsToFloat(b.intValue());
//                return Float.compare(valA, valB);
//            });
//
//            // Ép ngược lại mảng nguyên thủy
//            for (int i = 0; i < preds.length; i++) {
//                preds[i] = boxed[i];
//            }
//        }
//        LOG.info("✅ Pre-calculate hoàn tất trong {} ms.", (System.currentTimeMillis() - start));
//    }

    // 🔥 PRE-CALCULATE TỐI ƯU HÓA: Dùng Primitive QuickSort & Đa luồng (0 sinh rác Object)
    public static void preprocessFundingData(TreeMap<Long, long[]> time2FundingPre) {
        LOG.info("⚙️ Bắt đầu Pre-calculate (Sort sẵn) dữ liệu Funding Fee đa luồng...");
        long start = System.currentTimeMillis();

        // Dùng parallelStream để vắt kiệt 100% các lõi CPU của VPS/Kaggle
        time2FundingPre.values().parallelStream().forEach(preds -> {
            if (preds == null || preds.length <= 1) return;
            // Sort nguyên thủy trực tiếp trên mảng long[]
            quickSortByFloatPred(preds, 0, preds.length - 1);
        });

        LOG.info("✅ Pre-calculate hoàn tất trong {} ms.", (System.currentTimeMillis() - start));
    }

    // 🚀 Thuật toán QuickSort nguyên thủy (Extract 32 bit cuối ra so sánh Float)
    private static void quickSortByFloatPred(long[] arr, int low, int high) {
        if (low < high) {
            int pi = partition(arr, low, high);
            quickSortByFloatPred(arr, low, pi - 1);
            quickSortByFloatPred(arr, pi + 1, high);
        }
    }

    private static int partition(long[] arr, int low, int high) {
        long pivot = arr[high];
        // (int) pivot lấy đúng 32 bit cuối cùng (là giá trị float đã nén)
        float pivotVal = Float.intBitsToFloat((int) pivot);
        int i = (low - 1);

        for (int j = low; j < high; j++) {
            float jVal = Float.intBitsToFloat((int) arr[j]);
            // So sánh float
            if (Float.compare(jVal, pivotVal) <= 0) {
                i++;
                // Swap
                long temp = arr[i];
                arr[i] = arr[j];
                arr[j] = temp;
            }
        }
        // Swap pivot
        long temp = arr[i + 1];
        arr[i + 1] = arr[high];
        arr[high] = temp;
        return i + 1;
    }
}