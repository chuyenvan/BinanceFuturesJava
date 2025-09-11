package com.binance.chuyennd.bigchange.market;

import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.TechnicalAnalysisUtils;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class MarketBigChangeDetectorTest {
    public static final Logger LOG = LoggerFactory.getLogger(MarketBigChangeDetectorTest.class);
    public static String TIME_RUN = Configs.getString("TIME_RUN");


    public static void main(String[] args) throws ParseException {
        List<KlineObjectSimple> tickerSimples = TickerFuturesHelper.getTickerSimpleWithStartTime(Constants.SYMBOL_PAIR_BTC,
                Constants.INTERVAL_1M, Utils.sdfFileHour.parse("20250321 20:30").getTime() - 499 * Utils.TIME_MINUTE);
        while (tickerSimples.size() > 360) {
            tickerSimples.remove(0);
        }
        LOG.info("time check: {}", Utils.normalizeDateYYYYMMDDHHmm(tickerSimples.get(tickerSimples.size() - 1).startTime.longValue()));
        System.out.println(MarketBigChangeDetectorTest.isBtcTrendReverse(tickerSimples, Configs.BTC_TREND_REVERSE_RATE_MAX,
                Configs.BTC_TREND_REVERSE_RATE_MIN));


    }


    public static MarketDataObject calMarketData(Map<String, KlineObjectSimple> symbol2Ticker, Map<String, Double> symbol2PriceMax,
                                                 Map<String, Double> symbol2MinPrice) {
        TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateMin2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateMax2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
        KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
        Double rateChangeBtc = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = entry1.getValue();
            Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            // pass symbol big dump(delist/waring/monitor...)
            if (rateChangeBtc > -0.004 && rateChange < -0.15) {
                continue;
            }
            rateDown2Symbols.put(rateChange, symbol);
            rateUp2Symbols.put(-rateChange, symbol);
            Double maxPrice = symbol2PriceMax.get(symbol);
            if (maxPrice != null) {
                rateMax2Symbols.put(Utils.rateOf2Double(ticker.priceClose, maxPrice), symbol);
            }
            Double minPrice = symbol2MinPrice.get(symbol);
            if (minPrice != null) {
                rateMin2Symbols.put(-Utils.rateOf2Double(ticker.priceClose, minPrice), symbol);
            }
        }
        Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
        Double rateChangeDownAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateDown2Symbols, 100);
        Double rateChangeUpAvg = -MarketBigChangeDetectorTest.calRateLossAvg(rateUp2Symbols, 100);
        Double rateChangeDown15MAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateMax2Symbols, 100);

//        List<String> symbolsTopDown = MarketBigChangeDetectorTest.getTopSymbolSimple(rateDown2Symbols,
//                Configs.NUMBER_ENTRY_EACH_SIGNAL, null);
        MarketDataObject result = new MarketDataObject(rateChangeDownAvg, rateChangeUpAvg, btcRateChange,
                null, null);
        result.rate2Max = rateMax2Symbols;
        result.rate2Min = rateMin2Symbols;
        result.rateDown15MAvg = rateChangeDown15MAvg;
        result.rateBtcUp15M = Utils.rateOf2Double(btcTicker.priceClose, symbol2MinPrice.get(Constants.SYMBOL_PAIR_BTC));
        result.rateBtcDown15M = Utils.rateOf2Double(btcTicker.priceClose, symbol2PriceMax.get(Constants.SYMBOL_PAIR_BTC));
        result.symbol2PriceMax15M = symbol2PriceMax;
        return result;
    }

    public static List<String> getTopUpSymbol2TradeSimple(Map<String, KlineObjectSimple> value, int period) {
        TreeMap<Double, String> rateChange2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectSimple> entry1 : value.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = entry1.getValue();
            Double rateChange;
            rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            rateChange2Symbols.put(-rateChange, symbol);
        }
        return getTopSymbolSimple(rateChange2Symbols, period, null);
    }




    public static List<String> getTopSymbolSimple(TreeMap<Double, String> rateLoss2Symbols, int period, Set<String> symbolsRunning) {
        List<String> symbols = new ArrayList<>();

        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            if (symbolsRunning != null && symbolsRunning.contains(entry.getValue())) {
                continue;
            }
            symbols.add(entry.getValue());
            if (symbols.size() >= period) {
                break;
            }
        }
        return symbols;
    }

    public static Set<String> getTopSymbolSimpleNew(TreeMap<Double, String> rateLoss2Symbols, MarketLevelChange levelChange, int period,
                                                    Map<String, KlineObjectSimple> symbol2Ticker, Set<String> symbolLock) {

        Set<String> symbols = new HashSet<>();
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            String symbol = entry.getValue();
//            Double rateScam = Configs.RATE_TICKER_MAX_SCAN_ORDER;
            if (symbolLock != null && symbolLock.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
            if (ticker != null
//                    && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < rateScam
            ) {
                symbols.add(symbol);
                if (symbols.size() >= period) {
                    break;
                }
            }
        }
        return symbols;
    }



    public static Double calRateLossAvg(TreeMap<Double, String> rateLoss2Symbols, Integer period) {
        Double total = 0d;
        int counter = 0;
        if (period > rateLoss2Symbols.size() * 4 / 5) {
            period = rateLoss2Symbols.size() * 4 / 5;
        }
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            Double key = entry.getKey();
            counter++;
            total += key;
            if (period != null && counter >= period) {
                break;
            }
        }
        if (rateLoss2Symbols.isEmpty()) {
            return 0d;
        }
        return total / counter;
    }


    public static Boolean isSignalSell(List<KlineObjectNumber> tickers) {
        try {
            int index = tickers.size() - 1;
            KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
            Double minPrice = ticker.minPrice;
            for (int j = 0; j < 12; j++) {
                if (index - j - 1 > 0) {
                    minPrice = Math.min(minPrice, tickers.get(index - j - 1).minPrice);
                }
            }
            if (Utils.rateOf2Double(ticker.priceClose, minPrice) > 0.9) {
                return true;
            }
        } catch (
                Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    public static boolean isSellingExhausted(List<KlineObjectSimple> tickers, String symbol) {
        // ================== CÁC THAM SỐ CÓ THỂ TÙY CHỈNH ==================
        // 1. Số lượng nến 1M để xem xét
        final int LOOKBACK_PERIOD = 20;
        // 2. Tỷ lệ nến đỏ tối thiểu trong chuỗi (ví dụ: 0.7 tương đương 70%)
        final double MIN_RED_CANDLE_PERCENTAGE = 0.7;
        // 3. Mức giảm giá tối thiểu từ đỉnh của chuỗi đến giá đóng cửa hiện tại (số âm)
        final double MIN_PRICE_DROP_PERCENTAGE = -0.045; // Yêu cầu giảm ít nhất 6%
        // 4. Hệ số suy yếu của volume: volume cuối phải nhỏ hơn X lần volume trung bình
        final double VOLUME_WEAKENING_FACTOR = 0.6; // Volume cuối < 80% volume trung bình
        // =================================================================

        // --- Bước 1: Kiểm tra dữ liệu đầu vào có đủ không ---
        if (tickers == null || tickers.size() < LOOKBACK_PERIOD) {
            return false;
        }

        // --- Bước 2: Lấy dữ liệu trong chuỗi nến xem xét ---
        int redCandleCount = 0;
        double totalRedCandleVolume = 0;
        Double periodHigh = null;
        int startIndex = tickers.size() - LOOKBACK_PERIOD;

        for (int i = startIndex; i < tickers.size(); i++) {
            KlineObjectSimple candle = tickers.get(i);

            // Cập nhật giá cao nhất trong chuỗi
            if (periodHigh == null || candle.maxPrice > periodHigh) {
                periodHigh = candle.maxPrice;
            }

            // Đếm nến đỏ và tính tổng volume của chúng
            if (candle.priceClose < candle.priceOpen) {
                redCandleCount++;
                totalRedCandleVolume += candle.totalUsdt;
            }
        }

        // --- Bước 3: Áp dụng các bộ lọc điều kiện ---

        // Điều kiện 1: Phải có một đợt bán tháo kéo dài
        double redCandlePercentage = (double) redCandleCount / LOOKBACK_PERIOD;
        if (redCandlePercentage < MIN_RED_CANDLE_PERCENTAGE) {
            return false;
        }

        // Điều kiện 2: Mức giảm giá phải đủ sâu
        KlineObjectSimple lastCandle = tickers.get(tickers.size() - 1);
        double priceDropPercentage = Utils.rateOf2Double(lastCandle.priceClose, periodHigh);
        if (priceDropPercentage > MIN_PRICE_DROP_PERCENTAGE) {
            return false;
        }

        // Điều kiện 3: Lực bán (volume) phải có dấu hiệu suy yếu
        if (redCandleCount == 0) { // Tránh chia cho 0
            return false;
        }
        double averageRedVolume = totalRedCandleVolume / redCandleCount;
        // So sánh volume của cây nến cuối cùng với volume trung bình của các nến đỏ
        if (lastCandle.totalUsdt >= (averageRedVolume * VOLUME_WEAKENING_FACTOR)) {
            return false;
        }

        // --- Nếu vượt qua tất cả các điều kiện, tín hiệu được kích hoạt ---
//        LOG.info("!!! {} - TÍN HIỆU KIỆT SỨC PHE BÁN: Nến đỏ: {}% ({}/{}), Giảm giá: {}%, Volume cuối: {} < TB: {}",
//                symbol,
//                Utils.formatPercentNew(redCandlePercentage), redCandleCount, LOOKBACK_PERIOD,
//                Utils.formatPercentNew(priceDropPercentage),
//                Utils.formatLog(lastCandle.totalUsdt.longValue(), 4),
//                Utils.formatLog((long) (averageRedVolume * VOLUME_WEAKENING_FACTOR), 4));

        return true;
    }

    public static MarketLevelChange getMarketStatusSimple(Double rateDownAvg, Double rateUpAvg,
                                                          Double btcRateChange, Double rateDown15MAvg) {
        // big -> 2 order and x2 budget
        if (rateUpAvg > 0.025) {
            return MarketLevelChange.BIG_UP;
        }
        if (rateDownAvg < -0.032
                && btcRateChange < -0.01) {
            return MarketLevelChange.BIG_DOWN;
        }

        // medium 2 order
        if (rateUpAvg > 0.015) {
            return MarketLevelChange.MEDIUM_UP;
        }
        if (rateDownAvg < -0.030 ||
                (rateDownAvg < -0.014
                        && rateDown15MAvg < -0.07
                )
        ) {
            return MarketLevelChange.MEDIUM_DOWN;
        }
        if (rateUpAvg > 0.008 && rateDownAvg > 0) {
            return MarketLevelChange.SMALL_UP;
        }
        if (rateDownAvg < -0.006 && rateUpAvg < 0
                && rateDown15MAvg < -0.025
        ) {
            return MarketLevelChange.SMALL_DOWN;
        }

        if (rateDown15MAvg < -0.045) {
            return MarketLevelChange.MEDIUM_DOWN_15M;
        }
        if (rateDown15MAvg < -0.028) {
            return MarketLevelChange.SMALL_DOWN_15M;
        }

        return null;
    }


    public static Double isBtcTrendReverse(List<KlineObjectSimple> btcTickers, Double rateTrend, Double rateTrendMin) {
        int index = btcTickers.size() - 1;
        KlineObjectSimple lastTicker = btcTickers.get(index);
        Double priceReverse = null;
        Integer indexMin = null;

        while (priceReverse == null) {
//            LOG.info("Check btc reverse with rate: {}", rateTrend);
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
//                        priceReverse = Math.max(ticker15m.priceOpen, ticker15m.priceClose);
                        indexMin = i;
                        break;
                    }
                }
            }
            if (rateTrend > 0.01) {
                rateTrend = rateTrend - 0.002;
            } else {
                rateTrend = rateTrend - 0.0005;
            }
            if (rateTrend < rateTrendMin - 0.00005) {
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


    public static boolean isAltReverse15M(List<KlineObjectSimple> tickers) {
        int period = 15;
        int index = tickers.size() - 1;
        if (index < period + 3) {
            return false;
        }
        KlineObjectSimple finalTicker = tickers.get(index);
        KlineObjectSimple lastTicker = tickers.get(index - 1);
        Double volumeTotal = 0d;
        for (int i = 3; i < period + 3; i++) {
            KlineObjectSimple ticker = tickers.get(index - i);
            volumeTotal += ticker.totalUsdt;
        }
        double volumeAvg = volumeTotal / period;
        Double rateTicker = Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen);
        Double lastRateTicker = Utils.rateOf2Double(finalTicker.priceClose, lastTicker.priceOpen);

        if ((finalTicker.totalUsdt > 10 * volumeAvg || lastTicker.totalUsdt > 10 * volumeAvg)
                && (rateTicker < -0.018 || lastRateTicker < -0.02)
                && rateTicker < -0.01
        ) {
            return true;
        }
        return false;
    }


}




