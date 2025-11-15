package com.binance.chuyennd.ai_ml.extractor;

import com.binance.chuyennd.object.sw.KlineObjectSimple;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class LabelSimulator {

    private static final int SIMULATION_PERIOD_MINUTES = MainFeatureExtractor.SIMULATION_PERIOD_MINUTES;

    /**
     * HAM MOI: Tinh Label khi da co Data (khong can load lai)
     */
    public static LabelResult calculateSingleSymbolLabel_WithData(TreeMap<Long, KlineObjectSimple> symbolData, long currentTimestamp) {

        if (symbolData == null || symbolData.isEmpty()) return null;

        // Tim entry point
        KlineObjectSimple entryKline = symbolData.get(currentTimestamp);
        if (entryKline == null) return null; // Khong co data tai dung phut do

        double entryPrice = entryKline.priceClose;
        if (entryPrice < 0.0000001) return null;

        double maxFuturePrice = entryPrice;
        double minFuturePrice = entryPrice;
        double timeToProfit = 0;

        // Chuyen map values thanh list de duyet tuong lai
        // Can loc lay cac kline > currentTimestamp
        List<KlineObjectSimple> klines = new ArrayList<>();
        for(Map.Entry<Long, KlineObjectSimple> e : symbolData.tailMap(currentTimestamp, false).entrySet()) {
            klines.add(e.getValue());
            if (klines.size() >= SIMULATION_PERIOD_MINUTES) break;
        }

        if (klines.isEmpty()) return null;

        // Lap qua tuong lai
        for (int i = 0; i < klines.size(); i++) {
            KlineObjectSimple k = klines.get(i);
            if (k.maxPrice > maxFuturePrice) {
                maxFuturePrice = k.maxPrice;
                timeToProfit = i + 1;
            }
            if (k.minPrice < minFuturePrice) {
                minFuturePrice = k.minPrice;
            }
        }

        double pnl_final = (maxFuturePrice - entryPrice) / entryPrice;
        double max_drawdown = (minFuturePrice - entryPrice) / entryPrice;

        return new LabelResult(pnl_final, max_drawdown, timeToProfit);
    }

    // ... (Cac ham khac nhu calculateSingleSymbolLabel cu, loadFutureData... giu nguyen neu can) ...

    public static class LabelResult {
        public double pnl_final;
        public double max_drawdown;
        public double time_to_profit;

        public LabelResult(double pnl_final, double max_drawdown, double time_to_profit) {
            this.pnl_final = pnl_final;
            this.max_drawdown = max_drawdown;
            this.time_to_profit = time_to_profit;
        }
    }
}