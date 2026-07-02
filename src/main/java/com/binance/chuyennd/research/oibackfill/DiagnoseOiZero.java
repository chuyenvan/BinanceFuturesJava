package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-103f chan doan: 510 moc BTC OI <=0 nam dau? Rai deu hay cum?
 * In phan bo theo thang + vai vi du gia tri+thoi gian, de quyet: nhieu rai rac (noi nguong)
 * hay loi he thong 1 giai doan (can backfill lai doan do).
 */
public class DiagnoseOiZero {
    private static final Logger LOG = LoggerFactory.getLogger(DiagnoseOiZero.class);

    public static void main(String[] args) {
        String coin = args.length > 0 ? args[0] : "BTCUSDT";
        LOG.info("===== DIAGNOSE OI <=0 cho {} =====", coin);

        TreeMap<Long, Float> oi = DataManagerAerospikeFloatSim.getMetricMap226(
                OiMetricSets.OI.set, OiMetricSets.OI.bin, coin);
        if (oi == null || oi.isEmpty()) {
            LOG.error("OI empty cho {}", coin);
            return;
        }
        SimpleDateFormat ym = new SimpleDateFormat("yyyy-MM");
        SimpleDateFormat full = new SimpleDateFormat("yyyy-MM-dd HH:mm");

        TreeMap<String, Integer> byMonth = new TreeMap<>();
        int zero = 0, neg = 0;
        long firstBad = -1, lastBad = -1;
        List<String> samples = new ArrayList<>();
        for (Map.Entry<Long, Float> e : oi.entrySet()) {
            float v = e.getValue();
            if (v <= 0) {
                String mk = ym.format(new Date(e.getKey()));
                byMonth.merge(mk, 1, Integer::sum);
                if (v == 0) zero++; else neg++;
                if (firstBad < 0) firstBad = e.getKey();
                lastBad = e.getKey();
                if (samples.size() < 10) samples.add(full.format(new Date(e.getKey())) + " = " + v);
            }
        }
        LOG.info("Tong moc={} | OI<=0: {} (zero={} neg={})", oi.size(), zero + neg, zero, neg);
        LOG.info("Bad dau tien: {} | cuoi: {}",
                firstBad > 0 ? full.format(new Date(firstBad)) : "-",
                lastBad > 0 ? full.format(new Date(lastBad)) : "-");
        LOG.info("--- Phan bo <=0 theo thang ---");
        for (Map.Entry<String, Integer> e : byMonth.entrySet()) {
            LOG.info("  {} : {}", e.getKey(), e.getValue());
        }
        LOG.info("--- 10 vi du ---");
        for (String s : samples) LOG.info("  {}", s);

        // Ket luan tu dong
        int nMonths = byMonth.size();
        int maxInOneMonth = byMonth.values().stream().mapToInt(i -> i).max().orElse(0);
        boolean concentrated = nMonths <= 3 || maxInOneMonth > (zero + neg) * 0.7;
        LOG.info("===================================================");
        if (concentrated) {
            LOG.warn("KET LUAN: <=0 TAP TRUNG ({} thang, max 1 thang={}) -> nghi loi 1 giai doan, xem co can backfill lai doan do.",
                    nMonths, maxInOneMonth);
        } else {
            LOG.info("KET LUAN: <=0 RAI DEU ({} thang) -> nhieu rai rac, an toan coi la NaN/noi nguong pass.", nMonths);
        }
        System.exit(0);
    }
}
