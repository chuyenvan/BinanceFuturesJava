package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.funding.EntrySignalFilter;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Date;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * FUNCTION-TEST EntrySignalFilter tren data that 1 doan ngan (mac dinh 2022-05 LUNA crash).
 * In moi N moc: #coin co ticker, #qua vol-avg-2k, #qua top-10% (passFilter), vai gia tri rate30m.
 * Muc dich: xem filter loai sach o TANG NAO (vol? rate? warmup history?) — bug Q2-Q3 2022 = 0 record.
 *
 * Usage: java DiagnoseFilterEmpty <startEpochMs> <minutes>
 *   default: 1652313600000 (2022-05-12 07:00 GMT+7) , 720 phut (12h)
 */
public class DiagnoseFilterEmpty {
    private static final Logger LOG = LoggerFactory.getLogger(DiagnoseFilterEmpty.class);

    public static void main(String[] args) {
        Configs.IS_HPO_MODE = false;
        Configs.IS_KAGGLE_MODE = true;
        long start = args.length > 0 ? Long.parseLong(args[0]) : 1652313600000L;
        int minutes = args.length > 1 ? Integer.parseInt(args[1]) : 720;

        // warmup 48h truoc do de history co du data (giong Tool1)
        long warmup = start - 48L * 3600000L;
        int totalMin = minutes + 48 * 60;

        LOG.info("===== DIAGNOSE FILTER EMPTY | start={} minutes={} (warmup tu {}) =====",
                new Date(start), minutes, new Date(warmup));

        HistoryManager history = HistoryManager.getInstance();
        TreeMap<Long, Map<String, KlineObjectSimple>> data =
                DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(warmup, totalMin);
        if (data == null || data.isEmpty()) {
            LOG.error("❌ readDataFromAerospikeCustom tra RONG cho warmup={} totalMin={}", new Date(warmup), totalMin);
            return;
        }
        LOG.info("✅ doc {} moc tu Aerospike", data.size());

        int tick = 0, printed = 0;
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : data.entrySet()) {
            long time = e.getKey();
            Map<String, KlineObjectSimple> snap = e.getValue();
            history.updateHistory(snap); // nuoi history giong Tool1

            if (time < start) continue; // van trong warmup

            tick++;
            // dem tung tang
            int hasTicker = 0, passVol = 0;
            for (Map.Entry<String, KlineObjectSimple> se : snap.entrySet()) {
                KlineObjectSimple k = se.getValue();
                if (k == null || !Utils.isTickerAvailable(k)) continue;
                hasTicker++;
                short symId = com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper.getInstance().getId(se.getKey());
                if (symId < 0) continue;
                float volAvg = history.getAverageVolume(symId, 30);
                if (volAvg <= 0) volAvg = k.totalUsdt;
                if (volAvg >= 2000.0) passVol++;
            }
            Set<String> passFilter = EntrySignalFilter.selectCoins(snap, history);

            // in 1 moc moi 60 moc (1h) de khong spam
            if (tick % 60 == 1 && printed < 15) {
                printed++;
                // lay vai gia tri rate30m mau
                StringBuilder rateSample = new StringBuilder();
                int cnt = 0;
                for (String sym : snap.keySet()) {
                    float r = history.getReturn(sym, 30);
                    if (r != 0 && cnt < 5) { rateSample.append(sym).append("=").append(String.format("%.4f", r)).append(" "); cnt++; }
                }
                LOG.info("moc {} | ticker={} | qua_vol2k={} | passFilter(top10%)={} | rate30m mau: {}",
                        Utils.normalizeDateYYYYMMDDHHmm(time), hasTicker, passVol, passFilter.size(),
                        rateSample.length() > 0 ? rateSample.toString() : "(tat ca rate30m=0!)");
            }
        }
        LOG.info("===== HET: tong {} moc sau warmup =====", tick);
        System.exit(0);
    }
}
