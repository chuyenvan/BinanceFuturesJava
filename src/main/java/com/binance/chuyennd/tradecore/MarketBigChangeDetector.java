package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class MarketBigChangeDetector {
    public static final Logger LOG = LoggerFactory.getLogger(MarketBigChangeDetector.class);
//    public static OnnxMarketPredictor predictor = new OnnxMarketPredictor("storage/ai_ml_data/market_predictor_v2.onnx");
//    public static XGBoostMarketPredictor predictor = new XGBoostMarketPredictor("storage/ai_ml_data/xgboost");
//    public static ComprehensiveMarketFeatureExtractor featureExtractor = new ComprehensiveMarketFeatureExtractor();


    public static void main(String[] args) throws ParseException {
        try {
//            Long startTime = Utils.sdfFileHour.parse("20250831 19:23").getTime();
//
//            List<KlineObjectNumber> btcTickers = TickerFuturesHelper.getTickerWithStartTime(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1M,
//                    startTime - 360 * Utils.TIME_MINUTE);
//            while (true) {
//                if (btcTickers.get(btcTickers.size() - 1).startTime.longValue() > startTime) {
//                    btcTickers.remove(btcTickers.size() - 1);
//                } else {
//                    break;
//                }
//            }
//
//            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(0).startTime.longValue()),
//                    Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));
//
//            System.out.println(MarketBigChangeDetector.isBtcTrendReverse(btcTickers));

//            btcTickers.remove(btcTickers.size() - 1);
//            if (MarketBigChangeDetector.isBtcTrendReverse(btcTickers)) {
//                // check last time not btc trend reverse -> btc trend reverse
//                String finalTimeTrendReverse = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_MARKET_LEVEL_FINAL,
//                        MarketLevelChange.BTC_TREND_REVERSE.toString());
//                if (finalTimeTrendReverse == null || Long.parseLong(finalTimeTrendReverse) < btcTickers.get(btcTickers.size() - 1).startTime.longValue()) {
//                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_MARKET_LEVEL_FINAL,
//                            MarketLevelChange.BTC_TREND_REVERSE.toString(), String.valueOf(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));
//                    LOG.info("Fixbug btc trend reverse error {} ",
//                            Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));
//                }
//            }
            Long start = Utils.sdfFileHour.parse("20250830 23:11").getTime();
            for (int i = 0; i < 100; i++) {
                Long startTime = start - Utils.TIME_MINUTE * i;
                String symbol = "MUSDT";
//                List<KlineObjectNumber> tickerProds = TickerFuturesHelper.getTickerWithStartTime(symbol, Constants.INTERVAL_1M,
//                        startTime - 60 * Utils.TIME_MINUTE);
                List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M,
                        startTime - 60 * Utils.TIME_MINUTE);
                while (true) {
                    if (tickers.get(tickers.size() - 1).startTime.longValue() > startTime) {
                        tickers.remove(tickers.size() - 1);
                    } else {
                        break;
                    }
//                    if (tickerProds.get(tickers.size() - 1).startTime.longValue() > startTime) {
//                        tickerProds.remove(tickers.size() - 1);
//                    } else {
//                        break;
//                    }
                }

//            LOG.info("{} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(0).startTime.longValue()),
//                    Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()),
//                    Utils.normalizeDateYYYYMMDDHHmm(tickerProds.get(0).startTime.longValue()),
//                    Utils.normalizeDateYYYYMMDDHHmm(tickerProds.get(tickers.size() - 1).startTime.longValue()));
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static MarketDataObject calMarketData(Map<String, KlineObjectSimple> symbol2Ticker, Map<String, Double> symbol2PriceMax,
                                                 Map<String, Double> symbol2MinPrice) {
        TreeMap<Float, String> rateDown2Symbols = new TreeMap<>();
        TreeMap<Float, String> rateMin2Symbols = new TreeMap<>();
        TreeMap<Float, String> rateMax2Symbols = new TreeMap<>();
        TreeMap<Float, String> rateUp2Symbols = new TreeMap<>();
        KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
        Double rateChangeBtc;
        if (btcTicker == null) {
            rateChangeBtc = 0d;
        } else {
            rateChangeBtc = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
        }
        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = entry1.getValue();
            Float rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen).floatValue();
            // pass symbol big dump(delist/waring/monitor...)
            if (rateChangeBtc > -0.004 && rateChange < -0.15) {
                continue;
            }
            if (rateChange > 0.3) {
                continue;
            }
            rateDown2Symbols.put(rateChange, symbol);
            rateUp2Symbols.put(-rateChange, symbol);
            Double maxPrice = symbol2PriceMax.get(symbol);
            if (maxPrice != null) {
                rateMax2Symbols.put(Utils.rateOf2Double(ticker.priceClose, maxPrice).floatValue(), symbol);
            }
            Double minPrice = symbol2MinPrice.get(symbol);
            if (minPrice != null) {
                rateMin2Symbols.put(-Utils.rateOf2Double(ticker.priceClose, minPrice).floatValue(), symbol);
            }
        }
        Float rateChangeDownAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown2Symbols, 100);
        Float rateChangeUpAvg = -MarketBigChangeDetector.calRateChangeAvg(rateUp2Symbols, 100);
        Float rateChangeDown15MAvg = MarketBigChangeDetector.calRateChangeAvg(rateMax2Symbols, 100);

//        List<String> symbolsTopDown = MarketBigChangeDetectorTest.getTopSymbolSimple(rateDown2Symbols,
//                Configs.NUMBER_ENTRY_EACH_SIGNAL, null);
        MarketDataObject result = new MarketDataObject(rateChangeDownAvg, rateChangeUpAvg, rateChangeDown15MAvg);
        result.rateBtc = rateChangeBtc.floatValue();
        result.rate2Max = SimpleSymbolMapper.getInstance().convertSymbolList(rateMax2Symbols);
        result.rateDown15MAvg = rateChangeDown15MAvg.floatValue();


        return result;
    }

    public static Double isBtcTrendReverse(List<KlineObjectSimple> btcTickers) {
        int index = btcTickers.size() - 1;
        Double rateTrend = Configs.BTC_TREND_REVERSE_RATE_MAX;
        KlineObjectSimple lastTicker = btcTickers.get(index);
        Double priceReverse = null;
        Integer indexMin = null;
        while (priceReverse == null) {
            for (int i = 0; i < index; i++) {
                if (index >= i + 29) {
                    KlineObjectSimple ticker = btcTickers.get(index - i);
                    long minute = Utils.getCurrentMinute(ticker.startTime.longValue()) % 15;
                    if (minute != 14) {
                        continue;
                    }
                    KlineObjectSimple ticker15m = btcTickers.get(index - i - 14);
                    KlineObjectSimple ticker30m = btcTickers.get(index - i - 29);
                    double rate = Math.min(Utils.rateOf2Double(ticker.priceClose, ticker30m.maxPrice),
                            Utils.rateOf2Double(ticker.priceClose, ticker15m.maxPrice));
                    if (rate < -rateTrend) {
                        priceReverse = ticker15m.priceOpen;
                        indexMin = i;
                        break;
                    }
                }
            }
            rateTrend = rateTrend - 0.0005;
            if (rateTrend < Configs.BTC_TREND_REVERSE_RATE_MIN_TRADE - 0.00005) {
                break;
            }
        }
        if (priceReverse != null
                && lastTicker.priceClose > priceReverse
        ) {
            // by pass if last ticker not ticker first up over bottom 1%
            for (int i = 1; i < indexMin; i++) {
                KlineObjectSimple ticker = btcTickers.get(index - i);
                if (ticker.priceClose >= priceReverse) {
                    return null;
                }
            }
            LOG.info("IsBtcTrendReverse: {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()),
                    lastTicker.priceClose, priceReverse, Utils.rateOf2Double(lastTicker.priceClose, priceReverse),
                    Utils.sdfGoogle.format(new Date(lastTicker.startTime.longValue())));
            return rateTrend;
        }
        return null;
    }


    public static Set<String> getTopSymbol(TreeMap<Float, String> rateLoss2Symbols, int period, Map<String,
            KlineObjectSimple> symbol2FinalTicker, Set<String> symbolLocked) {
        Set<String> symbols = new HashSet<>();
        for (Map.Entry<Float, String> entry : rateLoss2Symbols.entrySet()) {
            String symbol = entry.getValue();
            if (symbolLocked != null && symbolLocked.contains(symbol)) {
//                LOG.info("Not trade {} because symbol locking: {}",
//                        symbol, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
                continue;
            }
            KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
            if (ticker != null) {
                symbols.add(symbol);
            }
            if (symbols.size() >= period) {
                break;
            }
        }
        return symbols;
    }


    public static Float calRateChangeAvg(TreeMap<Float, String> rateLoss2Symbols, Integer period) {
        Float total = 0f;
        int counter = 0;
        if (period > rateLoss2Symbols.size() * 4 / 5) {
            period = rateLoss2Symbols.size() * 4 / 5;
        }
        for (Map.Entry<Float, String> entry : rateLoss2Symbols.entrySet()) {
            Float key = entry.getKey();
            counter++;
            total += key;
            if (period != null && counter >= period) {
                break;
            }
        }
        if (rateLoss2Symbols.isEmpty()) {
            return 0f;
        }
        return total / counter;
    }

    //    public static MarketLevelChange getMarketStatus1M(Float rateDownAvg, Float rateUpAvg,
//                                                      Float btcRateChange, Float rateDown15MAvg) {
//        if (rateUpAvg > 0.025) {
//            return MarketLevelChange.BIG_UP;
//        }
//        if (rateDownAvg < -0.032
//                && btcRateChange < -0.01) {
//            return MarketLevelChange.BIG_DOWN;
//        }
//
//        // medium 2 order
//        if (rateUpAvg > 0.015) {
//            return MarketLevelChange.MEDIUM_UP;
//        }
//        if (rateDownAvg < -0.030 ||
//                (rateDownAvg < -0.014
//                        && rateDown15MAvg < -0.07
//                )
//        ) {
//            return MarketLevelChange.MEDIUM_DOWN;
//        }
//        if (rateUpAvg > 0.008 && rateDownAvg > 0) {
//            return MarketLevelChange.SMALL_UP;
//        }
//        if (rateDownAvg < -0.006 && rateUpAvg < 0
//                && rateDown15MAvg < -0.025
//        ) {
//            return MarketLevelChange.SMALL_DOWN;
//        }
//
//        if (rateDown15MAvg < -0.045) {
//            return MarketLevelChange.MEDIUM_DOWN_15M;
//        }
//        if (rateDown15MAvg < -0.028) {
//            return MarketLevelChange.SMALL_DOWN_15M;
//        }
//
//        return null;
//
//    }
    public static MarketLevelChange getMarketStatus1M(Float rateDownAvg, Float rateUpAvg,
                                                      Float btcRateChange, Float rateDown15MAvg) {

        // 1. BIG UP / BIG DOWN
        if (rateUpAvg > Configs.MS_UP_BIG_THRES) {
            return MarketLevelChange.BIG_UP;
        }
        if (rateDownAvg < Configs.MS_DOWN_BIG_AVG
                && btcRateChange < Configs.MS_DOWN_BIG_BTC) {
            return MarketLevelChange.BIG_DOWN;
        }

        // 2. MEDIUM UP / DOWN
        if (rateUpAvg > Configs.MS_UP_MED_THRES) {
            return MarketLevelChange.MEDIUM_UP;
        }
        // Logic Medium Down phức tạp (AVG < X HOẶC (AVG < Y VÀ 15M < Z))
        if (rateDownAvg < Configs.MS_DOWN_MED_AVG ||
                (rateDownAvg < Configs.MS_DOWN_MED_AVG_CMB
                        && rateDown15MAvg < Configs.MS_DOWN_MED_15M_CMB
                )
        ) {
            return MarketLevelChange.MEDIUM_DOWN;
        }

        // 3. SMALL UP / DOWN
        if (rateUpAvg > Configs.MS_UP_SMALL_THRES && rateDownAvg > 0) {
            return MarketLevelChange.SMALL_UP;
        }
        if (rateDownAvg < Configs.MS_DOWN_SMALL_AVG && rateUpAvg < 0
                && rateDown15MAvg < Configs.MS_DOWN_SMALL_15M
        ) {
            return MarketLevelChange.SMALL_DOWN;
        }

        // 4. RIÊNG BIỆT THEO 15M (Trường hợp Avg không giảm mạnh nhưng 15M sập)
        if (rateDown15MAvg < Configs.MS_DOWN_15M_MED_ONLY) {
            return MarketLevelChange.MEDIUM_DOWN_15M;
        }
        if (rateDown15MAvg < Configs.MS_DOWN_15M_SMALL_ONLY) {
            return MarketLevelChange.SMALL_DOWN_15M;
        }

        return null;
    }

    public static boolean isFundingFeeTrade(Float rateDown15MAvg, Float rateDownAvg, Float rateUpAvg,
                                            Float minRate15Min60M) {
//        Double rateMin2Trade = -0.025;
//        Double rateMin2TradeFull = -0.03;
//        return (rateDown15MAvg < rateMin2Trade && rateDown15MAvg <= minRate15Min60M)
//                || rateDown15MAvg < rateMin2TradeFull
//                || rateUpAvg > 0.005
//                || rateDownAvg < -0.005;
        return (rateDown15MAvg < Configs.FUNDING_RATE_MIN_TRADE && rateDown15MAvg <= minRate15Min60M)
                || rateDown15MAvg < Configs.FUNDING_RATE_MIN_TRADE_FULL
                || rateUpAvg > Configs.FUNDING_RATE_UP_AVG
                || rateDownAvg < Configs.FUNDING_RATE_DOWN_AVG;
    }

    public static boolean isDcaWithBtcReverse(Double rateLoss, Double budget, Double marginOfSym, Double priceClose,
                                              Double lastEntry) {
        int marginRatioLevel1 = 2;
        int marginRatioLevel2 = 4;
        if (marginOfSym > marginRatioLevel1 * budget) {
            if (marginOfSym > marginRatioLevel2 * budget) {
                if (Utils.rateOf2Double(priceClose, lastEntry) < -0.1) {
                    return true;
                }
            } else {
                if (rateLoss < -0.05 || rateLoss > 0.02) {
                    return true;
                }
            }
        } else {
            if (rateLoss < -0.03 || rateLoss > 0.02) {
                return true;
            }
        }
        return false;
    }


    public static boolean isDcaAlt(Float rateDown15MAvg,
                                   Float rateDownAvg,
                                   Float rateUpAvg) {
        return rateDown15MAvg < -0.035
                || rateUpAvg > 0.012
                || rateDownAvg < -0.012;
    }

    public static List<String> addSpecialSymbol(Map<String, KlineObjectSimple> symbol2Ticker, Set<String> symbol2BUY,
                                                Set<String> symbolRunning) {
        List<String> hashSet = new ArrayList<>();
        Double rateCheck = -0.013;

        Set<String> symbol2Checks = new HashSet<>();
        symbol2Checks.addAll(Constants.specialSymbol);
        symbol2Checks.addAll(Constants.stableSymbol);
        symbol2Checks.removeAll(symbolRunning);
        symbol2Checks.removeAll(symbol2BUY);
        for (String symbol : symbol2Checks) {
            KlineObjectSimple ticker = symbol2Ticker.get(symbol);

            if (ticker != null && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < rateCheck) {
                hashSet.add(symbol);
            }
        }
        return hashSet;
    }


}


