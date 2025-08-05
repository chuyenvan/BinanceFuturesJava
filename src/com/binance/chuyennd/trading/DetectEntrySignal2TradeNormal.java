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
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.helper.PositionHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
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
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);

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
            Map<String, KlineObjectNumber> symbol2FinalTicker = new HashMap<>();
            TreeMap<Double, String> rateDown15M2Symbols = new TreeMap<>();
            TreeMap<Double, String> rateUp15M2Symbols = new TreeMap<>();
            TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
            TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
            Map<String, Double> symbol2Max15m = new HashMap<>();
            Map<String, Double> symbol2Max4h = new HashMap<>();
            Map<String, Double> symbol2Min4h = new HashMap<>();
            Map<String, Double> symbol2Min15m = new HashMap<>();
            ConcurrentHashMap<String, List<KlineObjectNumber>> symbol2Tickers = ListenAllTicker.getInstance().getAllTicker();
            List<KlineObjectNumber> btcTickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BTC);
            KlineObjectNumber btcTicker = btcTickers.get(btcTickers.size() - 1);
            Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
            Double btcMax15M = null;

            long time = btcTicker.startTime.longValue();
//            symbol2Sell.clear();
            for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Tickers.entrySet()) {
                try {
                    String symbol = entry.getKey();
                    if (Constants.diedSymbol.contains(symbol)) {
                        continue;
                    }
                    List<KlineObjectNumber> tickers = entry.getValue();
                    KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
                    if (!Utils.isTickerAvailable(ticker)) {
                        continue;
                    }
                    symbol2FinalTicker.put(symbol, ticker);
                    Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                    // pass symbol big dump(delist/waring/monitor...)
                    if (btcRateChange > -0.004 && rateChange < -0.15) {
                        continue;
                    }
                    rateDown2Symbols.put(rateChange, symbol);
                    rateUp2Symbols.put(-rateChange, symbol);
                    Double priceMax = null;
                    Double priceMin = null;
                    for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                        int index = tickers.size() - i - 1;
                        if (index >= 0) {
                            KlineObjectNumber kline = tickers.get(index);
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
                    symbol2Min15m.put(symbol, priceMin);
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


            // dca buy
            List<String> symbolDcaLossBig = getDCA(null);
            if (!symbolDcaLossBig.isEmpty()) {
                LOG.info("DCA big loss:{}", symbolDcaLossBig);
            }
            for (String symbol : symbolDcaLossBig) {
                KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                if (Utils.isTickerAvailable(ticker)) {
                    PositionRisk position = BudgetManager.getInstance().symbol2Pos.get(symbol);
                    if (position != null) {
                        if (PositionHelper.callMargin(position) < 5 * BudgetManager.getInstance().getBudget()) {
                            createOrderBuyRequest(symbol, ticker, MarketLevelChange.DCA_LEVEL1,
                                    symbol2Max15m.get(symbol), marketRate);
                        } else {
                            LOG.info("Not dca because over budget:{} {}% {}/{}", symbol,
                                    Utils.formatPercent(PositionHelper.calRateLoss(position)),
                                    PositionHelper.callMargin(position).longValue(),
                                    5 * BudgetManager.getInstance().getBudget().longValue());
                        }
                    }
                }
            }

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
                List<String> symbol2BUY = MarketBigChangeDetector.getTopSymbol(rateDown15M2Symbols,
                        numberOrder, symbol2FinalTicker, symbolLocked);

                if (symbol2BUY.size() < numberOrder) {
                    LOG.info("Not symbol 2 buy: {} {} ", levelChange, Utils.normalizeDateYYYYMMDDHHmm(time));
                }

                symbol2BUY = addSpecialSymbol(symbol2BUY, symbol2FinalTicker);
                LOG.info("Level: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                        levelChange, symbol2BUY);
                for (String symbol : symbol2BUY) {
                    try {
                        KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                        createOrderBuyRequest(symbol, ticker, levelChange, symbol2Max15m.get(symbol), marketRate);
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
                try {
                    List<String> symbolDcaLevel = getDCA(levelChange);
                    for (String symbol : symbolDcaLevel) {
                        KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                        OrderTargetInfo orderRunning = getOrderInfo(symbol);
                        PositionRisk position = BudgetManager.getInstance().symbol2Pos.get(symbol);
                        if (position != null) {
                            if (orderRunning != null && orderRunning.priceEntry < ticker.priceClose
                                    && PositionHelper.callMargin(position) < 2 * BudgetManager.getInstance().getBudget()) {
                                LOG.info("Not dca {} {} {}", symbol, orderRunning.priceEntry, ticker.priceClose);
                                continue;
                            }
                            if (PositionHelper.callMargin(position) < BudgetManager.getInstance().getBudget()
                                    && BudgetManager.getInstance().marginRunning < 100 * BudgetManager.getInstance().getBudget()) {
                                createOrderBuyRequest(symbol, ticker, MarketLevelChange.DCA_LEVEL1,
                                        symbol2Max15m.get(symbol), marketRate);
                            } else {
                                createOrderBuyRequest(symbol, ticker, MarketLevelChange.DCA_LEVEL2,
                                        symbol2Max15m.get(symbol), marketRate);
                            }
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }

            // funding fee trade
            if (rateDown15MAvg < -0.018
                    || rateUpAvg > 0.006
                    || rateDownAvg < -0.006) {
                Set<String> symbolBuyFundingFee = new HashSet<>();
                symbolBuyFundingFee.addAll(FundingFeeManagerProduction.getInstance().fundingBuy);
                symbolBuyFundingFee.removeAll(BudgetManager.getInstance().symbol2Pos.keySet());
                for (String symbol : symbolBuyFundingFee) {
                    KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                    if (!Utils.isTickerAvailable(ticker)) {
                        continue;
                    }

                    Double priceMax15M = symbol2Max15m.get(symbol);
                    Double priceMin15M = symbol2Min15m.get(symbol);
                    Double rateTicker = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                    Double rateMax15M = Utils.rateOf2Double(ticker.priceClose, priceMax15M);
                    Double rateMax4h = 0.0;
                    Double priceMax4h = symbol2Max4h.get(symbol);
                    if (priceMax4h != null) {
                        rateMax4h = Utils.rateOf2Double(ticker.priceClose, priceMax4h);
                    }
                    Double rateMin4h = 0.0;
                    Double priceMin4h = symbol2Min4h.get(symbol);
                    if (priceMin4h != null) {
                        rateMin4h = Utils.rateOf2Double(priceMin4h, ticker.priceClose);
                    }
                    Double rateMin15M = 0.0;
                    if (priceMin15M != null) {
                        rateMin15M = Utils.rateOf2Double(priceMin15M, ticker.priceClose);
                    }
                    if (rateTicker < -0.013
                            || rateMax15M < -0.045
                            || (rateTicker < -0.006 && rateMax15M < -0.04)
                            || (rateTicker < -0.01 && rateMax15M < -0.035)
                            || (rateTicker < -0.01 && rateMin15M < -0.03)
                            || (rateTicker < -0.006 && rateMax4h < -0.1)
                            || (rateTicker < -0.01 && rateMin4h < -0.08)
                    ) {
                        LOG.info("Funding buy {} {} close: {} rate:{} max15M: {} min15M:{} max4h:{}" +
                                        " min4h:{} tickers:{}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time),
                                ticker.priceClose, rateTicker,
                                rateMax15M, rateMin15M, rateMax4h, rateMin4h, symbol2Tickers.get(symbol).size());
                        createOrderBuyRequest(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY,
                                symbol2Max15m.get(symbol), marketRate);
                    }


                }
            }

            // btc trend reverse
            Double rateTrendReverse = MarketBigChangeDetector.isBtcTrendReverse(btcTickers);
            if (rateTrendReverse != null && rateTrendReverse >= Configs.BTC_TREND_REVERSE_RATE_MIN_TRADE) {
                levelChange = MarketLevelChange.BTC_TREND_REVERSE;
                List<String> symbol2BUY = new ArrayList<>();
                for (String symbol : Constants.specialSymbol) {
                    if (BudgetManager.getInstance().symbolSell.contains(symbol)) {
                        continue;
                    }
                    if (calMarginRunning(symbol) > 2 * BudgetManager.getInstance().getBudget()) {
                        if (calMarginRunning(symbol) > 4 * BudgetManager.getInstance().getBudget()) {
                            KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                            OrderTargetInfo orderRunning = getOrderInfo(symbol);
                            if (ticker != null && orderRunning != null
                                    && Utils.rateOf2Double(ticker.priceClose, orderRunning.priceEntry) < -0.03) {
                                symbol2BUY.add(symbol);

                            }
                        } else {
                            if (calRateLoss(symbol) < -0.03 || calRateLoss(symbol) > 0.02) {
                                symbol2BUY.add(symbol);
                            }
                        }
                    } else {
                        if (calRateLoss(symbol) < -0.02 || calRateLoss(symbol) > 0.02) {
                            symbol2BUY.add(symbol);
                        }
                    }
                }
                LOG.info("Level: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()), levelChange, symbol2BUY);
                for (String symbol : symbol2BUY) {
                    KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                    createOrderBuyRequest(symbol, ticker, levelChange, symbol2Max15m.get(symbol), marketRate);
                }
            }
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

    public boolean isBtcTrendBuy(Long time) {
        Double maDif1d = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        Double maDif4h = SimpleMovingAverage4hManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        if ((maDif1d != null && maDif1d > 0)
                || (maDif4h != null && maDif4h > 0)) {
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


    public static List<String> getDCA(MarketLevelChange levelChange) {
        List<String> symbols = new ArrayList<>();
        Integer durationDca = null;
        Double rateLoss2Dca = null;
        Boolean isAll = false;
        if (levelChange == null) {
            durationDca = 1;
            rateLoss2Dca = -0.25;
        } else {
            if (levelChange.equals(MarketLevelChange.BIG_DOWN)) {
                isAll = true;
                durationDca = 8;
                rateLoss2Dca = -0.05;
            }
            if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                    || levelChange.equals(MarketLevelChange.BIG_UP)) {
                durationDca = 15;
                rateLoss2Dca = -0.08;
            }
            if (levelChange.equals(MarketLevelChange.MEDIUM_UP)
                    || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
            ) {
                durationDca = 15;
                rateLoss2Dca = -0.15;
            }
            if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
            ) {
                durationDca = 15;
                rateLoss2Dca = -0.2;
            }
        }

        if (rateLoss2Dca != null) {
            Map<String, PositionRisk> symbol2Pos = new HashMap<>();
            symbol2Pos.putAll(BudgetManager.getInstance().symbol2Pos);
            for (PositionRisk pos : symbol2Pos.values()) {
                Double rateLoss2DcaOfSym = rateLoss2Dca;
                MarketLevelChange level = BudgetManager.getInstance().symbol2Level.get(pos.getSymbol());
                if (!isAll) {
                    Double margin = PositionHelper.callMargin(pos);
                    rateLoss2DcaOfSym = BudgetManager.getInstance().callRate2DcaBuy(rateLoss2Dca, margin);
                }
                if (levelChange != null) {
                    LOG.info("Check DCA: {} {} {} {} {}", pos.getSymbol(), level, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                            PositionHelper.calRateLoss(pos), rateLoss2DcaOfSym);
                }
                if (pos != null
                        && pos.getPositionAmt().doubleValue() > 0
                        && PositionHelper.calRateLoss(pos) < rateLoss2DcaOfSym
                ) {
                    if (level != null
                            && (level.equals(MarketLevelChange.DCA_LEVEL2)
                            || level.equals(MarketLevelChange.DCA_LEVEL1))) {
                        if (System.currentTimeMillis() > pos.getUpdateTime() + durationDca * Utils.TIME_MINUTE) {
                            symbols.add(pos.getSymbol());
                        }
                    } else {
                        symbols.add(pos.getSymbol());
                    }
                }
            }
        }
        return symbols;
    }

    private List<String> addSpecialSymbol(List<String> symbol2BUY,
                                          Map<String, KlineObjectNumber> symbol2Ticker) {
        Set<String> symbol2Checks = new HashSet<>();
        if (BudgetManager.getInstance().marginRunning < 50 * BudgetManager.getInstance().getBudget()) {
            symbol2Checks.addAll(Constants.specialSymbol);
            symbol2Checks.addAll(Constants.stableSymbol);
            symbol2Checks.removeAll(BudgetManager.getInstance().symbol2Pos.keySet());
            symbol2Checks.removeAll(symbol2BUY);
        }
        for (String symbol : symbol2Checks) {
            KlineObjectNumber ticker = symbol2Ticker.get(symbol);
            if (ticker != null && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.013) {
                symbol2BUY.add(symbol);
            }
        }
        return symbol2BUY;
    }

    public void createOrderBuyRequest(String symbol, KlineObjectNumber ticker,
                                      MarketLevelChange levelChange, Double priceMax15M, MarketRateChange marketRate) {

        Double budget = BudgetManager.getInstance().getBudget();

        if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP)
                || levelChange.equals(MarketLevelChange.DCA_LEVEL1)
        ) {
            budget = budget / 2;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                || levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
                || levelChange.equals(MarketLevelChange.DCA_LEVEL2)
                || levelChange.equals(MarketLevelChange.FUNDING_FEE_BUY)
        ) {
            budget = budget / 3;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                || levelChange.equals(MarketLevelChange.SMALL_UP)
        ) {
            long time = ticker.startTime.longValue();
            if (isBtcTrendBuy(time)
                    || Constants.specialSymbol.contains(symbol)) {
                budget = budget / 4;
            } else {
                return;
            }
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

    private void writeOrder2File(OrderTargetInfo orderTrade, KlineObjectNumber ticker, MarketRateChange marketRate, Double priceMax15M) {
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

    private void createOrderSELLRequest(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange, Double priceMin15M,
                                        MarketRateChange marketRate) {

        Double budget = BudgetManager.getInstance().getBudgetSell();
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
                    ticker.startTime.longValue(), OrderSide.SELL, Constants.TRADING_TYPE_VOLUME_MINI);
            orderTrade.marketLevel = levelChange;
            orderTrade.priceTP = priceMin15M;
            RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
            writeOrder2File(orderTrade, ticker, marketRate, priceMin15M);
        } else {
            LOG.info("{} {} quantity false", symbol, quantity);
        }
    }


    public boolean isTimeProcessData() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 0 && miniSecond < 100;
    }

    private void initData() {
        Price4hManagerProduction.getInstance();
        SimpleMovingAverageDayManagerProduction.getInstance();
        SimpleMovingAverage4hManagerProduction.getInstance();
        ListenAllTicker.getInstance();
    }


}
