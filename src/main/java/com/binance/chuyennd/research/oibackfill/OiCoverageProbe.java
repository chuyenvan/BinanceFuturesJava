package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.TimeZone;
import java.util.TreeMap;

/**
 * TASK-035 (phan tich, DOC-ONLY) — Do COVERAGE 5 set OI/LS/taker tren 242 + record forward OI, de danh gia
 * rui ro HONG du lieu: moc dau/cuoi history (chunk-thang) vs forward, va khoang cach toi hien tai.
 * Chay TREN 226. SLF4j. KHONG ghi/xoa gi.
 */
public class OiCoverageProbe {

    private static final Logger LOG = LoggerFactory.getLogger(OiCoverageProbe.class);
    private static final SimpleDateFormat F = mk();
    private static final String[] SYMS = {"BTCUSDT", "ETHUSDT", "LUNAUSDT", "DOGEUSDT"};

    private static SimpleDateFormat mk() {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        return f;
    }

    private static String d(long ts) { return F.format(new java.util.Date(ts)); }

    public static void main(String[] args) {
        long now = System.currentTimeMillis();
        LOG.info("################ OI COVERAGE PROBE @242 | bay gio (GMT+7) = {} ################", d(now));
        for (String sym : SYMS) {
            LOG.info("==== {} ====", sym);
            for (OiMetricSets.Metric m : OiMetricSets.ALL) {
                TreeMap<Long, Float> h = DataManagerAerospikeFloatSim.getMetricMap242(m.set, m.bin, sym);
                if (h.isEmpty()) {
                    LOG.info("  {} history(chunk): RONG", pad(m.set));
                    continue;
                }
                long last = h.lastKey();
                double daysBehind = (now - last) / 86_400_000.0;
                LOG.info("  {} history(chunk): n={} [{} .. {}] | cach hien tai {} ngay",
                        pad(m.set), h.size(), d(h.firstKey()), d(last), String.format("%.1f", daysBehind));
            }
            TreeMap<Long, Float> fwd = DataManagerAerospikeFloatSim.getOpenInterestMap(sym);
            if (fwd.isEmpty()) {
                LOG.info("  open_interest FORWARD(key=SYM): RONG");
            } else {
                double daysBehind = (now - fwd.lastKey()) / 86_400_000.0;
                LOG.info("  open_interest FORWARD(key=SYM): n={} [{} .. {}] | cach hien tai {} ngay",
                        fwd.size(), d(fwd.firstKey()), d(fwd.lastKey()), String.format("%.1f", daysBehind));
            }
        }
        LOG.info("################ HET ################");
        System.exit(0);
    }

    private static String pad(String s) {
        StringBuilder b = new StringBuilder(s);
        while (b.length() < 22) b.append(' ');
        return b.toString();
    }
}
