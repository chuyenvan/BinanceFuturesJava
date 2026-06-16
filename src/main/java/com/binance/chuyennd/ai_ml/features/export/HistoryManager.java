package com.binance.chuyennd.ai_ml.features.export;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class HistoryManager {
    public static final Logger LOG = LoggerFactory.getLogger(HistoryManager.class);

    // 🔥 RING BUFFER CONSTANTS
    private static final int MAX_COINS = 1000;
    private static final int RING_SIZE = 2048; // Phải là lũy thừa của 2 để dùng Bitwise
    private static final int RING_MASK = 2047; // Tương đương (RING_SIZE - 1)

    private static final long CLEANUP_INTERVAL = 24 * 60 * 60 * 1000L;
    private static final long ZOMBIE_THRESHOLD = 4 * 60 * 60 * 1000L;
    private long lastCleanTime = -1L;

    private static volatile HistoryManager INSTANCE = null;

    // ========================================================
    // 🔥 CHIẾN LƯỢC ZERO-ALLOCATION CIRCULAR RING BUFFER O(1)
    // ========================================================
    private final KlineObjectSimple[][] historyRing = new KlineObjectSimple[MAX_COINS][RING_SIZE];
    private final int[] historyHead = new int[MAX_COINS]; // Con trỏ lưu số lượng nến đã nạp
    private final long[] lastUpdateTime = new long[MAX_COINS]; // Lưu thời gian cập nhật để quét Zombie

    private final Set<String> symbolsLastUpdate = new HashSet<>();
    private final Set<Short> symbolsLastUpdateShort = new HashSet<>();

    private HistoryManager() {}

    public static HistoryManager getInstance() {
        if (INSTANCE == null) {
            synchronized (HistoryManager.class) {
                if (INSTANCE == null) {
                    INSTANCE = new HistoryManager();
                }
            }
        }
        return INSTANCE;
    }

    // ========================================================
    // 1. NHÓM HÀM CẬP NHẬT (HỖ TRỢ STRING VÀ ARRAY)
    // ========================================================

    public void updateHistory(Map<String, KlineObjectSimple> snapshot) {
        symbolsLastUpdate.clear();
        symbolsLastUpdateShort.clear();
        symbolsLastUpdate.addAll(snapshot.keySet());

        if (snapshot.isEmpty()) return;
        long currentTime = snapshot.values().iterator().next().startTime.longValue();
        checkAndCleanup(currentTime);

        for (Map.Entry<String, KlineObjectSimple> entry : snapshot.entrySet()) {
            String symbol = entry.getKey();
            short symbolId = SimpleSymbolMapper.getInstance().getId(symbol);
            if (symbolId >= MAX_COINS) continue; // Bảo vệ mảng

            symbolsLastUpdateShort.add(symbolId);
            processKline(symbolId, entry.getValue());
        }
    }

    public void updateHistoryArray(KlineObjectSimple[] snapshot) {
        symbolsLastUpdateShort.clear();
        symbolsLastUpdate.clear();
        long currentTime = -1;

        for (short symbolId = 0; symbolId < snapshot.length && symbolId < MAX_COINS; symbolId++) {
            KlineObjectSimple kline = snapshot[symbolId];
            if (kline != null) {
                if (currentTime == -1) currentTime = kline.startTime;
                symbolsLastUpdateShort.add(symbolId);
                String symbolStr = com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper.getInstance().getSymbol(symbolId);
                symbolsLastUpdate.add(symbolStr);

                processKline(symbolId, kline);
            }
        }
        if (currentTime != -1) checkAndCleanup(currentTime);
    }

    /**
     * Logic lõi cập nhật nến O(1) tuyệt đối trên Ring Buffer
     */
    private void processKline(short symbolId, KlineObjectSimple kline) {
        int head = historyHead[symbolId];

        // Giữ nguyên logic cũ: Nếu nến mới có cùng startTime với nến cuối cùng -> Xóa/Ghi đè nến cuối
        if (head > 0) {
            KlineObjectSimple lastKline = historyRing[symbolId][(head - 1) & RING_MASK];
            if (lastKline != null && lastKline.startTime.longValue() == kline.startTime.longValue()) {
                head--; // Lùi con trỏ lại 1 bước để ghi đè
            }
        }

        historyRing[symbolId][head & RING_MASK] = kline;
        historyHead[symbolId] = head + 1;
        lastUpdateTime[symbolId] = kline.startTime;
    }

    private void checkAndCleanup(long currentTime) {
        if (lastCleanTime == -1L) {
            lastCleanTime = currentTime;
        } else if (currentTime - lastCleanTime >= CLEANUP_INTERVAL) {
            cleanupZombieCoins(currentTime);
            lastCleanTime = currentTime;
        }
    }

    private void cleanupZombieCoins(long currentTime) {
        for (short id = 0; id < MAX_COINS; id++) {
            if (historyHead[id] > 0) {
                if (currentTime - lastUpdateTime[id] >= ZOMBIE_THRESHOLD) {
                    historyHead[id] = 0; // Đưa con trỏ về 0 (Tương đương clear list)
                    lastUpdateTime[id] = 0;
                }
            }
        }
    }

    // ========================================================
    // 2. NHÓM HÀM TRUY XUẤT THÔNG DỤNG (XỬ LÝ QUA ID CHO NHANH)
    // ========================================================

    // Chuyển String thành ID để gọi hàm lõi
    public Float getPriceAt(String symbol, long timestamp) { return getPriceAt(SimpleSymbolMapper.getInstance().getId(symbol), timestamp); }
    public Float getRsi14(String symbol) { return getRsi14(SimpleSymbolMapper.getInstance().getId(symbol)); }
    public Float getMa(String symbol, int period) { return getMa(SimpleSymbolMapper.getInstance().getId(symbol), period); }
    public Float getLow24H(String symbol) { return getLow24H(SimpleSymbolMapper.getInstance().getId(symbol)); }
    public Float getHigh24H(String symbol) { return getHigh24H(SimpleSymbolMapper.getInstance().getId(symbol)); }
    public Float getMaxRateChange(String symbol, int minutes) { return getMaxRateChange(SimpleSymbolMapper.getInstance().getId(symbol), minutes); }
    public float getSumVolume(String symbol, int minutes) { return getSumVolume(SimpleSymbolMapper.getInstance().getId(symbol), minutes); }
    public float getAverageVolume(String symbol, int periods) { return getAverageVolume(SimpleSymbolMapper.getInstance().getId(symbol), periods); }
    public float getAverageRange(String symbol, int periods) { return getAverageRange(SimpleSymbolMapper.getInstance().getId(symbol), periods); }
    public float getVolumeZScore(String symbol, int periods) { return getVolumeZScore(SimpleSymbolMapper.getInstance().getId(symbol), periods); }

    public Set<String> getAllSymbols() { return symbolsLastUpdate; }

    public Set<Short> getAllSymbolsShort() { return symbolsLastUpdateShort; }

    // ========================================================
    // 3. LOGIC TÍNH TOÁN LÕI TRÊN RING BUFFER (Giữ chuẩn 100% logic cũ)
    // ========================================================

    public Float getPriceAt(short symbolId, long timestamp) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return null;
        int head = historyHead[symbolId] - 1; // Vị trí nến mới nhất

        for (int i = 0; i < count; i++) {
            KlineObjectSimple k = historyRing[symbolId][(head - i) & RING_MASK];
            if (k.startTime.longValue() <= timestamp) {
                if (timestamp - k.startTime.longValue() > 1800000L) return null;
                return k.priceClose;
            }
        }
        return null;
    }

    public Float getRsi14(short symbolId) {
        int period = 14;
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count <= period) return 50.0f;

        float gain = 0.0f;
        float loss = 0.0f;
        int head = historyHead[symbolId] - 1;

        // Vòng lặp chạy từ quá khứ đến hiện tại trong cửa sổ period
        for (int i = period; i > 0; i--) {
            KlineObjectSimple prev = historyRing[symbolId][(head - i) & RING_MASK];
            KlineObjectSimple curr = historyRing[symbolId][(head - i + 1) & RING_MASK];

            float change = curr.priceClose - prev.priceClose;
            if (change > 0) gain += change;
            else loss -= change;
        }

        float avgGain = gain / period;
        float avgLoss = loss / period;
        if (avgLoss == 0) return 100.0f;
        float rs = avgGain / avgLoss;
        return 100.0f - (100.0f / (1.0f + rs));
    }

    public Float getMa(short symbolId, int period) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count < period) return null;

        float sum = 0;
        int head = historyHead[symbolId] - 1;
        for (int i = 0; i < period; i++) {
            sum += historyRing[symbolId][(head - i) & RING_MASK].priceClose;
        }
        return sum / period;
    }

    public Float getLow24H(short symbolId) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return null;

        int lookback = Math.min(count, 1440);
        float minPrice = Float.MAX_VALUE;
        int head = historyHead[symbolId] - 1;

        for (int i = 0; i < lookback; i++) {
            float price = historyRing[symbolId][(head - i) & RING_MASK].minPrice;
            if (price < minPrice) minPrice = price;
        }
        return minPrice == Float.MAX_VALUE ? null : minPrice;
    }

    /**
     * Giá cao nhất 24h (đối xứng {@link #getLow24H(short)}): max của maxPrice trên ≤1440 nến gần nhất.
     * Chỉ dùng dữ liệu ≤ nến hiện tại trong ring (no-leak).
     *
     * @param symbolId id coin
     * @return giá cao nhất 24h, hoặc null nếu chưa có dữ liệu
     */
    public Float getHigh24H(short symbolId) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return null;

        int lookback = Math.min(count, 1440);
        float maxPrice = -Float.MAX_VALUE;
        int head = historyHead[symbolId] - 1;

        for (int i = 0; i < lookback; i++) {
            float price = historyRing[symbolId][(head - i) & RING_MASK].maxPrice;
            if (price > maxPrice) maxPrice = price;
        }
        return maxPrice == -Float.MAX_VALUE ? null : maxPrice;
    }

    public Float getMaxRateChange(short symbolId, int minutes) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count < 2) return 0.0f;

        int lookback = Math.min(count, minutes);
        float maxP = -1.0f;
        float minP = Float.MAX_VALUE;
        int head = historyHead[symbolId] - 1;

        for (int i = 0; i < lookback; i++) {
            KlineObjectSimple k = historyRing[symbolId][(head - i) & RING_MASK];
            if (k.maxPrice > maxP) maxP = k.maxPrice;
            if (k.minPrice < minP) minP = k.minPrice;
        }
        if (minP == 0 || minP == Float.MAX_VALUE) return 0.0f;
        return (maxP - minP) / minP;
    }

    public float getSumVolume(short symbolId, int minutes) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return 0.0f;

        float sum = 0;
        int lookback = Math.min(count, minutes);
        int head = historyHead[symbolId] - 1;

        for (int i = 0; i < lookback; i++) {
            sum += historyRing[symbolId][(head - i) & RING_MASK].totalUsdt;
        }
        return sum;
    }

    public float getAverageVolume(short symbolId, int periods) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count < periods) return 0.0f;

        float totalVol = 0;
        int startIndex = historyHead[symbolId] - 2; // list.size() - 2
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

    /**
     * Z-score của volume nến HIỆN TẠI so với phân phối {@code periods} nến TRƯỚC đó (cùng cửa sổ
     * với {@link #getAverageVolume(short, int)}: bỏ nến hiện tại, nhìn lùi {@code periods} nến).
     * Chỉ dùng dữ liệu ≤ nến hiện tại (no-leak).
     *
     * @param symbolId id coin
     * @param periods  số nến quá khứ để tính mean/std (vd 20)
     * @return (volume hiện tại − mean)/std; {@link Float#NaN} nếu thiếu nến hoặc std≤0
     */
    public float getVolumeZScore(short symbolId, int periods) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count < periods + 1) return Float.NaN;

        int head = historyHead[symbolId] - 1;
        float current = historyRing[symbolId][head & RING_MASK].totalUsdt;

        int startIndex = head - 1; // bỏ nến hiện tại
        float sum = 0, sumSq = 0;
        int n = 0;
        for (int i = 0; i < periods; i++) {
            int idx = startIndex - i;
            if (idx < 0) break;
            float v = historyRing[symbolId][idx & RING_MASK].totalUsdt;
            sum += v;
            sumSq += v * v;
            n++;
        }
        if (n < 2) return Float.NaN;
        float mean = sum / n;
        float var = (sumSq - (sum * sum) / n) / (n - 1);
        if (var <= 0) return Float.NaN;
        float std = (float) Math.sqrt(var);
        return (current - mean) / std;
    }

    public float getAverageRange(short symbolId, int periods) {
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count < periods) return 0.0f;

        float totalRange = 0;
        int startIndex = historyHead[symbolId] - 2; // list.size() - 2
        if (startIndex < 0) return 0.0f;

        int validCount = 0;
        for (int i = 0; i < periods; i++) {
            int idx = startIndex - i;
            if (idx >= 0) {
                KlineObjectSimple k = historyRing[symbolId][idx & RING_MASK];
                totalRange += (k.maxPrice - k.minPrice);
                validCount++;
            }
        }
        return validCount == 0 ? 0.0f : totalRange / validCount;
    }

    // ===== TASK-038 (microstructure 1m): N-bar high/low + wick ratio. Read-only ring, ≤t no-leak. =====

    /** Giá thấp nhất N nến gần nhất (min minPrice). null nếu chưa có dữ liệu. */
    public Float getLowN(String symbol, int periods) { return getLowN(SimpleSymbolMapper.getInstance().getId(symbol), periods); }
    public Float getLowN(short symbolId, int periods) {
        if (symbolId < 0 || symbolId >= MAX_COINS) return null;
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return null;
        int lookback = Math.min(count, periods);
        float min = Float.MAX_VALUE;
        int head = historyHead[symbolId] - 1;
        for (int i = 0; i < lookback; i++) {
            float p = historyRing[symbolId][(head - i) & RING_MASK].minPrice;
            if (p < min) min = p;
        }
        return min == Float.MAX_VALUE ? null : min;
    }

    /** Giá cao nhất N nến gần nhất (max maxPrice). null nếu chưa có dữ liệu. */
    public Float getHighN(String symbol, int periods) { return getHighN(SimpleSymbolMapper.getInstance().getId(symbol), periods); }
    public Float getHighN(short symbolId, int periods) {
        if (symbolId < 0 || symbolId >= MAX_COINS) return null;
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return null;
        int lookback = Math.min(count, periods);
        float max = -Float.MAX_VALUE;
        int head = historyHead[symbolId] - 1;
        for (int i = 0; i < lookback; i++) {
            float p = historyRing[symbolId][(head - i) & RING_MASK].maxPrice;
            if (p > max) max = p;
        }
        return max == -Float.MAX_VALUE ? null : max;
    }

    /** Tỉ lệ bấc trên trung bình N nến gần: mean((maxPrice−max(open,close))/(maxPrice−minPrice)). NaN nếu thiếu. */
    public float getAvgUpperWickRatio(String symbol, int periods) { return getAvgUpperWickRatio(SimpleSymbolMapper.getInstance().getId(symbol), periods); }
    public float getAvgUpperWickRatio(short symbolId, int periods) {
        if (symbolId < 0 || symbolId >= MAX_COINS) return Float.NaN;
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return Float.NaN;
        int lookback = Math.min(count, periods);
        int head = historyHead[symbolId] - 1;
        float sum = 0; int n = 0;
        for (int i = 0; i < lookback; i++) {
            KlineObjectSimple k = historyRing[symbolId][(head - i) & RING_MASK];
            float range = k.maxPrice - k.minPrice;
            if (range <= 0) continue;
            float body = Math.max(k.priceOpen, k.priceClose);
            sum += (k.maxPrice - body) / range;
            n++;
        }
        return n == 0 ? Float.NaN : sum / n;
    }

    // % thay đổi giá giữa nến mới nhất và nến cách đây `minutes` phút (thay cho getHistory()+getPriceAt cũ).
    public float getReturn(String symbol, int minutes)
    { return getReturn(SimpleSymbolMapper.getInstance().getId(symbol), minutes); }

    public float getReturn(short symbolId, int minutes) {
        if (symbolId < 0 || symbolId >= MAX_COINS) return 0.0f;
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return 0.0f;
        KlineObjectSimple current = historyRing[symbolId][(historyHead[symbolId] - 1) & RING_MASK];
        if (current == null || current.priceClose <= 0) return 0.0f;
        long pastTime = current.startTime.longValue() - (minutes * 60000L);
        Float pastPrice = getPriceAt(symbolId, pastTime);
        if (pastPrice != null && pastPrice > 0) return (current.priceClose - pastPrice) / pastPrice;
        return 0.0f;
    }

    // Độ lệch chuẩn return giữa các nến trong `periods` nến gần nhất (thay cho calculateVolatility cũ).
    public float getVolatility(String symbol, int periods) { return getVolatility(SimpleSymbolMapper.getInstance().getId(symbol), periods); }

    public float getVolatility(short symbolId, int periods) {
        if (symbolId < 0 || symbolId >= MAX_COINS) return 0.0f;
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count < 5) return 0.0f;
        int n = Math.min(count, periods);
        int head = historyHead[symbolId] - 1;
        float sum = 0, sumSq = 0;
        int c = 0;
        for (int i = n - 1; i > 0; i--) {
            KlineObjectSimple older = historyRing[symbolId][(head - i) & RING_MASK];
            KlineObjectSimple newer = historyRing[symbolId][(head - i + 1) & RING_MASK];
            if (older == null || newer == null || older.priceClose <= 0) continue;
            float r = (newer.priceClose - older.priceClose) / older.priceClose;
            sum += r;
            sumSq += r * r;
            c++;
        }
        return (c < 2) ? 0.0f : (float) Math.sqrt(Math.max(0, (sumSq - (sum * sum) / c) / (c - 1)));
    }

    // Giá đóng cửa nến mới nhất trong ring (null nếu chưa có dữ liệu).
    public Float getLatestClose(String symbol) { return getLatestClose(SimpleSymbolMapper.getInstance().getId(symbol)); }

    public Float getLatestClose(short symbolId) {
        if (symbolId < 0 || symbolId >= MAX_COINS) return null;
        int count = Math.min(historyHead[symbolId], RING_SIZE);
        if (count == 0) return null;
        KlineObjectSimple k = historyRing[symbolId][(historyHead[symbolId] - 1) & RING_MASK];
        return (k == null) ? null : k.priceClose;
    }

    // ========================================================
    // 4. BỘ TÌM KIẾM TIỀM NĂNG (Duyệt Array thay vì EntrySet)
    // ========================================================

    public List<Short> findPotentialLosersShort(long currentTimestamp) {
        List<Map.Entry<Short, Float>> drops = new ArrayList<>();
        long startTime = currentTimestamp - (15 * 60 * 1000L);

        for (short id = 0; id < MAX_COINS; id++) {
            int count = Math.min(historyHead[id], RING_SIZE);
            if (count == 0) continue;

            int head = historyHead[id] - 1;
            KlineObjectSimple currentKline = historyRing[id][head & RING_MASK];
            if (currentKline.totalUsdt < 5000) continue;

            float maxPrice15m = -1.0f;
            for (int i = 0; i < count; i++) {
                KlineObjectSimple k = historyRing[id][(head - i) & RING_MASK];
                if (k.startTime < startTime) break;
                if (k.maxPrice > maxPrice15m) maxPrice15m = k.maxPrice;
            }

            if (maxPrice15m > 0) {
                float dropFromPeak = (currentKline.priceClose - maxPrice15m) / maxPrice15m;
                if (dropFromPeak < -0.001) {
                    drops.add(new AbstractMap.SimpleEntry<>(id, dropFromPeak));
                }
            }
        }

        drops.sort(Map.Entry.comparingByValue());
        List<Short> result = new ArrayList<>();
        for (int i = 0; i < Math.min(60, drops.size()); i++) {
            result.add(drops.get(i).getKey());
        }
        return result;
    }

    // Trả về String cho tương thích ngược (Hạn chế dùng trong HPO)
    public List<String> findPotentialLosers(long currentTimestamp) {
        List<Short> ids = findPotentialLosersShort(currentTimestamp);
        List<String> result = new ArrayList<>(ids.size());
        for (Short id : ids) {
            result.add(SimpleSymbolMapper.getInstance().getSymbol(id));
        }
        return result;
    }

    public void resetCache() {
        Arrays.fill(historyHead, 0);
        Arrays.fill(lastUpdateTime, 0L);
        symbolsLastUpdate.clear();
        symbolsLastUpdateShort.clear();
        lastCleanTime = -1L;
    }
}