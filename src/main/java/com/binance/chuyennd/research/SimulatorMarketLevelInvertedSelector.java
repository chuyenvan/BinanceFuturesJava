package com.binance.chuyennd.research;

import ai.onnxruntime.OrtException;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.BacktestIntegrityGuard;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * SimulatorMarketLevelInvertedSelector — engine SELECTOR-ONLY doc lap (BEST-N / WORST-N qua
 * {@link Configs#SELECTOR_INVERT}). Muc dich: co lap 100% edge cua selector, khop proxy Kaggle.
 *
 * <p><b>⚠️ KHONG PARITY voi engine chinh {@link SimulatorMarketLevelTicker1MStopLoss}.</b>
 * (Javadoc cu ghi "byte-identical when SELECTOR_INVERT disabled" — SAI, da sua 2026-07-30.)
 * So voi engine chinh, class nay CO Y THIEU:
 * <ul>
 *   <li>leg entry theo market-signal (<code>symbol2BUY</code> / <code>getTopSymbolArray</code>) = luong FOMO;</li>
 *   <li>toan bo DCA (<code>DcaProcessor</code>, <code>DCA_LEVEL1</code>, <code>BIG_DOWN</code>);</li>
 *   <li>nhanh SHORT, breaker DCA-cap, <code>MAX_CONCURRENT_ORDERS</code>, <code>SIZE_MULT</code>;</li>
 *   <li>cap candidate bang <code>NUMBER_ENTRY_EACH_SIGNAL</code> (engine chinh lay het <code>nPass</code>).</li>
 * </ul>
 * ⇒ So PnL/so-lenh cua class nay TRUC TIEP voi baseline engine chinh = KET LUAN SAI. Chi so INVERT=0
 * vs INVERT=1 <b>trong cung class nay</b>.
 *
 * <p><b>⚠️ Chi vao qua {@link #initData()}</b> — no goi <code>preprocessFundingData()</code> (sort mang
 * pred) va <code>BudgetManagerSimple.resetInstance()</code>. {@link #initDataReady} KHONG goi 2 thu do:
 * neu gan vao WFO/HPO qua duong initDataReady thi mang pred CHUA SORT → vong <code>break</code> khi
 * <code>score &gt; maxThres</code> cat SAI → bug ngam.
 */
public class SimulatorMarketLevelInvertedSelector {
    public static final Logger LOG = LoggerFactory.getLogger(SimulatorMarketLevelInvertedSelector.class);
    public static final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";

    // Dataset collections
    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;
    public TreeMap<Long, MarketDataObject> time2MarketData;
    public TreeMap<Long, AiPredictionData> predictionMap;
    public TreeMap<Long, long[]> time2SymbolPred;
    public AIRejectFilter aiRejectFilter;

    // Simulation metrics & Circuit Breaker status
    public Boolean is50PercentOrderLoss = null;
    public long breakerMarginHaltCount = 0;
    public long breakerDcaCapCount = 0;

    // Ablation study metrics (Track B)
    public long ablationSignalSeen = 0;
    public long ablationPassCount = 0;
    public long ablationPlaceboPass = 0;
    public float ablationPassRate = 0.5f;

    // O(1) Arrays to avoid Garbage Collection churn (exact replica of optimized production engine)
    @SuppressWarnings("unchecked")
    public List<OrderTargetInfoTest>[] symbol2OrdersEntry = new ArrayList[1000];
    public OrderTargetInfoTest[] symbol2OrderRunning = new OrderTargetInfoTest[1000];
    public short[] activeRunningIds = new short[1000];
    public int activeRunningCount = 0;

    // Daily cache for high-speed minutes lookup
    private final Map<Long, TreeMap<Long, KlineObjectSimple[]>> dayCache = new HashMap<>();

    public SimulatorMarketLevelInvertedSelector() {
        // Initialization
    }

    /**
     * Initializes all market datasets dynamically from Aerospike (for HPO/WFO and standalone runs).
     */
    public void initData() throws IOException, ParseException {
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();
        time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        time2SymbolPred = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        aiRejectFilter = new AIRejectFilter();
        
        // Auto-sort candidate primitives to avoid quicksort degradation
        preprocessFundingData(time2SymbolPred);
    }

    /**
     * Nạp dữ liệu cấu hình sẵn từ môi trường ngoài (dành cho các tác vụ điều phối song song WFO/HPO).
     */
    public void initDataReady(TreeMap<Long, MarketDataObject> time2MarketData, 
                               TreeMap<Long, AiPredictionData> predictionMap, 
                               TreeMap<Long, long[]> time2FundingPre, 
                               AIRejectFilter aiRejectFilter) throws OrtException {
        this.time2MarketData = time2MarketData;
        this.predictionMap = predictionMap;
        this.time2SymbolPred = time2FundingPre;
        this.aiRejectFilter = aiRejectFilter;
    }

    /**
     * Core Backtest Engine loop driving simulation chronological order minute-by-minute.
     */
    public void simulatorWithInitEntry(Long startTime, Long endTime) throws ParseException {
        // 🔒 Cổng gác liêm chính backtest tối cao
        BacktestIntegrityGuard.assertProductionGrade();

        for (long time = startTime; time <= endTime; time += Utils.TIME_MINUTE) {
            MarketDataObject marketData = time2MarketData.get(time);

            // Step 1: Cập nhật biến động giá & Trạng thái dời SL (Trailing stop) cho cụm vị thế đang chạy
            for (int i = 0; i < activeRunningCount; i++) {
                short symbolId = activeRunningIds[i];
                KlineObjectSimple ticker = aero(symbolId, time);
                if (ticker != null) {
                    startUpdateOldOrderTrading(time, symbolId, ticker);
                }
            }

            // Step 2: Xử lý đóng cắt lỗ do Delist (Mất dữ liệu quá 2 ngày)
            for (int i = 0; i < activeRunningCount; i++) {
                short symbolId = activeRunningIds[i];
                updateSymbolDeListed(symbolId, time);
            }

            // Step 3: Bộ chọn ứng viên (Candidate Selector) & Giao dịch Long-Only
            long[] preds = time2SymbolPred.get(time);
            if (preds != null && preds.length > 0) {
                List<Long> qualifiedCandidates = new ArrayList<>();
                
                // Phân giải ngưỡng trần tối đa dựa theo cấu hình Selector
                float maxThres = Configs.SELECTOR_SCORE_MAX >= 0 ? 
                                 Configs.SELECTOR_SCORE_MAX : 
                                 (Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * Configs.AI_DYNAMIC_MAX);

                // Gom toàn bộ coin đạt chuẩn nằm dưới ngưỡng trần (score <= maxThres)
                for (long pred : preds) {
                    float symbolPred = Float.intBitsToFloat((int) (pred & 0xFFFFFFFFL));
                    if (symbolPred > maxThres) {
                        break; // Mảng primitives đã pre-sorted tăng dần, kết thúc quét sớm
                    }
                    qualifiedCandidates.add(pred);
                }

                int nPass = qualifiedCandidates.size();
                if (nPass > 0) {
                    int limit = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                    
                    int startIdx, endIdx, step;
                    
                    // 🌟 REFACTOR MÓC XỬ LÝ ĐẢO DẤU SELECTOR 🌟
                    if (!Configs.SELECTOR_INVERT) {
                        // BEST-N (Cơ chế cũ): Quét từ đầu mảng lên (score P-Fail thấp nhất, có xác suất pump mạnh nhất)
                        startIdx = 0;
                        endIdx = Math.min(nPass, limit);
                        step = 1;
                    } else {
                        // WORST-N (Đảo dấu): Quét ngược từ cuối mảng xuống (score P-Fail cao nhất, coin ít pump nhất/bị xả sâu nhất)
                        startIdx = nPass - 1;
                        endIdx = Math.max(-1, nPass - 1 - limit);
                        step = -1;
                    }

                    int entryCount = 0;
                    for (int i = startIdx; i != endIdx; i += step) {
                        long pred = qualifiedCandidates.get(i);
                        short symbolId = (short) (pred >> 32);
                        float symbolPred = Float.intBitsToFloat((int) (pred & 0xFFFFFFFFL));

                        if (isSymbolRunning(symbolId)) {
                            continue; // Đang chạy vị thế, bỏ qua
                        }

                        KlineObjectSimple ticker = aero(symbolId, time);
                        if (ticker == null || !Utils.isTickerAvailable(ticker)) {
                            continue; // Thiếu dữ liệu phút hiện tại
                        }

                        // Thực thi tạo lệnh
                        createOrderBUY(symbolId, ticker, MarketLevelChange.PREDICT_SYMBOL_TRADE, marketData, symbolPred);
                        entryCount++;
                        if (entryCount >= limit) {
                            break;
                        }
                    }
                }
            }
        }

        // Lưu vết kết quả giao dịch phục vụ đối chiếu phân tích
        if (Configs.WRITE_SIM_STORAGE) {
            Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
        }
    }

    /**
     * Logic tạo lệnh BUY - Áp các lớp kiểm duyệt: Cầu dao marginhalt, AI dynamic filter & Hạn mức budget.
     */
    public void createOrderBUY(short symbolId, KlineObjectSimple ticker, MarketLevelChange levelChange, MarketDataObject marketData, Float symbolPred) {
        // 🔒 CẦU DAO TỔNG: Chặn mở vị thế mới khi tổng Margin của danh mục vượt ngưỡng an toàn (Mặc định 50%)
        if ("MARGIN".equals(Configs.BREAKER_MODE) || "BOTH".equals(Configs.BREAKER_MODE)) {
            float marginRatio = BudgetManagerSimple.getInstance().marginRunning / BudgetManagerSimple.getInstance().balanceBasic;
            if (marginRatio >= Configs.BREAKER_MARGIN_HALT) {
                breakerMarginHaltCount++;
                return; 
            }
        }

        if (levelChange != MarketLevelChange.DCA_LEVEL1) {
            if (is50PercentOrderLoss == null) {
                is50PercentOrderLoss = MarketBigChangeDetector.is50PercentOrderLoss(getActiveOrderList(), ticker.startTime);
            }
            if (is50PercentOrderLoss) {
                return; // Cản mở lệnh do mật độ lỗ cao
            }
        }

        AiPredictionData predict = predictionMap.get(ticker.startTime);
        if (predict == null) {
            return; // Đảm bảo đồng bộ tuyệt đối Sim-Live (loại bỏ bẫy lệch in-sample)
        }

        if (!levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            if ("B".equals(Configs.ABLATION_MODE)) {
                // OFF AI
            } else if ("C".equals(Configs.ABLATION_MODE)) {
                // Placebo random gate
                ablationSignalSeen++;
                java.util.Random r = new java.util.Random(Configs.ABLATION_SEED ^ ticker.startTime);
                if (r.nextFloat() >= ablationPassRate) {
                    return;
                }
                ablationPlaceboPass++;
            } else {
                // AI Filter dynamic
                AIRejectFilter.FilterResult filterResult = null;
                if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) {
                    filterResult = aiRejectFilter.checkSignalDynamic(predict, symbolPred);
                }
                if (filterResult == null) {
                    filterResult = aiRejectFilter.checkSignal(predict);
                }
                if (filterResult != null && filterResult.decision == AIRejectFilter.FilterDecision.REJECT) {
                    return;
                }
            }
        }

        if (Configs.GATE_COUNT_ONLY) return;

        String symbolStr = SimpleSymbolMapper.getInstance().getSymbol(symbolId);
        Float budget = BudgetManagerSimple.getInstance().getBudget();
        Float entry = ticker.priceClose;
        Float quantity = Utils.calQuantityTest(budget, Configs.LEVERAGE_ORDER, entry, symbolStr);

        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity, Configs.LEVERAGE_ORDER, symbolStr, ticker.startTime, ticker.startTime, OrderSide.BUY);
        order.minPrice = entry;
        order.maeLow = entry;
        order.lastEntry = entry;
        order.lastPrice = entry;
        order.firstEntryPrice = entry;
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

        if (Configs.WFO_LOG_ENTRIES) {
            LOG.info("ENTRY_DUMP {} {} {}", symbolStr, ticker.startTime, levelChange);
        }

        BudgetManagerSimple.getInstance().counterOrderCreated.incrementAndGet();
        symbol2OrderRunning[symbolId] = mergeOrder(orders, ticker, symbol2OrderRunning[symbolId]);
        addActiveRunningId(symbolId);

        BudgetManagerSimple.getInstance().updateMaxOrderRunning(counterOrderRunning());
        BudgetManagerSimple.getInstance().marginRunning += order.calMargin();
    }

    private void startUpdateOldOrderTrading(Long time, short symbolId, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning[symbolId];
        if (orderMulti != null) {
            if (orderMulti.timeStart <= ticker.startTime) {
                orderMulti.updatePriceByKlineSimple(ticker);

                // HARD Stop-Loss Blanket (Kiểm soát rủi ro gầm sập)
                if (Configs.HARD_SL_PCT > 0f && orderMulti.firstEntryPrice != null && 
                    ticker.minPrice <= orderMulti.firstEntryPrice * (1f - Configs.HARD_SL_PCT)) {
                    float slTrigger = orderMulti.firstEntryPrice * (1f - Configs.HARD_SL_PCT);
                    orderMulti.status = OrderTargetStatus.STOP_LOSS_DONE;
                    float fill = Math.min(slTrigger, ticker.priceOpen);
                    if (orderMulti.priceSL != null) {
                        fill = Math.min(fill, orderMulti.priceSL);
                    }
                    orderMulti.priceTP = fill;
                    closeOrder(symbolId, orderMulti);
                    return;
                }

                // Kiểm soát Trailing-Stop khi có lời vượt mốc PST
                if (ticker.maxPrice >= orderMulti.priceEntry * (1 + Configs.RATE_PROFIT_STOP_MARKET) || 
                    orderMulti.priceSL != null) {
                    Float predReturn15M = getPredReturn15MForTradingStop(time);
                    orderMulti.updateStatusNew(predReturn15M, ticker);
                    if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE) || 
                        orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE) || 
                        orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                        closeOrder(symbolId, orderMulti);
                    } else {
                        orderMulti.updateTPSL(predReturn15M, ticker);
                    }
                }
            }
        }
    }

    private void closeOrder(short symbolId, OrderTargetInfoTest orderMulti) {
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry[symbolId];
        if (orders != null) {
            // Tính phí funding ròng một lượt duy nhất khi đóng cụm lệnh để tối ưu hiệu năng
            orderMulti.computeFundingOnClose();
            boolean fundingAssigned = false;
            for (OrderTargetInfoTest order : orders) {
                order.timeUpdate = orderMulti.timeUpdate;
                order.status = orderMulti.status;
                order.priceTP = orderMulti.priceTP;
                order.minPrice = orderMulti.minPrice;
                order.maeLow = orderMulti.maeLow;
                order.lastPrice = orderMulti.lastPrice;
                if (!fundingAssigned) {
                    order.time2FundingFee = orderMulti.time2FundingFee;
                    fundingAssigned = true;
                }
                allOrderDone.put(order.timeUpdate, order);
            }
        }
        symbol2OrderRunning[symbolId] = null;
        symbol2OrdersEntry[symbolId] = null;
        removeActiveRunningId(symbolId);
        BudgetManagerSimple.getInstance().marginRunning -= orderMulti.calMargin();
    }

    private OrderTargetInfoTest mergeOrder(List<OrderTargetInfoTest> orders, KlineObjectSimple ticker, OrderTargetInfoTest prevRunning) {
        float quantity = 0f;
        float margin = 0f;
        long firstLegTime = Long.MAX_VALUE;
        for (OrderTargetInfoTest orderInfo : orders) {
            margin += orderInfo.priceEntry * orderInfo.quantity;
            quantity += orderInfo.quantity;
            if (orderInfo.timeStart < firstLegTime) {
                firstLegTime = orderInfo.timeStart;
            }
        }
        float entry = margin / quantity;

        OrderTargetInfoTest orderMulti = new OrderTargetInfoTest(
            OrderTargetStatus.POSITION_RUNNING, entry, null, quantity, Configs.LEVERAGE_ORDER, 
            orders.get(0).symbol, ticker.startTime, ticker.startTime, OrderSide.BUY
        );
        orderMulti.firstEntryPrice = orders.get(0).priceEntry;
        orderMulti.clusterFirstLegTime = firstLegTime;

        float minPrice = entry;
        float maeLow = entry;
        float maePeak = entry;
        if (prevRunning != null) {
            minPrice = Math.min(prevRunning.minPrice, entry);
            maeLow = Math.min(prevRunning.maeLow, entry);
            maePeak = Math.max(prevRunning.maePeak, entry);
        }
        orderMulti.minPrice = minPrice;
        orderMulti.maeLow = maeLow;
        orderMulti.maePeak = maePeak;
        orderMulti.lastPrice = ticker.priceClose;
        orderMulti.lastEntry = ticker.priceClose;
        orderMulti.tickerOpen = ticker;
        orderMulti.marketLevelChange = orders.get(orders.size() - 1).marketLevelChange;
        orderMulti.predict = orders.get(orders.size() - 1).predict;
        orderMulti.symbolPred = orders.get(orders.size() - 1).symbolPred;

        return orderMulti;
    }

    private void updateSymbolDeListed(short symbolId, Long time) {
        OrderTargetInfoTest order = symbol2OrderRunning[symbolId];
        if (order != null) {
            if (order.timeUpdate < time - 2 * Utils.TIME_DAY) {
                order.status = OrderTargetStatus.STOP_LOSS_DONE;
                order.priceTP = order.lastPrice;
                closeOrder(symbolId, order);
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

    // Helper data-retrieval methods
    private KlineObjectSimple aero(short sid, long minute) {
        TreeMap<Long, KlineObjectSimple[]> day = getDay(tradingDayStart(minute));
        if (day == null) return null;
        KlineObjectSimple[] arr = day.get(minute);
        if (arr == null || sid < 0 || sid >= arr.length) return null;
        return arr[sid];
    }

    private TreeMap<Long, KlineObjectSimple[]> getDay(long anchor) {
        if (!dayCache.containsKey(anchor)) {
            try {
                dayCache.put(anchor, DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(anchor));
            } catch (Exception e) {
                dayCache.put(anchor, null);
            }
        }
        return dayCache.get(anchor);
    }

    private long tradingDayStart(long t) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(t);
        cal.set(Calendar.HOUR_OF_DAY, 7);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        if (cal.getTimeInMillis() > t) {
            cal.add(Calendar.DAY_OF_MONTH, -1);
        }
        return cal.getTimeInMillis();
    }

    // O(1) Arrays utility helpers
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

    private List<OrderTargetInfoTest> getActiveOrderList() {
        List<OrderTargetInfoTest> list = new ArrayList<>(activeRunningCount);
        for (int i = 0; i < activeRunningCount; i++) {
            list.add(symbol2OrderRunning[activeRunningIds[i]]);
        }
        return list;
    }

    private int counterOrderRunning() {
        int counter = 0;
        for (int i = 0; i < activeRunningCount; i++) {
            short id = activeRunningIds[i];
            if (symbol2OrdersEntry[id] != null) {
                counter += symbol2OrdersEntry[id].size();
            }
        }
        return counter;
    }

    /**
     * Pre-calculate & sort the primitives values to avoid quicksort degradation during heavy HPO loops.
     */
    public static void preprocessFundingData(TreeMap<Long, long[]> time2FundingPre) {
        if (time2FundingPre == null) return;
        LOG.info("⚙️ Bắt đầu Pre-calculate và Sắp xếp sẵn dữ liệu Funding Fee...");
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

    /**
     * Standalone main runner class allowing instant validation execution.
     */
    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        LOG.info("Khởi động SimulatorMarketLevelInvertedSelector...");
        LOG.info("Cấu hình: TICKER_SOURCE: {} | AEROSPIKE_READ_CLUSTER: {}", Configs.TICKER_SOURCE, Configs.AEROSPIKE_READ_CLUSTER);
        LOG.info("Chế độ SELECTOR_INVERT (Worst-N): {}", Configs.SELECTOR_INVERT);

        SimulatorMarketLevelInvertedSelector test = new SimulatorMarketLevelInvertedSelector();
        test.initData();

        Long endTime = System.currentTimeMillis();
        String simEndDate = System.getenv("SIM_END_DATE");
        if (simEndDate != null && !simEndDate.isBlank()) {
            endTime = Utils.sdfFile.parse(simEndDate).getTime();
            LOG.info("🔀 SIM_END_DATE được ghi đè: chạy tới {}", simEndDate);
        }

        test.simulatorWithInitEntry(startTime, endTime);
        Thread.sleep(5000);
        System.exit(0);
    }
}