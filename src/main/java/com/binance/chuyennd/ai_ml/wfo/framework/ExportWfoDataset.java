package com.binance.chuyennd.ai_ml.wfo.framework;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * WFO FRAMEWORK — entrypoint EXPORT dataset offline (chạy 1 lần trên node có Aerospike, vd Oracle/226).
 * Scan 3 khối từ Aerospike 226 → file binary + manifest md5 vào outDir. Sau đó phân phát file cho các
 * node (VPS scp; Kaggle upload Dataset). Chỉ chạy lại khi DATA NGUỒN đổi.
 *
 * Arg: [outDir=~/claudedata/wfo_dataset]
 */
public class ExportWfoDataset {
    private static final Logger LOG = LoggerFactory.getLogger(ExportWfoDataset.class);

    public static void main(String[] args) {
        try {
            // export ĐỌC từ 226 (market/pred/funding là 226-native qua getClient226) → không cần kaggle-mode,
            // nhưng set cho an toàn nếu chạy ở node chỉ với được 226.
            com.binance.chuyennd.tradecore.Configs.IS_KAGGLE_MODE = true;
            String home = System.getProperty("user.home");
            String outDir = args.length > 0 ? args[0] : home + "/claudedata/wfo_dataset";
            WfoDataset.export(outDir);
            LOG.info("EXPORT xong -> {}. Phan phat file cho cac node (VPS scp / Kaggle Dataset).", outDir);
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("ExportWfoDataset FAIL", e);
            System.exit(1);
        }
    }
}
