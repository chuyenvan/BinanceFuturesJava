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

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.helper.PositionHelper;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.tradecore.DcaProcessor;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.tradecore.TrendDetector;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.chuyennd.websocket.ListenAllTicker;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.PositionRisk;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * @author pc
 */
public class DetectEntrySignal2TradeNormal {

    public static final Logger LOG = LoggerFactory.getLogger(DetectEntrySignal2TradeNormal.class);
    private static final String FILE_STORAGE_SELLING_EXHAUSTED = "storage/data/SellingExhausted.data";
    private static final String FILE_STORAGE_TIME_RATE_DOWN15M = "storage/data/time2RatDown15M.data";
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    public ConcurrentHashMap<String, Long> symbolSellingExhausted = new ConcurrentHashMap<>();
    public TreeMap<Long, Double> time2RateDown15MAvg = new TreeMap<>();

    public static void main(String[] args) throws InterruptedException, ParseException {
//        new DetectEntrySignal2Trader().getTickerBySymbol("QNTUSDT");
//        String symbol = "ALTUSDT";
        Long time = Utils.sdfFileHour.parse("20250726 08:16").getTime();

        System.out.println(new DetectEntrySignal2TradeNormal().isBtcTrendSell(time));
//        new DetectEntrySignal2Trader().testCreateOrder("BNBUSDT");
//        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1M);
//        new DetectEntrySignal2Trader().createOrderBuyRequest(symbol, tickers.get(tickers.size() - 1),
//                MarketLevelChange.DCA_ORDER);
//        System.out.println(getOrderMarketLevelRunning());
    }


    public void start() throws InterruptedException, ParseException {
        initData();
        startThreadDetectMarketLevel2Trader();
    }


    public void startThreadDetectMarketLevel2Trader() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadDetectMarketLevel2Trader");
            LOG.info("Start thread ThreadDetectMarketLevel2Trader");
            while (true) {
                if (isTimeProcessData()) {
                    try {
                        executorService.execute(() -> checkMarketLevelChange2Trade());
                    } catch (Exception e) {
                        LOG.error("ERROR during ThreadDetectMarketLevel2Trader: {}", e);
                        e.printStackTrace();
                    }
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND / 10);
                } catch (InterruptedException ex) {
                    ex.printStackTrace();
                }
            }
        }).start();
    }

    private void checkMarketLevelChange2Trade() {
        try {
            LOG.info("Start check level change of market for trade! {}", new Date());
            Map<String, KlineObjectSimple> symbol2FinalTicker = new HashMap<>();
            TreeMap<Double, String> rateDown15M2Symbols = new TreeMap<>();
            TreeMap<Double, String> rateUp15M2Symbols = new TreeMap<>();
            TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
            TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
            Map<String, Double> symbol2Max15m = new HashMap<>();

            ConcurrentHashMap<String, List<KlineObjectSimple>> symbol2LastTickers = ListenAllTicker.getInstance().getAllTicker();
            List<KlineObjectSimple> btcTickers = symbol2LastTickers.get(Constants.SYMBOL_PAIR_BTC);
            KlineObjectSimple btcTicker = btcTickers.get(btcTickers.size() - 1);
            Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
            Double btcMax15M = null;

            LOG.info("Btc ticker size: {}", symbol2LastTickers.get(Constants.SYMBOL_PAIR_BTC).size());
            long time = btcTicker.startTime.longValue();
//            symbol2Sell.clear();
            for (Map.Entry<String, List<KlineObjectSimple>> entry : symbol2LastTickers.entrySet()) {
                try {
                    String symbol = entry.getKey();
                    if (Constants.diedSymbol.contains(symbol)) {
                        continue;
                    }
                    List<KlineObjectSimple> tickers = entry.getValue();
                    KlineObjectSimple ticker = tickers.get(tickers.size() - 1);
                    if (!Utils.isTickerAvailable(ticker)) {
                        continue;
                    }
                    if (MarketBigChangeDetector.isSellingExhausted(tickers, symbol)) {
                        symbolSellingExhausted.put(symbol, time);
                    }
                    symbol2FinalTicker.put(symbol, ticker);
                    Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                    // pass symbol big dump(delist/waring/monitor...)
                    if (btcRateChange > -0.004 && rateChange < -0.15) {
                        continue;
                    }
                    if (rateChange > 0.3) {
                        continue;
                    }
                    rateDown2Symbols.put(rateChange, symbol);
                    rateUp2Symbols.put(-rateChange, symbol);
                    Double priceMax = null;
                    Double priceMin = null;
                    for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                        int index = tickers.size() - i - 1;
                        if (index >= 0) {
                            KlineObjectSimple kline = tickers.get(index);
                            if (priceMax == null || priceMax < kline.maxPrice) {
                                priceMax = kline.maxPrice;
                            }
                            if (priceMin == null || priceMin > kline.minPrice) {
                                priceMin = kline.minPrice;
                            }
                        }
                    }

                    if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
                        btcMax15M = priceMax;
                    }
                    rateDown15M2Symbols.put(Utils.rateOf2Double(tickers.get(tickers.size() - 1).priceClose, priceMax), symbol);
                    symbol2Max15m.put(symbol, priceMax);
                    rateUp15M2Symbols.put(-Utils.rateOf2Double(tickers.get(tickers.size() - 1).priceClose, priceMin), symbol);

                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            Double rateDownAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown2Symbols, 100);
            Double rateUpAvg = -MarketBigChangeDetector.calRateChangeAvg(rateUp2Symbols, 100);
            Double rateDown15MAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown15M2Symbols, 100);
            MarketRateChange marketRate = new MarketRateChange(rateDownAvg, rateDown15MAvg, rateUpAvg);
            Double rateBtcDown15M = Utils.rateOf2Double(btcTicker.priceClose, btcMax15M);
            MarketLevelChange levelChange = MarketBigChangeDetector.getMarketStatus1M(rateDownAvg, rateUpAvg, btcRateChange
                    , rateDown15MAvg);
            boolean isTrendBuyWithBtc = TrendDetector.isBtcTrendBuyProduction(time);
            boolean isTrendBuyWithETH = TrendDetector.isETHTrendBuyProduction(time);
            LOG.info("Check level market: {} DownAvg: {}% UpAvg:{}% DownAvg15M:{}%  btcRate: {}% btcRate15M: {}% {}",
                    Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                    Utils.formatDouble(rateDownAvg * 100, 3),
                    Utils.formatDouble(rateUpAvg * 100, 3),
                    Utils.formatDouble(rateDown15MAvg * 100, 3),
                    Utils.formatDouble(btcRateChange * 100, 3),
                    Utils.formatDouble(rateBtcDown15M * 100, 3)
                    , levelChange);
            LOG.info("Market level change: {} level: {} symbols:{}", Utils.normalizeDateYYYYMMDDHHmm(time),
                    levelChange, symbol2FinalTicker.size());

            Set<String> symbolLocked = new HashSet<>();
            symbolLocked.addAll(BudgetManager.getInstance().symbol2Pos.keySet());

            if (levelChange != null) {
                Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                        || levelChange.equals(MarketLevelChange.SMALL_UP)
                        || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                        || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                ) {
                    numberOrder = numberOrder / 2;
                }
                Set<String> symbol2BUY = MarketBigChangeDetector.getTopSymbol(rateDown15M2Symbols,
                        numberOrder, symbol2FinalTicker, symbolLocked);

                if (symbol2BUY.size() < numberOrder) {
                    LOG.info("Not symbol 2 buy: {} {} ", levelChange, Utils.normalizeDateYYYYMMDDHHmm(time));
                }

                symbol2BUY.addAll(addSpecialSymbol(symbol2FinalTicker));
                LOG.info("Level: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                        levelChange, symbol2BUY);
                for (String symbol : symbol2BUY) {
                    try {
                        KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                        List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                        // ================== GỌI HÀM LỌC DUY NHẤT ==================
                        if (TradeUtils.shouldAvoidEntry(symbol, tickers, isTrendBuyWithETH)) {
                            continue; // Bỏ qua nếu có rủi ro
                        }
                        createOrderBuyRequest(symbol, ticker, levelChange, symbol2Max15m.get(symbol), marketRate,
                                isTrendBuyWithBtc, isTrendBuyWithETH);
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
                try {

                    List<String> symbolDcaLevel = DcaProcessor.getDCAProduction(levelChange, System.currentTimeMillis(),
                            BudgetManager.getInstance().getBudget(), BudgetManager.getInstance().symbol2Pos, isTrendBuyWithBtc,
                            isTrendBuyWithETH);
                    for (String symbol : symbolDcaLevel) {
                        KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                        PositionRisk position = BudgetManager.getInstance().symbol2Pos.get(symbol);
                        if (position != null) {
                            MarketLevelChange levelDca;
                            if (PositionHelper.callMargin(position) < BudgetManager.getInstance().getBudget()) {
                                levelDca = MarketLevelChange.DCA_LEVEL1;
                            } else {
                                levelDca = MarketLevelChange.DCA_LEVEL2;
                            }
                            createOrderBuyRequest(symbol, ticker, levelDca,
                                    symbol2Max15m.get(symbol), marketRate, isTrendBuyWithBtc, isTrendBuyWithETH);
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            // dca buy
            if (MarketBigChangeDetector.isDcaAlt(rateDown15MAvg, rateDownAvg, rateUpAvg)) {
                List<String> symbolDcaLossBig = DcaProcessor.getDCAProduction(null, System.currentTimeMillis(),
                        BudgetManager.getInstance().getBudget(), BudgetManager.getInstance().symbol2Pos, isTrendBuyWithBtc, isTrendBuyWithETH);
                if (!symbolDcaLossBig.isEmpty()) {
                    LOG.info("DCA big loss:{}", symbolDcaLossBig);
                }
                for (String symbol : symbolDcaLossBig) {
                    KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                    if (Utils.isTickerAvailable(ticker)) {
                        PositionRisk position = BudgetManager.getInstance().symbol2Pos.get(symbol);
                        if (position != null) {
                            MarketLevelChange levelDca;
                            if (PositionHelper.callMargin(position) < BudgetManager.getInstance().getBudget()) {
                                levelDca = MarketLevelChange.DCA_LEVEL1;
                            } else {
                                levelDca = MarketLevelChange.DCA_LEVEL2;
                            }
                            createOrderBuyRequest(symbol, ticker, levelDca,
                                    symbol2Max15m.get(symbol), marketRate, isTrendBuyWithBtc, isTrendBuyWithETH);

                        }
                    }
                }
            }
            // funding fee trade
            time2RateDown15MAvg.put(time, rateDown15MAvg);
            while (time2RateDown15MAvg.size() > 60) {
                time2RateDown15MAvg.remove(time2RateDown15MAvg.firstKey());
            }
            Double minRate15Min30M = Collections.min(time2RateDown15MAvg.values());
            if (MarketBigChangeDetector.isFundingFeeTrade(rateDown15MAvg, rateDownAvg, rateUpAvg,
                    minRate15Min30M, isTrendBuyWithETH)) {
                Set<String> symbolBuyFundingFee = new HashSet<>();
                symbolBuyFundingFee.addAll(FundingFeeManagerProduction.getInstance().fundingBuy);
                symbolBuyFundingFee.removeAll(BudgetManager.getInstance().symbol2Pos.keySet());
                for (String symbol : symbolBuyFundingFee) {
                    KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                    if (!Utils.isTickerAvailable(ticker)) {
                        continue;
                    }
                    Double priceMax15M = symbol2Max15m.get(symbol);
                    Double rateTicker = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                    Double rateMax15M = Utils.rateOf2Double(ticker.priceClose, priceMax15M);

                    if (MarketBigChangeDetector.isRateChangeAvailable2Trade(rateTicker, rateMax15M)) {
                        LOG.info("Funding buy {} {} close: {} rate:{} max15M: {} tickers:{}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time),
                                ticker.priceClose, rateTicker, rateMax15M, symbol2LastTickers.get(symbol).size());
                        List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                        // ================== GỌI HÀM LỌC DUY NHẤT ==================
                        if (TradeUtils.shouldAvoidEntry(symbol, tickers, isTrendBuyWithETH)) {
                            continue; // Bỏ qua nếu có rủi ro
                        }
                        createOrderBuyRequest(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY,
                                symbol2Max15m.get(symbol), marketRate, isTrendBuyWithBtc, isTrendBuyWithETH);
                    }
                }
                // ========== LOGIC CHO TÍN HIỆU FUNDING ÂM CỰC ĐOAN ==========
                Set<String> extremeFundingSymbols = FundingFeeManagerProduction.getInstance().extremeNegative;
                for (String symbol : extremeFundingSymbols) {
                    // Chỉ vào lệnh nếu chưa có vị thế đang chạy cho symbol này
                    if (!BudgetManager.getInstance().symbol2Pos.containsKey(symbol) && symbolSellingExhausted.containsKey(symbol)) {
                        KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                        if (!Utils.isTickerAvailable(ticker)) {
                            continue;
                        }
                        if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) > -0.01) {
                            continue;
                        }
                        if (symbolSellingExhausted.get(symbol) < time - Configs.FUNDING_TIME_EXTREME) {
                            LOG.info("SellingExhausted of {} over time: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time),
                                    Utils.normalizeDateYYYYMMDDHHmm(symbolSellingExhausted.get(symbol)));
                            symbolSellingExhausted.remove(symbol);
                            continue;
                        }
                        List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                        // ================== GỌI HÀM LỌC DUY NHẤT ==================
                        if (TradeUtils.shouldAvoidEntry(symbol, tickers, isTrendBuyWithETH)) {
                            continue; // Bỏ qua nếu có rủi ro
                        }
                        Double priceMax15M = symbol2Max15m.get(symbol);
                        Double rateTicker = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                        Double rateMax15M = Utils.rateOf2Double(ticker.priceClose, priceMax15M);
                        if (rateTicker > -0.01 && rateMax15M > -0.04) {
                            continue;
                        }
                        createOrderBuyRequest(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY_SPECIAL,
                                symbol2Max15m.get(symbol), marketRate, isTrendBuyWithBtc, isTrendBuyWithETH);
                    }
                }
            }

            // btc trend reverse
            Double rateTrendReverse = MarketBigChangeDetector.isBtcTrendReverse(btcTickers);
            if (rateTrendReverse != null && rateTrendReverse >= Configs.BTC_TREND_REVERSE_RATE_MIN_TRADE) {
                levelChange = MarketLevelChange.BTC_TREND_REVERSE;
                Set<String> symbol2BUY = new HashSet<>();
                for (String symbol : Constants.specialSymbol) {

                    Double rateLoss = calRateLoss(symbol);
                    Double budget = BudgetManager.getInstance().getBudget();
                    Double marginOfSym = calMarginRunning(symbol);
                    KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                    OrderTargetInfo order = getOrderInfo(symbol);

                    boolean isDcaSpecialSymbol = true;
                    if (order != null) {
                        isDcaSpecialSymbol = MarketBigChangeDetector.isDcaWithBtcReverse(rateLoss,
                                budget, marginOfSym, ticker.priceClose, order.priceEntry);
                    }
                    if (isDcaSpecialSymbol) {
                        symbol2BUY.add(symbol);
                    }
                }
                LOG.info("Level: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()), levelChange, symbol2BUY);
                for (String symbol : symbol2BUY) {
                    KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                    createOrderBuyRequest(symbol, ticker, levelChange, symbol2Max15m.get(symbol), marketRate, isTrendBuyWithBtc, isTrendBuyWithETH);
                }
            }
            StorageSnappy.writeObject2File(FILE_STORAGE_TIME_RATE_DOWN15M, time2RateDown15MAvg);
            StorageSnappy.writeObject2File(FILE_STORAGE_SELLING_EXHAUSTED, symbolSellingExhausted);
            StorageSnappy.writeObject2File("storage/data/rateMax15M/" + Utils.normalizeDateYYYYMMDD(time)
                    + "/" + time, rateDown15M2Symbols);
            StorageSnappy.writeObject2File("storage/data/rateDown1M/" + Utils.normalizeDateYYYYMMDD(time)
                    + "/" + time, rateDown2Symbols);
        } catch (Exception e) {
            e.printStackTrace();
        }
        LOG.info("Finish check level change of market 2 trade: {}", new Date());
    }

    public boolean isBtcTrendSell(Long time) {
        Double maDif1d = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        Double maDif4h = SimpleMovingAverage4hManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        if ((maDif4h != null && maDif4h < 0)
                || (maDif1d != null && maDif1d < 0)) {
            return true;
        }
        return false;
    }


    private OrderTargetInfo getOrderInfo(String symbol) {
        try {
            String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
            OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
            return order;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }


    private Set<String> addSpecialSymbol(Map<String, KlineObjectSimple> symbol2Ticker) {
        Set<String> symbol2Checks = new HashSet<>();
        Set<String> symbol2Trade = new HashSet<>();
        symbol2Checks.addAll(Constants.specialSymbol);
        symbol2Checks.addAll(Constants.stableSymbol);
        symbol2Checks.removeAll(BudgetManager.getInstance().symbol2Pos.keySet());
        for (String symbol : symbol2Checks) {
            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
            if (ticker != null && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.013) {
                symbol2Trade.add(symbol);
            }
        }
        return symbol2Trade;
    }

    public void createOrderBuyRequest(String symbol, KlineObjectSimple ticker,
                                      MarketLevelChange levelChange, Double priceMax15M, MarketRateChange marketRate,
                                      boolean isTrendBuyWithBtc, boolean isTrendBuyWithETH) {

        long time = ticker.startTime.longValue();
        Double marginRunning = BudgetManager.getInstance().marginRunning;
        Double balanceBasic = BudgetManager.getInstance().balanceBasic;
        Double budget = BudgetManager.getInstance().getBudget();

        budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange, isTrendBuyWithBtc, isTrendBuyWithETH);
        if (budget == null) {
            LOG.info("Not trade because over capital: {} {} {}", symbol, levelChange,
                    Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            return;
        }

        Double priceEntry = ticker.priceClose;
        Double quantity = Utils.calQuantity(budget, BudgetManager.getInstance().getLeverage(), priceEntry, symbol);
        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
            Double minBtcTrade = 0.002;
            if (quantity < minBtcTrade) {
                quantity = minBtcTrade;
            }
        }
        LOG.info("Market level:{} {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                levelChange, symbol, budget, quantity, ticker.priceClose);
        if (quantity != null && quantity != 0) {
            OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
                    null, quantity, BudgetManager.getInstance().getLeverage(), symbol, ticker.startTime.longValue(),
                    ticker.startTime.longValue(), OrderSide.BUY, Constants.TRADING_TYPE_VOLUME_MINI);
            orderTrade.marketLevel = levelChange;
            orderTrade.priceTP = priceMax15M;
            LOG.info("Push redis order: {} {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                    symbol, levelChange, budget.longValue(), quantity, ticker.priceClose);
            RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
            writeOrder2File(orderTrade, ticker, marketRate, priceMax15M);
        } else {
            LOG.info("{} {} quantity false", symbol, quantity);
        }
    }

    private void writeOrder2File(OrderTargetInfo orderTrade, KlineObjectSimple ticker, MarketRateChange marketRate, Double priceMax15M) {
        try {
            Map<Object, Object> data = new HashMap<>();
            data.put("ticker", ticker);
            data.put("order", orderTrade);
            data.put("marketRate", marketRate);
            data.put("max15M", priceMax15M);
//            data.put("symbol2Sell", symbol2Sell);
            data.put("fundingBuy", FundingFeeManagerProduction.getInstance().fundingBuy);
            data.put("fundingSell", FundingFeeManagerProduction.getInstance().fundingSell);
            String fileName = "storage/data/order/";
            fileName += Utils.normalizeDateYYYYMMDD(ticker.startTime.longValue());
            fileName += "/";
            fileName += orderTrade.symbol + "-" + ticker.startTime.longValue();
            StorageSnappy.writeObject2File(fileName, data);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static Double calMarginRunning(String symbol) {
        if (BudgetManager.getInstance().symbol2Margin.get(symbol) != null) {
            return BudgetManager.getInstance().symbol2Margin.get(symbol);
        }
        return 0d;
    }

    public static Double calRateLoss(String symbol) {
        PositionRisk pos = BudgetManager.getInstance().symbol2Pos.get(symbol);
        if (pos != null) {
            return PositionHelper.calRateLoss(pos);
        }
        return 1d;
    }

    public boolean isTimeProcessData() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 0 && miniSecond < 100;
    }

    private void initData() {
        SimpleMovingAverageDayManagerProduction.getInstance();
        SimpleMovingAverage4hManagerProduction.getInstance();
        if (new File(FILE_STORAGE_SELLING_EXHAUSTED).exists()) {
            symbolSellingExhausted = (ConcurrentHashMap<String, Long>) StorageSnappy.readObjectFromFile(FILE_STORAGE_SELLING_EXHAUSTED);
        }
        if (new File(FILE_STORAGE_TIME_RATE_DOWN15M).exists()) {
            time2RateDown15MAvg = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(FILE_STORAGE_TIME_RATE_DOWN15M);
        }
        ListenAllTicker.getInstance();
    }


}
