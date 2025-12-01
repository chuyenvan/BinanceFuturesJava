package com.binance.chuyennd.ai_ml.extractor;

import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.TechnicalAnalysisUtils;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;

import java.text.SimpleDateFormat;
import java.util.*;

public class FeatureCalculator {

    private static final int WARMUP = MainFeatureExtractor.WARMUP_PERIOD;
    private static final int P_5M = 5;
    private static final int P_15M = 15;
    private static final int P_30M = 30;
    private static final int P_60M = 60;
    private static final int SMA_VOL_PERIOD = 60;

    private static final int RSI_PERIOD = 14;
    private static final int BB_PERIOD = 20;
    private static final int MACD_FAST = 12;
    private static final int MACD_SLOW = 26;
    private static final int MACD_SIGNAL = 9;
    private static final SimpleDateFormat SDF_DEBUG = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
    /**
     * Tinh 9 features chung (Market/Context)
     */
    public static FeatureRow calculateFeatures(int i) {

        if (i < WARMUP) {
            return null;
        }

        FeatureRow row = new FeatureRow();
        long timestamp = DataContext.ALL_TIMESTAMPS_LIST.get(i);
        row.debug_date = SDF_DEBUG.format(new Date(timestamp));

        KlineObjectSimple kline_btc = DataContext.ALL_BTC_KLINES_LIST.get(i);
        List<KlineObjectSimple> klines_btc = DataContext.ALL_BTC_KLINES_LIST;

        // === NHOM 1: MARKET & CONTEXT (9) ===

        // 1. BTC Rate
        row.btc_rate_change_15m = Utils.rateOf2Double(kline_btc.priceClose, klines_btc.get(i - P_15M).priceClose);

        // 2. Trends
        row.isTrendBuyWithBTC = getTrend(Constants.SYMBOL_PAIR_BTC, timestamp) ? 1.0 : 0.0;
        row.isTrendBuyWithETH = getTrend(Constants.SYMBOL_PAIR_ETH, timestamp) ? 1.0 : 0.0;

        // 3. Market Data
        MarketDataObject marketData = DataContext.CACHED_time2MarketData.get(timestamp);
        if (marketData == null) return null;
        row.market_rate_down_avg_15m = marketData.rateDown15MAvg;
        row.top_symbols_down_15m_count = (marketData.symbolsTopDown != null) ? marketData.symbolsTopDown.size() : 0.0;

        // 4. Time
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(timestamp);
        int hour = cal.get(Calendar.HOUR_OF_DAY);
        int day = cal.get(Calendar.DAY_OF_WEEK);

        row.hour_of_day_sin = Math.sin(2 * Math.PI * hour / 24.0);
        row.hour_of_day_cos = Math.cos(2 * Math.PI * hour / 24.0);
        row.day_of_week_sin = Math.sin(2 * Math.PI * day / 7.0);
        row.day_of_week_cos = Math.cos(2 * Math.PI * day / 7.0);

        return row;
    }

    /**
     * Tinh 13 features rieng (Symbol)
     */
    public static void calculateSymbolFeatures(FeatureRow row, List<KlineObjectSimple> symHistory,
                                               List<Double> symCloses) {

        if (symHistory == null || symHistory.size() < WARMUP) return;

        int i = symHistory.size() - 1; // index hien tai
        KlineObjectSimple kline = symHistory.get(i);

        // 1. Rate Changes
        row.sym_rate_change_5m = Utils.rateOf2Double(kline.priceClose, symHistory.get(i - P_5M).priceClose);
        row.sym_rate_change_15m = Utils.rateOf2Double(kline.priceClose, symHistory.get(i - P_15M).priceClose);
        row.sym_rate_change_60m = Utils.rateOf2Double(kline.priceClose, symHistory.get(i - P_60M).priceClose);

        // 2. So voi Dinh 30m
        double high30 = findMaxPrice(symHistory.subList(i - P_30M, i + 1));
        row.sym_rate_vs_high_30m = (kline.priceClose - high30) / high30;

        // 3. So voi BTC/ETH (Lay tu DataContext da cache)
        int global_i = DataContext.getTimestampIndex(kline.startTime.longValue());
        if (global_i == -1) return; // Khong tim thay timestamp

        double btc_rate_15m = Utils.rateOf2Double(
                DataContext.ALL_BTC_KLINES_LIST.get(global_i).priceClose,
                DataContext.ALL_BTC_KLINES_LIST.get(global_i - P_15M).priceClose);

        double eth_rate_15m = Utils.rateOf2Double(
                DataContext.ALL_ETH_KLINES_LIST.get(global_i).priceClose,
                DataContext.ALL_ETH_KLINES_LIST.get(global_i - P_15M).priceClose);

        row.sym_rate_vs_btc_15m = row.sym_rate_change_15m - btc_rate_15m;
        row.sym_rate_vs_eth_15m = row.sym_rate_change_15m - eth_rate_15m;

        // 4. TA
        row.sym_rsi_14_1m = TechnicalAnalysisUtils.calculateRSI(symHistory, RSI_PERIOD);
        row.sym_macd_hist_1m = calculateMACD(symCloses, MACD_FAST, MACD_SLOW, MACD_SIGNAL).get("hist");
        row.sym_atr_14_1m_percent = (kline.priceClose > 0)
                ? TechnicalAnalysisUtils.calculateATR(symHistory, 14) / kline.priceClose
                : 0;

        // 5. Bollinger Bands
        Map<String, Double> bb = TechnicalAnalysisUtils.calculateBollingerBands(symHistory, BB_PERIOD, 2.0);
        if (bb != null) {
            double upper = bb.get("UPPER");
            double lower = bb.get("LOWER");
            double middle = bb.get("MIDDLE");
            row.sym_bb_width_20_1m = (middle > 0) ? (upper - lower) / middle : 0;
            // Tinh BB Position
            row.sym_bb_position_20_1m = (upper > lower)
                    ? (kline.priceClose - lower) / (upper - lower) // Normal 0-1
                    : 0.5; // Neu band = 0
        }

        // 6. Volume vs SMA
        double smaVolume = calculateVolumeSMA(symHistory.subList(i - SMA_VOL_PERIOD, i + 1), SMA_VOL_PERIOD);
        row.sym_volume_1m_vs_sma_60m = (smaVolume > 0) ? kline.totalUsdt / smaVolume : 0;

        // 7. Wick Ratio
        row.sym_5m_candle_wick_ratio = calculateWickRatio(symHistory.subList(i - P_5M, i + 1));
    }

    public static String getCsvHeader() {
        return
                // Nhom 1 (9)
                "btc_rate_change_15m," +
                        "isTrendBuyWithBTC,isTrendBuyWithETH," +
                        "market_rate_down_avg_15m,top_symbols_down_15m_count," +
                        "hour_of_day_sin,hour_of_day_cos,day_of_week_sin,day_of_week_cos," +

                        // Nhom 2 (13)
                        "sym_rate_change_5m,sym_rate_change_15m,sym_rate_change_60m," +
                        "sym_rate_vs_high_30m,sym_rate_vs_btc_15m,sym_rate_vs_eth_15m," +
                        "sym_rsi_14_1m,sym_macd_hist_1m," +
                        "sym_bb_width_20_1m,sym_bb_position_20_1m," +
                        "sym_atr_14_1m_percent," +
                        "sym_volume_1m_vs_sma_60m,sym_5m_candle_wick_ratio," +

                        // Labels
                        "pnl_final,max_drawdown,time_to_profit," +
                        "debug_date,debug_symbol,debug_entry,debug_price_to_profit";
    }

    // --- Cac ham ho tro ---
    private static double findMaxPrice(List<KlineObjectSimple> klines) { double max = 0; for(KlineObjectSimple k:klines) max = Math.max(max, k.maxPrice); return max; }
    private static double findMinPrice(List<KlineObjectSimple> klines) { double min = Double.MAX_VALUE; for(KlineObjectSimple k:klines) min = Math.min(min, k.minPrice); return min; }
    private static boolean getTrend(String symbol, Long time) {
        Map<Long, Boolean> trendData = DataContext.CACHED_symbol2TrendData.get(symbol);
        if (trendData == null) return false;
        Boolean trend = trendData.get(Utils.getDate(time));
        return trend != null && trend;
    }

    /**
     * HAM MOI: Tinh SMA cho Volume
     */
    private static double calculateVolumeSMA(List<KlineObjectSimple> klines, int period) {
        if (klines == null || klines.size() < period) return 0.0;
        double sum = 0;
        for (int i = klines.size() - period; i < klines.size(); i++) {
            sum += klines.get(i).totalUsdt;
        }
        return sum / period;
    }

    /**
     * HAM MOI: Tinh ty le Wick cho 1 list klines (gop thanh 1 nen lon)
     */
    private static double calculateWickRatio(List<KlineObjectSimple> klines) {
        if (klines == null || klines.isEmpty()) return 0;

        double open = klines.get(0).priceOpen;
        double close = klines.get(klines.size() - 1).priceClose;
        double high = findMaxPrice(klines);
        double low = findMinPrice(klines);

        double body = Math.abs(open - close);
        double range = high - low;

        if (range == 0) return 0; // Tranh chia cho 0

        double wicks = range - body;
        return wicks / range;
    }

    // (Cac ham calculateSMA, calculateEMA, calculateMACD giu nguyen...)
    // ...
    public static double calculateSMA(List<Double> prices, int period) {
        if (prices == null || prices.size() < period) return 0.0;
        double sum = 0; for (int i=prices.size()-period; i<prices.size(); i++) sum += prices.get(i); return sum / period;
    }
    public static double calculateEMA(List<Double> prices, int period, double previousEMA) {
        double k = 2.0 / (period + 1); return (prices.get(prices.size()-1) - previousEMA) * k + previousEMA;
    }
    public static Map<String, Double> calculateMACD(List<Double> closePrices, int fast, int slow, int signal) {
        Map<String, Double> result = new HashMap<>(); result.put("macd",0.0); result.put("signal",0.0); result.put("hist",0.0);
        if (closePrices.size() < (slow + signal + 50)) return result;

        List<Double> emaFastList = new ArrayList<>();
        List<Double> emaSlowList = new ArrayList<>();
        List<Double> macdList = new ArrayList<>();
        List<Double> signalList = new ArrayList<>();

        double firstEmaFast = calculateSMA(closePrices.subList(0, fast), fast);
        double firstEmaSlow = calculateSMA(closePrices.subList(0, slow), slow);
        emaFastList.add(firstEmaFast);
        emaSlowList.add(firstEmaSlow);

        for (int i = fast; i < closePrices.size(); i++) {
            List<Double> subPricesFast = closePrices.subList(0, i + 1);
            List<Double> subPricesSlow = closePrices.subList(0, i + 1);
            if (i >= slow) {
                double emaSlow = calculateEMA(subPricesSlow, slow, emaSlowList.get(emaSlowList.size() - 1));
                emaSlowList.add(emaSlow);
            }
            double emaFast = calculateEMA(subPricesFast, fast, emaFastList.get(emaFastList.size() - 1));
            emaFastList.add(emaFast);
            if (i >= (slow - 1)) {
                macdList.add(emaFastList.get(emaFastList.size() - 1) - emaSlowList.get(emaSlowList.size() - 1));
            }
        }
        if (macdList.size() < signal) return result;
        double firstSignal = calculateSMA(macdList.subList(0, signal), signal);
        signalList.add(firstSignal);
        for (int i = signal; i < macdList.size(); i++) {
            List<Double> subMacd = macdList.subList(0, i + 1);
            double emaSignal = calculateEMA(subMacd, signal, signalList.get(signalList.size() - 1));
            signalList.add(emaSignal);
        }
        result.put("macd", macdList.get(macdList.size()-1));
        result.put("signal", signalList.get(signalList.size()-1));
        result.put("hist", macdList.get(macdList.size()-1) - signalList.get(signalList.size()-1));
        return result;
    }
}