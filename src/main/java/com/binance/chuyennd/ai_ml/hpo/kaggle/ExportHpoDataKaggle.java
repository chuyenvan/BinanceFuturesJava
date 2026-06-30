package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
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
    private static final String EXPORT_DIR = "kaggle_data_hpo/";

    public static void main(String[] args) throws Exception {
        new File(EXPORT_DIR).mkdirs();

        // Doc qua client 226 (getReadClient khi HPO_MODE) -> tren Oracle config AEROSPIKE_HOST_226=127.0.0.1
        // => doc Aerospike LOCAL (server 8, batch-get OK), nhanh, khong qua mang VN.
        com.binance.chuyennd.tradecore.Configs.IS_HPO_MODE = true;

        // Range qua args: arg0=start (yyyyMMdd), arg1=end. arg2="ticker" => chi export ticker (bo core).
        String startStr = args.length > 0 ? args[0] : "20251001";
        String endStr = args.length > 1 ? args[1] : "20260501";
        boolean tickerOnly = args.length > 2 && "ticker".equalsIgnoreCase(args[2]);

        long startTs = Utils.sdfFile.parse(startStr).getTime();
        long endTs = Utils.sdfFile.parse(endStr).getTime();
        LOG.info("Export range {} -> {} (tickerOnly={})", startStr, endStr, tickerOnly);

        if (!tickerOnly) exportCoreData(startTs, endTs);
        exportTickerData(startTs, endTs);

        LOG.info("🎉 All data exported to: {}", EXPORT_DIR);
    }

    private static void exportCoreData(long startTs, long endTs) {
        LOG.info("📥 Exporting Core Data (MarketData, AiPred, FundingPred)...");
        try {
            TreeMap<Long, MarketDataObject> marketData = DataManagerAerospikeFloatSim.getMarketDataByRange(startTs, (int) ((endTs - startTs) / Utils.TIME_MINUTE));
            TreeMap<Long, AiPredictionData> aiPred = DataManagerAerospikeFloatSim.getMarketAiPredictionsByRange(startTs, (int) ((endTs - startTs) / Utils.TIME_MINUTE));
            TreeMap<Long, long[]> fundingPred = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTs, (int) ((endTs - startTs) / Utils.TIME_MINUTE));

            saveObject(EXPORT_DIR + "core_market_data.bin.gz", marketData);
            saveObject(EXPORT_DIR + "core_ai_pred.bin.gz", aiPred);
            saveObject(EXPORT_DIR + "core_funding_pred.bin.gz", fundingPred);

            LOG.info("✅ Core data saved.");
        } catch (Exception e) {
            LOG.error("❌ Failed to export core data", e);
        }
    }

    private static void exportTickerData(long startTs, long endTs) {
        LOG.info("📥 Exporting 1M Tickers chunk by chunk...");
        long currentTs = startTs;
        while (currentTs < endTs) {
            try {
                // Export daily chunks to avoid OOM during export
                TreeMap<Long, Map<String, KlineObjectSimple>> dailyData = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTs);
                if (dailyData != null && !dailyData.isEmpty()) {
                    String fileName = EXPORT_DIR + "ticker_" + Utils.sdfFile.format(new Date(currentTs)) + ".bin.gz";
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