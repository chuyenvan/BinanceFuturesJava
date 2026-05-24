package com.binance.chuyennd.ai_ml.features.export;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class HistoryManager15M {
    public static final Logger LOG = LoggerFactory.getLogger(HistoryManager15M.class);

    private static final int MAX_COINS = 1000;
    // Nến 15m: 512 nến = 128 giờ = 5.3 ngày (Đủ sức để tính MA/RSI/Vol 24H)
    private static final int RING_SIZE = 512;
    private static final int RING_MASK = 511;

    private static final long CLEANUP_INTERVAL = 24 * 60 * 60 * 1000L;
    private static final long ZOMBIE_THRESHOLD = 12 * 60 * 60 * 1000L; // Quá 12h ko có nến -> Zombie
    private long lastCleanTime = -1L;

    private static volatile HistoryManager15M INSTANCE = null;

    private final KlineObjectSimple[][] historyRing = new KlineObjectSimple[MAX_COINS][RING_SIZE];
    private final int[] historyHead = new int[MAX_COINS];
    private final long[] lastUpdateTime = new long[MAX_COINS];

    private final Set<String> symbolsLastUpdate = new HashSet<>();
    private final Set<Short> symbolsLastUpdateShort = new HashSet<>();

    private HistoryManager15M() {
    }

    public static HistoryManager15M getInstance() {
        if (INSTANCE == null) {
            synchronized (HistoryManager15M.class) {
                if (INSTANCE == null) INSTANCE = new HistoryManager15M();
            }
        }
        return INSTANCE;
    }

    // Thay đổi đầu vào thành Map<Short, ...>
    public void updateHistory(Map<Short, KlineObjectSimple> snapshot) {
        symbolsLastUpdateShort.clear();

        if (snapshot.isEmpty()) return;
        long currentTime = snapshot.values().iterator().next().startTime.longValue();
        checkAndCleanup(currentTime);

        for (Map.Entry<Short, KlineObjectSimple> entry : snapshot.entrySet()) {
            short symbolId = entry.getKey();
            if (symbolId >= MAX_COINS) continue;

            symbolsLastUpdateShort.add(symbolId);
            processKline(symbolId, entry.getValue()); // Nạp trực tiếp ID vào mảng O(1)
        }
    }

    private void processKline(short symbolId, KlineObjectSimple kline) {
        int head = historyHead[symbolId];
        if (head > 0) {
            KlineObjectSimple lastKline = historyRing[symbolId][(head - 1) & RING_MASK];
            if (lastKline != null && lastKline.startTime.longValue() == kline.startTime.longValue()) {
                head--;
            }
        }
        historyRing[symbolId][head & RING_MASK] = kline;
        historyHead[symbolId] = head + 1;
        lastUpdateTime[symbolId] = kline.startTime;
    }

    private void checkAndCleanup(long currentTime) {
        if (lastCleanTime == -1L) lastCleanTime = currentTime;
        else if (currentTime - lastCleanTime >= CLEANUP_INTERVAL) {
            for (short id = 0; id < MAX_COINS; id++) {
                if (historyHead[id] > 0 && currentTime - lastUpdateTime[id] >= ZOMBIE_THRESHOLD) {
                    historyHead[id] = 0;
                    lastUpdateTime[id] = 0;
                }
            }
            lastCleanTime = currentTime;
        }
    }

    public Float getPriceAt(short symbolId, long timestamp) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return null;
        int head = historyHead[symbolId] - 1;

        for (int i = 0; i < count; i++) {
            KlineObjectSimple k = historyRing[symbolId][(head - i) & RING_MASK];
            if (k.startTime.longValue() <= timestamp) {
                // Nến 15m, chênh lệch tối đa 45 phút
                if (timestamp - k.startTime.longValue() > 45 * 60000L) return null;
                return k.priceClose;
            }
        }
        return null;
    }

    public Float getRsi14(short symbolId) {
        int period = 14;
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count <= period) return 50.0f;

        float gain = 0.0f, loss = 0.0f;
        int head = historyHead[symbolId] - 1;

        for (int i = period; i > 0; i--) {
            KlineObjectSimple prev = historyRing[symbolId][(head - i) & RING_MASK];
            KlineObjectSimple curr = historyRing[symbolId][(head - i + 1) & RING_MASK];
            float change = curr.priceClose - prev.priceClose;
            if (change > 0) gain += change;
            else loss -= change;
        }
        float avgGain = gain / period, avgLoss = loss / period;
        if (avgLoss == 0) return 100.0f;
        return 100.0f - (100.0f / (1.0f + (avgGain / avgLoss)));
    }

    public Float getMa(short symbolId, int period) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count < period) return null;
        float sum = 0;
        int head = historyHead[symbolId] - 1;
        for (int i = 0; i < period; i++) sum += historyRing[symbolId][(head - i) & RING_MASK].priceClose;
        return sum / period;
    }

    public Float getLow24H(short symbolId) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return null;
        int lookback = Math.min(count, 96); // 24H = 96 nến 15M
        float minPrice = Float.MAX_VALUE;
        int head = historyHead[symbolId] - 1;
        for (int i = 0; i < lookback; i++) {
            float price = historyRing[symbolId][(head - i) & RING_MASK].minPrice;
            if (price < minPrice) minPrice = price;
        }
        return minPrice == Float.MAX_VALUE ? null : minPrice;
    }

    public float getSumVolume(short symbolId, int periods) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return 0.0f;
        float sum = 0;
        int lookback = Math.min(count, periods);
        int head = historyHead[symbolId] - 1;
        for (int i = 0; i < lookback; i++) sum += historyRing[symbolId][(head - i) & RING_MASK].totalUsdt;
        return sum;
    }

    public float getAverageVolume(short symbolId, int periods) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count < periods) return 0.0f;
        float totalVol = 0;
        int startIndex = historyHead[symbolId] - 2;
        if (startIndex < 0) return 0.0f;
        int validCount = 0;
        for (int i = 0; i < periods; i++) {
            int idx = startIndex - i;
            if (idx >= 0) {
                totalVol += historyRing[symbolId][idx & RING_MASK].totalUsdt;
                validCount++;
            }
        }
        return validCount == 0 ? 0.0f : totalVol / validCount;
    }

    public List<Short> findPotentialLosersShort(long currentTimestamp) {
        List<Map.Entry<Short, Float>> drops = new ArrayList<>();
        long startTime = currentTimestamp - (4 * 60 * 60 * 1000L); // Nhìn về 4H trước

        for (short id = 0; id < MAX_COINS; id++) {
            int count = Math.min(historyHead[id], RING_SIZE);
            if (count == 0) continue;

            int head = historyHead[id] - 1;
            KlineObjectSimple currentKline = historyRing[id][head & RING_MASK];
            if (currentKline.totalUsdt < 50000) continue; // Nến 15m volume phải cao hơn

            float maxPrice4h = -1.0f;
            for (int i = 0; i < count; i++) {
                KlineObjectSimple k = historyRing[id][(head - i) & RING_MASK];
                if (k.startTime < startTime) break;
                if (k.maxPrice > maxPrice4h) maxPrice4h = k.maxPrice;
            }

            if (maxPrice4h > 0) {
                float dropFromPeak = (currentKline.priceClose - maxPrice4h) / maxPrice4h;
                if (dropFromPeak < -0.005) { // Đòi hỏi nhịp rơi mạnh hơn ở 15m
                    drops.add(new AbstractMap.SimpleEntry<>(id, dropFromPeak));
                }
            }
        }

        drops.sort(Map.Entry.comparingByValue());
        List<Short> result = new ArrayList<>();
        for (int i = 0; i < Math.min(60, drops.size()); i++) result.add(drops.get(i).getKey());
        return result;
    }

    public List<String> findPotentialLosers(long currentTimestamp) {
        List<Short> ids = findPotentialLosersShort(currentTimestamp);
        List<String> result = new ArrayList<>(ids.size());
        for (Short id : ids) result.add(SimpleSymbolMapper.getInstance().getSymbol(id));
        return result;
    }

    public void resetCache() {
        Arrays.fill(historyHead, 0);
        Arrays.fill(lastUpdateTime, 0L);
        symbolsLastUpdate.clear();
        symbolsLastUpdateShort.clear();
        lastCleanTime = -1L;
    }

    public Set<Short> getAllSymbolsShort() {
        return symbolsLastUpdateShort;
    }

    public Float getPriceAt(String symbol, long timestamp) {
        return getPriceAt(SimpleSymbolMapper.getInstance().getId(symbol), timestamp);
    }

    // =========================================================================
    // 🔥 ĐÃ BỔ SUNG: HÀM TÍNH BIÊN ĐỘ TRUNG BÌNH O(1) CHO HỆ 15M THUẦN SHORT ID
    // =========================================================================
    public float getAverageRange(String symbol, int periods) {
        return getAverageRange(SimpleSymbolMapper.getInstance().getId(symbol), periods);
    }

    public float getAverageRange(short symbolId, int periods) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count < periods) return 0.0f;

        float totalRange = 0;
        int startIndex = historyHead[symbolId] - 2; // list.size() - 2 (Lùi 1 bước tránh lấy nến đang chạy)
        if (startIndex < 0) return 0.0f;

        int validCount = 0;
        for (int i = 0; i < periods; i++) {
            int idx = startIndex - i;
            if (idx >= 0) {
                KlineObjectSimple k = historyRing[symbolId][idx & RING_MASK];
                if (k != null) {
                    totalRange += (k.maxPrice - k.minPrice);
                    validCount++;
                }
            }
        }
        return validCount == 0 ? 0.0f : totalRange / validCount;
    }
}