package com.binance.chuyennd.research.oibackfill;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Info;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * TASK-013 — VALIDATE sau khi {@link PushOiSetsTo242} day 5 set OI/LS/taker 226->242, + cross-check voi
 * luong ingest forward ({@link com.binance.chuyennd.websocket.OpenInterestIngestor2AerospikeNew}), + bao cao
 * tai nguyen Aerospike 242 (giong {@code AerospikeCheckData} nhung chay cho 242).
 *
 * <p>DOC-ONLY. Chay TREN 226 (226 thay ca 242). SLF4j (khong System.out).
 */
public class OiPush242Validate {

    private static final Logger LOG = LoggerFactory.getLogger(OiPush242Validate.class);
    private static final String NS = Configs.AEROSPIKE_NAMESPACE;
    private static final String OI_SET = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_OPEN_INTEREST; // "open_interest"
    private static final int SPOT_N = 8;          // so symbol spot-check value
    private static final int RECONCILE_N = 6;     // so symbol doi chieu forward vs history

    public static void main(String[] args) {
        boolean allPass = true;
        try {
            AerospikeClient c226 = DataManagerAerospikeFloatSim.getClientOracle();
            AerospikeClient c242 = DataManagerAerospikeFloatSim.getClient242();

            List<String> symbols = listDoneSymbols(c226);
            LOG.info("################ OI PUSH 226->242 VALIDATE (doc-only, chay tren 226) ################");
            LOG.info("namespace={} | done_set symbol={} | OI set={}", NS, symbols.size(), OI_SET);

            reportNamespace(c242);                          // A
            allPass &= pushIntegrity(c226, c242, symbols);  // B
            allPass &= ingestCrossCheck(c242, symbols);     // C

            LOG.info("################ KET LUAN: {} ################", allPass ? "PASS" : "CO CANH BAO (xem log)");
        } catch (Exception e) {
            LOG.error("Validate loi: ", e);
            System.exit(1);
        }
        System.exit(0);
    }

    // ===================== A. BAO CAO TAI NGUYEN 242 =====================
    private static void reportNamespace(AerospikeClient c242) {
        LOG.info("================ A. BAO CAO TAI NGUYEN AEROSPIKE 242 ================");
        try {
            Map<String, String> ns = parseSemis(Info.request(c242.getNodes()[0], "namespace/" + NS));
            String[] keys = {"objects", "memory-size", "memory_used_bytes", "memory_free_pct",
                    "device_total_bytes", "device_used_bytes", "device_free_pct", "device_available_pct",
                    "data_total_bytes", "data_used_bytes", "data_used_pct", "data_avail_pct",
                    "stop-writes", "stop_writes", "replication-factor"};
            LOG.info("---- namespace/{} ----", NS);
            for (String k : keys) {
                if (ns.containsKey(k)) {
                    String v = ns.get(k);
                    boolean bytes = k.endsWith("_bytes") || k.equals("memory-size");
                    LOG.info("  {} = {}{}", k, v, bytes ? "  (" + fmtSize(parseLong(v)) + ")" : "");
                }
            }
        } catch (Exception e) {
            LOG.warn("  A namespace loi: {}", e.getMessage());
        }

        try {
            String resp = Info.request(c242.getNodes()[0], "sets/" + NS);
            Map<String, long[]> sets = new LinkedHashMap<>(); // name -> [objects, mem, dev]
            for (String rec : resp.split(";")) {
                if (!rec.contains("set=")) continue;
                String name = "";
                long objects = 0, mem = 0, dev = 0;
                for (String f : rec.split(":")) {
                    int eq = f.indexOf('=');
                    if (eq < 0) continue;
                    String k = f.substring(0, eq), v = f.substring(eq + 1);
                    switch (k) {
                        case "set": name = v; break;
                        case "objects": objects = nz(parseLong(v)); break;
                        case "memory_data_bytes": mem = nz(parseLong(v)); break;
                        case "device_data_bytes":
                        case "data_used_bytes": dev = nz(parseLong(v)); break;
                        default: break;
                    }
                }
                if (!name.isEmpty()) sets.put(name, new long[]{objects, mem, dev});
            }
            List<Map.Entry<String, long[]>> list = new ArrayList<>(sets.entrySet());
            list.sort((a, b) -> Long.compare(b.getValue()[2], a.getValue()[2]));
            long totObj = 0, totMem = 0, totDev = 0;
            LOG.info("---- MOI SET tren 242 ({} set) ----", list.size());
            LOG.info(String.format("  %-34s %12s %12s %12s", "set", "objects", "memory", "device"));
            for (Map.Entry<String, long[]> e : list) {
                long[] s = e.getValue();
                totObj += s[0]; totMem += s[1]; totDev += s[2];
                LOG.info(String.format("  %-34s %12d %12s %12s", e.getKey(), s[0], fmtSize(s[1]), fmtSize(s[2])));
            }
            LOG.info(String.format("  %-34s %12d %12s %12s", "TONG", totObj, fmtSize(totMem), fmtSize(totDev)));
        } catch (Exception e) {
            LOG.warn("  A sets loi: {}", e.getMessage());
        }
    }

    // ===================== B. PUSH INTEGRITY 226<->242 =====================
    private static boolean pushIntegrity(AerospikeClient c226, AerospikeClient c242, List<String> symbols) {
        LOG.info("================ B. PUSH INTEGRITY 226<->242 (5 set) ================");
        boolean pass = true;
        Map<String, Long> o226 = setObjects(c226), o242 = setObjects(c242);
        LOG.info(String.format("  %-26s %12s %12s   %s", "set", "226 objects", "242 objects", "ghi chu"));
        for (OiMetricSets.Metric m : OiMetricSets.ALL) {
            long a = nz(o226.get(m.set)), b = nz(o242.get(m.set));
            String note;
            if (m.set.equals(OI_SET)) {
                note = (b >= a) ? "242>=226 (chenh = #forward key=SYMBOL, xem C)" : "242<226 THIEU chunk-thang!";
                if (b < a) pass = false;
            } else {
                note = (b == a) ? "khop" : "LECH (LS/taker chi history -> phai bang)";
                if (b != a) pass = false;
            }
            LOG.info(String.format("  %-26s %12d %12d   %s", m.set, a, b, note));
        }

        List<String> spot = pick(symbols, SPOT_N);
        LOG.info("  -- spot-check value ({} symbol): getMetricMap226 vs getMetricMap242 --", spot.size());
        for (String sym : spot) {
            for (OiMetricSets.Metric m : OiMetricSets.ALL) {
                TreeMap<Long, Float> a = safeMap(true, m, sym);
                TreeMap<Long, Float> b = safeMap(false, m, sym);
                long mism = 0; double maxDiff = 0;
                for (Map.Entry<Long, Float> e : a.entrySet()) {
                    Float vb = b.get(e.getKey());
                    if (vb == null) { mism++; continue; }
                    double d = Math.abs(e.getValue() - vb);
                    if (d > maxDiff) maxDiff = d;
                }
                boolean ok = a.size() == b.size() && mism == 0 && maxDiff == 0.0;
                if (!ok) {
                    pass = false;
                    LOG.warn("    LECH {} {}: 226={} 242={} mismatchTs={} maxDiff={}", sym, m.set, a.size(), b.size(), mism, maxDiff);
                }
            }
        }
        LOG.info("  -> spot-check {} symbol x 5 set: {}", spot.size(), pass ? "TRUNG tuyet doi" : "CO LECH");
        return pass;
    }

    // ===================== C. CROSS-CHECK INGEST FORWARD =====================
    private static boolean ingestCrossCheck(AerospikeClient c242, List<String> symbols) {
        LOG.info("================ C. CROSS-CHECK INGEST FORWARD (open_interest) ================");
        boolean pass = true;

        int fwd = 0;
        List<String> fwdSyms = new ArrayList<>();
        for (String sym : symbols) {
            Record r = c242.get(null, new Key(NS, OI_SET, sym)); // key = SYMBOL (khong _yyyyMM)
            if (r != null) { fwd++; if (fwdSyms.size() < RECONCILE_N) fwdSyms.add(sym); }
        }
        long oiObj242 = nz(setObjects(c242).get(OI_SET));
        LOG.info("  open_interest 242: tong objects={} | record forward key=SYMBOL={} | con lai (chunk-thang key=SYMBOL_yyyyMM)~={}",
                oiObj242, fwd, oiObj242 - fwd);
        if (fwd > 0) {
            LOG.warn("  SCHEMA KEP: set open_interest chua CA {} record forward (key=SYMBOL, 1-record) LAN chunk-thang (history).", fwd);
            LOG.warn("     -> reader chunk-thang (getMetricMap242) KHONG doc record forward; reader key=SYMBOL (getOpenInterestMap) KHONG doc history.");
            LOG.warn("     -> khuyen nghi TASK-035: migrate forward 007-C sang chunk-thang de history+forward MOT schema.");
        } else {
            LOG.info("  (khong con record forward key=SYMBOL -- khong xung dot schema)");
        }

        LOG.info("  -- C2 doi chieu gia tri forward(key=SYMBOL) vs history(chunk-thang) tai ts trung --");
        for (String sym : fwdSyms) {
            TreeMap<Long, Float> fwdMap = DataManagerAerospikeFloatSim.getOpenInterestMap(sym);
            TreeMap<Long, Float> hisMap = DataManagerAerospikeFloatSim.getMetricMap242(OiMetricSets.OI.set, OiMetricSets.OI.bin, sym);
            long overlap = 0, mism = 0; double maxRel = 0;
            for (Map.Entry<Long, Float> e : fwdMap.entrySet()) {
                Float h = hisMap.get(e.getKey());
                if (h == null) continue;
                overlap++;
                float f = e.getValue();
                double rel = f == 0 ? (h == 0 ? 0 : 1) : Math.abs(f - h) / Math.abs(f);
                if (rel > 1e-6) mism++;
                if (rel > maxRel) maxRel = rel;
            }
            String verdict = overlap == 0 ? "KHONG co ts trung (forward moi, history chua toi thang do)"
                    : (mism == 0 ? "khop dinh nghia/don vi" : "LECH gia tri (bac thang!)");
            if (overlap > 0 && mism > 0) pass = false;
            LOG.info("    {}: forwardTs={} historyTs={} overlap={} mismatch={} maxRelDiff={} -> {}",
                    sym, fwdMap.size(), hisMap.size(), overlap, mism, String.format("%.2e", maxRel), verdict);
        }

        LOG.info("  -- C3 LS/taker: kiem KHONG co record forward key=SYMBOL --");
        for (OiMetricSets.Metric m : OiMetricSets.ALL) {
            if (m.set.equals(OI_SET)) continue;
            int fk = 0;
            for (String sym : pick(symbols, 30)) {
                if (c242.get(null, new Key(NS, m.set, sym)) != null) fk++;
            }
            if (fk > 0) { pass = false; LOG.warn("    {}: phat hien {} record key=SYMBOL (mau 30) -- KHONG mong doi", m.set, fk); }
            else LOG.info("    {}: 0 record forward (mau 30)", m.set);
        }
        return pass;
    }

    // ===================== helpers =====================
    private static List<String> listDoneSymbols(AerospikeClient c226) {
        List<String> out = new ArrayList<>();
        try {
            c226.scanAll(null, NS, OiMetricSets.DONE_SET, (key, rec) -> {
                if (key.userKey != null) out.add(key.userKey.toString());
            });
        } catch (Exception e) {
            LOG.warn("scan done_set loi: {}", e.getMessage());
        }
        return out;
    }

    private static Map<String, Long> setObjects(AerospikeClient client) {
        Map<String, Long> m = new LinkedHashMap<>();
        try {
            for (String rec : Info.request(client.getNodes()[0], "sets/" + NS).split(";")) {
                if (!rec.contains("set=")) continue;
                String name = ""; long obj = 0;
                for (String f : rec.split(":")) {
                    int eq = f.indexOf('=');
                    if (eq < 0) continue;
                    if (f.startsWith("set=")) name = f.substring(eq + 1);
                    else if (f.startsWith("objects=")) obj = nz(parseLong(f.substring(eq + 1)));
                }
                if (!name.isEmpty()) m.put(name, obj);
            }
        } catch (Exception e) {
            LOG.warn("setObjects loi: {}", e.getMessage());
        }
        return m;
    }

    private static TreeMap<Long, Float> safeMap(boolean from226, OiMetricSets.Metric m, String sym) {
        try {
            return from226 ? DataManagerAerospikeFloatSim.getMetricMap226(m.set, m.bin, sym)
                           : DataManagerAerospikeFloatSim.getMetricMap242(m.set, m.bin, sym);
        } catch (Exception e) {
            return new TreeMap<>();
        }
    }

    private static List<String> pick(List<String> all, int n) {
        List<String> out = new ArrayList<>();
        TreeSet<String> uniq = new TreeSet<>(all);
        for (String s : new String[]{"BTCUSDT", "ETHUSDT", "LUNAUSDT"}) if (uniq.contains(s)) out.add(s);
        int step = Math.max(1, all.size() / Math.max(1, n));
        for (int i = 0; i < all.size() && out.size() < n; i += step) {
            String s = all.get(i);
            if (!out.contains(s)) out.add(s);
        }
        return out;
    }

    private static Map<String, String> parseSemis(String resp) {
        Map<String, String> m = new LinkedHashMap<>();
        if (resp == null) return m;
        for (String p : resp.split(";")) {
            int eq = p.indexOf('=');
            if (eq > 0) m.put(p.substring(0, eq).trim(), p.substring(eq + 1).trim());
        }
        return m;
    }

    private static Long parseLong(String s) {
        try { return s == null ? null : Long.parseLong(s.trim()); } catch (Exception e) { return null; }
    }

    private static long nz(Long v) { return v == null ? 0L : v; }

    private static String fmtSize(long bytes) {
        if (bytes <= 0) return "0";
        String[] u = {"B", "KB", "MB", "GB", "TB"};
        int i = 0; double b = bytes;
        while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
        return String.format("%.2f %s", b, u[i]);
    }
}
