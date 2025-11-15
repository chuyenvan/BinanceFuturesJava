package com.binance.chuyennd.ai_ml.extractor;

import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.TechnicalAnalysisUtils;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;

import java.util.*;

public class FeatureCalculator {

    private static final int WARMUP = MainFeatureExtractor.WARMUP_PERIOD;
    private static final int P_1M = 1;
    private static final int P_5M = 5;
    private static final int P_15M = 15;
    private static final int P_30M = 30;
    private static final int P_60M = 60;

    private static final int RSI_PERIOD = 14;
    private static final int BB_PERIOD = 20;
    private static final int MACD_FAST = 12;
    private static final int MACD_SLOW = 26;
    private static final int MACD_SIGNAL = 9;

    public static FeatureRow calculateFeatures(int i) {

        // Kiem tra du lieu co ban (200 phut)
        if (i < WARMUP) {
            return null;
        }

        FeatureRow row = new FeatureRow();
        long timestamp = DataContext.ALL_TIMESTAMPS_LIST.get(i);

        // !!! GAN DEBUG DATE !!!
        row.debug_date = Utils.normalizeDateYYYYMMDDHHmm(timestamp);

        KlineObjectSimple kline = DataContext.ALL_BTC_KLINES_LIST.get(i);
        List<KlineObjectSimple> klines_btc = DataContext.ALL_BTC_KLINES_LIST;
        List<Double> closes_btc = DataContext.ALL_BTC_CLOSE_PRICES_LIST;
        List<KlineObjectSimple> klines_eth = DataContext.ALL_ETH_KLINES_LIST;
        List<Double> closes_eth = DataContext.ALL_ETH_CLOSE_PRICES_LIST;

        // === NHOM 1: TRIGGER ===
        row.btc_rate_change_1m = Utils.rateOf2Double(kline.priceClose, kline.priceOpen);
        row.btc_rate_change_5m = Utils.rateOf2Double(kline.priceClose, klines_btc.get(i - P_5M).priceClose);
        row.btc_rate_change_15m = Utils.rateOf2Double(kline.priceClose, klines_btc.get(i - P_15M).priceClose);

        double high15 = findMaxPrice(klines_btc.subList(i - P_15M, i + 1));
        double high30 = findMaxPrice(klines_btc.subList(i - P_30M, i + 1));
        double high60 = findMaxPrice(klines_btc.subList(i - P_60M, i + 1));
        double low15 = findMinPrice(klines_btc.subList(i - P_15M, i + 1));

        row.btc_rate_vs_high_15m = (kline.priceClose - high15) / high15;
        row.btc_rate_vs_high_30m = (kline.priceClose - high30) / high30;
        row.btc_rate_vs_high_60m = (kline.priceClose - high60) / high60;
        row.btc_rate_vs_low_15m = (kline.priceClose - low15) / low15;

        row.btc_volume_1m_vs_sma_60m = 0.0;
        row.btc_5m_candle_wick_ratio = 0.0;

        // === NHOM 2: MACRO TREND ===
        row.isTrendBuyWithBTC = getTrend(Constants.SYMBOL_PAIR_BTC, timestamp) ? 1.0 : 0.0;
        row.isTrendBuyWithETH = getTrend(Constants.SYMBOL_PAIR_ETH, timestamp) ? 1.0 : 0.0;

        // === NHOM 3: MOMENTUM/VOL (TA) ===
        List<KlineObjectSimple> btcHistory = klines_btc.subList(i - WARMUP, i + 1);
        List<Double> btcCloseHistory = closes_btc.subList(i - WARMUP, i + 1);
        List<KlineObjectSimple> ethHistory = klines_eth.subList(i - WARMUP, i + 1);
        List<Double> ethCloseHistory = closes_eth.subList(i - WARMUP, i + 1);

        row.btc_rsi_14_1m = TechnicalAnalysisUtils.calculateRSI(btcHistory, RSI_PERIOD);
        row.btc_macd_hist_1m = calculateMACD(btcCloseHistory, MACD_FAST, MACD_SLOW, MACD_SIGNAL).get("hist");
        Map<String, Double> bb_btc = TechnicalAnalysisUtils.calculateBollingerBands(btcHistory, BB_PERIOD, 2.0);
        row.btc_bb_width_20_1m = (bb_btc.get("UPPER") - bb_btc.get("LOWER")) / bb_btc.get("MIDDLE");

        row.eth_rsi_14_1m = TechnicalAnalysisUtils.calculateRSI(ethHistory, RSI_PERIOD);
        row.eth_macd_hist_1m = calculateMACD(ethCloseHistory, MACD_FAST, MACD_SLOW, MACD_SIGNAL).get("hist");
        Map<String, Double> bb_eth = TechnicalAnalysisUtils.calculateBollingerBands(ethHistory, BB_PERIOD, 2.0);
        row.eth_bb_width_20_1m = (bb_eth.get("UPPER") - bb_eth.get("LOWER")) / bb_eth.get("MIDDLE");

        // === NHOM 4: MARKET CONTEXT ===
        MarketDataObject marketData = DataContext.CACHED_time2MarketData.get(timestamp);
        if (marketData == null) return null;
        row.market_rate_down_avg_1m = marketData.rateDownAvg;
        row.market_rate_down_avg_15m = marketData.rateDown15MAvg;
        row.market_rate_up_avg_1m = marketData.rateUpAvg;
        row.top_symbols_down_15m_count = (marketData.symbolsTopDown != null) ? marketData.symbolsTopDown.size() : 0.0;
        row.corr_btc_eth_1h = 0.0;

        // === NHOM 5: TIME ===
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

    public static void calculateSymbolFeatures(FeatureRow row, List<KlineObjectSimple> symHistory,
                                               List<Double> symCloses) {
        if (symHistory == null || symHistory.size() < WARMUP) return;
        KlineObjectSimple kline = symHistory.get(symHistory.size() - 1);

        // 1. Rate Changes
        row.sym_rate_change_1m = Utils.rateOf2Double(kline.priceClose, kline.priceOpen);
        row.sym_rate_change_5m = Utils.rateOf2Double(kline.priceClose, symHistory.get(symHistory.size() - P_5M).priceClose);
        row.sym_rate_change_15m = Utils.rateOf2Double(kline.priceClose, symHistory.get(symHistory.size() - P_15M).priceClose);

        // 2. So voi Dinh 30m
        double high30 = findMaxPrice(symHistory.subList(symHistory.size() - P_30M, symHistory.size()));
        row.sym_rate_vs_high_30m = (kline.priceClose - high30) / high30;

        // 3. So voi BTC
        row.sym_rate_vs_btc_15m = row.sym_rate_change_15m - row.btc_rate_change_15m;

        // 4. TA
        row.sym_rsi_14_1m = TechnicalAnalysisUtils.calculateRSI(symHistory, RSI_PERIOD);
        row.sym_macd_hist_1m = calculateMACD(symCloses, MACD_FAST, MACD_SLOW, MACD_SIGNAL).get("hist");

        Map<String, Double> bb = TechnicalAnalysisUtils.calculateBollingerBands(symHistory, BB_PERIOD, 2.0);
        if (bb != null) {
            row.sym_bb_width_20_1m = (bb.get("UPPER") - bb.get("LOWER")) / bb.get("MIDDLE");
        }

        double atr = TechnicalAnalysisUtils.calculateATR(symHistory, 14);
        row.sym_atr_14_1m_percent = (kline.priceClose > 0) ? atr / kline.priceClose : 0;

        // (DA XOA sym_volume_vs_sma_60m)
    }

    public static String getCsvHeader() {
        return
                "btc_rate_change_1m,btc_rate_change_5m,btc_rate_change_15m," +
                        "btc_rate_vs_high_15m,btc_rate_vs_high_30m,btc_rate_vs_high_60m,btc_rate_vs_low_15m," +
                        "btc_volume_1m_vs_sma_60m,btc_5m_candle_wick_ratio," +
                        "isTrendBuyWithBTC,isTrendBuyWithETH," +
                        "btc_rsi_14_1m,btc_macd_hist_1m,btc_bb_width_20_1m," +
                        "eth_rsi_14_1m,eth_macd_hist_1m,eth_bb_width_20_1m," +
                        "market_rate_down_avg_1m,market_rate_down_avg_15m,market_rate_up_avg_1m," +
                        "corr_btc_eth_1h,top_symbols_down_15m_count," +
                        "hour_of_day_sin,hour_of_day_cos,day_of_week_sin,day_of_week_cos," +

                        // Nhom 6
                        "sym_rate_change_1m,sym_rate_change_5m,sym_rate_change_15m," +
                        "sym_rate_vs_high_30m,sym_rate_vs_btc_15m," +
                        "sym_rsi_14_1m,sym_macd_hist_1m,sym_bb_width_20_1m," +
                        "sym_atr_14_1m_percent," + // (Da xoa volume)

                        "pnl_final,max_drawdown,time_to_profit," +
                        "debug_date,debug_symbol";
    }

    // --- Cac ham ho tro khac GIU NGUYEN ---
    private static double findMaxPrice(List<KlineObjectSimple> klines) { double max = 0; for(KlineObjectSimple k:klines) max = Math.max(max, k.maxPrice); return max; }
    private static double findMinPrice(List<KlineObjectSimple> klines) { double min = Double.MAX_VALUE; for(KlineObjectSimple k:klines) min = Math.min(min, k.minPrice); return min; }
    private static boolean getTrend(String symbol, Long time) {
        Map<Long, Boolean> trendData = DataContext.CACHED_symbol2TrendData.get(symbol);
        if (trendData == null) return false;
        Boolean trend = trendData.get(Utils.getDate(time));
        return trend != null && trend;
    }
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