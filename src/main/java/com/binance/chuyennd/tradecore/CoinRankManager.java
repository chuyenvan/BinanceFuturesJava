package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Class chuyên quản lý việc xếp hạng thanh khoản của các đồng coin.
 * Giữ nguyên signature hàm getCoinTier cũ.
 */
public class CoinRankManager {
    public static final Logger LOG = LoggerFactory.getLogger(CoinRankManager.class);
    public static int number_minute_update = 60;

    public List<String> getTopCoin(long currentTime) {
        // 1. Kiểm tra mốc 15 phút chẵn (00, 15, 30, 45)
        // Dùng thêm lastIntervalKey để đảm bảo trong 60 giây của phút đó chỉ chạy update 1 lần duy nhất
        long currentIntervalKey = currentTime / (number_minute_update * Utils.TIME_MINUTE);

        if (((currentTime / Utils.TIME_MINUTE) % number_minute_update == 0 && currentIntervalKey > lastIntervalKey) || symbolTiers.isEmpty()) {
            updateRanking(currentTime);
            lastIntervalKey = currentIntervalKey; // Khóa lại ngay
        }
        return top50PercentSymbols;
    }

    public enum CoinTier {
        TIER_1_BLUECHIP, // Top 20% (Volume siêu lớn)
        TIER_2_MIDCAP,   // Mid 60% (Volume tầm trung)
        TIER_3_SHITCOIN  // Bottom 20% (Volume rác)
    }

    private static volatile CoinRankManager INSTANCE = null;

    private final ConcurrentHashMap<String, CoinTier> symbolTiers = new ConcurrentHashMap<>();

    private final List<String> top50PercentSymbols = new ArrayList<>();

    // Biến phụ để chốt chặn không cho update liên tục trong cùng 1 phút chẵn
    private long lastIntervalKey = -1L;

    private CoinRankManager() {
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
     * 🔥 GIỮ NGUYÊN SIGNATURE CŨ CỦA BÁC
     */
    public CoinTier getCoinTier(String symbol, long currentTime) {
        // 1. Kiểm tra mốc 15 phút chẵn (00, 15, 30, 45)
        // Dùng thêm lastIntervalKey để đảm bảo trong 60 giây của phút đó chỉ chạy update 1 lần duy nhất
        long currentIntervalKey = currentTime / (number_minute_update * Utils.TIME_MINUTE);

        if (((currentTime / Utils.TIME_MINUTE) % number_minute_update == 0 && currentIntervalKey > lastIntervalKey) || symbolTiers.isEmpty()) {
            updateRanking(currentTime);
            lastIntervalKey = currentIntervalKey; // Khóa lại ngay
        }

        return symbolTiers.getOrDefault(symbol, CoinTier.TIER_3_SHITCOIN);
    }

    /**
     * Thuật toán sắp xếp bằng TreeMap và lọc Top 50%
     */
    private synchronized void updateRanking(long currentTime) {
        Map<String, ArrayList<KlineObjectSimple>> symbol2LastTickers = HistoryManager.getInstance().getAllHistory();
        Set<String> symbolLastUpdate = HistoryManager.getInstance().getAllSymbols();
        // 1. Dùng TreeMap sắp xếp Volume giảm dần
        TreeMap<Float, List<String>> volumeMap = new TreeMap<>(Collections.reverseOrder());
        int size = symbol2LastTickers.get(Constants.SYMBOL_PAIR_BTC).size();
        for (String sym: symbolLastUpdate) {
            float sumVol = 0;
            int counter = 0;
            List<KlineObjectSimple> tickers =symbol2LastTickers.get(sym);
            if (tickers == null || tickers.size() == 0) continue;

            // Tính Volume 200 nến
            for (int i = tickers.size() - 1; i >= 0 && counter < 720; i--) {
                KlineObjectSimple k = tickers.get(i);
                if (k != null) sumVol += k.totalUsdt;
                counter++;
            }

            if (counter > 0) {
                volumeMap.computeIfAbsent(sumVol, k -> new ArrayList<>()).add(sym);
            }
        }

        // 2. Chuyển sang List phẳng để tính toán index
        List<String> sortedSymbols = new ArrayList<>();
        for (List<String> syms : volumeMap.values()) {
            Collections.sort(syms);
            sortedSymbols.addAll(syms);
        }

        int totalCoins = sortedSymbols.size();
        if (totalCoins == 0) return;

        // 3. Cập nhật danh sách TOP 50% (Giải pháp 2)
        top50PercentSymbols.clear();
        int top50Count = totalCoins / 2;
        for (int i = 0; i < top50Count; i++) {
            top50PercentSymbols.add(sortedSymbols.get(i));
        }

        // 4. Phân rổ Tier 20-60-20
        int top20Index = (int) (totalCoins * 0.20);
        int bottom20Index = (int) (totalCoins * 0.80);

        int countTier1 = 0;
        int countTier2 = 0;
        int countTier3 = 0;

        for (int i = 0; i < totalCoins; i++) {
            String sym = sortedSymbols.get(i);
            if (i < top20Index) {
                symbolTiers.put(sym, CoinTier.TIER_1_BLUECHIP);
                countTier1++;
            } else if (i >= bottom20Index) {
                symbolTiers.put(sym, CoinTier.TIER_3_SHITCOIN);
                countTier3++;
            } else {
                symbolTiers.put(sym, CoinTier.TIER_2_MIDCAP);
                countTier2++;
            }
        }

//        LOG.info("🔄 Ranking Updated at {}: Total={} size={}, TIER_1={}, TIER_2={}, TIER_3={} (Top50%={})",
//                Utils.normalizeDateYYYYMMDDHHmm(currentTime), totalCoins, size, countTier1, countTier2,
//                countTier3, top50PercentSymbols.size());
    }

    /**
     * Hàm bổ sung để bác gọi từ Feature Extractor (Giải pháp 2)
     */
    public boolean isInsideStandardUniverse(String symbol) {
        return top50PercentSymbols.contains(symbol);
    }

    public void resetCache() {
        symbolTiers.clear();
        top50PercentSymbols.clear();
        lastIntervalKey = -1L;
    }
}