package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.*;

public class HPOSmartCache {

    private static final Logger LOG = LoggerFactory.getLogger(HPOSmartCache.class);

    // KHO CHỨA DỮ LIỆU NÉN (Dùng RAM ít nhất có thể)
    private static final ConcurrentHashMap<Long, Map<Short, CompactDayData>> RAM_STORE = new ConcurrentHashMap<>();

    // Executor riêng để bung nén (Dùng 4 luồng là đủ nhanh xé gió rồi)
    private static final ExecutorService reconstructExecutor = Executors.newFixedThreadPool(3);

    /**
     * CÁCH 1: Lấy dữ liệu CẢ NGÀY (Đã tối ưu tốc độ)
     * Dùng cho Simulator cũ hoặc khi muốn load 1 cục vào xử lý cho nhanh.
     */
    public static TreeMap<Long, Map<String, KlineObjectSimple>> getData(long dayStart) {
        // 1. Kiểm tra RAM
        Map<Short, CompactDayData> compressedMap = RAM_STORE.get(dayStart);

        if (compressedMap == null) {
            // Chưa có thì load từ Disk/DB
            TreeMap<Long, Map<String, KlineObjectSimple>> rawData = DataManagerAerospikeFloatSim.readDataFromAerospike1M(dayStart);
            if (rawData != null && !rawData.isEmpty()) {
                compressAndStore(dayStart, rawData);
            }
            return rawData;
        } else {
            // Đã có nén -> Bung ra (Dùng bản TỐI ƯU MỚI)
            return reconstructTreeMapOptimized(dayStart, compressedMap);
        }
    }

    /**
     * CÁCH 2: Lấy dữ liệu TỪNG PHÚT (Lazy Loading)
     * Dùng cho Simulator mới để tiết kiệm RAM tối đa.
     */
    public static Map<String, KlineObjectSimple> getDataAtMinute(long timestamp) {
        long dayStart = Utils.getStartOfDayGMT7(timestamp);
        Map<Short, CompactDayData> compressedMap = RAM_STORE.get(dayStart);

        // Load Disk nếu chưa có
        if (compressedMap == null) {
            TreeMap<Long, Map<String, KlineObjectSimple>> rawData = DataManagerAerospikeFloatSim.readDataFromAerospike1M(dayStart);
            if (rawData != null && !rawData.isEmpty()) {
                compressAndStore(dayStart, rawData);
                compressedMap = RAM_STORE.get(dayStart);
            } else {
                return new HashMap<>();
            }
        }

        // Tính index phút (0 - 1439)
        int minuteIndex = (int) ((timestamp - dayStart) / 60000L);
        if (minuteIndex < 0 || minuteIndex >= 1440) return new HashMap<>();

        // Chỉ bung nén phút này
        Map<String, KlineObjectSimple> result = new HashMap<>(2500);
        for (Map.Entry<Short, CompactDayData> entry : compressedMap.entrySet()) {
            KlineObjectSimple kline = entry.getValue().get(dayStart, minuteIndex);
            if (kline != null) {
                String symbol = SimpleSymbolMapper.getInstance().getSymbol(entry.getKey());
                if (symbol != null) result.put(symbol, kline);
            }
        }
        return result;
    }

    // --- CÁC HÀM PHỤ TRỢ ---

    // Nén dữ liệu
    private static void compressAndStore(long dayStart, TreeMap<Long, Map<String, KlineObjectSimple>> rawData) {
        Map<Short, CompactDayData> compactMap = new HashMap<>();
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : rawData.entrySet()) {
            long time = entry.getKey();
            Map<String, KlineObjectSimple> symbolMap = entry.getValue();
            for (Map.Entry<String, KlineObjectSimple> ticker : symbolMap.entrySet()) {
                short symbolId = SimpleSymbolMapper.getInstance().getId(ticker.getKey());
                KlineObjectSimple kline = ticker.getValue();
                CompactDayData compactData = compactMap.computeIfAbsent(symbolId, k -> new CompactDayData());
                compactData.set(dayStart, time, kline);
            }
        }
        RAM_STORE.put(dayStart, compactMap);
    }

    /**
     * 🔥 HÀM MỚI: TÁI TẠO MAP TỐI ƯU (Loop Inversion + Multi-thread)
     * Thay thế hàm cũ chạy 12 phút.
     */
    private static TreeMap<Long, Map<String, KlineObjectSimple>> reconstructTreeMapOptimized(long dayStart, Map<Short, CompactDayData> compressedMap) {
        TreeMap<Long, Map<String, KlineObjectSimple>> finalResult = new TreeMap<>();

        // 1. Lấy danh sách Symbol ID và Cache tên Symbol để không phải tra cứu nhiều lần
        List<Short> allSymbolIds = new ArrayList<>(compressedMap.keySet());
        Map<Short, String> idCache = new HashMap<>(allSymbolIds.size());
        for (Short id : allSymbolIds) {
            String sym = SimpleSymbolMapper.getInstance().getSymbol(id);
            if (sym != null) idCache.put(id, sym);
        }

        // 2. Chia 1440 phút thành 4 phần để chạy song song
        List<Callable<Map<Long, Map<String, KlineObjectSimple>>>> tasks = new ArrayList<>();
        int chunk = 360; // 1440 / 4 = 360 phút mỗi luồng

        for (int i = 0; i < 4; i++) {
            int startMin = i * chunk;
            int endMin = (i + 1) * chunk;

            tasks.add(() -> {
                Map<Long, Map<String, KlineObjectSimple>> chunkResult = new HashMap<>();

                // --- KỸ THUẬT ĐẢO NGƯỢC VÒNG LẶP ---
                // Duyệt Thời gian trước -> Duyệt Coin sau
                for (int m = startMin; m < endMin; m++) {
                    long currentTime = dayStart + m * 60000L;

                    // Tạo map con cho phút này
                    Map<String, KlineObjectSimple> minuteMap = new HashMap<>(2500);

                    // Điền dữ liệu của tất cả coin vào phút này
                    for (Short symbolId : allSymbolIds) {
                        CompactDayData data = compressedMap.get(symbolId);
                        // Truy cập mảng trực tiếp -> O(1) siêu nhanh
                        KlineObjectSimple kline = data.get(dayStart, m);

                        if (kline != null) {
                            String sym = idCache.get(symbolId);
                            if (sym != null) minuteMap.put(sym, kline);
                        }
                    }

                    if (!minuteMap.isEmpty()) {
                        chunkResult.put(currentTime, minuteMap);
                    }
                }
                return chunkResult;
            });
        }

        try {
            // 3. Chạy và gộp kết quả
            List<Future<Map<Long, Map<String, KlineObjectSimple>>>> results = reconstructExecutor.invokeAll(tasks);

            for (Future<Map<Long, Map<String, KlineObjectSimple>>> future : results) {
                finalResult.putAll(future.get());
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        return finalResult;
    }

    /**
     * 🔥 CHO WFO/SIMULATOR: lấy CẢ NGÀY dạng array short-indexed (KlineObjectSimple[1000]/phút),
     * khớp định dạng SimulatorMarketLevelTicker1MStopLoss dùng. Cache nén theo ngày: lần đầu đọc
     * Aerospike (local) + nén; các lần sau (N sample cùng window) bung từ RAM nén — KHÔNG đọc lại DB.
     */
    public static TreeMap<Long, KlineObjectSimple[]> getDataShort(long dayStart) {
        Map<Short, CompactDayData> compressedMap = RAM_STORE.get(dayStart);
        if (compressedMap == null) {
            TreeMap<Long, Map<String, KlineObjectSimple>> rawData = DataManagerAerospikeFloatSim.readDataFromAerospike1M(dayStart);
            if (rawData == null || rawData.isEmpty()) return null;
            compressAndStore(dayStart, rawData);
            compressedMap = RAM_STORE.get(dayStart);
        }
        final Map<Short, CompactDayData> cmap = compressedMap;
        final List<Short> ids = new ArrayList<>(cmap.keySet());

        TreeMap<Long, KlineObjectSimple[]> result = new TreeMap<>();
        List<Callable<Map<Long, KlineObjectSimple[]>>> tasks = new ArrayList<>();
        int chunk = 360; // 1440/4
        for (int i = 0; i < 4; i++) {
            final int startMin = i * chunk;
            final int endMin = (i + 1) * chunk;
            tasks.add(() -> {
                Map<Long, KlineObjectSimple[]> chunkResult = new HashMap<>();
                for (int m = startMin; m < endMin; m++) {
                    long t = dayStart + m * 60000L;
                    KlineObjectSimple[] arr = new KlineObjectSimple[1000];
                    boolean any = false;
                    for (Short id : ids) {
                        KlineObjectSimple k = cmap.get(id).get(dayStart, m);
                        if (k != null) { arr[id] = k; any = true; }
                    }
                    if (any) chunkResult.put(t, arr);
                }
                return chunkResult;
            });
        }
        try {
            for (Future<Map<Long, KlineObjectSimple[]>> f : reconstructExecutor.invokeAll(tasks)) result.putAll(f.get());
        } catch (Exception e) {
            e.printStackTrace();
        }
        return result;
    }

    /** Xóa toàn bộ cache (gọi giữa các window WFO để giải phóng RAM — tránh tích lũy OOM). */
    public static void clearCache() {
        RAM_STORE.clear();
    }

    /** Evict các ngày NGOÀI [keepStart, keepEnd] (giữ đúng cửa sổ đang chạy). */
    public static void evictOutside(long keepStart, long keepEnd) {
        RAM_STORE.keySet().removeIf(day -> day < keepStart || day > keepEnd);
    }

    /** Số ngày đang giữ trong cache (để log/giám sát RAM). */
    public static int cachedDays() {
        return RAM_STORE.size();
    }

    // Hàm getKline lẻ
    public static KlineObjectSimple getKline(short symbolId, long time) {
        long dayStart = Utils.getStartOfDayGMT7(time);
        Map<Short, CompactDayData> dayMap = RAM_STORE.get(dayStart);
        if (dayMap == null) return null;
        CompactDayData data = dayMap.get(symbolId);
        if (data == null) return null;
        int index = (int) ((time - dayStart) / 60000L);
        if (index < 0 || index >= 1440) return null;
        return data.get(dayStart, index);
    }

}