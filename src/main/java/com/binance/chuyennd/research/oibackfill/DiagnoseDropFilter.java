package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Date;
import java.util.Map;
import java.util.TreeMap;

/**
 * TASK (giam size export): do filter 2-tang giong RunFundingDataCollection giam bao nhieu record.
 *   Tang 1: totalUsdt >= VOL_MIN
 *   Tang 2: rate1m < -0.004 HOAC rate15m < -0.015 (coin dang ROI)
 * So sanh: tong nen vs sau-tang-1 vs sau-tang-2, cho nhieu nguong VOL_MIN.
 * Day la filter PHAI dung chung train/backtest/hpo/wfo/live.
 *
 * Usage: java DiagnoseDropFilter <startEpochMs> <days>
 */
public class DiagnoseDropFilter {
    private static final Logger LOG = LoggerFactory.getLogger(DiagnoseDropFilter.class);

    public static void main(String[] args) throws Exception {
        Configs.IS_HPO_MODE = false;
        Configs.IS_KAGGLE_MODE = true;
        long start = args.length > 0 ? Long.parseLong(args[0]) : 1704067200000L;
        int days = args.length > 1 ? Integer.parseInt(args[1]) : 7;

        long[] volMins = {5000, 10000, 20000};
        FundingDataCollectionManager manager = new FundingDataCollectionManager("storage/tmp_diag_drop");

        long total = 0;
        long[] afterVol = new long[volMins.length];
        long[] afterDrop = new long[volMins.length];

        LOG.info("===== DIAGNOSE DROP FILTER (start={} days={}) =====", new Date(start), days);
        for (int d = 0; d < days; d++) {
            long dayStart = start + (long) d * Utils.TIME_DAY;
            TreeMap<Long, Map<String, KlineObjectSimple>> data =
                    DataManagerAerospikeFloatSim.readDataFromAerospike1M(dayStart);
            if (data == null) continue;
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : data.entrySet()) {
                Map<String, KlineObjectSimple> snap = e.getValue();
                manager.updateHistory(snap); // nuoi history de getReturn(15) dung
                for (Map.Entry<String, KlineObjectSimple> se : snap.entrySet()) {
                    String symbol = se.getKey();
                    KlineObjectSimple k = se.getValue();
                    if (k == null || !Utils.isTickerAvailable(k)) continue;
                    total++;
                    float rate1m = (k.priceClose - k.priceOpen) / k.priceOpen;
                    float rate15m = manager.getReturn(symbol, 15);
                    boolean dropping = !(rate1m >= -0.004f && rate15m >= -0.015f);
                    for (int i = 0; i < volMins.length; i++) {
                        if (k.totalUsdt >= volMins[i]) {
                            afterVol[i]++;
                            if (dropping) afterDrop[i]++;
                        }
                    }
                }
            }
            LOG.info("  ...ngay {}/{} total={}", d + 1, days, total);
        }

        LOG.info("===================================================");
        LOG.info("Tong nen (coin x moc 1m, isTickerAvailable) = {}", total);
        for (int i = 0; i < volMins.length; i++) {
            double volPct = total > 0 ? 100.0 * afterVol[i] / total : 0;
            double dropPct = total > 0 ? 100.0 * afterDrop[i] / total : 0;
            LOG.info(String.format("  VOL>=%-6d : sau-vol=%d (%.1f%% giu) -> sau-drop=%d (%.2f%% giu | giam %.2f%% so tong)",
                    volMins[i], afterVol[i], volPct, afterDrop[i], dropPct, 100 - dropPct));
        }
        LOG.info("===================================================");
        LOG.info("=> filter 2-tang (vol + drop) la don bay that. Day la filter CHUNG train/backtest/hpo/wfo/live.");
        System.exit(0);
    }
}
