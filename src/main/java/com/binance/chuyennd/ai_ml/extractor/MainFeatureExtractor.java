package com.binance.chuyennd.ai_ml.extractor;

import com.binance.chuyennd.aerospike.DataManagerAerospike;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * LOP CHINH (MAIN CLASS) DE CHAY
 * Phien ban V16 (FINAL):
 * - Dung duong dan ../storage...
 * - Tu dong Resume (doc dong cuoi cung cua CSV de chay tiep).
 */
public class MainFeatureExtractor {

    public static final Logger LOG = LoggerFactory.getLogger(MainFeatureExtractor.class);

    // --- Cau hinh ---
    public static final String CSV_FILE_PATH = "../storage/ai_ml/dl4j/btc_model_dataset_v16_final.csv";
    public static final String ENTRIES_DATA_FILE = "../storage/ai_ml/dl4j/entries.data";

    public static final int WARMUP_PERIOD = 200;
    public static final int SIMULATION_PERIOD_MINUTES = 7 * 24 * 60;

    public static void main(String[] args) {

        LOG.info("BAT DAU QUA TRINH XUAT DU LIEU (FEATURE EXTRACTION V16 - AUTO RESUME)...");
        long globalStartTime = System.currentTimeMillis();
        CsvWriter csvWriter = null;

        try {
            // --- BUOC 0: DOC TIME CUOI CUNG TRONG CSV (DE RESUME) ---
            Set<Long> timeProcessed = readLastProcessedTimestamp(CSV_FILE_PATH);
            if (timeProcessed != null) {
                LOG.info(">>> TIM THAY DU LIEU CU: Tiep tuc chay tu");
            } else {
                LOG.info(">>> KHONG CO DU LIEU CU (HOAC FILE MOI): Chay tu dau.");
            }

            // --- BUOC 1: TAI DU LIEU ---
            LOG.info("Dang tai du lieu tinh...");
            DataContext.loadAllStaticData();
            LOG.info("Tai du lieu static thanh cong.");

            LOG.info("Dang tai file entries.data tu: {}", ENTRIES_DATA_FILE);
            @SuppressWarnings("unchecked")
            Map<Long, Set<String>> time2symbols2trade =
                    (Map<Long, Set<String>>) StorageSnappy.readObjectFromFile(ENTRIES_DATA_FILE);

            if (time2symbols2trade == null || time2symbols2trade.isEmpty()) {
                throw new RuntimeException("KHONG THE TAI 'entries.data' hoac file bi trong!");
            }
            LOG.info("Tong cong co {} entry points.", time2symbols2trade.size());

            // --- BUOC 2: CHUAN BI CSV (Append Mode) ---
            setupCsvFile();
            csvWriter = new CsvWriter(CSV_FILE_PATH, FeatureCalculator.getCsvHeader());

            int rowsWritten = 0;
            int totalSymbolNeedProcess = 0;
            long processedEntries = 0;
            long skippedEntries = 0;
            for (Set<String> symbols : time2symbols2trade.values()) {
                totalSymbolNeedProcess += symbols.size();
            }

            // --- BUOC 3: LOOP QUA ENTRIES ---
            for (Map.Entry<Long, Set<String>> entry : time2symbols2trade.entrySet()) {

                long currentTimestamp = entry.getKey();
                Set<String> symbolsToSimulate = entry.getValue();

                // !!! LOGIC RESUME !!!
                // Neu timestamp nay nho hon hoac bang timestamp cuoi cung da ghi -> Bo qua
                processedEntries += symbolsToSimulate.size();
                if (timeProcessed.contains(currentTimestamp)) {
                    skippedEntries += symbolsToSimulate.size();
                    continue;
                }
                LOG.info("... Dang xu ly entry {}/{} (Da skip: {}) | Time: {}",
                        processedEntries, totalSymbolNeedProcess, skippedEntries, Utils.normalizeDateYYYYMMDDHHmm(currentTimestamp));

                int i = DataContext.getTimestampIndex(currentTimestamp);

                if (i < WARMUP_PERIOD || i >= DataContext.ALL_TIMESTAMPS_LIST.size() - SIMULATION_PERIOD_MINUTES) {
                    continue;
                }

                FeatureRow commonFeatures = FeatureCalculator.calculateFeatures(i);
                if (commonFeatures == null) continue;

                for (String symbol : symbolsToSimulate) {

                    long startLoad = currentTimestamp - (WARMUP_PERIOD * Utils.TIME_MINUTE);
                    long endLoad = currentTimestamp + (SIMULATION_PERIOD_MINUTES * Utils.TIME_MINUTE);

                    TreeMap<Long, KlineObjectSimple> symbolData =
                            DataManagerAerospike.readDataForPeriod(symbol, startLoad, endLoad);

                    if (symbolData == null || symbolData.isEmpty()) continue;

                    List<KlineObjectSimple> historyKlines = new ArrayList<>();
                    List<Double> historyCloses = new ArrayList<>();

                    for (Map.Entry<Long, KlineObjectSimple> e : symbolData.entrySet()) {
                        if (e.getKey() <= currentTimestamp) {
                            historyKlines.add(e.getValue());
                            historyCloses.add(e.getValue().priceClose);
                        }
                    }

                    if (historyKlines.size() < WARMUP_PERIOD) continue;

                    FeatureRow symbolRow = copyRow(commonFeatures);
                    symbolRow.debug_symbol = symbol;

                    FeatureCalculator.calculateSymbolFeatures(symbolRow, historyKlines, historyCloses);

                    LabelSimulator.LabelResult label =
                            LabelSimulator.calculateSingleSymbolLabel_WithData(symbolData, currentTimestamp);

                    if (label == null) continue;

                    symbolRow.pnl_final = label.pnl_final;
                    symbolRow.max_drawdown = label.max_drawdown;
                    symbolRow.time_to_profit = label.time_to_profit;

                    csvWriter.writeRow(symbolRow);
                    rowsWritten++;
                }
            }

            LOG.info("\n--- HOAN TAT: Tong so dong MOI da ghi: {} ---", rowsWritten);

        } catch (Exception e) {
            LOG.error("Gap loi nghiem trong:", e);
        } finally {
            if (csvWriter != null) csvWriter.close();
            DataManagerAerospike.closeConnection();
        }

        long globalEndTime = System.currentTimeMillis();
        LOG.info("Tong thoi gian chay: {} phut.", ((globalEndTime - globalStartTime) / 1000.0 / 60.0));
    }

    /**
     * Ham doc nguoc file CSV de lay TimeStamp cua dong cuoi cung.
     */
    private static Set<Long> readLastProcessedTimestamp(String filePath) {
        Set<Long> timeProcessed = new HashSet<>();
        File file = new File(filePath);
        if (!file.exists() || file.length() == 0) {
            return timeProcessed;
        }

        try {
            List<String> lines = FileUtils.readLines(file);
            SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd HH:mm");
            for (String line : lines) {
                try {
                    if (line.trim().isEmpty() || line.startsWith("debug_date")) {
                        continue;
                    }
                    String[] parts = line.split(",");
                    if (parts.length > 2) {
                        String dateString = parts[parts.length - 2];
                        timeProcessed.add(sdf.parse(dateString).getTime());
                    }
                } catch (Exception e) {
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        return timeProcessed;
    }

    private static FeatureRow copyRow(FeatureRow original) {
        FeatureRow copy = new FeatureRow();
        copy.debug_date = original.debug_date;
        copy.btc_rate_change_1m = original.btc_rate_change_1m;
        copy.btc_rate_change_5m = original.btc_rate_change_5m;
        copy.btc_rate_change_15m = original.btc_rate_change_15m;
        copy.btc_rate_vs_high_15m = original.btc_rate_vs_high_15m;
        copy.btc_rate_vs_high_30m = original.btc_rate_vs_high_30m;
        copy.btc_rate_vs_high_60m = original.btc_rate_vs_high_60m;
        copy.btc_rate_vs_low_15m = original.btc_rate_vs_low_15m;
        copy.btc_volume_1m_vs_sma_60m = original.btc_volume_1m_vs_sma_60m;
        copy.btc_5m_candle_wick_ratio = original.btc_5m_candle_wick_ratio;
        copy.isTrendBuyWithBTC = original.isTrendBuyWithBTC;
        copy.isTrendBuyWithETH = original.isTrendBuyWithETH;
        copy.btc_rsi_14_1m = original.btc_rsi_14_1m;
        copy.btc_macd_hist_1m = original.btc_macd_hist_1m;
        copy.btc_bb_width_20_1m = original.btc_bb_width_20_1m;
        copy.eth_rsi_14_1m = original.eth_rsi_14_1m;
        copy.eth_macd_hist_1m = original.eth_macd_hist_1m;
        copy.eth_bb_width_20_1m = original.eth_bb_width_20_1m;
        copy.market_rate_down_avg_1m = original.market_rate_down_avg_1m;
        copy.market_rate_down_avg_15m = original.market_rate_down_avg_15m;
        copy.market_rate_up_avg_1m = original.market_rate_up_avg_1m;
        copy.corr_btc_eth_1h = original.corr_btc_eth_1h;
        copy.top_symbols_down_15m_count = original.top_symbols_down_15m_count;
        copy.hour_of_day_sin = original.hour_of_day_sin;
        copy.hour_of_day_cos = original.hour_of_day_cos;
        copy.day_of_week_sin = original.day_of_week_sin;
        copy.day_of_week_cos = original.day_of_week_cos;
        return copy;
    }

    private static void setupCsvFile() throws java.io.IOException {
        File csvFile = new File(CSV_FILE_PATH);
        File parentDir = csvFile.getParentFile();
        if (parentDir != null && !parentDir.exists()) parentDir.mkdirs();
    }
}