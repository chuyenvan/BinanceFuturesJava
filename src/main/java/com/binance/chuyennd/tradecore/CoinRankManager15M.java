package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager15M;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

public class CoinRankManager15M {
    public static final Logger LOG = LoggerFactory.getLogger(CoinRankManager15M.class);

    // Nến 15m, cập nhật hạng mỗi 60 phút là hợp lý
    public static int number_minute_update = 60;

    public enum CoinTier {
        TIER_1_BLUECHIP, // Top 20%
        TIER_2_MIDCAP,   // Mid 60%
        TIER_3_SHITCOIN, // Bottom 20%
        UNKNOWN          // Trạng thái chờ cập nhật
    }

    private static volatile CoinRankManager15M INSTANCE = null;

    // ========================================================
    // 🔥 CHIẾN LƯỢC DUAL-CACHE (BẢO TOÀN BACKWARD COMPATIBILITY)
    // ========================================================

    // Rổ 1: Dành cho hệ thống cũ/log/debug (Dùng String)
    private final ConcurrentHashMap<String, CoinTier> symbolTiers = new ConcurrentHashMap<>();

    // Rổ 2: Dành cho AI Pipeline 15M siêu tốc (Dùng Short nguyên thủy O(1))
    private final CoinTier[] symbolTiersShort = new CoinTier[5000];
    private final boolean[] isTop50PercentShort = new boolean[5000];
    private final List<Short> top50PercentSymbolsShortList = new CopyOnWriteArrayList<>();

    private long lastIntervalKey = -1L;

    private CoinRankManager15M() {
        Arrays.fill(symbolTiersShort, CoinTier.UNKNOWN);
    }

    public static CoinRankManager15M getInstance() {
        if (INSTANCE == null) {
            synchronized (CoinRankManager15M.class) {
                if (INSTANCE == null) {
                    INSTANCE = new CoinRankManager15M();
                }
            }
        }
        return INSTANCE;
    }


    public CoinTier getCoinTier(String symbol, long currentTime) {
        checkAndUpdate(currentTime);
        return symbolTiers.getOrDefault(symbol, CoinTier.TIER_3_SHITCOIN);
    }

    // ========================================================
    // 2. NHÓM HÀM CHO PIPELINE 15M MỚI (SHORT) - DÙNG CHÍNH
    // ========================================================
    public List<Short> getTopCoinShort(long currentTime) {
        checkAndUpdate(currentTime);
        return top50PercentSymbolsShortList;
    }

    public CoinTier getCoinTierShort(short symbolId, long currentTime) {
        checkAndUpdate(currentTime);
        if (symbolId >= 0 && symbolId < symbolTiersShort.length) {
            CoinTier tier = symbolTiersShort[symbolId];
            return tier == CoinTier.UNKNOWN ? CoinTier.TIER_3_SHITCOIN : tier;
        }
        return CoinTier.TIER_3_SHITCOIN;
    }

    public boolean isInsideStandardUniverseShort(short symbolId) {
        if (symbolId >= 0 && symbolId < isTop50PercentShort.length) {
            return isTop50PercentShort[symbolId];
        }
        return false;
    }

    // ========================================================
    // 3. LOGIC CẬP NHẬT XẾP HẠNG
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

        // Lấy danh sách ID coin đang active từ HistoryManager15M
        Set<Short> activeSymbolIds = HistoryManager15M.getInstance().getAllSymbolsShort();

        TreeMap<Float, List<Short>> volumeMap = new TreeMap<>(Collections.reverseOrder());

        for (short symId : activeSymbolIds) {
            // 48 nến 15m = 12 Giờ
            float sumVol = HistoryManager15M.getInstance().getSumVolume(symId, 48);
            volumeMap.computeIfAbsent(sumVol, k -> new ArrayList<>()).add(symId);
        }

        List<Short> sortedIds = new ArrayList<>();
        for (List<Short> syms : volumeMap.values()) {
            // Tie-breaker: Đồng hạng Volume thì sort theo bảng chữ cái A-Z
            Collections.sort(syms, (a, b) -> {
                String strA = SimpleSymbolMapper.getInstance().getSymbol(a);
                String strB = SimpleSymbolMapper.getInstance().getSymbol(b);
                if(strA == null) strA = "";
                if(strB == null) strB = "";
                return strA.compareTo(strB);
            });
            sortedIds.addAll(syms);
        }

        int totalCoins = sortedIds.size();
        if (totalCoins == 0) return;

        // Xóa sạch cache cũ
        top50PercentSymbolsShortList.clear();
        symbolTiers.clear();
        Arrays.fill(symbolTiersShort, CoinTier.UNKNOWN);
        Arrays.fill(isTop50PercentShort, false);

        int top50Count = totalCoins / 2;
        int top20Index = (int) (totalCoins * 0.20);
        int bottom20Index = (int) (totalCoins * 0.80);

        // Đổ dữ liệu mới vào Dual-Cache
        for (int i = 0; i < totalCoins; i++) {
            short symId = sortedIds.get(i);
            String symStr = SimpleSymbolMapper.getInstance().getSymbol(symId);
            if (symStr == null || symStr.startsWith("UNKNOWN")) continue;

            if (i < top50Count) {
                // Nhét vào cả 2 rổ
                top50PercentSymbolsShortList.add(symId);

                if (symId >= 0 && symId < isTop50PercentShort.length) {
                    isTop50PercentShort[symId] = true;
                }
            }

            CoinTier tier = (i < top20Index) ? CoinTier.TIER_1_BLUECHIP :
                    (i >= bottom20Index) ? CoinTier.TIER_3_SHITCOIN : CoinTier.TIER_2_MIDCAP;

            // Cập nhật rổ String
            symbolTiers.put(symStr, tier);

            // Cập nhật rổ Short
            if (symId >= 0 && symId < symbolTiersShort.length) {
                symbolTiersShort[symId] = tier;
            }
        }

        lastIntervalKey = currentIntervalKey;
    }

    public void resetCache() {
        symbolTiers.clear();
        top50PercentSymbolsShortList.clear();
        Arrays.fill(symbolTiersShort, CoinTier.UNKNOWN);
        Arrays.fill(isTop50PercentShort, false);
        lastIntervalKey = -1L;
    }
}