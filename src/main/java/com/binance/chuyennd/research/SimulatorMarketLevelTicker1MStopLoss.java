/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import ai.onnxruntime.OrtException;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.onnx.entry.RunGeneratePredictions;
import com.binance.chuyennd.ai_ml.onnx.funding.GenerateFundingPredictionsTool;
import com.binance.chuyennd.bigchange.test.TraceOrderDone;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.*;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

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
    public Map<String, KlineObjectSimple> symbol2LastTicker = new HashMap<>();


    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry = new ConcurrentHashMap();
    public ConcurrentHashMap<String, OrderTargetInfoTest> symbol2OrderRunning = new ConcurrentHashMap();
    public ConcurrentHashMap<String, Long> symbol2LastTimeTrade = new ConcurrentHashMap<>();

    public void setConfig(BotTradingConfig config) {
        // =================================================================
        // 🔥 ĐỒNG BỘ TOÀN BỘ BOT_TRADING_CONFIG SANG BIẾN STATIC CỦA CONFIGS
        // Đảm bảo Simulator và các class Core (TradeUtils, BigChangeDetector)
        // luôn chạy đúng bộ gen/tham số vừa được thuật toán tối ưu sinh ra.
        // =================================================================

        // ---------------------------------------------------------
        // NHÓM 1: BỘ LỌC AI & DỰ ĐOÁN (AI Thresholds)
        // ---------------------------------------------------------
        Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD = config.aiPredictRateMaxThreshold;
        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = config.aiPredictRateDown15m;
        Configs.PREDICT_SYMBOL_RATE_UP_AVG = config.aiPredictRateUpAvg;
        Configs.PREDICT_SYMBOL_RATE_DOWN_AVG = config.aiPredictRateDownAvg;

        // ---------------------------------------------------------
        // NHÓM 2: ĐIỀU KIỆN THỊ TRƯỜNG (Market Signal Thresholds)
        // ---------------------------------------------------------
        Configs.MS_UP_BIG_THRES = config.msUpBigThres;
        Configs.MS_DOWN_BIG_AVG = config.msDownBigAvg;
        Configs.MS_UP_MED_THRES = config.msUpMedThres;
        Configs.MS_DOWN_MED_AVG = config.msDownMedAvg;
        Configs.MS_UP_SMALL_THRES = config.msUpSmallThres;
        Configs.MS_DOWN_SMALL_AVG = config.msDownSmallAvg;
        Configs.MS_DOWN_15M_MED_ONLY = config.msDown15mMedOnly;
        Configs.MS_DOWN_15M_SMALL_ONLY = config.msDown15mSmallOnly;

        // Các biến mở rộng kết hợp BTC/Logic phụ
        Configs.MS_DOWN_BIG_BTC = config.msDownBigBtc;
        Configs.MS_DOWN_MED_AVG_CMB = config.msDownMedAvgCmb;
        Configs.MS_DOWN_MED_15M_CMB = config.msDownMed15mCmb;
        Configs.MS_DOWN_SMALL_15M = config.msDownSmall15m;

        // ---------------------------------------------------------
        // NHÓM 3: CHỐT LỜI & DỜI CẮT LỖ ĐỘNG (Trailing Stop)
        // ---------------------------------------------------------
        Configs.RATE_PROFIT_STOP_MARKET = config.rateProfitStopMarket;

        Configs.TS_VOL_HIGH_THRES = config.tsVolHighThres;
        Configs.TS_RATE_HIGH = config.tsRateHigh;

        Configs.TS_VOL_MED_THRES = config.tsVolMedThres;
        Configs.TS_RATE_MED = config.tsRateMed;

        Configs.TS_VOL_LOW_THRES = config.tsVolLowThres;
        Configs.TS_RATE_LOW = config.tsRateLow;

        // ---------------------------------------------------------
        // NHÓM 4: QUẢN TRỊ VỐN & NGÂN SÁCH (Budget Management)
        // ---------------------------------------------------------
        Configs.number_order_budget = config.numberOrderBudget;

        Configs.BUDGET_MARGIN_RATIO_1 = config.budgetMarginRatio1;
        Configs.BUDGET_DIVIDER_1 = config.budgetDivider1;

        Configs.BUDGET_MARGIN_RATIO_2 = config.budgetMarginRatio2;
        Configs.BUDGET_DIVIDER_2 = config.budgetDivider2;

        // ---------------------------------------------------------
        // NHÓM 5: HẰNG SỐ HỆ THỐNG (System Constants)
        // ---------------------------------------------------------
        Configs.LEVERAGE_ORDER = config.leverageOrder;
        // Bỏ comment dòng dưới nếu bạn muốn map động Rate Fee và khai báo biến này không phải là final trong Configs
        // Configs.RATE_FEE = config.rateFee;
        Configs.NUMBER_RATE_DOWN_HISTORY_TRADE = config.numberRateDownHistoryTrade;
        Configs.NUMBER_ENTRY_EACH_SIGNAL = config.numberEntryEachSignal;

        Configs.MAX_CONCURRENT_ORDERS = config.maxConcurrentOrders; // Nhớ khai báo public static int MAX_CONCURRENT_ORDERS = 10 trong Configs.java
    }


    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        LOG.info("Start with kaggle mode: {} ", Configs.IS_KAGGLE_MODE);
        SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
        if (Configs.IS_KAGGLE_MODE) {
            test.initDataOnKaggle();
        } else {
            test.initData();
        }
        test.simulatorWithInitEntry(startTime, System.currentTimeMillis());
        Thread.sleep(5000);
        System.exit(1);
    }

    private void initDataOnKaggle() throws ParseException {
        Configs.TIME_RUN = "20250101";
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();

        LOG.info("Loading Data... {}", Configs.TIME_RUN);
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        int numberMinutes = System.currentTimeMillis() - startTime > 0 ? (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_MINUTE) : 0;

        // SỬ DỤNG DATAMANAGER
        time2MarketData = DataManager.getMarketData();
        Utils.printMemoryUsage("Load time2MarketData");

        predictionMap = DataManager.getAiPredictionData();
        Utils.printMemoryUsage("Load predictionMap");

        time2SymbolPred = DataManager.getFundingPredictionData(startTime, numberMinutes);
        Utils.printMemoryUsage("Load time2FundingPre");
        aiRejectFilter = new AIRejectFilter();
        Utils.printMemoryUsage("Load time2FundingPre (time2SymbolPred)");
    }

    public void simulatorWithInitEntry(Long startTime, Long endTime) throws ParseException {
        LOG.info("=== 🚀 BẮT ĐẦU SIMULATE TỪ {} ĐẾN {} ===", Utils.normalizeDateYYYYMMDDHHmm(startTime), Utils.normalizeDateYYYYMMDDHHmm(endTime));
        Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();

        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                if (Configs.IS_KAGGLE_MODE) {
//                    time2Tickers = HPOSmartCache.getData(startTime);
                    time2Tickers = DataManager.getTickers1M(startTime);
                } else {
                    time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);
                }

                if (time2Tickers == null) {
                    LOG.info("File data error or not found for time: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                }
                if (time2Tickers != null && time2Tickers.size() >= 1440) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        Long startTimeRun = System.currentTimeMillis();
                        try {
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            for (String symbol : symbol2Ticker.keySet()) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (!Utils.isTickerAvailable(ticker)) {
                                    updateSymbolDeListed(symbol, time);
                                    continue;
                                }
                                symbol2LastTicker.put(symbol, ticker);
                                List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                if (tickers == null) {
                                    tickers = new ArrayList<>();
                                    symbol2LastTickers.put(symbol, tickers);
                                }
                                tickers.add(ticker);
                                int sizeRemove = 201;
                                // Chỉ dọn dẹp khi dư ra một khoảng để đỡ tốn CPU dọn liên tục
                                if (tickers.size() > sizeRemove + 50) {
                                    tickers.subList(0, tickers.size() - sizeRemove).clear();
                                }

                            }
                            // --- BƯỚC 2: UPDATE ACTIVE ORDERS (SIÊU TỐI ƯU) ---
                            // Thay vì duyệt 2000 symbol, chỉ duyệt danh sách đang chạy (vài chục lệnh)
                            if (!symbol2OrderRunning.isEmpty()) {
                                // Dùng keySet copy hoặc iterator để tránh ConcurrentModificationException nếu có lệnh đóng
                                for (String runningSymbol : new ArrayList<>(symbol2OrderRunning.keySet())) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(runningSymbol);
                                    if (ticker != null) { // Chỉ update nếu có data mới của symbol đó
                                        startUpdateOldOrderTrading(time, runningSymbol, symbol2LastTickers.get(runningSymbol));
                                    }
                                }
                            }

                            logByProcessTime(startTimeRun, "Done update order", time);

                            startTimeRun = System.currentTimeMillis();

                            MarketDataObject marketData;
                            marketData = time2MarketData.get(time);
                            Set<String> symbolLocked = new HashSet<>();
                            MarketLevelChange levelChange = null;

                            if (marketData != null) {

                                levelChange = MarketBigChangeDetector.getMarketStatus1M(marketData.rateDownAvg, marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg);
                                // buy signal new
                                if (levelChange != null) {
                                    Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                                    symbolLocked.addAll(symbol2OrderRunning.keySet());
                                    if (levelChange.equals(MarketLevelChange.SMALL_DOWN) || levelChange.equals(MarketLevelChange.SMALL_UP) || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M) || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)) {
                                        numberOrder = numberOrder / 2;
                                    }
                                    Set<String> symbol2BUY = new HashSet<>();
                                    TreeMap<Float, String> predict2Symbol = extractPredict2Symbol(time2SymbolPred.get(time));
                                    symbol2BUY.addAll(MarketBigChangeDetector.getTopSymbol(numberOrder, symbol2Ticker, symbolLocked, predict2Symbol));

                                    List<String> symbolDcaLevel = DcaProcessor.getDCA(levelChange, time, BudgetManagerSimple.getInstance().getBudget(), symbol2OrderRunning);

                                    // check create order new
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        createOrderBUY(symbol, ticker, levelChange, time2MarketData.get(time), symbol2LastTickers);
                                    }
                                    for (String symbol : symbolDcaLevel) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (Utils.isTickerAvailable(ticker)) {
                                            createOrderBUY(symbol, ticker, MarketLevelChange.DCA_LEVEL1, time2MarketData.get(time), symbol2LastTickers);
                                        }
                                    }
                                }
                            }
                            logByProcessTime(startTimeRun, "Done market data", time);
                            startTimeRun = System.currentTimeMillis();

                            if (marketData != null) {
                                float hungerMultiplier = TradeUtils.getHungerMultiplier(symbol2OrderRunning, time);
                                if (MarketBigChangeDetector.isDcaAlt(marketData.rateDown15MAvg, marketData.rateDownAvg, marketData.rateUpAvg)) {
                                    // dca buy
                                    List<String> symbolDcaLossBig = DcaProcessor.getDCA(null, time, BudgetManagerSimple.getInstance().getBudget(), symbol2OrderRunning);
                                    for (String symbol : symbolDcaLossBig) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (Utils.isTickerAvailable(ticker)) {
                                            createOrderBUY(symbol, ticker, MarketLevelChange.DCA_LEVEL1, time2MarketData.get(time), symbol2LastTickers);
                                        }
                                    }

                                    logByProcessTime(startTimeRun, "Done dca big", time);
                                    startTimeRun = System.currentTimeMillis();
                                }

                                // funding level 1
                                Set<String> symbolFundingBuy = symbol2Ticker.keySet();
                                Set<String> symbolPred2Buy = new HashSet<>();
                                symbolPred2Buy.addAll(symbolFundingBuy);
                                symbolPred2Buy.removeAll(symbol2OrderRunning.keySet());
                                TreeMap<Float, String> fundingPredict2Symbol = new TreeMap<>();
                                for (String symbol : symbolPred2Buy) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    if (!Utils.isTickerAvailable(ticker)) {
                                        continue;
                                    }

                                    long[] symbol2Pred = time2SymbolPred.get(time);
                                    if (symbol2Pred != null) {
                                        // Dùng Helper thay cho lệnh Map.get()
                                        Float symbolPred = getPredictionFromPrimitiveArray(symbol2Pred, SimpleSymbolMapper.getInstance().getId(symbol));

                                        if (symbolPred != null) {
                                            // Biến symbolPred giờ là 1 số thực đơn thuần, không phải mảng nữa
                                            if (symbolPred > Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * (1 / hungerMultiplier)) {
                                                continue;
                                            }
                                            fundingPredict2Symbol.put(symbolPred, symbol);
                                        }
                                    }
                                }
                                for (String symbol : fundingPredict2Symbol.values()) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    createOrderBUY(symbol, ticker, MarketLevelChange.PREDICT_SYMBOL_TRADE, time2MarketData.get(time), symbol2LastTickers);
                                }
                            }
                            logByProcessTime(startTimeRun, "Done funding fee", time);
                            startTimeRun = System.currentTimeMillis();

                            if (time % Utils.TIME_DAY == 0) {
                                if (Configs.IS_HPO_MODE) {
                                    if (Utils.isMidnightFirstDay(time)) {
                                        System.gc();
                                        BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, true);
                                        BudgetManagerSimple.getInstance().updateBudget();
                                    } else {
                                        BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                                        BudgetManagerSimple.getInstance().updateBudget();
                                    }
                                } else {
                                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, true);
                                    BudgetManagerSimple.getInstance().updateBudget();
                                }
                            } else {
                                if (time % (15 * Utils.TIME_MINUTE) == 0) {
                                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                                }
                            }
                            logByProcessTime(startTimeRun, "Done budget data", time);


                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                }
                time2Tickers = null;
            } catch (Exception e) {
                e.printStackTrace();
            }
            Long finalStartTime1 = startTime;
            startTime += Utils.TIME_DAY;
            if (startTime > endTime) {
                BudgetManagerSimple.getInstance().updateBalance(finalStartTime1, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                break;
            }
        }
        // add all order running to done
        for (List<OrderTargetInfoTest> orderRunning : symbol2OrdersEntry.values()) {
            for (OrderTargetInfoTest orderInfo : orderRunning) {
                orderInfo.lastPrice = symbol2OrderRunning.get(orderInfo.symbol).lastPrice;
                orderInfo.priceTP = orderInfo.lastPrice;
                orderInfo.minPrice = symbol2OrderRunning.get(orderInfo.symbol).minPrice;
                orderInfo.timeUpdate = symbol2OrderRunning.get(orderInfo.symbol).timeUpdate;
                orderInfo.updateFundingFee();
                allOrderDone.put(-orderInfo.timeUpdate + allOrderDone.size(), orderInfo);
            }
        }
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime); // Hoặc dùng biến startTime của vòng lặp
        int finalYear = cal.get(Calendar.YEAR);
        BudgetManagerSimple.getInstance().balanceIndex.year2UnrealizedPnl.put(finalYear, 0f);
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
        Storage.writeObject2File("storage/orderRunning.data", symbol2OrderRunning);
        Storage.writeObject2File("storage/BalanceIndex.data", BudgetManagerSimple.getInstance().balanceIndex);

        try {
            TraceOrderDone.printOrderTestDone("storage/printDone.csv", allOrderDone);
        } catch (Exception e) {
            e.printStackTrace();
        }
        Utils.printMemoryUse();
    }

    private TreeMap<Float, String> extractPredict2Symbol(long[] encodedDataArray) {
        TreeMap<Float, String> predict2Symbol = new TreeMap<>();
        if (encodedDataArray != null && encodedDataArray.length > 0) {
            for (long encodedData : encodedDataArray) {
                short symbolId = (short) (encodedData >> 32);
                float pred = Float.intBitsToFloat((int) encodedData);
                String symbol = SimpleSymbolMapper.getInstance().getSymbol(symbolId);
                if (StringUtils.isNotEmpty(symbol)) {
                    predict2Symbol.put(pred, symbol);
                }
            }
        }
        return predict2Symbol;
    }

    private void logByProcessTime(Long startTimeRun, String msg, Long time) {
        long duration = (System.currentTimeMillis() - startTimeRun);
        if (duration > 50) {
            LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), msg, duration);
        }
    }

    public void updateSymbolDeListed(String symbol, Long time) {
        OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
        if (order != null) {
            if (order.timeUpdate < time - 2 * Utils.TIME_DAY) {
                LOG.info("Close order by delist: {} {} {} {}", order.symbol, Utils.normalizeDateYYYYMMDDHHmm(time), Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate), Utils.normalizeDateYYYYMMDDHHmm(time - 2 * Utils.TIME_DAY));
                order.status = OrderTargetStatus.STOP_LOSS_DONE;
                order.priceTP = order.lastPrice;
                closeOrder(order.symbol, order);
            }
        }
    }


    public void initData() throws IOException, ParseException {
        // clear Data Old
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();

        // =====================================================================
        // 1. KIỂM TRA MỐC THỜI GIAN CHUẨN TỪ MARKET DATA
        // =====================================================================
        LOG.info("🔍 Đang kiểm tra Metadata của Market Data để làm mốc chuẩn...");
        long lastMarketDataTime = DataManagerAerospikeFloatSim.getLastTimestampFromSet(DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_MARKET_DATA);

        if (lastMarketDataTime == 0L || lastMarketDataTime < System.currentTimeMillis() - Utils.TIME_DAY) {
            String lastTimeStr = (lastMarketDataTime == 0L) ? "NULL" : Utils.normalizeDateYYYYMMDDHHmm(lastMarketDataTime);
            LOG.info("⚠️ Dữ liệu cần cập nhật (Last: {}). Bắt đầu chạy bù cả 3 loại dữ liệu...", lastTimeStr);

            Long timeToRun = (lastMarketDataTime == 0L) ? null : lastMarketDataTime;

            // 1.1 Chạy bù Market Data
            LOG.info("▶️ 1/3: Kích hoạt ExportMarketData2File...");
            new ExportMarketData2File().exportMarketEntries(timeToRun);

            // 1.2 Chạy bù AI Prediction (Entry)
            LOG.info("▶️ 2/3: Kích hoạt RunGeneratePredictions...");
            try {
                new RunGeneratePredictions().generateAndSave(timeToRun);
            } catch (Exception e) {
                throw new RuntimeException("Lỗi khi chạy RunGeneratePredictions: " + e.getMessage(), e);
            }

            // 1.3 Chạy bù Funding Prediction
            LOG.info("▶️ 3/3: Kích hoạt GenerateFundingPredictionsTool...");
            try {
                new GenerateFundingPredictionsTool().generateAndSave(timeToRun);
            } catch (Exception e) {
                throw new RuntimeException("Lỗi khi chạy GenerateFundingPredictionsTool: " + e.getMessage(), e);
            }
        }

        // =====================================================================
        // 2. TẢI TOÀN BỘ DỮ LIỆU VÀO RAM SAU KHI ĐÃ ĐỒNG BỘ
        // =====================================================================
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        int numberMinutes = System.currentTimeMillis() - startTime > 0 ? (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_MINUTE) : 0;

        LOG.info("📥 Đang tải dữ liệu vào RAM...");
        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        time2SymbolPred = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, numberMinutes);
        aiRejectFilter = new AIRejectFilter();
        Utils.printMemoryUsage("Load time2FundingPre (time2SymbolPred)");

        LOG.info("✅ TẤT CẢ DỮ LIỆU ĐÃ SẴN SÀNG. BẮT ĐẦU SIMULATE...");
    }

    private void startUpdateOldOrderTrading(Long time, String symbol, List<KlineObjectSimple> tickers) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
        if (orderMulti != null) {
            KlineObjectSimple ticker = tickers.get(tickers.size() - 1);
            if (orderMulti.timeStart <= ticker.startTime.longValue()) {
                orderMulti.updatePriceByKlineSimple(ticker);
                if (ticker.maxPrice >= orderMulti.priceEntry * 1.007 || orderMulti.priceSL != null) {
                    Float maxChangeIn90M = getMaxRateIn90MForTradingStop(time);
                    orderMulti.updateStatusNew(maxChangeIn90M, ticker);
                    if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE) || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE) || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                        closeOrder(symbol, orderMulti);
                    } else {
                        orderMulti.updateTPSL(maxChangeIn90M, ticker);
                    }
                }
            }
        }
    }

    private Float getMaxRateIn90MForTradingStop(Long time) {
        AiPredictionData predict = predictionMap.get(time);
        if (predict == null) {
            return 0f;
        } else {
            return predict.predReturn15M;
        }
    }


    private void closeOrder(String symbol, OrderTargetInfoTest orderMulti) {
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        for (OrderTargetInfoTest order : orders) {
            order.timeUpdate = orderMulti.timeUpdate;
            order.status = orderMulti.status;
            order.priceTP = orderMulti.priceTP;
            order.minPrice = orderMulti.minPrice;
            order.lastPrice = orderMulti.lastPrice;
//            order.updateFundingFee();
            // Nếu là HPO, bỏ qua để Garbage Collector tự động xóa Object Order này đi
            if (!Configs.IS_HPO_MODE) {
                allOrderDone.put(-order.timeUpdate + allOrderDone.size(), order);
            }
            BudgetManagerSimple.getInstance().updatePnl(order);
        }
        symbol2OrdersEntry.remove(symbol);
        symbol2OrderRunning.remove(symbol);
        BudgetManagerSimple.getInstance().updatePositionMargin(symbol2OrderRunning.values());
    }

    private OrderTargetInfoTest mergeOrder(List<OrderTargetInfoTest> orders, KlineObjectSimple ticker) {
        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        Float quantity = 0f;
        String priceEntry = "";
        Float margin = 0f;
        OrderSide side = orders.get(0).side;
        for (OrderTargetInfoTest orderInfo : orders) {
            if (!side.equals(orderInfo.side)) {
                LOG.info("Error order: {} {} {} {}", orders.get(0).symbol, Utils.normalizeDateYYYYMMDDHHmm(orders.get(0).timeStart), side, orderInfo.side);
            }
            time2Order.put(orderInfo.timeStart, orderInfo);
            margin += orderInfo.priceEntry * orderInfo.quantity;
            quantity += orderInfo.quantity;
            priceEntry += orderInfo.priceEntry + "-";
        }
        float entry = margin / quantity;
        OrderTargetInfoTest orderResult = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity, Configs.LEVERAGE_ORDER, time2Order.lastEntry().getValue().symbol, time2Order.lastEntry().getKey(), time2Order.lastEntry().getKey(), orders.get(0).side);
        orderResult.minPrice = ticker.priceClose;
        orderResult.lastPrice = ticker.priceClose;
        orderResult.lastEntry = orders.get(orders.size() - 1).lastEntry;
        orderResult.rateChange = orders.get(orders.size() - 1).rateChange;
        orderResult.tickerOpen = time2Order.lastEntry().getValue().tickerOpen;
        orderResult.marketLevelChange = time2Order.lastEntry().getValue().marketLevelChange;

        return orderResult;
    }

    public void createOrderBUY(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange,
                               MarketDataObject marketData, Map<String, List<KlineObjectSimple>> symbol2LastTickers) {

// 🔥 NÂNG CẤP 1: Chỉ bật Cầu dao dò mìn đối với lệnh MỚI (Không chặn lệnh DCA)
        if (levelChange != MarketLevelChange.DCA_LEVEL1 && levelChange != MarketLevelChange.DCA_LEVEL2) {
            if (MarketBigChangeDetector.is50PercentOrderLoss(symbol2OrderRunning, ticker.startTime)) {
                // LOG.debug("⚠️ CẦU DAO BẬT: >=50% lệnh mua trong 30p qua đang lỗ. Tạm ngưng mở mới!");
                return;
            }

            // 🔥 NÂNG CẤP 2: Giới hạn tổng số lệnh chạy đồng thời CHUẨN XÁC
            // (Bạn code ở vòng for bên ngoài thì nó chỉ giới hạn số lệnh của 1 nến 1M,
            // chứ nến sau nó lại táng tiếp 30 lệnh). Phải chặn ở đây!
//            if (symbol2OrderRunning.size() >= Configs.MAX_CONCURRENT_ORDERS) {
//                return;
//            }
        }
        AiPredictionData predict = predictionMap.get(ticker.startTime);
        if (predict != null && !levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            if (aiRejectFilter.checkSignal(predict).decision.equals(AIRejectFilter.FilterDecision.REJECT)) {
//                LOG.info("⛔ REJECTED BY RISK FILTER: {} {}", predict.predReturn1H, predict.predRisk4H);
                return; // Dừng ngay
            }
        }
        Float entry = ticker.priceClose;
        Integer leverage = Configs.LEVERAGE_ORDER;

        Float marginRunning = calMarginRunning();
        Float balanceBasic = BudgetManagerSimple.getInstance().balanceBasic;
        Float budget = BudgetManagerSimple.getInstance().getBudget();

        budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange);

        if (budget == null) {
            return;
        }

        // =========================================================
        // 🚀 CẤP VỐN THÔNG MINH BẰNG COIN RANK MANAGER
        // =========================================================
        long currentTs = ticker.startTime.longValue();

        // 1. Lấy Hệ số nhân Budget (1.2 | 1.0 | 0.5)
        // Lưu ý: Tự động truyền symbol2LastTickers để Manager tự tính toán khi cần
        float tierMultiplier = CoinRankManager.getInstance().getBudgetMultiplier(symbol);

        // 2. Chặn đứng DCA rác
        CoinRankManager.CoinTier myTier = CoinRankManager.getInstance().getCoinTier(symbol, currentTs, symbol2LastTickers);
        if (myTier == CoinRankManager.CoinTier.TIER_3_SHITCOIN) {
            if (levelChange == MarketLevelChange.DCA_LEVEL1 || levelChange == MarketLevelChange.DCA_LEVEL2) {
                LOG.info("🚫 Chặn DCA vào đồng Shitcoin: {}", symbol);
                return;
            }
        }

        // Áp dụng hệ số vào Budget
        budget *= tierMultiplier;

        Float quantity = Utils.calQuantityTest(budget, leverage, entry, symbol);

        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
            Float minBtcTrade = 0.002f;
            if (quantity < minBtcTrade) {
                quantity = minBtcTrade;
            }
        }

        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity, leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BUY);
        order.minPrice = entry;
        order.lastEntry = entry;
        order.lastPrice = entry;

        order.tickerOpen = ticker;
        order.marketLevelChange = levelChange;
        if (marketData != null) {
            order.marketData = marketData;
        }
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);

        BudgetManagerSimple.getInstance().counterOrderCreated.incrementAndGet();
        symbol2OrdersEntry.put(symbol, orders);
        symbol2OrderRunning.put(symbol, mergeOrder(orders, ticker));
        symbol2LastTimeTrade.put(symbol, order.timeStart);
        BudgetManagerSimple.getInstance().updateMaxOrderRunning(counterOrderRunning());
        BudgetManagerSimple.getInstance().updatePositionMargin(symbol2OrderRunning.values());
    }


    private Integer counterOrderRunning() {
        Integer counter = 0;
        for (List<OrderTargetInfoTest> orders : symbol2OrdersEntry.values()) {
            if (orders != null) {
                counter += orders.size();
            }
        }
        return counter;
    }


    private Float calMarginRunning() {
        Float marginTotal = 0f;
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.priceSL == null) {
                marginTotal += order.calMargin();
            }
        }
        BudgetManagerSimple.getInstance().marginRunning = marginTotal;
        return marginTotal;
    }


    // 🔥 THÊM THAM SỐ time2FundingPre
    public void initDataReady(TreeMap<Long, MarketDataObject> time2MarketData, TreeMap<Long, AiPredictionData> predictionMap, TreeMap<Long, long[]> time2FundingPre, AIRejectFilter aiRejectFilter) throws OrtException {

        // Reset Data Old
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();

        // Gán dữ liệu cache vào biến của instance
        this.time2MarketData = time2MarketData;
        this.predictionMap = predictionMap;
        this.time2SymbolPred = time2FundingPre; // 🔥 GÁN BIẾN MỚI
        this.aiRejectFilter = aiRejectFilter;
    }

    private Float getPredictionFromPrimitiveArray(long[] encodedArray, short targetId) {
        for (long encodedData : encodedArray) {
            if ((short) (encodedData >> 32) == targetId) {
                return Float.intBitsToFloat((int) encodedData);
            }
        }
        return null;
    }

}
