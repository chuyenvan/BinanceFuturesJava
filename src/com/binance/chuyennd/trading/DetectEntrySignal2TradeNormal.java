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
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.trading.grid.FundingFeeManagerProduction;
import com.binance.chuyennd.trading.grid.SimpleMovingAverage4hManagerProduction;
import com.binance.chuyennd.trading.grid.SimpleMovingAverageDayManagerProduction;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
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
import java.util.logging.Level;

/**
 * @author pc
 */
public class DetectEntrySignal2TradeNormal {

    public static final Logger LOG = LoggerFactory.getLogger(DetectEntrySignal2TradeNormal.class);
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    public BinanceOrderTradingManager orderManager = new BinanceOrderTradingManager();
    public Set<? extends String> allSymbol;
    //    public Set<String> symbolVolumeLower = new HashSet<>();

    public ConcurrentHashMap<String, List<KlineObjectNumber>> symbol2Tickers = new ConcurrentHashMap<>();

    public static void main(String[] args) throws InterruptedException, ParseException {
//        new DetectEntrySignal2Trader().getTickerBySymbol("QNTUSDT");
//        String symbol = "ALTUSDT";

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
            LOG.info("Start thread ThreadDetectMarketLevel2Trader  target: {}", Configs.RATE_TARGET);
            int counter = 0;
            while (true) {
                counter++;
                if (counter % 36000 == 0) {
                    allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
                    allSymbol.removeAll(Constants.diedSymbol);
                    allSymbol.remove(Constants.SYMBOL_PAIR_BTC);
                }
                if (isTimeGetData()) {
                    try {
                        LOG.info("Start get data of market! {}", new Date());
                        Long startTime = Utils.getMinute(System.currentTimeMillis() -
                                (Configs.NUMBER_TICKER_CAL_RATE_CHANGE + 5) * Utils.TIME_MINUTE);
                        allSymbol.remove(Constants.SYMBOL_PAIR_BTC);
                        for (String symbol : allSymbol) {
                            executorService.execute(() -> getTickerBySymbol(symbol, startTime));
                        }
                        executorService.execute(() -> getTickerBySymbol(Constants.SYMBOL_PAIR_BTC, startTime -
                                (Configs.BTC_TREND_REVERSE_DURATION - 20) * Utils.TIME_MINUTE));
                        executorService.execute(() -> orderManager.processManagerPosition());
                        executorService.execute(() -> checkMarketLevelChange2Trade());

                    } catch (Exception e) {
                        LOG.error("ERROR during ThreadDetectMarketLevel2Trader: {}", e);
                        e.printStackTrace();
                    }
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND / 10);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectEntrySignal2TradeNormal.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private void checkMarketLevelChange2Trade() {
        LOG.info("Start check data ticker for trade! {}", new Date());
        while (true) {
            if (symbol2Tickers.containsKey(Constants.SYMBOL_PAIR_BTC)) {
                try {
                    LOG.info("Start check level change of market for trade! {}", new Date());
                    Map<String, KlineObjectNumber> symbol2FinalTicker = new HashMap<>();
                    TreeMap<Double, String> rateDown15M2Symbols = new TreeMap<>();
                    TreeMap<Double, String> rateUp15M2Symbols = new TreeMap<>();
                    TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
                    TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
                    Map<String, Double> symbol2Max15m = new HashMap<>();

                    List<KlineObjectNumber> btcTickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BTC);
                    KlineObjectNumber btcTicker = btcTickers.get(btcTickers.size() - 1);
                    Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
                    Double btcMax15M = null;
                    List<String> symbol2Sell = new ArrayList<>();
                    long time = btcTicker.startTime.longValue();

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
                            if (btcRateChange > -0.002 && rateChange < -0.15) {
                                continue;
                            }
                            rateDown2Symbols.put(rateChange, symbol);
                            rateUp2Symbols.put(-rateChange, symbol);
                            Double priceMax = null;
                            Double minPrice = null;
                            for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                                int index = tickers.size() - i - 1;
                                if (index >= 0) {
                                    KlineObjectNumber kline = tickers.get(index);
                                    if (priceMax == null || priceMax < kline.maxPrice) {
                                        priceMax = kline.maxPrice;
                                    }
                                    if (minPrice == null || minPrice > kline.minPrice) {
                                        minPrice = kline.minPrice;
                                    }
                                }
                            }
                            Double rateMax = 0.1;
                            Double rateMin = 0.6;
                            Double priceMin2d = Price4hManagerProduction.getInstance().getPriceMinIn2D(symbol, time);
                            Double priceMax2d = Price4hManagerProduction.getInstance().getPriceMaxIn2D(symbol, time);

                            if (priceMin2d != null && Utils.rateOf2Double(ticker.priceClose, priceMin2d) > rateMin
                                    && priceMax2d != null && Utils.rateOf2Double(ticker.priceClose, priceMax2d) < -rateMax) {
                                LOG.info("SignalSell: {} {} {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time),
                                        priceMax2d, priceMin2d, ticker.priceClose);
                                symbol2Sell.add(symbol);
                            }

                            if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
                                btcMax15M = priceMax;
                            }
                            rateDown15M2Symbols.put(Utils.rateOf2Double(tickers.get(tickers.size() - 1).priceClose, priceMax), symbol);
                            symbol2Max15m.put(symbol, priceMax);
                            rateUp15M2Symbols.put(-Utils.rateOf2Double(tickers.get(tickers.size() - 1).priceClose, minPrice), symbol);

                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                    // sell
                    if (time == Utils.getTimeInterval15m(time)) {
                        if (!symbol2Sell.isEmpty()) {
                            Double maDif1d = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                            Double maDif4h = SimpleMovingAverage4hManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                            if ((maDif4h != null && maDif4h < 0)
                                    || (maDif1d != null && maDif1d < 0)) {
                                symbol2Sell.removeAll(FundingFeeManagerProduction.getInstance().fundingBuy);
                                for (String symbol : symbol2Sell) {
                                    KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                                    if (Utils.isTickerAvailable(ticker) && !BudgetManager.getInstance().symbolBuy.contains(symbol)
                                            && !BudgetManager.getInstance().symbolSell.contains(symbol)) {
                                        PositionRisk pos = BudgetManager.getInstance().symbol2Pos.get(symbol);
                                        if (pos == null) {
                                            createOrderSELLRequest(symbol, ticker, MarketLevelChange.ORDER_SELL);
                                        }
                                    }
                                }
                            }
                        }
                    }
                    // dca sell
                    Set<String> symbolSelling = new HashSet<>();
                    symbolSelling.addAll(BudgetManager.getInstance().symbolSell);
                    for (String symbol : symbolSelling) {
                        KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                        if (Utils.isTickerAvailable(ticker)) {
                            PositionRisk position = BudgetManager.getInstance().symbol2Pos.get(symbol);
                            if (position != null
                                    && position.getPositionAmt().doubleValue() < 0) {
                                Double rateDca = -1.0;
                                if (PositionHelper.callMargin(position) > BudgetManager.getInstance().getBudget()) {
                                    if (PositionHelper.callMargin(position) > 2 * BudgetManager.getInstance().getBudget()) {
                                        rateDca = -5.0;
                                    } else {
                                        rateDca = -3.0;
                                    }
                                }
                                if (PositionHelper.calRateLoss(position) < rateDca) {
                                    createOrderSELLRequest(symbol, ticker, MarketLevelChange.ORDER_SELL_DCA);
                                }
                            }
                        }
                    }
                    // dca buy
                    List<String> symbolDcaLossBig = getDCA(null);
                    LOG.info("DCA big loss:{}", symbolDcaLossBig);
                    for (String symbol : symbolDcaLossBig) {
                        KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                        if (Utils.isTickerAvailable(ticker)) {
                            PositionRisk position = BudgetManager.getInstance().symbol2Pos.get(symbol);
                            if (position != null) {
                                if (PositionHelper.callMargin(position) < 5 * BudgetManager.getInstance().getBudget()) {
                                    createOrderBuyRequest(symbol, ticker, MarketLevelChange.DCA_BIG_LOSS, symbol2Max15m.get(symbol));
                                } else {
                                    LOG.info("Not dca because over budget:{} {}% {}/{}", symbol,
                                            Utils.formatPercent(PositionHelper.calRateLoss(position)),
                                            PositionHelper.callMargin(position).longValue(),
                                            5 * BudgetManager.getInstance().getBudget().longValue());
                                }
                            }
                        }
                    }
                    Double rateDownAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown2Symbols, 50);
                    Double rateUpAvg = -MarketBigChangeDetector.calRateChangeAvg(rateUp2Symbols, 50);
                    Double rateDown15MAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown15M2Symbols, 50);
                    Double rateUp15MAvg = -MarketBigChangeDetector.calRateChangeAvg(rateUp15M2Symbols, 50);
                    Double rateBtcDown15M = Utils.rateOf2Double(btcTicker.priceClose, btcMax15M);
                    MarketLevelChange levelChange = MarketBigChangeDetector.getMarketStatus1M(rateDownAvg, rateUpAvg, btcRateChange
                            , rateDown15MAvg, rateUp15MAvg, rateBtcDown15M);
                    LOG.info("Check level market: {} DownAvg: {}% UpAvg:{}% DownAvg15M:{}%  UpAvg15M:{}% btcRate: {}% btcRate15M: {}% {}",
                            Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                            Utils.formatDouble(rateDownAvg * 100, 3), Utils.formatDouble(rateUpAvg * 100, 3),
                            Utils.formatDouble(rateDown15MAvg * 100, 3), Utils.formatDouble(rateUp15MAvg * 100, 3),
                            Utils.formatDouble(btcRateChange * 100, 3), Utils.formatDouble(rateBtcDown15M * 100, 3)
                            , levelChange);
                    LOG.info("Market level change: {} level: {} symbols:{}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                            levelChange, symbol2FinalTicker.size());

                    Set<String> symbolLocked = new HashSet<>();
                    symbolLocked.addAll(symbol2Sell);
                    symbolLocked.addAll(BudgetManager.getInstance().marginBig);
                    symbolLocked.addAll(BudgetManager.getInstance().symbol2Pos.keySet());
                    if (rateUpAvg > 0.008
                            && BudgetManager.getInstance().symbolSell.size() < 50) {
                        // quick sell
                        Double maDif1d = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                        Double maDif4h = SimpleMovingAverage4hManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                        if ((maDif4h != null && maDif4h < 0)
                                || (maDif1d != null && maDif1d < 0)
                        ) {
                            symbolLocked.addAll(FundingFeeManagerProduction.getInstance().fundingBuy);
                            List<String> symbol2SELL = MarketBigChangeDetector.getTopSymbol(rateUp15M2Symbols,
                                    1, symbol2FinalTicker, symbolLocked);
                            if (symbol2SELL.size() < 1) {
                                LOG.info("Not symbol 2 sell: {} {} ", rateUp15MAvg, Utils.normalizeDateYYYYMMDDHHmm(time));
                            }
                            for (String symbol : symbol2SELL) {
                                KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                                if (!Utils.isTickerAvailable(ticker)) {
                                    continue;
                                }
                                createOrderSELLRequest(symbol, ticker, MarketLevelChange.ORDER_SELL_QUICK);
                            }
                        }
                    }


                    if (levelChange != null) {
                        Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                                || levelChange.equals(MarketLevelChange.SMALL_UP)
                                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                                || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                                || levelChange.equals(MarketLevelChange.TINY_DOWN)
                                || levelChange.equals(MarketLevelChange.TINY_UP)
                        ) {
                            numberOrder = numberOrder / 2;
                        }
                        List<String> symbol2BUY = MarketBigChangeDetector.getTopSymbol(rateDown15M2Symbols,
                                numberOrder, symbol2FinalTicker, symbolLocked);

                        if (symbol2BUY.size() < numberOrder) {
                            LOG.info("Not symbol 2 buy: {} {} ", levelChange, Utils.normalizeDateYYYYMMDDHHmm(time));
                        }

                        symbol2BUY = addSpecialSymbol(symbol2BUY, levelChange, symbol2FinalTicker);
                        LOG.info("Level: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()), levelChange, symbol2BUY);
                        for (String symbol : symbol2BUY) {
                            try {
                                KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                                createOrderBuyRequest(symbol, ticker, levelChange, symbol2Max15m.get(symbol));
                            } catch (Exception e) {
                                e.printStackTrace();
                            }
                        }
                        try {
                            List<String> symbolDcaLevel = getDCA(levelChange);
                            for (String symbol : symbolDcaLevel) {
                                KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                                OrderTargetInfo orderRunning = getOrderInfo(symbol);
                                if (orderRunning != null && orderRunning.priceEntry < ticker.priceClose) {
                                    LOG.info("Not dca {} {} {}", symbol, orderRunning.priceEntry, ticker.priceClose);
                                    continue;
                                }
                                PositionRisk position = BudgetManager.getInstance().symbol2Pos.get(symbol);
                                if (position != null
                                        && PositionHelper.callMargin(position) < 5 * BudgetManager.getInstance().getBudget()) {
                                    createOrderBuyRequest(symbol, ticker, MarketLevelChange.DCA_ORDER, symbol2Max15m.get(symbol));
                                } else {
                                    LOG.info("Not dca because over budget:{} {}% {}/{}", symbol, Utils.formatPercent(PositionHelper.calRateLoss(position)),
                                            PositionHelper.callMargin(position).longValue(),
                                            5 * BudgetManager.getInstance().getBudget().longValue());
                                }
                            }
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                    // funding fee trade
                    Set<String> symbolBuyFundingFee = new HashSet<>();
                    symbolBuyFundingFee.addAll(FundingFeeManagerProduction.getInstance().fundingBuy);
                    symbolBuyFundingFee.removeAll(BudgetManager.getInstance().symbol2Pos.keySet());
                    for (String symbol : symbolBuyFundingFee) {
                        KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                        if (!Utils.isTickerAvailable(ticker)) {
                            continue;
                        }
                        if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.013) {
                            createOrderBuyRequest(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY, symbol2Max15m.get(symbol));
                        } else {
                            Double priceMax15M = symbol2Max15m.get(symbol);
                            if (priceMax15M != 0
                                    && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.005
                                    && Utils.rateOf2Double(ticker.priceClose, priceMax15M) < -0.05) {
                                createOrderBuyRequest(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY, symbol2Max15m.get(symbol));
                            }
                        }
                    }
                    Set<String> symbolSellFundingFee = new HashSet<>();
                    symbolSellFundingFee.addAll(FundingFeeManagerProduction.getInstance().fundingSell);
                    symbolSellFundingFee.removeAll(BudgetManager.getInstance().symbol2Pos.keySet());
                    for (String symbol : symbolSellFundingFee) {
                        KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                        if (!Utils.isTickerAvailable(ticker)) {
                            continue;
                        }
                        if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) > 0.015) {
                            createOrderSELLRequest(symbol, ticker, MarketLevelChange.FUNDING_FEE_SELL);
                        }
                    }
                    // btc trend reverse
                    boolean isBtcReverse = false;
                    Double rateTrendReverse = MarketBigChangeDetector.isBtcTrendReverse(btcTickers);
                    if (rateTrendReverse != null && rateTrendReverse >= Configs.BTC_TREND_REVERSE_RATE_MIN_TRADE) {
                        isBtcReverse = true;
                    } else {
                        // fixbug detect reverse production error
                        btcTickers.remove(btcTickers.size() - 1);
                        rateTrendReverse = MarketBigChangeDetector.isBtcTrendReverse(btcTickers);
                        if (rateTrendReverse != null && rateTrendReverse >= Configs.BTC_TREND_REVERSE_RATE_MIN_TRADE) {
                            // check last time not btc trend reverse -> btc trend reverse
                            String finalTimeTrendReverse = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_MARKET_LEVEL_FINAL,
                                    MarketLevelChange.BTC_TREND_REVERSE.toString());
                            if (finalTimeTrendReverse == null || Long.parseLong(finalTimeTrendReverse) < btcTickers.get(btcTickers.size() - 1).startTime.longValue()) {
                                LOG.info("Fixbug btc trend reverse error {} {}",
                                        Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()),
                                        Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()));
                                isBtcReverse = true;
                            }
                        }
                    }
                    if (isBtcReverse) {
                        levelChange = MarketLevelChange.BTC_TREND_REVERSE;
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_MARKET_LEVEL_FINAL,
                                MarketLevelChange.BTC_TREND_REVERSE.toString(), String.valueOf(btcTicker.startTime.longValue()));
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
                                            && ticker.priceClose < orderRunning.priceEntry) {
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
                            createOrderBuyRequest(symbol, ticker, levelChange, symbol2Max15m.get(symbol));
                        }

                    }
                    Storage.writeObject2File("storage/data/rateMax15M/" + Utils.normalizeDateYYYYMMDD(time)
                            + "/" + time, rateDown15M2Symbols);
                    Storage.writeObject2File("storage/data/rateDown1M/" + Utils.normalizeDateYYYYMMDD(time)
                            + "/" + time, rateDown2Symbols);
                } catch (Exception e) {
                    e.printStackTrace();
                }
                // exit while true
                LOG.info("Symbol not ticker: {} {}", allSymbol.size(), symbol2Tickers.size());
                symbol2Tickers.clear();
                break;
            }
            try {
                Thread.sleep(Utils.TIME_SECOND / 10);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        LOG.info("Finish check level change of market 2 trade: {}", new Date());
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
            rateLoss2Dca = -0.3;
        } else {
            if (levelChange.equals(MarketLevelChange.BIG_DOWN)) {
                isAll = true;
                rateLoss2Dca = -0.05;
                durationDca = 8;
            }
            if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                    || levelChange.equals(MarketLevelChange.BIG_UP)) {
                rateLoss2Dca = -0.08;
                durationDca = 15;
            }
        }

        if (rateLoss2Dca != null) {
            Map<String, PositionRisk> symbol2Pos = new HashMap<>();
            symbol2Pos.putAll(BudgetManager.getInstance().symbol2Pos);
            for (PositionRisk pos : symbol2Pos.values()) {
                if (!isAll && Constants.specialSymbol.contains(pos.getSymbol())) {
                    continue;
                }
                Double rateLoss2DcaOfSym = rateLoss2Dca;
                MarketLevelChange level = BudgetManager.getInstance().symbol2Level.get(pos.getSymbol());
                if (!isAll && PositionHelper.callMargin(pos) >= BudgetManager.getInstance().getBudget()) {
                    rateLoss2DcaOfSym = -0.5;
                }
                if (levelChange != null) {
                    LOG.info("Check DCA: {} {} {} {} {}", pos.getSymbol(), level, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                            PositionHelper.calRateLoss(pos), rateLoss2DcaOfSym);
                }
                if (pos != null
                        && pos.getPositionAmt().doubleValue() > 0
                        && PositionHelper.calRateLoss(pos) < rateLoss2DcaOfSym
                ) {
                    if (level != null && level.equals(MarketLevelChange.DCA_ORDER)) {
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

    private List<String> addSpecialSymbol(List<String> symbol2BUY, MarketLevelChange levelChange,
                                          Map<String, KlineObjectNumber> symbol2Ticker) {
        if (levelChange != null && (levelChange.equals(MarketLevelChange.BIG_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN))
        ) {
            Set<String> symbol2Checks = new HashSet<>();
            if (BudgetManager.getInstance().marginRunning < 30 * BudgetManager.getInstance().getBudget()) {
                symbol2Checks.addAll(Constants.specialSymbol);
                symbol2Checks.addAll(Constants.stableSymbol);
            }
            for (String symbol : symbol2Checks) {
                if (calMarginRunning(symbol) < 3 * BudgetManager.getInstance().getBudget()) {
                    KlineObjectNumber ticker = symbol2Ticker.get(symbol);
                    if (ticker != null && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.015) {
                        symbol2BUY.add(symbol);
                    }
                }
            }
        }
        return symbol2BUY;
    }

    public static void createOrderBuyRequest(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange, Double priceMax15M) {

        Double budget = BudgetManager.getInstance().getBudget();

        if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP)
                || levelChange.equals(MarketLevelChange.DCA_BIG_LOSS)
        ) {
            budget = budget / 2;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                || levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
                || levelChange.equals(MarketLevelChange.TINY_DOWN)
                || levelChange.equals(MarketLevelChange.DCA_ORDER)
                || levelChange.equals(MarketLevelChange.FUNDING_FEE_BUY)
        ) {
            budget = budget / 3;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                || levelChange.equals(MarketLevelChange.SMALL_UP)
                || levelChange.equals(MarketLevelChange.TINY_UP)
        ) {
            long time = ticker.startTime.longValue();
            Double maDif1d = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
            Double maDif4h = SimpleMovingAverage4hManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
            if ((maDif1d != null && maDif1d > 0)
                    || (maDif4h != null && maDif4h > 0)
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
        } else {
            LOG.info("{} {} quantity false", symbol, quantity);
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

    private void createOrderSELLRequest(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange) {
        Double rateTarget = Configs.RATE_TARGET;
        Double budget = BudgetManager.getInstance().getBudgetSell();
        if (levelChange.equals(MarketLevelChange.ORDER_SELL_QUICK)
                || levelChange.equals(MarketLevelChange.FUNDING_FEE_SELL)) {
            budget = budget * 2 / 3;
        }
        Double priceEntry = ticker.priceClose;
        Double priceTarget = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, rateTarget);
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
                    priceTarget, quantity, BudgetManager.getInstance().getLeverage(), symbol, ticker.startTime.longValue(),
                    ticker.startTime.longValue(), OrderSide.SELL, Constants.TRADING_TYPE_VOLUME_MINI);
            orderTrade.marketLevel = levelChange;
            RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
        } else {
            LOG.info("{} {} quantity false", symbol, quantity);
        }
    }


    public boolean isTimeGetData() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 0 && miniSecond < 100;
    }

    public boolean isTimeProcessPositionQuick() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 40 && miniSecond < 100;
    }

    private void initData() {
        allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        allSymbol.removeAll(Constants.diedSymbol);
        symbol2Tickers.clear();
    }

    public void getTickerBySymbol(String symbol, Long time) {
        try {
            List<KlineObjectNumber> tickers = TickerFuturesHelper.getTickerWithStartTime(symbol, Constants.INTERVAL_1M, time);
            if (!tickers.isEmpty()) {
                if (tickers.get(tickers.size() - 1).endTime.longValue() > System.currentTimeMillis()) {
                    tickers.remove(tickers.size() - 1);
                }
                symbol2Tickers.put(symbol, tickers);
            }
//            if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)){
//                LOG.info("BTC ticker: {} {}", Utils.sdfGoogle.format(System.currentTimeMillis()),
//                        Utils.sdfGoogle.format(tickers.get(tickers.size() - 1).endTime.longValue()));
//            }
        } catch (Exception e) {
            LOG.info("Error get ticker of:{}", symbol);
            e.printStackTrace();
        }
    }


}
