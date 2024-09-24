//package com.binance.chuyennd.bigchange.test;
//
//import com.binance.chuyennd.bigchange.market.MarketLevelChange;
//import com.binance.chuyennd.bigchange.statistic.BreadDetectObject;
//import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
//import com.binance.chuyennd.client.TickerFuturesHelper;
//import com.binance.chuyennd.indicators.SimpleMovingAverage1DManager;
//import com.binance.chuyennd.movingaverage.MAStatus;
//import com.binance.chuyennd.object.KlineObjectNumber;
//import com.binance.chuyennd.redis.RedisConst;
//import com.binance.chuyennd.redis.RedisHelper;
//import com.binance.chuyennd.trading.BinanceOrderTradingManager;
//import com.binance.chuyennd.trading.DetectEntrySignal2Trader;
//import com.binance.chuyennd.trading.MarketBigChangeDetector;
//import com.binance.chuyennd.utils.Configs;
//import com.binance.chuyennd.utils.Utils;
//import com.binance.client.constant.Constants;
//import com.binance.client.model.enums.OrderSide;
//import com.educa.chuyennd.funcs.BreadProductFunctions;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//import java.text.ParseException;
//import java.util.*;
//
///**
// * @author pc
// */
//public class CheckMissSignalCurrentTime {
//
//    public static final Logger LOG = LoggerFactory.getLogger(CheckMissSignalCurrentTime.class);
//
//    public Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");
//    public final Double RATE_MA_MAX = Configs.getDouble("RATE_MA_MAX");
//
//
//    private void printAllSignalByTime(Long startTime) {
//        Map<String, List<KlineObjectNumber>> symbol2TickerAll = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);
//        Long time = startTime + Utils.TIME_DAY;
//        List<KlineObjectNumber> btcTickers = symbol2TickerAll.get(Constants.SYMBOL_PAIR_BTC);
//        Long maxTime = btcTickers.get(btcTickers.size() - 1).startTime.longValue();
//        while (true) {
//            Map<String, List<KlineObjectNumber>> symbol2Tickers = new HashMap<>();
//            for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2TickerAll.entrySet()) {
//                String symbol = entry.getKey();
//                List<KlineObjectNumber> values = entry.getValue();
//                List<KlineObjectNumber> tickers = new ArrayList<>();
//                for (KlineObjectNumber ticker : values) {
//                    if (ticker.startTime.longValue() > time){
//                        break;
//                    }
//                    tickers.add(ticker);
//                }
//                symbol2Tickers.put(symbol, tickers);
//            }
//            printAllSignalByTickers(symbol2Tickers);
//            time += 15* Utils.TIME_MINUTE;
//            if (time > maxTime){
//                break;
//            }
//        }
//    }
//
//    void printAllSignalByTickers(Map<String, List<KlineObjectNumber>> allSymbolTickers) {
//        try {
//            Map<String, KlineObjectNumber> symbol2LastTicker = new HashMap<>();
//            for (Map.Entry<String, List<KlineObjectNumber>> entry : allSymbolTickers.entrySet()) {
//                String symbol = entry.getKey();
//                List<KlineObjectNumber> values = entry.getValue();
//                symbol2LastTicker.put(symbol, values.get(values.size() - 1));
//            }
//            MarketLevelChange levelChange = MarketBigChangeDetector.detectLevelChangeProduction(symbol2LastTicker);
//            Long time = System.currentTimeMillis() - Utils.TIME_MINUTE * 15;
//            if (symbol2LastTicker.get(Constants.SYMBOL_PAIR_BTC) != null) {
//                time = symbol2LastTicker.get(Constants.SYMBOL_PAIR_BTC).startTime.longValue();
//            }
//            LOG.info("Market level change: {} level: {} symbols:{}", Utils.normalizeDateYYYYMMDDHHmm(time),
//                    levelChange, symbol2LastTicker.size());
//            if (levelChange != null) {
//
//                if (levelChange != null) {
//                    // check and dca all order running when big down
//                    if (levelChange.equals(MarketLevelChange.BIG_DOWN)
//                            || levelChange.equals(MarketLevelChange.MAYBE_BIG_DOWN_AFTER)
//                            || levelChange.equals(MarketLevelChange.MEDIUM_DOWN)) {
//                        BinanceOrderTradingManager.checkAndDca();
//                    }
//                    // create new order
//                    List<String> symbol2Trade = MarketBigChangeDetector.getTopSymbol2TradeWithRateChange(symbol2LastTicker, 20, levelChange);
//                    LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), levelChange, symbol2Trade);
//                    for (String symbol : symbol2Trade) {
//                        try {
//                            KlineObjectNumber ticker = symbol2LastTicker.get(symbol);
//                            LOG.info("{} BUY {} {}", levelChange, symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
//                        } catch (Exception e) {
//                            e.printStackTrace();
//                        }
//                    }
//                }
//            } else {
//                // check not position running
//                MarketLevelChange orderMarketRunning = DetectEntrySignal2Trader.getOrderMarketLevelRunning();
//                TreeMap<Double, String> rateChange2Symbol = new TreeMap<>();
//                TreeMap<Double, String> rateChange2SymbolExtend = new TreeMap<>();
//                TreeMap<Double, String> rateChange2SymbolUnder5 = new TreeMap<>();
//                List<String> symbolSellCouples = new ArrayList<>();
//                if (orderMarketRunning == null || orderMarketRunning.equals(MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND)) {
//                    for (Map.Entry<String, List<KlineObjectNumber>> entry1 : allSymbolTickers.entrySet()) {
//                        String symbol = entry1.getKey();
//                        List<KlineObjectNumber> tickers = entry1.getValue();
//                        KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
//                        // check sell
//                        if (MarketBigChangeDetector.isSignalSELL(tickers, tickers.size() - 1)) {
//                            symbolSellCouples.add(symbol);
//                        }
//                        // check buy
//                        List<Integer> altReverseStatus = MarketBigChangeDetector.getStatusTradingAlt15M(tickers, tickers.size() - 1);
//                        if (altReverseStatus.contains(1)) {
//                            rateChange2Symbol.put(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen), symbol);
//                        }
//                        if (altReverseStatus.contains(2)) {
//                            rateChange2SymbolExtend.put(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen), symbol);
//                        }
//                        if (altReverseStatus.contains(3)) {
//                            rateChange2SymbolUnder5.put(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen), symbol);
//                        }
//                    }
//                    if (rateChange2Symbol.size() >= 5) {
//                        levelChange = MarketLevelChange.ALT_BIG_CHANGE_REVERSE;
//                        int counter = 0;
//                        for (Map.Entry<Double, String> entry2 : rateChange2Symbol.entrySet()) {
//                            String symbol = entry2.getValue();
//                            LOG.info("Alt reverse: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol);
//                            KlineObjectNumber ticker = symbol2LastTicker.get(symbol);
//
//                            counter++;
//                            if (counter >= 6) {
//                                break;
//                            }
//                        }
//                    } else {
//                        if (orderMarketRunning == null) {
//                            if (!rateChange2SymbolExtend.isEmpty()) {
//                                levelChange = MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND;
//                                int counter = 0;
//                                for (Map.Entry<Double, String> entry2 : rateChange2SymbolExtend.entrySet()) {
//                                    String symbol = entry2.getValue();
//                                    LOG.info("Alt Reverse extend: {} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange,
//                                            symbol, rateChange2SymbolExtend.size());
//                                    counter++;
//                                    if (counter >= 5) {
//                                        break;
//                                    }
//                                }
//                            } else {
//                                levelChange = MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND;
//                                for (Map.Entry<Double, String> entry2 : rateChange2SymbolUnder5.entrySet()) {
//                                    if (BinanceFuturesClientSingleton.getInstance().getAllOpenOrderInfos().size() < 3) {
//                                        String symbol = entry2.getValue();
//                                        LOG.info("Alt reverse2: {} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange,
//                                                symbol, rateChange2Symbol.size());
//                                    }
//                                }
//                            }
//                        }
//                    }
//                }
//                levelChange = MarketLevelChange.ALT_SIGNAL_SELL;
//                for (String symbol : symbolSellCouples) {
//                    LOG.info("Alt Sell: {} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange,
//                            symbol, rateChange2Symbol.size());
//                }
//            }
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//
//    }
//
//    public static void main(String[] args) throws ParseException {
//        new CheckMissSignalCurrentTime().printAllSignalByTime(Utils.sdfFileHour.parse("20240730 00:00").getTime());
//    }
//
//}
