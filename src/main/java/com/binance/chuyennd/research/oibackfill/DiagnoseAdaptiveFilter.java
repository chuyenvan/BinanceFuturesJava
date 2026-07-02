package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * TASK (giam size export): do filter ADAPTIVE top-10% cross-sectional, DA-GIAI-DOAN.
 *
 * Filter: tai MOI moc 1m -> (1) loc coin co vol-avg-30m >= VOL_MIN (gat coin rac thanh khoan thap),
 *   (2) xep cac coin con lai theo |rate30m|, GIU top 10% bien dong manh nhat (2 chieu: tang+roi).
 *
 * Top-10% cross-sectional LUON giu ~10% moi moc => % giu on dinh moi regime (do la diem manh).
 * Cai DO o day la: NGUONG |rate30m| tuong ung top-10% (P90) dao dong the nao qua cac giai doan
 *   -> de thay tai sao adaptive tot hon co dinh (neu P90 nhay tu 0.8% den 5% thi nguong co dinh sai).
 * Va: vol-avg-30m filter gat bao nhieu % truoc khi xep hang.
 *
 * Chay nhieu cua so rai khap 2021-2025 (crash/bull/sideway/gan day) qua args.
 * Usage: java DiagnoseAdaptiveFilter <volMin> <pct> <windowsCsvLabel...>
 *   (cua so hardcode ben duoi cho de chay 1 phat)
 */
public class DiagnoseAdaptiveFilter {
    private static final Logger LOG = LoggerFactory.getLogger(DiagnoseAdaptiveFilter.class);

    // cua so da-giai-doan: {label, startEpochMs, days}
    private static final Object[][] WINDOWS = {
            {"2022-05 LUNA crash", 1651363200000L, 5},
            {"2022-11 FTT crash",  1667260800000L, 5},
            {"2023-06 sideway",    1685577600000L, 5},
            {"2024-03 bull",       1709251200000L, 5},
            {"2024-11 bull-late",  1730419200000L, 5},
            {"2025-02 recent",     1738368000000L, 5},
            {"2025-10 recent2",    1759276800000L, 5},
    };

    public static void main(String[] args) throws Exception {
        long volMin = args.length > 0 ? Long.parseLong(args[0]) : 2000;
        double pct = args.length > 1 ? Double.parseDouble(args[1]) : 0.10; // top 10%
        int window = 30; // rate30m

        LOG.info("===== ADAPTIVE FILTER top-{}% cross-sectional, |rate{}m|, volMin={} =====",
                (int) (pct * 100), window, volMin);
        LOG.info("Cua so | tongNen | %quaVol | P90_thr(|rate30m|) | P50_thr | giu(top{}%)",
                (int) (pct * 100));

        for (Object[] w : WINDOWS) {
            String label = (String) w[0];
            long start = (Long) w[1];
            int days = (Integer) w[2];
            runWindow(label, start, days, volMin, pct, window);
        }
        LOG.info("===================================================");
        LOG.info("Doc: neu P90_thr DAO DONG MANH qua cac cua so (vd 0.8%% -> 5%%) -> nguong co dinh SAI,");
        LOG.info("     adaptive top-10%% dung (tu co gian theo regime). %%giu luon ~10%% = size on dinh.");
        System.exit(0);
    }

    private static void runWindow(String label, long start, int days, long volMin, double pct, int window) {
        FundingDataCollectionManager manager = new FundingDataCollectionManager("storage/tmp_diag_adp");
        long total = 0, passVol = 0, kept = 0;
        // gom |rate30m| cua cac coin qua-vol de tinh percentile nguong (gop ca cua so de co P90/P50 dai dien)
        List<Float> absRates = new ArrayList<>();

        for (int d = 0; d < days; d++) {
            long dayStart = start + (long) d * Utils.TIME_DAY;
            TreeMap<Long, Map<String, KlineObjectSimple>> data =
                    DataManagerAerospikeFloatSim.readDataFromAerospike1M(dayStart);
            if (data == null) continue;
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : data.entrySet()) {
                Map<String, KlineObjectSimple> snap = e.getValue();
                manager.updateHistory(snap);
                // tinh |rate30m| cho cac coin qua-vol TAI moc nay
                List<Float> perTick = new ArrayList<>();
                for (Map.Entry<String, KlineObjectSimple> se : snap.entrySet()) {
                    KlineObjectSimple k = se.getValue();
                    if (k == null || !Utils.isTickerAvailable(k)) continue;
                    total++;
                    if (k.totalUsdt < volMin) continue; // dung totalUsdt nen-cuoi lam proxy vol (don gian);
                    passVol++;
                    float r = manager.getReturn(se.getKey(), window);
                    if (Float.isNaN(r)) continue;
                    float ar = Math.abs(r);
                    perTick.add(ar);
                    absRates.add(ar);
                }
                // top-pct TAI moc nay (cross-sectional): nguong = percentile(1-pct) cua perTick
                if (!perTick.isEmpty()) {
                    Collections.sort(perTick);
                    int idx = (int) Math.floor((1 - pct) * perTick.size());
                    if (idx >= perTick.size()) idx = perTick.size() - 1;
                    float tickThr = perTick.get(idx);
                    for (float ar : perTick) if (ar >= tickThr) kept++;
                }
            }
        }
        // P90/P50 cua |rate30m| tren toan cua so (de thay nguong adaptive ~ bao nhieu o regime nay)
        float p90 = percentile(absRates, 0.90), p50 = percentile(absRates, 0.50);
        double pctVol = total > 0 ? 100.0 * passVol / total : 0;
        double pctKept = total > 0 ? 100.0 * kept / total : 0;
        LOG.info(String.format("%-20s | %9d | %6.1f%% | P90=%.3f%% | P50=%.3f%% | giu=%.2f%%",
                label, total, pctVol, p90 * 100, p50 * 100, pctKept));
    }

    private static float percentile(List<Float> xs, double p) {
        if (xs.isEmpty()) return Float.NaN;
        List<Float> s = new ArrayList<>(xs);
        Collections.sort(s);
        int idx = (int) Math.floor(p * s.size());
        if (idx >= s.size()) idx = s.size() - 1;
        return s.get(idx);
    }
}
