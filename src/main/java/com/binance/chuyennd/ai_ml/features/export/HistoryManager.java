package com.binance.chuyennd.ai_ml.features.export;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.stream.Collectors;

public class HistoryManager {
    private static final Logger LOG = LoggerFactory.getLogger(HistoryManager.class);

    // 🔥 GIỮ SIZE 2000 ĐỂ TIẾT KIỆM RAM
    private static final int MAX_HISTORY_SIZE = 2000;

    // 🔥 DÙNG ARRAYLIST CHO TỐC ĐỘ TRUY XUẤT O(1)
    private final Map<String, ArrayList<KlineObjectSimple>> historyMap = new HashMap<>();

    public void updateHistory(Map<String, KlineObjectSimple> snapshot) {
        for (Map.Entry<String, KlineObjectSimple> entry : snapshot.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple kline = entry.getValue();

            ArrayList<KlineObjectSimple> list = historyMap.computeIfAbsent(symbol, k -> new ArrayList<>());

            // Logic check duplicate (Thay removeLast bằng remove index cuối)
            if (!list.isEmpty() && list.get(list.size() - 1).startTime.equals(kline.startTime)) {
                list.remove(list.size() - 1);
            }

            list.add(kline);

            // Logic trim size (Thay removeFirst bằng remove index 0)
            if (list.size() > MAX_HISTORY_SIZE) {
                list.remove(0);
            }
        }
    }

    public List<KlineObjectSimple> getHistory(String symbol) {
        return historyMap.get(symbol);
    }

    // --- CÁC HÀM TRUY XUẤT ---

    public Double getPriceAt(String symbol, long timestamp) {
        ArrayList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.isEmpty()) return null;

        // Duyệt ngược từ cuối mảng
        for (int i = list.size() - 1; i >= 0; i--) {
            KlineObjectSimple k = list.get(i);
            if (k.startTime <= timestamp) {
                if (timestamp - k.startTime > 300000) return null;
                return k.priceClose;
            }
        }
        return null;
    }

    public Double getHighInPeriod(String symbol, int minutesLookback) {
        ArrayList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.isEmpty()) return null;

        int lookback = Math.min(list.size(), minutesLookback);
        double maxPrice = -1.0;

        for (int i = 0; i < lookback; i++) {
            // Lấy từ cuối list về trước
            double p = list.get(list.size() - 1 - i).maxPrice;
            if (p > maxPrice) maxPrice = p;
        }
        return (maxPrice == -1.0) ? null : maxPrice;
    }

    // --- INDICATORS (ArrayList get(index) cực nhanh) ---

    public Double getRsi14(String symbol) {
        ArrayList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.size() < 15) return 50.0;
        return calculateRSI(list, 14);
    }

    public Double getMa(String symbol, int period) {
        ArrayList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.size() < period) return null;
        double sum = 0;
        for (int i = 0; i < period; i++) {
            sum += list.get(list.size() - 1 - i).priceClose;
        }
        return sum / period;
    }

    public Double getLow24H(String symbol) {
        ArrayList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.isEmpty()) return null;
        int lookback = Math.min(list.size(), 1440);
        double minPrice = Double.MAX_VALUE;
        for (int i = 0; i < lookback; i++) {
            double price = list.get(list.size() - 1 - i).minPrice;
            if (price < minPrice) minPrice = price;
        }
        return minPrice == Double.MAX_VALUE ? null : minPrice;
    }

    public Double getMaxRateChange(String symbol, int minutes) {
        ArrayList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.size() < 2) return 0.0;
        int lookback = Math.min(list.size(), minutes);
        double maxP = -1.0;
        double minP = Double.MAX_VALUE;
        for (int i = 0; i < lookback; i++) {
            KlineObjectSimple k = list.get(list.size() - 1 - i);
            if (k.maxPrice > maxP) maxP = k.maxPrice;
            if (k.minPrice < minP) minP = k.minPrice;
        }
        if (minP == 0 || minP == Double.MAX_VALUE) return 0.0;
        return (maxP - minP) / minP;
    }

    // --- VOLUME INDICATORS ---

    public double getSumVolume(String symbol, int minutes) {
        ArrayList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.isEmpty()) return 0.0;
        double sum = 0;
        int lookback = Math.min(list.size(), minutes);
        for (int i = 0; i < lookback; i++) {
            sum += list.get(list.size() - 1 - i).totalUsdt;
        }
        return sum;
    }

    public double getAverageVolume(String symbol, int periods) {
        ArrayList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.size() < periods) return 0.0;
        double totalVol = 0;
        int startIndex = list.size() - 2;
        if (startIndex < 0) return 0.0;
        int count = 0;
        for (int i = 0; i < periods; i++) {
            int idx = startIndex - i;
            if (idx >= 0) {
                totalVol += list.get(idx).totalUsdt;
                count++;
            }
        }
        return count == 0 ? 0.0 : totalVol / count;
    }

    public double getAverageRange(String symbol, int periods) {
        ArrayList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.size() < periods) return 0.0;
        double totalRange = 0;
        int startIndex = list.size() - 2;
        if (startIndex < 0) return 0.0;
        int count = 0;
        for (int i = 0; i < periods; i++) {
            int idx = startIndex - i;
            if (idx >= 0) {
                KlineObjectSimple k = list.get(idx);
                totalRange += (k.maxPrice - k.minPrice);
                count++;
            }
        }
        return count == 0 ? 0.0 : totalRange / count;
    }

    // --- HELPER RSI ---
    private Double calculateRSI(List<KlineObjectSimple> data, int period) {
        if (data.size() <= period) return 50.0;
        double gain = 0.0;
        double loss = 0.0;
        for (int i = data.size() - period - 1; i < data.size() - 1; i++) {
            double change = data.get(i + 1).priceClose - data.get(i).priceClose;
            if (change > 0) gain += change;
            else loss -= change;
        }
        double avgGain = gain / period;
        double avgLoss = loss / period;
        if (avgLoss == 0) return 100.0;
        double rs = avgGain / avgLoss;
        return 100.0 - (100.0 / (1.0 + rs));
    }

    // --- BASKET FINDER (Sửa lỗi descendingIterator) ---
    public List<String> findPotentialLosers(long currentTimestamp) {
        List<Map.Entry<String, Double>> drops = new ArrayList<>();
        long startTime = currentTimestamp - (15 * 60 * 1000L);

        for (Map.Entry<String, ArrayList<KlineObjectSimple>> entry : historyMap.entrySet()) {
            String symbol = entry.getKey();
            ArrayList<KlineObjectSimple> history = entry.getValue();
            if (history == null || history.isEmpty()) continue;

            KlineObjectSimple currentKline = history.get(history.size() - 1);

            // Filter Volume 5k
            if (currentKline.totalUsdt < 5000) continue;

            double maxPrice15m = -1.0;

            // 🔥 SỬA LỖI: Thay Iterator bằng vòng lặp ngược
            for (int i = history.size() - 1; i >= 0; i--) {
                KlineObjectSimple k = history.get(i);
                if (k.startTime < startTime) break;
                if (k.maxPrice > maxPrice15m) maxPrice15m = k.maxPrice;
            }

            if (maxPrice15m > 0) {
                double dropFromPeak = (currentKline.priceClose - maxPrice15m) / maxPrice15m;
                if (dropFromPeak < -0.001) {
                    drops.add(new AbstractMap.SimpleEntry<>(symbol, dropFromPeak));
                }
            }
        }

        drops.sort(Map.Entry.comparingByValue());
        return drops.stream().limit(60).map(Map.Entry::getKey).collect(Collectors.toList());
    }
}