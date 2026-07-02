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
        long start = args.length > 0 ? Long.parseLong(args[0]) : 1704067200000L;
        int days = args.length > 1 ? Integer.parseInt(args[1]) : 7;

        // BIEN DONG 2 CHIEU: |rate(window)| > THR, volume >= 5000. So 3 kieu: chi-roi, chi-tang, 2-chieu (abs).
        // Bat ca trend tang manh, khong chi coin roi. Window {15,30} x thr {0.01,0.015}.
        long volMin = 5000;
        int[] windows = {15, 30};
        float[] thrs = {0.01f, 0.015f};
        FundingDataCollectionManager manager = new FundingDataCollectionManager("storage/tmp_diag_drop");

        long total = 0, afterVol = 0;
        // [windowIdx][thrIdx] x 3 kieu
        long[][] down = new long[windows.length][thrs.length];
        long[][] up = new long[windows.length][thrs.length];
        long[][] both = new long[windows.length][thrs.length];

        LOG.info("===== DIAGNOSE VOLATILITY FILTER (vol>={}, start={} days={}) =====", volMin, new Date(start), days);
        for (int d = 0; d < days; d++) {
            long dayStart = start + (long) d * Utils.TIME_DAY;
            TreeMap<Long, Map<String, KlineObjectSimple>> data =
                    DataManagerAerospikeFloatSim.readDataFromAerospike1M(dayStart);
            if (data == null) continue;
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : data.entrySet()) {
                Map<String, KlineObjectSimple> snap = e.getValue();
                manager.updateHistory(snap); // nuoi history de getReturn(window) dung
                for (Map.Entry<String, KlineObjectSimple> se : snap.entrySet()) {
                    String symbol = se.getKey();
                    KlineObjectSimple k = se.getValue();
                    if (k == null || !Utils.isTickerAvailable(k)) continue;
                    total++;
                    if (k.totalUsdt < volMin) continue;
                    afterVol++;
                    for (int wi = 0; wi < windows.length; wi++) {
                        float rate = manager.getReturn(symbol, windows[wi]);
                        for (int ti = 0; ti < thrs.length; ti++) {
                            if (rate < -thrs[ti]) down[wi][ti]++;
                            if (rate > thrs[ti]) up[wi][ti]++;
                            if (Math.abs(rate) > thrs[ti]) both[wi][ti]++;
                        }
                    }
                }
            }
            LOG.info("  ...ngay {}/{} total={}", d + 1, days, total);
        }

        LOG.info("===================================================");
        LOG.info("Tong nen (coin x moc 1m, isTickerAvailable) = {} | sau vol>={} = {} ({}%)",
                total, volMin, afterVol, String.format("%.1f", total > 0 ? 100.0 * afterVol / total : 0));
        for (int wi = 0; wi < windows.length; wi++) {
            for (int ti = 0; ti < thrs.length; ti++) {
                double pd = total > 0 ? 100.0 * down[wi][ti] / total : 0;
                double pu = total > 0 ? 100.0 * up[wi][ti] / total : 0;
                double pb = total > 0 ? 100.0 * both[wi][ti] / total : 0;
                LOG.info(String.format("  w%dm thr%.1f%%: roi=%.2f%% | tang=%.2f%% | 2chieu(abs)=%.2f%% (giu) -> giam %.2f%%",
                        windows[wi], thrs[ti] * 100, pd, pu, pb, 100 - pb));
            }
        }
        LOG.info("===================================================");
        LOG.info("=> 2chieu bat ca trend tang+roi. Chon window+thr cho giu ~5-12%. Filter CHUNG train/backtest/hpo/wfo/live.");
        System.exit(0);
    }
}
