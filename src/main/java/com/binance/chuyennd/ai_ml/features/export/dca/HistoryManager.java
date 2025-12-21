package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.stream.Collectors;

public class HistoryManager {
    private static final Logger LOG = LoggerFactory.getLogger(HistoryManager.class);

    // Lưu trữ lịch sử nến: Symbol -> List Nến (Sắp xếp theo thời gian tăng dần)
    // Giữ lại khoảng 2000 nến (hơn 24h một chút để tính toán an toàn)
    private final Map<String, LinkedList<KlineObjectSimple>> historyMap = new HashMap<>();
    private static final int MAX_HISTORY_SIZE = 2000;

    public void updateHistory(Map<String, KlineObjectSimple> snapshot) {
        for (Map.Entry<String, KlineObjectSimple> entry : snapshot.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple kline = entry.getValue();

            LinkedList<KlineObjectSimple> list = historyMap.computeIfAbsent(symbol, k -> new LinkedList<>());

            // Tránh duplicate nếu update cùng 1 timestamp (trường hợp data stream bị lặp)
            if (!list.isEmpty() && list.getLast().startTime.equals(kline.startTime)) {
                list.removeLast();
            }

            list.add(kline);

            // Trim bớt nếu quá dài để tiết kiệm RAM
            if (list.size() > MAX_HISTORY_SIZE) {
                list.removeFirst();
            }
        }
    }

    public List<KlineObjectSimple> getHistory(String symbol) {
        return historyMap.get(symbol);
    }

    // --- CÁC HÀM TRUY XUẤT GIÁ TRỊ QUÁ KHỨ ---

    public Double getPriceAt(String symbol, long timestamp) {
        LinkedList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.isEmpty()) return null;

        // Tìm nến có startTime gần nhất với timestamp yêu cầu
        // Do list đã sort, ta tìm ngược từ cuối lên sẽ nhanh hơn cho các yêu cầu gần đây
        for (int i = list.size() - 1; i >= 0; i--) {
            KlineObjectSimple k = list.get(i);
            if (k.startTime <= timestamp) {
                // Nếu khoảng cách thời gian quá lớn (ví dụ data bị lủng), trả về null
                if (timestamp - k.startTime > 300000) return null; // 5 phút lệch
                return k.priceClose;
            }
        }
        return null; // Không tìm thấy data quá khứ đó
    }

    // --- CÁC HÀM TÍNH INDICATOR ---

    public Double getRsi14(String symbol) {
        LinkedList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.size() < 15) return 50.0; // Mặc định 50 nếu thiếu data

        return calculateRSI(list, 14);
    }

    public Double getMa(String symbol, int period) {
        LinkedList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.size() < period) return null;

        double sum = 0;
        for (int i = 0; i < period; i++) {
            sum += list.get(list.size() - 1 - i).priceClose;
        }
        return sum / period;
    }

    public Double getLow24H(String symbol) {
        LinkedList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.isEmpty()) return null;

        // 24h = 1440 phút
        int lookback = Math.min(list.size(), 1440);
        double minPrice = Double.MAX_VALUE;

        for (int i = 0; i < lookback; i++) {
            double price = list.get(list.size() - 1 - i).minPrice;
            if (price < minPrice) minPrice = price;
        }
        return minPrice == Double.MAX_VALUE ? null : minPrice;
    }

    public Double getMaxRateChange(String symbol, int minutes) {
        LinkedList<KlineObjectSimple> list = historyMap.get(symbol);
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

    // --- [MỚI] Hỗ trợ Volume Spike ---
    public double getAverageVolume(String symbol, int periods) {
        LinkedList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.size() < periods) return 0.0;

        double totalVol = 0;
        // Lấy trung bình của N cây nến TRƯỚC cây hiện tại (để so sánh cây hiện tại với quá khứ)
        // size-1 là cây hiện tại, nên ta lấy từ size-2 trở về sau
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

    // --- [MỚI] Hỗ trợ Volatility Shock ---
    public double getAverageRange(String symbol, int periods) {
        LinkedList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list == null || list.size() < periods) return 0.0;

        double totalRange = 0;
        int startIndex = list.size() - 2; // Tương tự, lấy nến quá khứ
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

    public double getVolumeAnomaly(String symbol) {
        // Hàm cũ, có thể tái sử dụng logic getAverageVolume
        double currentVol = 0;
        LinkedList<KlineObjectSimple> list = historyMap.get(symbol);
        if (list != null && !list.isEmpty()) currentVol = list.getLast().totalUsdt;

        double avg = getAverageVolume(symbol, 20);
        if (avg == 0) return 1.0;
        return currentVol / avg;
    }

    // --- Helper: Tính RSI ---
    private Double calculateRSI(List<KlineObjectSimple> data, int period) {
        if (data.size() <= period) return 50.0;

        double gain = 0.0;
        double loss = 0.0;

        // Tính RSI ban đầu
        for (int i = data.size() - period - 1; i < data.size() - 1; i++) {
            double change = data.get(i + 1).priceClose - data.get(i).priceClose;
            if (change > 0) {
                gain += change;
            } else {
                loss -= change;
            }
        }

        double avgGain = gain / period;
        double avgLoss = loss / period;

        // Smooth RSI (Wilder's Smoothing) - Lấy giá trị gần nhất để chính xác hơn
        // Ở đây dùng Simple RSI cho nhanh, nếu muốn chính xác Wilders cần lưu state
        // Với mục đích Machine Learning, Simple RSI trên window trượt là đủ tốt.

        if (avgLoss == 0) return 100.0;
        double rs = avgGain / avgLoss;
        return 100.0 - (100.0 / (1.0 + rs));
    }
    public List<String> findPotentialLosers(long currentTimestamp) {
        List<Map.Entry<String, Double>> drops = new ArrayList<>();
        long startTime = currentTimestamp - (15 * 60 * 1000L); // 15 phút trước

        for (Map.Entry<String, LinkedList<KlineObjectSimple>> entry : historyMap.entrySet()) {
            String symbol = entry.getKey();
            LinkedList<KlineObjectSimple> history = entry.getValue();

            if (history == null || history.isEmpty()) continue;

            KlineObjectSimple currentKline = history.getLast();

            // 1. Lọc Volume rác (< 50k USDT) - Giữ đúng logic Entry
            // (Lưu ý: Nếu muốn bắt coin nhỏ hơn cho DCA thì có thể giảm xuống 5000 như bạn từng chỉnh)
            if (currentKline.totalUsdt < 50000) continue;

            // 2. Tìm đỉnh giá trong 15 phút gần nhất từ History
            double maxPrice15m = -1.0;

            // Duyệt ngược từ cuối lên
            Iterator<KlineObjectSimple> it = history.descendingIterator();
            while (it.hasNext()) {
                KlineObjectSimple k = it.next();
                if (k.startTime < startTime) break; // Đã quá 15p thì dừng
                if (k.maxPrice > maxPrice15m) {
                    maxPrice15m = k.maxPrice;
                }
            }

            // 3. Tính độ sụt giảm
            if (maxPrice15m > 0) {
                double currentPrice = currentKline.priceClose;
                double dropFromPeak = (currentPrice - maxPrice15m) / maxPrice15m;

                // Giảm > 0.1% là lấy (Logic Relaxed từ Entry)
                if (dropFromPeak < -0.001) {
                    drops.add(new AbstractMap.SimpleEntry<>(symbol, dropFromPeak));
                }
            }
        }

        // Sort giảm dần theo mức giảm (giảm nhiều nhất lên đầu)
        drops.sort(Map.Entry.comparingByValue());

        // Lấy Top 60 coin giảm mạnh nhất làm "Market Context"
        return drops.stream()
                .limit(60)
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
    }
}