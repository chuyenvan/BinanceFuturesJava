/*
 * Copyright 2024 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.trading;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.helper.OrderHelper;
import com.binance.chuyennd.helper.PositionHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.trading.monitor.Reporter;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderType;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;

/**
 * @author pc
 */
public class BinanceOrderTradingManager {

    public static final Logger LOG = LoggerFactory.getLogger(BinanceOrderTradingManager.class);
    public ExecutorService executorServiceOrderNew = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    private final ConcurrentHashMap<String, Long> symbol2Processing = new ConcurrentHashMap<>();
    private final Map<String, List<KlineObjectSimple>> symbol2Tickers = new HashMap<>();

    public static void main(String[] args) throws InterruptedException, ParseException {
        Configs.assertLiveRuntime();   // #12 (TASK-030/112): fail-fast nếu AEROSPIKE_READ_CLUSTER thiếu/khác 242 → tránh đọc 226 (backtest) trên live
        Utils.writePid2File();
        new DetectEntrySignal2TradeNormal().start();
        new BinanceOrderTradingManager().start();
    }

    private void start() {
        initData();
        startThreadListenQueueOrder2ManagerNew();
        startThreadManagerOrder();
        startThreadAutoRestartProgram();
    }


    private void startThreadManagerOrder() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadManagerOrder");
            LOG.info("Start thread ThreadManagerOrder {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
            try {
                // update first
                updatePositionInfo();
            } catch (Exception e) {
                e.printStackTrace();
            }
            while (true) {
                try {
                    processManagerPosition();
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadManagerOrder: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectEntrySignal2TradeNormal.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private void startThreadAutoRestartProgram() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadAutoRestartProgram");
            LOG.info("Start thread ThreadAutoRestartProgram");
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_HOUR * 4);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectEntrySignal2TradeNormal.class.getName()).log(Level.SEVERE, null, ex);
                }
                try {
                    Utils.reset("Reset by Schedule");
                } catch (Exception e) {
                    LOG.error("ERROR during Restart: {}", e);
                    e.printStackTrace();
                }
            }

        }).start();
    }

    private void startThreadListenQueueOrder2ManagerNew() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadListenQueueOrder2ManagerNew");
            LOG.info("Start thread ThreadListenQueueOrder2ManagerNew!");
            while (true) {
                List<String> data;
                try {
                    data = RedisHelper.getInstance().get().blpop(0, RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE);
                    String orderJson = data.get(1);
                    try {
                        OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
                        LOG.info("Queue listen order to manager order received : {} {} ", order.side, order.symbol);
                        if (!symbol2Processing.containsKey(order.symbol)
                                || symbol2Processing.get(order.symbol) < System.currentTimeMillis() - 2 * Utils.TIME_MINUTE) {
                            if (order.status.equals(OrderTargetStatus.REQUEST)) {
                                symbol2Processing.put(order.symbol, System.currentTimeMillis());
                                executorServiceOrderNew.execute(() -> processOrderNewMarketNew(order));
                            }
                        } else {
                            LOG.info("{} is lock because processing! {}", order.symbol, symbol2Processing.size());
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadListenQueuePosition2ManagerNew {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }


    private void processOrderNewMarketNew(OrderTargetInfo order) {
        try {
            LOG.info("Create order market {} {}", order.side, order.symbol);
            if (SymbolOrderLockingManager.getInstance().isLockReduceOnly(order.symbol)) {
                LOG.info("Symbol {} is locking ReduceOnly !", order.symbol);
                return;
            } else {
                if ("true".equalsIgnoreCase(System.getenv("SHADOW_NO_PUSH"))) {
                    LOG.info("[SHADOW] would-BUY {} {} entry: {} quantity: {} time:{} market level: {}",
                            order.side, order.symbol, order.priceEntry, order.quantity,
                            Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), order.marketLevel);
                    symbol2Processing.remove(order.symbol);
                    return;
                }
                Order orderInfo = OrderHelper.newOrderMarket(order.symbol, order.side, order.quantity);
                if (orderInfo == null) {
                    return;
                }
                BudgetManager.getInstance().symbol2Level.put(order.symbol, order.marketLevel);
                BudgetManager.getInstance().symbol2Pos.put(order.symbol, PositionHelper.createPosNew(order.symbol, new BigDecimal(order.priceEntry)
                        , new BigDecimal(order.quantity)));
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, order.symbol, Utils.toJson(order));
                String log = order.side + " " + order.symbol + " entry: " + order.priceEntry
                        + " quantity: " + order.quantity
                        + " time:" + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)
                        + " market level: " + order.marketLevel;
                LOG.info(log);
                updatePositionInfo();
            }
        } catch (Exception e) {
            LOG.info("Error during process order: {}", Utils.toJson(order));
            try {
                Thread.sleep(200);
                if (order.timeStart > System.currentTimeMillis() - 5 * Utils.TIME_MINUTE) {
                    RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE, Utils.toJson(order));
                }
                LOG.info("ReCreate order symbol false! {} {}", order.symbol, Utils.toJson(order));
            } catch (Exception ex) {
                ex.printStackTrace();
            }
            e.printStackTrace();
        }
        symbol2Processing.remove(order.symbol);

    }

    private void initData() {

        ClientSingleton.getInstance();
        symbol2Tickers.putAll(DataManagerAerospikeFloatSim.readDataForSymbols(
                System.currentTimeMillis() - 90 * Utils.TIME_MINUTE, 90));
    }

    public void processManagerPosition() {
        try {
            int currentSecond = Utils.getCurrentSecond();
            if (currentSecond == 10) {
                executorServiceOrderNew.execute(() -> updatePositionInfo());
            }
            // sl dynamic
            if (currentSecond % 2 == 0) {
                executorServiceOrderNew.execute(() -> updatePositionMarkPrice());
                executorServiceOrderNew.execute(() -> processDynamicTP_SL());
                executorServiceOrderNew.execute(() -> initSLFirst());

            }
            // sl dynamic
            if (currentSecond % 30 == 0) {
                symbol2Tickers.putAll(DataManagerAerospikeFloatSim.readDataForSymbols(
                        System.currentTimeMillis() - 90 * Utils.TIME_MINUTE, 90));
            }
            // reporter
            if (Utils.getCurrentMinute() % 30 == 0 && Utils.getCurrentSecond() == 30) {
                executorServiceOrderNew.execute(() -> new Reporter().buildReport());
            }
        } catch (Exception e) {
            LOG.error("ERROR during ThreadManagerOrderNew: {}", e);
            e.printStackTrace();
        }
    }

    private void updatePositionMarkPrice() {
        try {
            Set<PositionRisk> positions = new HashSet<>();
            positions.addAll(BudgetManager.getInstance().symbol2Pos.values());
            Map<String, Float> symbol2Price = DataManagerAerospikeFloatSim.getAllPriceRealtimeLegacy(BudgetManager.getInstance().symbol2Pos.keySet());
            for (PositionRisk pos : positions) {
                Float lastPrice = symbol2Price.get(pos.getSymbol());
                if (lastPrice != null) {
                    pos.setMarkPrice(new BigDecimal(lastPrice));
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void initSLFirst() {
        long startTime = System.currentTimeMillis();
        Set<PositionRisk> positions = new HashSet<>();
        positions.addAll(BudgetManager.getInstance().symbol2Pos.values());
        for (PositionRisk position : positions) {
            if (position == null) {
                continue;
            }
            String symbol = position.getSymbol();
//            if (StringUtils.equals(position.getSymbol(), "MOODENGUSDT")) {
//                System.out.println("debug");
//            }
            OrderTargetInfo orderInfo = getOrderInfo(position.getSymbol());
            Float rateLoss = PositionHelper.calRateLoss(position);
            OrderSide positionSide = OrderSide.BUY;
            if (position.getPositionAmt().compareTo(new BigDecimal("0")) < 0) {
                continue;
            }
            if (orderInfo != null && orderInfo.side.equals(positionSide)) {
                if (position.getUpdateTime() < startTime + 30 * Utils.TIME_MINUTE) {
                    BudgetManager.getInstance().symbol2Level.put(symbol, orderInfo.marketLevel);
                } else {
                    BudgetManager.getInstance().symbol2Level.remove(symbol);
                }
                List<KlineObjectSimple> tickers = symbol2Tickers.get(symbol);

                Float predReturn15M  = 0f;
                AiPredictionData predictData = DataManagerAerospikeFloatSim.getAiPredictionAtTime(System.currentTimeMillis() - Utils.TIME_MINUTE);
                if (predictData != null) {
//                    LOG.info("Predict data for SL init: {} {}", Utils.normalizeDateYYYYMMDDHHmm(predictData.timestamp), Utils.toJson(predictData));
                    predReturn15M  = predictData.predReturn15M;
                }
                Float rateMin2MoveSl = TradeUtils.calRateMinWithPredReturn15MForTradingStop(predReturn15M );
                if (rateLoss > rateMin2MoveSl) {
                    // [FIX LIVE 2026-09-02] tu chua SL SAI dang treo: da arm (rateLoss > nguong) ma priceSL < entry (do bug
                    //   tsGap fallback truoc day) -> coi nhu chua co SL de tao lai o tren entry. Chi ap dung BUY.
                    boolean slBelowEntry = orderInfo.priceSL != null && orderInfo.side.equals(OrderSide.BUY)
                            && orderInfo.priceSL < position.getEntryPrice().floatValue();
                    if (slBelowEntry) {
                        LOG.warn("[TS-GAP] {} SL dang treo {} < entry {} du da lai {}% -> tao lai SL", symbol, orderInfo.priceSL,
                                position.getEntryPrice().floatValue(), Utils.formatPercent(rateLoss));
                    }
                    if (orderInfo.priceSL == null || slBelowEntry) {
                        OrderSide sideSL = OrderSide.SELL;
                        Float rateStop = tsGap(rateLoss, predReturn15M, symbol);
                        if (orderInfo.side.equals(OrderSide.SELL)) {
                            sideSL = OrderSide.BUY;
                        }
                        Float priceSLNew = Utils.calPriceTarget(symbol, position.getEntryPrice().floatValue(), sideSL, -rateStop);
                        if (priceSLNew != 0) {
                            LOG.info("New price SL:{} {} {} {} {} {}%", symbol, orderInfo.marketLevel,
                                    Utils.normalizeDateYYYYMMDDHHmm(position.getUpdateTime()),
                                    Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                                    priceSLNew, Utils.formatPercent(-rateStop));
                            if (createSL(position, priceSLNew)) {
                                orderInfo.priceSL = priceSLNew;
                                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderInfo));
                            }
                        }
                    }
                }
            } else {
                OrderSide side = OrderSide.BUY;
                if (position.getPositionAmt().compareTo(new BigDecimal("0")) < 0) {
                    side = OrderSide.SELL;
                }
                OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, position.getEntryPrice().floatValue(),
                        null, position.getPositionAmt().floatValue(), Configs.LEVERAGE_ORDER, symbol, position.getUpdateTime(),
                        position.getUpdateTime(), side, Constants.TRADING_TYPE_VOLUME_MINI);
                orderTrade.marketLevel = MarketLevelChange.ORDER_PROFIT;
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderTrade));
                LOG.info("New order 2 redis because order null: {}", Utils.toJson(orderTrade));
            }
        }
    }


    public void updatePositionInfo() {
        String lockName = "UpdateAllPos";
        if (SymbolOrderLockingManager.getInstance().isLock(lockName, 3)) {
            LOG.info("Symbol {} is locking for loop!", lockName);
            return;
        }
        SymbolOrderLockingManager.getInstance().addLock(lockName);
        try {
            long startTime = System.currentTimeMillis();
            List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
            if (positions == null || positions.isEmpty()) {
                LOG.info("Error get position from binance! {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
                return; // lock được nhả ở finally
            }
            // 🔒 #9: BUILD MAP MỚI rồi SWAP — KHÔNG clear-then-fill map đang được luồng khác đọc
            // (markPrice executor + processDynamicTP_SL đọc symbol2Pos song song → clear giữa chừng = mất position tạm thời).
            Map<String, PositionRisk> newSymbol2Pos = new HashMap<>();
            Map<String, Float> newSymbol2Margin = new HashMap<>();
            Set<String> newMarginBig = new HashSet<>();
            Set<String> newSymbolBuy = new HashSet<>();
            Set<String> newSymbolSell = new HashSet<>();
            float marginTotal = 0f;
            float budget = BudgetManager.getInstance().getBudget();
            for (PositionRisk position : positions) {
                if (position.getPositionAmt().compareTo(BigDecimal.ZERO) == 0) {
                    continue;
                }
                String symbol = position.getSymbol();
                float margin = PositionHelper.callMargin(position);
                newSymbol2Pos.put(symbol, position);
                if (PositionHelper.calRateLoss(position) < 6 * Configs.RATE_PROFIT_STOP_MARKET) {
                    marginTotal += margin;
                }
                newSymbol2Margin.put(symbol, margin);
                if (margin >= 1.5 * budget) {
                    newMarginBig.add(symbol);
                }
                if (position.getPositionAmt().compareTo(BigDecimal.ZERO) > 0) {
                    newSymbolBuy.add(symbol);
                } else {
                    newSymbolSell.add(symbol);
                }
            }
            // SWAP nguyên tử-tham-chiếu: luồng đọc thấy map CŨ (đầy đủ) cho tới khi gán xong map MỚI — không có cửa sổ rỗng.
            BudgetManager bm = BudgetManager.getInstance();
            bm.symbol2Margin = newSymbol2Margin;
            bm.marginBig = newMarginBig;
            bm.symbolBuy = newSymbolBuy;
            bm.symbolSell = newSymbolSell;
            bm.marginRunning = marginTotal;
            bm.symbol2Pos = newSymbol2Pos;   // swap CUỐI (map được đọc nhiều nhất)
            bm.removeSymbolNotPos(newSymbol2Pos.keySet());
            updateSymbolRunning(newSymbol2Pos.keySet());
            Long timeProcess = (System.currentTimeMillis() - startTime);
            LOG.info("Update all position:{} {} ms", bm.symbol2Pos.size(), timeProcess.floatValue());
        } finally {
            SymbolOrderLockingManager.getInstance().removeLock(lockName); // nhả lock ở MỌI đường ra (return/exception)
        }
    }

    /**
     * [PRED-GAP] Chon gap trailing: neu env TS_PRED_GAP=1 va co selector per-coin P(no-pump) (tuoi tu tick
     * entry 15m) -> dung gap theo pred per-coin (weak khi P(no-pump)>TS_PNOPUMP_WEAK_THR, default 0.29).
     * Nguoc lai (flag off / thieu pred) -> gap cu theo market gate pred (byte-identical hanh vi cu).
     */
    // [FIX LIVE 2026-09-02] SL duoi entry sau khi arm (CLOUSDT: entry 0.14956 -> SL 0.14806 = -1%).
    //   Nguyen nhan: initSLFirst chay NGAY SAU restart (auto-restart ~4h), TRUOC tick selector dau tien
    //   -> LATEST_SEL_PNOPUMP rong -> fallback calRateLossDynamicBuy(rateLoss, gatePred). Tu FROZEN v1 (2026-08-24)
    //   tham so 2 cua ham do la pNoPump (0..1), gatePred=predReturn15M ~0.01 bi hieu la pNoPump=0.01
    //   -> pGood 0.99 -> gap = 0.99*TS_MAX_GAP ~ 7.9% -> rate = rateLoss(5-7%) - 7.9% < 0 -> SL DUOI entry.
    //   Sua: (1) pnp null -> coi nhu coin YEU (nhanh weak, maxGap TS_MAX_GAP_WEAK 3%) thay vi truyen gatePred sai nghia;
    //        (2) invariant live: da arm (rateLoss > nguong) thi SL KHONG BAO GIO duoi entry (san TS_LIVE_MIN_LOCK, mac dinh 0.5%).
    private static final float TS_LIVE_MIN_LOCK = com.binance.chuyennd.tradecore.Cfg.get("TS_LIVE_MIN_LOCK") != null
            ? Float.parseFloat(com.binance.chuyennd.tradecore.Cfg.get("TS_LIVE_MIN_LOCK").trim()) : 0.005f;
    // [2026-09-02 LOSER-TS] gio toi da cho lenh CHUA arm (sim G1 = 168). 0/unset = OFF. Buffer duoi mark de dat STOP_MARKET thoat.
    private static final long LIVE_LOSER_TIME_STOP_HOURS = com.binance.chuyennd.tradecore.Cfg.get("LIVE_LOSER_TIME_STOP_HOURS") != null
            ? Long.parseLong(com.binance.chuyennd.tradecore.Cfg.get("LIVE_LOSER_TIME_STOP_HOURS").trim()) : 0L;
    private static final float LIVE_LOSER_TS_BUFFER = com.binance.chuyennd.tradecore.Cfg.get("LIVE_LOSER_TS_BUFFER") != null
            ? Float.parseFloat(com.binance.chuyennd.tradecore.Cfg.get("LIVE_LOSER_TS_BUFFER").trim()) : 0.003f;

    private static float tsGap(float rateLoss, Float gatePred, String symbol) {
        float rate;
        if ("1".equals(com.binance.chuyennd.tradecore.Cfg.get("TS_PRED_GAP"))) {
            Float pnp = DetectEntrySignal2TradeNormal.LATEST_SEL_PNOPUMP.get(symbol);
            float thr = 0.29f;
            String v = com.binance.chuyennd.tradecore.Cfg.get("TS_PNOPUMP_WEAK_THR");
            if (v != null) { try { thr = Float.parseFloat(v.trim()); } catch (Exception ignore) { } }
            if (pnp == null) {
                LOG.info("[TS-GAP] {} chua co pNoPump (sau restart/chua qua tick selector) -> dung nhanh WEAK gap<={}",
                        symbol, Configs.TS_MAX_GAP_WEAK);
            }
            rate = TradeUtils.calRateLossDynamicBuyPNoPump(rateLoss, pnp != null ? pnp : 1f, thr);
        } else {
            rate = TradeUtils.calRateLossDynamicBuy(rateLoss, gatePred);
        }
        if (rate < TS_LIVE_MIN_LOCK) {
            LOG.warn("[TS-GAP] {} rateStop {} < san {} (rateLoss={}) -> ep SL len tren entry", symbol, rate, TS_LIVE_MIN_LOCK, rateLoss);
            rate = TS_LIVE_MIN_LOCK;
        }
        return rate;
    }

    public void processDynamicTP_SL() {
        Set<PositionRisk> positions = new HashSet<>();
        positions.addAll(BudgetManager.getInstance().symbol2Pos.values());
        for (PositionRisk position : positions) {
            try {
                if (position == null || position.getPositionAmt().compareTo(new BigDecimal("0")) == 0) {
                    continue;
                }
                Float rateLoss = PositionHelper.calRateLoss(position);
                Float priceEntry = position.getEntryPrice().floatValue();
                String symbol = position.getSymbol();
                OrderTargetInfo orderInfo = getOrderInfo(symbol);
                if (orderInfo == null) {
                    continue;
                }
                if (orderInfo.priceEntry != priceEntry) {
                    orderInfo.priceEntry = priceEntry;
                }
                // [2026-09-02 LOSER-TS] Dong bo voi sim G1 (SIM_LOSER_TIME_STOP_HOURS=168): lenh BUY CHUA arm (priceSL null)
                //   qua LIVE_LOSER_TIME_STOP_HOURS gio -> dat STOP_MARKET ngay duoi mark (LIVE_LOSER_TS_BUFFER, mac dinh 0.3%)
                //   de thoat o tick ke tiep (tai dung createSL, khong them duong dat lenh moi). env unset/0 -> OFF (byte-identical).
                if (LIVE_LOSER_TIME_STOP_HOURS > 0 && orderInfo.priceSL == null
                        && position.getPositionAmt().compareTo(new BigDecimal("0")) > 0
                        && orderInfo.timeStart > 0
                        && System.currentTimeMillis() - orderInfo.timeStart > LIVE_LOSER_TIME_STOP_HOURS * Utils.TIME_HOUR) {
                    if (position.getMarkPrice() == null) {
                        continue;
                    }
                    float mark = position.getMarkPrice().floatValue();
                    // calPriceTarget(SELL, +r) = mark - r*mark -> STOP_MARKET ngay DUOI mark.
                    Float priceStop = Utils.calPriceTarget(symbol, mark, OrderSide.SELL, LIVE_LOSER_TS_BUFFER);
                    LOG.info("[LOSER-TS] {} chua arm sau {}h (start {}) rateLoss={} mark={} -> SL {} de thoat",
                            symbol, LIVE_LOSER_TIME_STOP_HOURS, Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart),
                            rateLoss, mark, priceStop);
                    if (createSL(position, priceStop)) {
                        orderInfo.priceSL = priceStop;
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderInfo));
                    }
                    continue;
                }
                OrderSide side2Sl;
                Float maxChange60M = 0f;
                AiPredictionData predictData = DataManagerAerospikeFloatSim.getAiPredictionAtTime(System.currentTimeMillis() - Utils.TIME_MINUTE);
                if (predictData != null) {
//                    LOG.info("Predict data for SL DL: {} {}", Utils.normalizeDateYYYYMMDDHHmm(predictData.timestamp), Utils.toJson(predictData));
                    maxChange60M = predictData.predReturn15M;
                }
                Float rateMin2MoveSl = Configs.TS_PROFIT_MULTIPLIER * TradeUtils.calRateMinWithPredReturn15MForTradingStop(maxChange60M);
                // BUY
                if (position.getPositionAmt().compareTo(new BigDecimal("0")) > 0) {
                    side2Sl = OrderSide.SELL;
                } else { // SELL
                    side2Sl = OrderSide.BUY;
                }
                if (orderInfo.priceSL != null && rateLoss > rateMin2MoveSl) {
                    // move SL
                    Float priceSL = orderInfo.priceSL;
                    Float rateSL = tsGap(rateLoss, maxChange60M, symbol);
                    Float priceSLNew = Utils.calPriceTarget(symbol, priceEntry, side2Sl, -rateSL);
                    float priceSLChange = priceSLNew - priceSL;
                    if (position.getPositionAmt().compareTo(new BigDecimal("0")) < 0) {
                        priceSLNew = Utils.calPriceTarget(symbol, priceEntry, side2Sl, -rateSL);
                        priceSLChange = priceSL - priceSLNew;
                    }

                    // move sl

                    if (rateLoss >= rateMin2MoveSl
                            && priceSLChange > 0) {
                        if (symbol2Processing.containsKey(symbol)) {
                            if (symbol2Processing.get(symbol) > System.currentTimeMillis() - 5 * Utils.TIME_MINUTE) {
                                LOG.info("{} is locking in list: {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(symbol2Processing.get(symbol)));
                                return;
                            }
                        }
                        LOG.info("Update SL {} {} {} {}->{} {}%", Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart),
                                Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), symbol, priceSL,
                                priceSLNew, Utils.formatPercent(rateSL));
                        if (createSL(position, priceSLNew)) {
                            orderInfo.priceSL = priceSLNew;
                            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderInfo));
                        }
                    }
                }

            } catch (Exception e) {
                LOG.info("Error process position: {}", position.getSymbol());
                e.printStackTrace();
            }
        }
    }

    private void updateSymbolRunning(Set<String> symbols) {
        try {
            Set<String> symbolsAtRedis = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING);
            for (String symbol : symbols) {
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING, symbol, symbol);
            }
            for (String symbol : symbolsAtRedis) {
                if (!symbols.contains(symbol)) {
                    RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING, symbol);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public boolean createSL(PositionRisk pos, Float priceSL) {
        try {
            if (priceSL == null) {
                return false;
            }
            String symbol = pos.getSymbol();
            if (symbol2Processing.containsKey(symbol)) {
                if (symbol2Processing.get(symbol) > System.currentTimeMillis() - 2 * Utils.TIME_MINUTE) {
                    LOG.info("{} is locking in list: {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(symbol2Processing.get(symbol)));
                    return false;
                }
            }
            symbol2Processing.put(symbol, System.currentTimeMillis());
            Order orderSLResult = null;
            try {
                List<Order> openOrders = ClientSingleton.getInstance().syncRequestClient.getOpenAlgoOrders(symbol);
                if (!openOrders.isEmpty()) {
                    for (Order openOrder : openOrders) {
                        if (openOrder.getType().equals(OrderType.STOP_MARKET.toString())) {
                            if (openOrder.getStopPrice().floatValue() != priceSL) {
                                LOG.info("Cancel order sl to renew: {}", openOrder.getSymbol());
                                ClientSingleton.getInstance().syncRequestClient.cancelAlgoOrder(
                                        openOrder.getOrderId(), null);
                            } else {
                                LOG.info("{} have sl order -> not create sl", pos.getSymbol());
                                return true;
                            }
                        }
                        if (openOrder.getType().equals(OrderType.LIMIT.toString()) && openOrder.getPrice().floatValue() == priceSL) {
                            LOG.info("Cancel order sl type limit: " + openOrder.getOrderId() + " of " + openOrder.getSymbol());
                            BinanceFuturesClientSingleton.getInstance().cancelOrder(openOrder.getSymbol(), openOrder.getClientOrderId());
                        }
                    }
                }
                // chua co sl -> tao sl
                String log;
                if (pos.getPositionAmt().compareTo(new BigDecimal("0")) > 0) {
                    if (pos.getEntryPrice().equals(new BigDecimal("0.0"))) {
                        LOG.info("Error process SL for: {} {}", pos.getSymbol(), pos.getEntryPrice());
                    } else {
                        pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo(pos.getSymbol());
                        if (pos.getEntryPrice().equals(new BigDecimal("0.0"))) {
                            LOG.info("Position has finished: {} {} {}", pos.getSymbol(), pos.getEntryPrice(),
                                    Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
                        } else {
                            if (pos != null) {
                                log = "Create sl -> SELL "
                                        + pos.getSymbol() + " " + pos.getPositionAmt().floatValue() + " " + pos.getEntryPrice().floatValue()
                                        + " -> " + priceSL + " rate: " + Utils.formatPercent(Math.abs(Utils.rateOf2Double(priceSL,
                                        pos.getEntryPrice().floatValue())));
                                LOG.info(log);
                                orderSLResult = OrderHelper.stopLoss(pos.getSymbol(), pos.getPositionAmt().floatValue(), priceSL);
                            }
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            symbol2Processing.remove(symbol);
            if (orderSLResult != null) {
                return true;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    public OrderTargetInfo getOrderInfo(String symbol) {
        try {
            String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
            OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
            return order;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }
}
