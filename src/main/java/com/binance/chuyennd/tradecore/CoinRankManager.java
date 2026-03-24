package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Class chuyên quản lý việc xếp hạng thanh khoản của các đồng coin.
 * Áp dụng mô hình Singleton để dùng chung Cache cho toàn bộ hệ thống.
 */
public class CoinRankManager {
    public static final Logger LOG = LoggerFactory.getLogger(CoinRankManager.class);

    // Enum định nghĩa 3 phân khúc
    public enum CoinTier {
        TIER_1_BLUECHIP, // Top 20% (Volume siêu lớn)
        TIER_2_MIDCAP,   // Mid 60% (Volume tầm trung)
        TIER_3_SHITCOIN  // Bottom 20% (Volume rác, dễ quét râu)
    }

    // --- CƠ CHẾ SINGLETON ---
    private static volatile CoinRankManager INSTANCE = null;

    // --- BỘ NHỚ CACHE ---
    private final ConcurrentHashMap<String, CoinTier> symbolTiers = new ConcurrentHashMap<>();
    private long lastUpdateTime = 0L;

    // Cập nhật 1 giờ / 1 lần (Có thể đưa vào Configs nếu muốn)
    private static final long UPDATE_INTERVAL_MILLIS = 60 * 60 * 1000L;

    private CoinRankManager() {
        // Private constructor
    }

    public static CoinRankManager getInstance() {
        if (INSTANCE == null) {
            synchronized (CoinRankManager.class) {
                if (INSTANCE == null) {
                    INSTANCE = new CoinRankManager();
                }
            }
        }
        return INSTANCE;
    }

    /**
     * Lấy Tier của một đồng coin. Tự động tính toán lại nền nếu Cache đã hết hạn.
     */
    public CoinTier getCoinTier(String symbol, long currentTime, Map<String, List<KlineObjectSimple>> symbol2LastTickers) {
        // Kiểm tra xem đã đến giờ phải tính toán lại bảng xếp hạng chưa
        if (currentTime - lastUpdateTime > UPDATE_INTERVAL_MILLIS || symbolTiers.isEmpty()) {
            updateRanking(symbol2LastTickers, currentTime);
        }

        // Trả về kết quả từ Cache siêu tốc (O(1)).
        // Mặc định ném vào Tier 3 nếu không tìm thấy (Để an toàn vốn).
        return symbolTiers.getOrDefault(symbol, CoinTier.TIER_3_SHITCOIN);
    }

    /**
     * Trả về Hệ số nhân Ngân sách (Budget Multiplier) dựa trên Tier.
     * Tiện ích giúp Simulator gọi 1 dòng là xong.
     */
    public float getBudgetMultiplier(String symbol) {
        CoinTier tier = symbolTiers.getOrDefault(symbol, CoinTier.TIER_3_SHITCOIN);
        switch (tier) {
            case TIER_1_BLUECHIP:
                return 1.20f; // Bơm thêm 20% tiền
            case TIER_2_MIDCAP:
                return 1.00f; // Giữ nguyên
            case TIER_3_SHITCOIN:
                return 0.50f; // Phạt giảm 50% tiền
            default:
                return 1.00f;
        }
    }

    /**
     * Trái tim của class: Thuật toán chia rổ 20-60-20.
     * Dùng synchronized để tránh nhiều luồng cùng tranh nhau tính toán một lúc.
     */
    private synchronized void updateRanking(Map<String, List<KlineObjectSimple>> symbol2LastTickers, long currentTime) {
        // Double-check bên trong synchronized (để luồng thứ 2 đến sau sẽ tự thoát ra)
        if (currentTime - lastUpdateTime <= UPDATE_INTERVAL_MILLIS && !symbolTiers.isEmpty()) {
            return;
        }

        if (symbol2LastTickers == null || symbol2LastTickers.isEmpty()) {
            return;
        }

        List<Map.Entry<String, Float>> volumeList = new ArrayList<>();

        // 1. Tính tổng Volume trong khoảng thời gian hiện có
        for (Map.Entry<String, List<KlineObjectSimple>> entry : symbol2LastTickers.entrySet()) {
            String sym = entry.getKey();
            float sumVol = 0;
            for (KlineObjectSimple k : entry.getValue()) {
                if (k != null) {
                    sumVol += k.totalUsdt;
                }
            }
            volumeList.add(new AbstractMap.SimpleEntry<>(sym, sumVol));
        }

        // 2. Sắp xếp giảm dần theo Volume
        volumeList.sort((a, b) -> b.getValue().compareTo(a.getValue()));

        int totalCoins = volumeList.size();
        if (totalCoins == 0) return;

        // 3. Phân mảnh 20% - 60% - 20%
        int top20Index = (int) (totalCoins * 0.20);
        int bottom20Index = (int) (totalCoins * 0.70);

        symbolTiers.clear();

        for (int i = 0; i < totalCoins; i++) {
            String sym = volumeList.get(i).getKey();
            if (i < top20Index) {
                symbolTiers.put(sym, CoinTier.TIER_1_BLUECHIP);
            } else if (i >= bottom20Index) {
                symbolTiers.put(sym, CoinTier.TIER_3_SHITCOIN);
            } else {
                symbolTiers.put(sym, CoinTier.TIER_2_MIDCAP);
            }
        }

        lastUpdateTime = currentTime; // Chốt mốc thời gian
        // LOG.info("🔄 Re-ranked {} coins based on Volume. Top 20% cut-off index: {}", totalCoins, top20Index);
    }

    // Thêm hàm dọn dẹp Cache (nếu cần thiết khi chạy backtest nhiều năm liên tục)
    public void resetCache() {
        symbolTiers.clear();
        lastUpdateTime = 0L;
    }
}