package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * TASK (giam size export): danh gia filter volume nen 1m (totalUsdt) giam bao nhieu record.
 * Doc ticker 1m tu Aerospike 226 trong 1 khoang mau, dem % nen vuot cac nguong 1k/5k/10k/20k/50k.
 * => chon nguong nho nhat ma van giam du nhieu. Day chinh la filter se dung CHUNG cho
 *    export + backtest + live (note ky trong task).
 *
 * Usage: java DiagnoseVolumeFilter <startEpochMs> <days>
 */
public class DiagnoseVolumeFilter {
    private static final Logger LOG = LoggerFactory.getLogger(DiagnoseVolumeFilter.class);

    public static void main(String[] args) {
        Configs.IS_HPO_MODE = false;
        Configs.IS_KAGGLE_MODE = true;
        long start = args.length > 0 ? Long.parseLong(args[0]) : 1704067200000L; // 2024-01-01
        int days = args.length > 1 ? Integer.parseInt(args[1]) : 7;
        long[] thresholds = {1000, 5000, 10000, 20000, 50000};

        LOG.info("===== DIAGNOSE VOLUME FILTER (start={} days={}) =====", new Date(start), days);
        long total = 0;
        long[] passCount = new long[thresholds.length];
        long nanVol = 0;

        // doc theo tung ngay de khong tran RAM
        for (int d = 0; d < days; d++) {
            long dayStart = start + (long) d * 1440 * 60_000L;
            TreeMap<Long, Map<String, KlineObjectSimple>> data =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(dayStart, 1440);
            if (data == null) continue;
            for (Map<String, KlineObjectSimple> snap : data.values()) {
                for (KlineObjectSimple k : snap.values()) {
                    if (k == null) continue;
                    total++;
                    float vol = k.totalUsdt;
                    if (Float.isNaN(vol)) { nanVol++; continue; }
                    for (int i = 0; i < thresholds.length; i++) {
                        if (vol >= thresholds[i]) passCount[i]++;
                    }
                }
            }
            LOG.info("  ...ngay {}/{} xong, total tich luy={}", d + 1, days, total);
        }

        LOG.info("===================================================");
        LOG.info("Tong nen (coin x moc 1m) = {} | NaN vol = {}", total, nanVol);
        LOG.info("{'nguong':>10} {'pass':>14} {'%giu':>8} {'%giam':>8}");
        for (int i = 0; i < thresholds.length; i++) {
            double keepPct = total > 0 ? 100.0 * passCount[i] / total : 0;
            LOG.info(String.format("  >=%-8d %14d %7.2f%% %7.2f%%",
                    thresholds[i], passCount[i], keepPct, 100 - keepPct));
        }
        LOG.info("===================================================");
        LOG.info("CHON: nguong giam du nhieu (vd >=70%) nhung khong cat coin tot. Day la filter CHUNG export+backtest+live.");
        System.exit(0);
    }
}
