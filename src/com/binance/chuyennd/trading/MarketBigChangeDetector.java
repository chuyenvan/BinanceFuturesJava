package com.binance.chuyennd.trading;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class MarketBigChangeDetector {
    public static final Logger LOG = LoggerFactory.getLogger(MarketBigChangeDetector.class);
    public static final String TIME_RUN = Configs.getString("TIME_RUN");

    public static void main(String[] args) throws ParseException {
        try {
            Long startTime = Utils.sdfFileHour.parse("20250611 03:20").getTime();

            List<KlineObjectNumber> btcTickers = TickerFuturesHelper.getTickerWithStartTime(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1M,
                    startTime - 360 * Utils.TIME_MINUTE);
            while (true) {
                if (btcTickers.get(btcTickers.size() - 1).startTime.longValue() > startTime) {
                    btcTickers.remove(btcTickers.size() - 1);
                } else {
                    break;
                }
            }

            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(0).startTime.longValue()),
                    Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));

            System.out.println(MarketBigChangeDetector.isBtcTrendReverse(btcTickers));

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
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static boolean isSellingExhausted(List<KlineObjectNumber> tickers, String symbol) {
        // ================== CÁC THAM SỐ CÓ THỂ TÙY CHỈNH ==================
        // 1. Số lượng nến 1M để xem xét
        final int LOOKBACK_PERIOD = 20;
        // 2. Tỷ lệ nến đỏ tối thiểu trong chuỗi (ví dụ: 0.7 tương đương 70%)
        final double MIN_RED_CANDLE_PERCENTAGE = 0.7;
        // 3. Mức giảm giá tối thiểu từ đỉnh của chuỗi đến giá đóng cửa hiện tại (số âm)
        final double MIN_PRICE_DROP_PERCENTAGE = -0.05; // Yêu cầu giảm ít nhất 6%
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
            KlineObjectNumber candle = tickers.get(i);

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
        KlineObjectNumber lastCandle = tickers.get(tickers.size() - 1);
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

    public static Double isBtcTrendReverse(List<KlineObjectNumber> btcTickers) {
        int index = btcTickers.size() - 1;
        Double rateTrend = Configs.BTC_TREND_REVERSE_RATE_MAX;
        KlineObjectNumber lastTicker = btcTickers.get(index);
        Double priceReverse = null;
        Integer indexMin = null;
        while (priceReverse == null) {
            for (int i = 0; i < index; i++) {
                if (index >= i + 29) {
                    KlineObjectNumber ticker = btcTickers.get(index - i);
                    long minute = Utils.getCurrentMinute(ticker.startTime.longValue()) % 15;
                    if (minute != 14) {
                        continue;
                    }
                    KlineObjectNumber ticker15m = btcTickers.get(index - i - 14);
                    KlineObjectNumber ticker30m = btcTickers.get(index - i - 29);
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
                KlineObjectNumber ticker = btcTickers.get(index - i);
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

    public static boolean isBtcReverse(List<KlineObjectNumber> btcTickers, Double rateDown15MAvg) {
        int period = 15;
        int index = btcTickers.size() - 1;
        if (index < period + 3) {
            return false;
        }
        KlineObjectNumber finalTicker = btcTickers.get(index);
        KlineObjectNumber lastTicker = btcTickers.get(index - 1);
        Double volumeTotal = 0d;
        for (int i = 3; i < period + 3; i++) {
            KlineObjectNumber ticker = btcTickers.get(index - i);
            volumeTotal += ticker.totalUsdt;
        }
        double volumeAvg = volumeTotal / period;
        Double rateBtc = Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen);
        Double rateBtc2Ticker = Utils.rateOf2Double(finalTicker.priceClose, lastTicker.priceOpen);
        LOG.info("Check btc reverse: {} {} {}% {} {}% {} {}", Utils.normalizeDateYYYYMMDDHHmm(finalTicker.startTime.longValue()),
                finalTicker.priceClose, Utils.formatDouble(rateBtc * 100, 3), finalTicker.totalUsdt / volumeAvg,
                Utils.formatDouble(rateBtc2Ticker * 100, 3),
                Utils.formatDouble(rateDown15MAvg * 100, 3), lastTicker.totalUsdt / volumeAvg);
        if ((finalTicker.totalUsdt > 10 * volumeAvg || lastTicker.totalUsdt > 10 * volumeAvg)
                && (rateBtc < -0.0029 || rateBtc2Ticker < -0.0029)
                && rateBtc > -0.02
                && rateBtc < 0.002
        ) {
            return true;
        }

        return false;
    }

    public static boolean isBtcReverse15M(List<KlineObjectNumber> btcTickers) {
        int period = 15;
        int index = btcTickers.size() - 1;
        if (index < period * 3) {
            return false;
        }
        KlineObjectNumber finalTicker = btcTickers.get(index);
        long minute = Utils.getCurrentMinute(finalTicker.startTime.longValue()) % 15;
        if (minute != 14) {
            return false;
        }
        KlineObjectNumber ticker15m = btcTickers.get(index - 14);
        KlineObjectNumber ticker30m = btcTickers.get(index - 29);
        if (Utils.rateOf2Double(finalTicker.priceClose, ticker15m.priceOpen) < -0.004
                || Utils.rateOf2Double(finalTicker.priceClose, ticker30m.priceOpen) < -0.007) {
            return true;
        }
        return false;
    }


    public static Set<String> getTopSymbol(TreeMap<Double, String> rateLoss2Symbols, int period, Map<String,
            KlineObjectNumber> symbol2FinalTicker, Set<String> symbolLocked) {
        Set<String> symbols = new HashSet<>();
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            String symbol = entry.getValue();
            if (symbolLocked != null && symbolLocked.contains(symbol)) {
                LOG.info("Not trade {} because symbol locking: {}",
                        symbol, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
                continue;
            }
            KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
            if (ticker != null) {
                symbols.add(symbol);
            }
            if (symbols.size() >= period) {
                break;
            }
        }
        return symbols;
    }


    public static Double calRateChangeAvg(TreeMap<Double, String> rateLoss2Symbols, Integer period) {
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

    private static boolean isDoubleReverse(List<Double> lastRateDown15Ms, int period, Double rateDown15MAvg) {
        if (lastRateDown15Ms != null && lastRateDown15Ms.size() > period) {
            int size = lastRateDown15Ms.size();
            List<Long> lastRateLong = new ArrayList<>();
            for (int i = 0; i < size; i++) {
                Double rate = lastRateDown15Ms.get(i);
                rate = rate * 1000;
                lastRateLong.add(rate.longValue());
            }

            for (int i = 0; i < period; i++) {
                if (lastRateLong.get(size - i - 1) > lastRateLong.get(size - i - 2)) {
                    return false;
                }
            }
            if (lastRateDown15Ms.get(size - 1) < rateDown15MAvg) {
                return true;
            }
        }
        return false;
    }

    public static MarketLevelChange getMarketStatus1M(Double rateDownAvg, Double rateUpAvg,
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
        // tiny 1 order and budget/2
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

    public static List<Object> isUnderSideWay2Trade(List<KlineObjectNumber> tickers) {
        List<Object> results = new ArrayList<>();

        Double duration = 0.005;
        KlineObjectNumber tickerClose = tickers.get(tickers.size() - 1);
        Double priceClose = tickerClose.priceClose;

        TreeMap<Double, Integer> price2Counter = new TreeMap<>();
        for (int i = 0; i < 9; i++) {
            price2Counter.put(priceClose + (i - 2) * duration * priceClose, 0);
        }
        for (KlineObjectNumber ticker : tickers) {
            for (Map.Entry<Double, Integer> entry : price2Counter.entrySet()) {
                Double price = entry.getKey();
                Integer counter = entry.getValue();
                if (ticker.minPrice <= price && price <= ticker.maxPrice) {
                    counter++;
                    price2Counter.put(price, counter);
                }
            }
        }
        Integer priceCloseCounter = price2Counter.get(priceClose);
        int counterBelow = 0;
        int counterAbove = 0;
        for (Map.Entry<Double, Integer> entry : price2Counter.entrySet()) {
            Double price = entry.getKey();
            Integer counter = entry.getValue();
            if (price < priceClose) {
                counterBelow += counter;
            } else {
                if (price > priceClose) {
                    counterAbove += counter;
                }
            }
//            LOG.info("{} {}", price, counter);
        }
        if (priceCloseCounter >= 20
                && counterAbove > 2 * priceCloseCounter
                && Utils.rateOf2Double(tickerClose.priceClose, tickerClose.priceOpen) < -0.005
        ) {
            results.add(priceClose);
            results.add(priceCloseCounter);
            results.add(counterAbove);
            results.add(counterBelow);
            results.add(duration);
            return results;
        }

        return null;
    }

}


