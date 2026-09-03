package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class MarketBigChangeDetector {
    public static final Logger LOG = LoggerFactory.getLogger(MarketBigChangeDetector.class);

    public static void main(String[] args) throws ParseException {
        try {
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

                }

            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static MarketDataObject calMarketData(Map<String, KlineObjectSimple> symbol2Ticker, Map<String, Float> symbol2PriceMax,
                                                 Map<String, Float> symbol2MinPrice) {
        TreeMap<Float, String> rateDown2Symbols = new TreeMap<>();
        TreeMap<Float, String> rateMin2Symbols = new TreeMap<>();
        TreeMap<Float, String> rateMax2Symbols = new TreeMap<>();
        TreeMap<Float, String> rateUp2Symbols = new TreeMap<>();
        KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
        Float rateChangeBtc;
        if (btcTicker == null) {
            rateChangeBtc = 0f;
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
            Float maxPrice = symbol2PriceMax.get(symbol);
            if (maxPrice != null) {
                rateMax2Symbols.put(Utils.rateOf2Double(ticker.priceClose, maxPrice).floatValue(), symbol);
            }
            Float minPrice = symbol2MinPrice.get(symbol);
            if (minPrice != null) {
                rateMin2Symbols.put(-Utils.rateOf2Double(ticker.priceClose, minPrice).floatValue(), symbol);
            }
        }
        Float rateChangeDownAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown2Symbols, 100);
        Float rateChangeUpAvg = -MarketBigChangeDetector.calRateChangeAvg(rateUp2Symbols, 100);
        Float rateChangeDown15MAvg = MarketBigChangeDetector.calRateChangeAvg(rateMax2Symbols, 100);

        MarketDataObject result = new MarketDataObject(rateChangeDownAvg, rateChangeUpAvg, rateChangeDown15MAvg);
        result.rateDown15MAvg = rateChangeDown15MAvg.floatValue();


        return result;
    }

    // Thêm <K> vào hàm getTopSymbol
    public static <K> Set<K> getTopSymbol(int period,
                                          Map<K, KlineObjectSimple> symbol2FinalTicker,
                                          Set<K> symbolLocked,
                                          TreeMap<Float, K> predict2Symbol) {
        Set<K> symbols = new HashSet<>();
        if (predict2Symbol != null && !predict2Symbol.isEmpty()) {
            for (Map.Entry<Float, K> entry : predict2Symbol.entrySet()) {
                K symbolKey = entry.getValue(); // Có thể là String hoặc Short

                if (symbolLocked != null && symbolLocked.contains(symbolKey)) {
                    continue;
                }

                KlineObjectSimple ticker = symbol2FinalTicker.get(symbolKey);
                if (ticker != null) {
                    symbols.add(symbolKey);
                }
                if (symbols.size() >= period) {
                    break;
                }
            }
        }
        return symbols;
    }

    public static Set<Short> getTopSymbolArray(int period,
                                               KlineObjectSimple[] symbol2FinalTicker,
                                               Set<Short> symbolLocked,
                                               TreeMap<Float, Short> predict2Symbol) {
        Set<Short> symbols = new HashSet<>();
        if (predict2Symbol != null && !predict2Symbol.isEmpty()) {
            for (Map.Entry<Float, Short> entry : predict2Symbol.entrySet()) {
                Short symbolKey = entry.getValue(); // Có thể là String hoặc Short

                if (symbolLocked != null && symbolLocked.contains(symbolKey)) {
                    continue;
                }

                KlineObjectSimple ticker = symbol2FinalTicker[symbolKey];
                if (ticker != null) {
                    symbols.add(symbolKey);
                }
                if (symbols.size() >= period) {
                    break;
                }
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

    /**
     * MÔ HÌNH GEOMETRIC PROGRESSION (CẤP SỐ NHÂN)
     * Giải quyết bài toán Fat Tails và giảm số lượng tham số cho HPO.
     */

    public static MarketLevelChange getMarketStatus1M(Float rateDownAvg, Float rateUpAvg,
                                                      Float rateDown15MAvg) {

        // 2026-09-03: co OFF_FLAT_HARD da go -> chi con MOT nhanh song la BIG_DOWN
        // (BIG_UP / SMALL_UP / SMALL_DOWN_15M da bi tat cung tu truoc, nay xoa han).
        if (rateDownAvg < Configs.MS_DOWN_BIG_AVG) {
            return MarketLevelChange.BIG_DOWN;
        }



        return null;
    }

    public static boolean isDcaAlt(Float rateDown15MAvg, Float rateDownAvg, Float rateUpAvg) {
        return rateDown15MAvg < Configs.MS_DOWN_BIG_AVG
                || rateDownAvg < Configs.MS_DOWN_BIG_AVG / 3;
    }


}


