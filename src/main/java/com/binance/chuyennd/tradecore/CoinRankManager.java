package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

public class CoinRankManager {
    public static final Logger LOG = LoggerFactory.getLogger(CoinRankManager.class);
    public static int number_minute_update = 60;

    public enum CoinTier {
        TIER_1_BLUECHIP, // Top 20%
        TIER_2_MIDCAP,   // Mid 60%
        TIER_3_SHITCOIN, // Bottom 20%
        UNKNOWN          // Trạng thái chờ cập nhật
    }

    private static volatile CoinRankManager INSTANCE = null;

    // ========================================================
    // 🔥 CHIẾN LƯỢC DUAL-CACHE
    // ========================================================

    // Rổ 1: Dành cho hệ thống Production/Live cũ (String)
    private final ConcurrentHashMap<String, CoinTier> symbolTiers = new ConcurrentHashMap<>();
    private final List<String> top50PercentSymbols = new CopyOnWriteArrayList<>();

    // Rổ 2: Dành cho hệ thống Simulator siêu tốc (MẢNG NGUYÊN THỦY O(1))
    private final CoinTier[] symbolTiersShort = new CoinTier[5000]; // Kích thước đủ bao trọn mọi ID
    private final boolean[] isTop50PercentShort = new boolean[5000];
    private final List<Short> top50PercentSymbolsShortList = new CopyOnWriteArrayList<>(); // Giữ để tương thích hàm trả về List

    private long lastIntervalKey = -1L;

    private CoinRankManager() {
        Arrays.fill(symbolTiersShort, CoinTier.UNKNOWN);
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

    // ========================================================
    // 1. NHÓM HÀM CHO HỆ THỐNG CŨ (STRING)
    // ========================================================
    public List<String> getTopCoin(long currentTime) {
        checkAndUpdate(currentTime);
        return top50PercentSymbols;
    }

    public CoinTier getCoinTier(String symbol, long currentTime) {
        checkAndUpdate(currentTime);
        return symbolTiers.getOrDefault(symbol, CoinTier.TIER_3_SHITCOIN);
    }

    public float getBudgetMultiplier(String symbol) {
        CoinTier tier = symbolTiers.getOrDefault(symbol, CoinTier.TIER_3_SHITCOIN);
        return getMultiplierByTier(tier);
    }

    public boolean isInsideStandardUniverse(String symbol) {
        return top50PercentSymbols.contains(symbol);
    }

    // ========================================================
    // 2. NHÓM HÀM CHO SIMULATOR MỚI (SHORT - TỐC ĐỘ O(1))
    // ========================================================
    public List<Short> getTopCoinShort(long currentTime) {
        checkAndUpdate(currentTime);
        return top50PercentSymbolsShortList;
    }

    public CoinTier getCoinTier(short symbolId, long currentTime) {
        checkAndUpdate(currentTime);
        if (symbolId >= 0 && symbolId < symbolTiersShort.length) {
            CoinTier tier = symbolTiersShort[symbolId];
            return tier == CoinTier.UNKNOWN ? CoinTier.TIER_3_SHITCOIN : tier;
        }
        return CoinTier.TIER_3_SHITCOIN;
    }

    public float getBudgetMultiplier(short symbolId) {
        if (symbolId >= 0 && symbolId < symbolTiersShort.length) {
            CoinTier t = symbolTiersShort[symbolId];
            return getMultiplierByTier(t == CoinTier.UNKNOWN ? CoinTier.TIER_3_SHITCOIN : t);
        }
        return getMultiplierByTier(CoinTier.TIER_3_SHITCOIN);
    }

    public boolean isInsideStandardUniverse(short symbolId) {
        if (symbolId >= 0 && symbolId < isTop50PercentShort.length) {
            return isTop50PercentShort[symbolId];
        }
        return false;
    }

    // Hàm tiện ích nội bộ dùng chung
    private float getMultiplierByTier(CoinTier tier) {
        switch (tier) {
            case TIER_1_BLUECHIP: return 1.20f;
            case TIER_2_MIDCAP:   return 1.00f;
            case TIER_3_SHITCOIN: return 0.50f;
            default:              return 1.00f;
        }
    }

    // ========================================================
    // 3. LOGIC CẬP NHẬT XẾP HẠNG (TƯƠNG THÍCH RING BUFFER)
    // ========================================================
    private void checkAndUpdate(long currentTime) {
        long currentIntervalKey = currentTime / (number_minute_update * Utils.TIME_MINUTE);
        if (((currentTime / Utils.TIME_MINUTE) % number_minute_update == 0 && currentIntervalKey > lastIntervalKey) || symbolTiers.isEmpty()) {
            updateRanking(currentIntervalKey);
        }
    }

    private synchronized void updateRanking(long currentIntervalKey) {
        // Double check locking
        if (currentIntervalKey <= lastIntervalKey && !symbolTiers.isEmpty()) return;

        // Lấy danh sách ID coin đang active từ HistoryManager
        Set<Short> activeSymbolIds = HistoryManager.getInstance().getAllSymbolsShort();

        TreeMap<Float, List<Short>> volumeMap = new TreeMap<>(Collections.reverseOrder());

        for (short symId : activeSymbolIds) {
            // 🚀 Gọi O(1): Yêu cầu trực tiếp tổng Volume 720 nến từ Ring Buffer
            float sumVol = HistoryManager.getInstance().getSumVolume(symId, 720);

            // 🔥 THỦ PHẠM SỐ 1 ĐÃ ĐƯỢC FIX TẠI ĐÂY:
            // KHÔNG check sumVol > 0 nữa, cứ có nến là ném vào xếp hạng y như bản cũ!
            volumeMap.computeIfAbsent(sumVol, k -> new ArrayList<>()).add(symId);
        }

        List<Short> sortedIds = new ArrayList<>();
        for (List<Short> syms : volumeMap.values()) {

            // 🔥 THỦ PHẠM SỐ 2 ĐÃ ĐƯỢC FIX TẠI ĐÂY:
            // Tie-breaker: Đồng hạng Volume thì sort theo bảng chữ cái String A-Z
            Collections.sort(syms, (a, b) -> {
                String strA = SimpleSymbolMapper.getInstance().getSymbol(a);
                String strB = SimpleSymbolMapper.getInstance().getSymbol(b);
                return strA.compareTo(strB);
            });

            sortedIds.addAll(syms);
        }

        int totalCoins = sortedIds.size();
        if (totalCoins == 0) return;

        // Clear toàn bộ cache cũ
        top50PercentSymbols.clear();
        top50PercentSymbolsShortList.clear();
        symbolTiers.clear();
        Arrays.fill(symbolTiersShort, CoinTier.UNKNOWN);
        Arrays.fill(isTop50PercentShort, false);

        int top50Count = totalCoins / 2;
        int top20Index = (int) (totalCoins * 0.20);
        int bottom20Index = (int) (totalCoins * 0.80);

        // Đổ dữ liệu mới vào hệ thống Dual-Cache
        for (int i = 0; i < totalCoins; i++) {
            short symId = sortedIds.get(i);
            String symStr = SimpleSymbolMapper.getInstance().getSymbol(symId);

            if (i < top50Count) {
                top50PercentSymbols.add(symStr);
                top50PercentSymbolsShortList.add(symId);
                if (symId >= 0 && symId < isTop50PercentShort.length) {
                    isTop50PercentShort[symId] = true;
                }
            }

            CoinTier tier;
            if (i < top20Index) {
                tier = CoinTier.TIER_1_BLUECHIP;
            } else if (i >= bottom20Index) {
                tier = CoinTier.TIER_3_SHITCOIN;
            } else {
                tier = CoinTier.TIER_2_MIDCAP;
            }

            // Ghi vào Map String
            symbolTiers.put(symStr, tier);

            // Ghi vào Mảng Array Short
            if (symId >= 0 && symId < symbolTiersShort.length) {
                symbolTiersShort[symId] = tier;
            }
        }

        lastIntervalKey = currentIntervalKey;
    }

    public void resetCache() {
        symbolTiers.clear();
        top50PercentSymbols.clear();
        top50PercentSymbolsShortList.clear();
        Arrays.fill(symbolTiersShort, CoinTier.UNKNOWN);
        Arrays.fill(isTop50PercentShort, false);
        lastIntervalKey = -1L;
    }
}