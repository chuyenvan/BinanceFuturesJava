package com.binance.chuyennd.ai_ml.extractor;

import com.binance.chuyennd.aerospike.DataManagerAerospike;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.stream.Collectors;

/**
 * LOP CHINH (MAIN CLASS) DE CHAY
 * Phien ban V21 (Sliding Window - Da sua loi OutOfMemory):
 * - Sua loi logic xoa cache.
 * - Thay vi xoa 1 phut/lan, se xoa tat ca data cu (headMap.clear()).
 */
public class MainFeatureExtractor {

    public static final Logger LOG = LoggerFactory.getLogger(MainFeatureExtractor.class);

    // --- Cau hinh ---
    public static final String CSV_FILE_PATH = "../storage/ai_ml/dl4j/btc_model_dataset_v21_final.csv";
    public static final String ENTRIES_DATA_FILE = "../storage/ai_ml/dl4j/entries.data";

    public static final int WARMUP_PERIOD = 200; // Phut
    public static final int SIMULATION_PERIOD_MINUTES = 1 * 24 * 60; // 1 Ngay (1440 phut)
    private static final long WARMUP_MS = WARMUP_PERIOD * Utils.TIME_MINUTE;
    private static final long SIMULATION_MS = SIMULATION_PERIOD_MINUTES * Utils.TIME_MINUTE;

    // --- Bien toan cuc ---
    private CsvWriter csvWriter;
    private Set<Long> timeProcessedInCsv;
    private Map<Long, Set<String>> time2symbols2trade;
    private int rowsWritten = 0;

    // === CUA SO TRUOT (SLIDING WINDOW CACHE) ===
    private TreeMap<Long, Map<String, KlineObjectSimple>> windowCache = new TreeMap<>();
    private Set<Long> daysLoadedFromAerospike = new HashSet<>();


    public static void main(String[] args) {
        LOG.info("BAT DAU QUA TRINH XUAT DU LIEU (FEATURE EXTRACTION V21 - SLIDING WINDOW - FIXED)...");
        long globalStartTime = System.currentTimeMillis();
        MainFeatureExtractor extractor = new MainFeatureExtractor();

        try {
            // (Cac buoc 0, 1, 2, 3 giu nguyen)
            // --- BUOC 0: DOC TIME CUOI CUNG TRONG CSV (DE RESUME) ---
            extractor.timeProcessedInCsv = extractor.readLastProcessedTimestamp(CSV_FILE_PATH);
            if (extractor.timeProcessedInCsv != null && !extractor.timeProcessedInCsv.isEmpty()) {
                LOG.info(">>> TIM THAY DU LIEU CU: Tiep tuc chay (da xu ly {} timestamps).", extractor.timeProcessedInCsv.size());
            } else {
                LOG.info(">>> KHONG CO DU LIEU CU (HOAC FILE MOI): Chay tu dau.");
            }

            // --- BUOC 1: TAI DU LIEU "STATIC" (BTC, ETH, ...) ---
            LOG.info("Dang tai du lieu tinh (BTC, ETH, Market, Trend)...");
            DataContext.loadAllStaticData();
            LOG.info("Tai du lieu static thanh cong.");

            // --- BUOC 2: TAI FILE "DRIVER" (entries.data) ---
            LOG.info("Dang tai file entries.data (Good Signals) tu: {}", ENTRIES_DATA_FILE);
            extractor.time2symbols2trade = (Map<Long, Set<String>>) StorageSnappy.readObjectFromFile(ENTRIES_DATA_FILE);

            if (extractor.time2symbols2trade == null || extractor.time2symbols2trade.isEmpty()) {
                throw new RuntimeException("KHONG THE TAI 'entries.data'!");
            }
            LOG.info("Tong cong co {} timestamps can xu ly tu entries.data.", extractor.time2symbols2trade.size());

            // --- BUOC 3: CHUAN BI CSV (Append Mode) ---
            extractor.setupCsvFile();
            extractor.csvWriter = new CsvWriter(CSV_FILE_PATH, FeatureCalculator.getCsvHeader());

            // --- BUOC 4: CHAY VONG LAP (Theo PHUT tu entries.data) ---
            extractor.runFeatureExtractionLoop();

            LOG.info("\n--- HOAN TAT: Tong so dong MOI da ghi: {} ---", extractor.rowsWritten);

        } catch (Exception e) {
            LOG.error("Gap loi nghiem trong:", e);
        } finally {
            if (extractor.csvWriter != null) extractor.csvWriter.close();
            DataManagerAerospike.closeConnection();
        }

        long globalEndTime = System.currentTimeMillis();
        LOG.info("Tong thoi gian chay: {} phut.", ((globalEndTime - globalStartTime) / 1000.0 / 60.0));
    }

    /**
     * Vong lap chinh, doc Aerospike theo "Cua so truot".
     */
    public void runFeatureExtractionLoop() {

        long processedCount = 0;
        long totalToProcess = time2symbols2trade.size();

        for (long currentTimestamp : time2symbols2trade.keySet()) {

            processedCount++;

            if (timeProcessedInCsv.contains(currentTimestamp)) {
                continue;
            }

            Set<String> goodSymbols = time2symbols2trade.get(currentTimestamp);

            if (processedCount % 1000 == 0) {
                LOG.info("... Dang xu ly Time: {} ({}/{}). Cache size: {}",
                        Utils.normalizeDateYYYYMMDDHHmm(currentTimestamp), processedCount, totalToProcess, windowCache.size());
            }

            // --- BUOC 5: LOGIC CAP NHAT "CUA SO TRUOT" (SLIDING WINDOW) ---
            long requiredStart = currentTimestamp - WARMUP_MS;
            long requiredEnd = currentTimestamp + SIMULATION_MS;

            try {
                updateSlidingWindow(requiredStart, requiredEnd);
            } catch (Exception e) {
                LOG.error("Loi khi cap nhat windowCache cho {}: {}", Utils.normalizeDateYYYYMMDDHHmm(currentTimestamp), e.getMessage());
                continue;
            }

            Map<String, KlineObjectSimple> allSymbolsAtTime = windowCache.get(currentTimestamp);
            if (allSymbolsAtTime == null || allSymbolsAtTime.isEmpty()) {
                continue;
            }

            int i = DataContext.getTimestampIndex(currentTimestamp);
            if (i < WARMUP_PERIOD) {
                continue;
            }

            FeatureRow commonFeatures = FeatureCalculator.calculateFeatures(i);
            if (commonFeatures == null) continue;

            // Lap qua TAT CA symbol tai thoi diem nay
            for (String symbol : allSymbolsAtTime.keySet()) {

                KlineObjectSimple kline = allSymbolsAtTime.get(symbol);
                if (!Utils.isTickerAvailable(kline)) {
                    continue;
                }

                TreeMap<Long, KlineObjectSimple> symbolData = buildSymbolDataFromCache(symbol, requiredStart, requiredEnd);

                if (symbolData == null || symbolData.isEmpty()) {
                    continue;
                }

                LabelSimulator.LabelResult label =
                        LabelSimulator.calculateSingleSymbolLabel_WithData(symbolData, currentTimestamp);
                if (label == null) continue;

                boolean isGoodSignal = goodSymbols.contains(symbol);
                boolean isBadPnL = (label.pnl_final < 0.03);

                if (isGoodSignal || isBadPnL) {

                    SortedMap<Long, KlineObjectSimple> historyMap = symbolData.headMap(currentTimestamp, true);
                    if (historyMap.size() < WARMUP_PERIOD) {
                        continue;
                    }

                    List<KlineObjectSimple> historyKlines = new ArrayList<>(historyMap.values());
                    List<Double> historyCloses = historyKlines.stream()
                            .map(k -> k.priceClose)
                            .collect(Collectors.toList());

                    FeatureRow symbolRow = copyRow(commonFeatures);
                    symbolRow.debug_symbol = symbol;
                    FeatureCalculator.calculateSymbolFeatures(symbolRow, historyKlines, historyCloses);

                    symbolRow.pnl_final = label.pnl_final;
                    symbolRow.max_drawdown = label.max_drawdown;
                    symbolRow.time_to_profit = label.time_to_profit;

                    symbolRow.debug_entry = label.entry_price;
                    symbolRow.debug_price_to_profit = label.price_to_profit;

                    csvWriter.writeRow(symbolRow);
                    rowsWritten++;
                }
            }

            // !!! === LOGIC XOA CACHE (DA SUA) === !!!
            // Thay vi xoa 1 dong, chung ta xoa tat ca cac dong cu hon cua so hien tai.
            // .headMap(requiredStart) tra ve tat ca cac entry co key < requiredStart.
            // .clear() se xoa chung khoi TreeMap (windowCache) mot cach hieu qua.

            windowCache.headMap(requiredStart).clear();

            // === KET THUC SUA LOI ===
        }
    }

    /**
     * Ham (MOI) de cap nhat windowCache
     * No se doc Aerospike neu du lieu can thiet chua co trong cache
     */
    private void updateSlidingWindow(long requiredStart, long requiredEnd) {

        Set<Long> daysToLoad = new HashSet<>();

        long startDay = Utils.getStartTimeOfDay(requiredStart);
        long endDay = Utils.getStartTimeOfDay(requiredEnd);

        long currentDay = startDay;
        while (currentDay <= endDay) {
            daysToLoad.add(currentDay);
            currentDay += Utils.TIME_DAY;
        }

        for (long day : daysToLoad) {
            if (!daysLoadedFromAerospike.contains(day)) {
                LOG.info("... Dang doc du lieu Aerospike cho ngay: {}", Utils.normalizeDateYYYYMMDD(day));
                try {
                    TreeMap<Long, Map<String, KlineObjectSimple>> dailyData =
                            DataManagerAerospike.readDataFromAerospike1M(day);

                    if (dailyData != null && !dailyData.isEmpty()) {
                        windowCache.putAll(dailyData);
                    }
                    daysLoadedFromAerospike.add(day);

                } catch (Exception e) {
                    LOG.error("Khong the doc du lieu Aerospike cho ngay {}: {}", Utils.normalizeDateYYYYMMDD(day), e.getMessage());
                }
            }
        }
    }

    /**
     * Ham (MOI) de xay dung du lieu cho 1 symbol tu cache
     * (Thay the readDataForPeriod)
     */
    private TreeMap<Long, KlineObjectSimple> buildSymbolDataFromCache(String symbol, long requiredStart, long requiredEnd) {

        TreeMap<Long, KlineObjectSimple> symbolData = new TreeMap<>();

        // Loc windowCache de lay dung pham vi thoi gian
        // Su dung subMap de bao gom ca requiredStart va requiredEnd
        SortedMap<Long, Map<String, KlineObjectSimple>> windowInRange =
                windowCache.subMap(requiredStart, true, requiredEnd, true);

        if (windowInRange.isEmpty()) {
            return null;
        }

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> minuteEntry : windowInRange.entrySet()) {
            Map<String, KlineObjectSimple> symbolsAtMinute = minuteEntry.getValue();
            if (symbolsAtMinute != null) {
                KlineObjectSimple kline = symbolsAtMinute.get(symbol);
                if (kline != null) {
                    symbolData.put(minuteEntry.getKey(), kline);
                }
            }
        }

        return symbolData;
    }


    /**
     * Ham doc nguoc file CSV de lay TimeStamp (DA CAP NHAT FORMAT MOI)
     */
    private Set<Long> readLastProcessedTimestamp(String filePath) {
        Set<Long> timeProcessed = new HashSet<>();
        File file = new File(filePath);
        if (!file.exists() || file.length() == 0) {
            return timeProcessed;
        }

        try {
            List<String> lines = FileUtils.readLines(file);
            SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

            for (String line : lines) {
                try {
                    if (line.trim().isEmpty() || line.startsWith("btc_rate_change_15m")) { // Kiem tra header
                        continue;
                    }
                    String[] parts = line.split(",");
                    if (parts.length > 4) {
                        String dateString = parts[parts.length - 4]; // debug_date o vi tri -4
                        timeProcessed.add(sdf.parse(dateString).getTime());
                    }
                } catch (Exception e) {
                    // Bo qua dong loi
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        return timeProcessed;
    }

    /**
     * Ham copy 9 features chung (DA CAP NHAT V18/V20)
     */
    private static FeatureRow copyRow(FeatureRow original) {
        FeatureRow copy = new FeatureRow();

        // Nhom 1 (9 Common Features)
        copy.debug_date = original.debug_date; // Dinh dang yyyy-MM-dd HH:mm:ss
        copy.btc_rate_change_15m = original.btc_rate_change_15m;
        copy.isTrendBuyWithBTC = original.isTrendBuyWithBTC;
        copy.isTrendBuyWithETH = original.isTrendBuyWithETH;
        copy.market_rate_down_avg_15m = original.market_rate_down_avg_15m;
        copy.top_symbols_down_15m_count = original.top_symbols_down_15m_count;
        copy.hour_of_day_sin = original.hour_of_day_sin;
        copy.hour_of_day_cos = original.hour_of_day_cos;
        copy.day_of_week_sin = original.day_of_week_sin;
        copy.day_of_week_cos = original.day_of_week_cos;

        return copy;
    }

    private void setupCsvFile() throws java.io.IOException {
        File csvFile = new File(CSV_FILE_PATH);
        File parentDir = csvFile.getParentFile();
        if (parentDir != null && !parentDir.exists()) parentDir.mkdirs();
    }
}