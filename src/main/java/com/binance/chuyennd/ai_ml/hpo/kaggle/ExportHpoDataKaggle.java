package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.util.Date;
import java.util.Map;
import java.util.TreeMap;
import java.util.zip.GZIPOutputStream;

public class ExportHpoDataKaggle {
    private static final Logger LOG = LoggerFactory.getLogger(ExportHpoDataKaggle.class);
    private static final String EXPORT_DIR = "kaggle_data_hpo_15m/";

    public static void main(String[] args) throws Exception {
        new File(EXPORT_DIR).mkdirs();

        String startStr = "20251001";
        String endStr = "20260501";

        long startTs = Utils.sdfFile.parse(startStr).getTime();
        long endTs = Utils.sdfFile.parse(endStr).getTime();

        // 🔥 Tính tổng số Block 15 Phút
        int total15mBlocks = (int) ((endTs - startTs) / (15 * Utils.TIME_MINUTE));

        exportCoreData(startTs, total15mBlocks);
        exportTickerData(startTs, endTs);

        LOG.info("🎉 All 15M data exported to: {}", EXPORT_DIR);
        System.exit(0);
    }

    private static void exportCoreData(long startTs, int total15mBlocks) {
        LOG.info("📥 Exporting Core Data 15M (MarketData, AiPred, FundingPred)...");
        try {
            // Gọi 3 hàm Range mới tinh dành cho 15M
            TreeMap<Long, MarketDataObject15M> marketData = DataManagerAerospikeFloatSim.getMarketData15MByRange(startTs, total15mBlocks);
            TreeMap<Long, AiPredictionData> aiPred = DataManagerAerospikeFloatSim.getAiPredictions15MByRange(startTs, total15mBlocks);
            TreeMap<Long, long[]> fundingPred = DataManagerAerospikeFloatSim.getFundingPredictions15MByRange(startTs, total15mBlocks);

            saveObject(EXPORT_DIR + "core_market_data.bin.gz", marketData);
            saveObject(EXPORT_DIR + "core_ai_pred.bin.gz", aiPred);
            saveObject(EXPORT_DIR + "core_funding_pred.bin.gz", fundingPred);

            LOG.info("✅ Core data 15M saved.");
        } catch (Exception e) {
            LOG.error("❌ Failed to export core data", e);
        }
    }

    private static void exportTickerData(long startTs, long endTs) {
        LOG.info("📥 Exporting 15M Tickers chunk by chunk (1 Day = 96 Blocks)...");
        long currentTs = startTs;
        while (currentTs < endTs) {
            try {
                // Đọc chính xác 96 nến (1 ngày) qua hàm Custom 15M
                TreeMap<Long, Map<Short, KlineObjectSimple>> dailyData = DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTs, 96);

                if (dailyData != null && !dailyData.isEmpty()) {
                    String fileName = EXPORT_DIR + "ticker_15m_" + Utils.sdfFile.format(new Date(currentTs)) + ".bin.gz";
                    saveObject(fileName, dailyData);
                    LOG.info("  -> Saved {}", fileName);
                }
            } catch (Exception e) {
                LOG.error("Failed on " + Utils.normalizeDateYYYYMMDD(currentTs), e);
            }
            currentTs += Utils.TIME_DAY;
        }
    }

    private static void saveObject(String path, Object obj) throws IOException {
        try (ObjectOutputStream oos = new ObjectOutputStream(new BufferedOutputStream(new GZIPOutputStream(new FileOutputStream(path)), 1024 * 1024))) {
            oos.writeObject(obj);
        }
    }
}