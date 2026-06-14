package com.binance.chuyennd.ai_ml.validation.data;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Info;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.google.gson.reflect.TypeToken;
import org.xerial.snappy.Snappy;

import java.lang.reflect.Type;
import java.text.SimpleDateFormat;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.TimeZone;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * TASK-032 — Inventory TOÀN DIỆN Aerospike (242 + 226) để chốt DATA_ARCHITECTURE §6 (A/B + replicate).
 * Đọc-only, ƯU TIÊN {@code Info.request} (metadata namespace/sets — nhẹ, KHÔNG scan-all record). Chỉ
 * sample vài key/set cho range thời gian. Chạy <b>TRÊN 226</b> (226 thấy cả 242). In stdout để capture.
 *
 * <p>Phần A namespace-stats (objects, memory/disk used+free+%, stop-writes, replication, storage-engine) ·
 * B liệt kê MỌI set (#object + bytes mem/disk) · C chi tiết market set (range ts + schema bin, qua sample
 * key BTC/ETH + probe ngày cho {@code kline_1m_opt}) · D đối chiếu set 242 vs 226.
 */
public class Aerospike242Inventory {

    private static final String NS = Configs.AEROSPIKE_NAMESPACE;
    private static final Type MAP_SF = new TypeToken<Map<String, Float>>() {}.getType();
    private static final Type MAP_KLINE = new TypeToken<TreeMap<Long, float[]>>() {}.getType();

    private static final SimpleDateFormat TS = mk("yyyy-MM-dd HH:mm");

    private static SimpleDateFormat mk(String p) {
        SimpleDateFormat f = new SimpleDateFormat(p);
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        return f;
    }

    /** set → objects, cho phần D đối chiếu. */
    private static final Map<String, Long> sets242 = new LinkedHashMap<>();
    private static final Map<String, Long> sets226 = new LinkedHashMap<>();

    public static void main(String[] args) {
        System.out.println("################ AEROSPIKE 242+226 INVENTORY (TASK-032, đọc-only) ################");
        System.out.println("scan-time (GMT+7) = " + TS.format(new java.util.Date(System.currentTimeMillis())));
        System.out.println("namespace = " + NS);

        scan("242-LIVE", safe(true), sets242);
        scan("226-BACKTEST", safe(false), sets226);

        // D — đối chiếu set 242 vs 226
        System.out.println("\n================ D. ĐỐI CHIẾU SET 242 vs 226 ================");
        TreeSet<String> all = new TreeSet<>();
        all.addAll(sets242.keySet());
        all.addAll(sets226.keySet());
        System.out.printf("%-34s %14s %14s   %s%n", "set", "242 objects", "226 objects", "ghi chú");
        for (String s : all) {
            Long a = sets242.get(s), b = sets226.get(s);
            String note = (a != null && b != null) ? "cả hai" : (a != null ? "CHỈ-242" : "CHỈ-226");
            System.out.printf("%-34s %14s %14s   %s%n", s,
                    a == null ? "-" : a.toString(), b == null ? "-" : b.toString(), note);
        }
        System.out.println("################ HẾT ################");
        System.exit(0);
    }

    private static AerospikeClient safe(boolean is242) {
        try {
            return is242 ? DataManagerAerospikeFloatSim.getClient242() : DataManagerAerospikeFloatSim.getClient226();
        } catch (Exception e) {
            System.out.println("❌ client " + (is242 ? "242" : "226") + " lỗi: " + e.getMessage());
            return null;
        }
    }

    private static void scan(String label, AerospikeClient client, Map<String, Long> setSink) {
        System.out.println("\n================ [" + label + "] ================");
        if (client == null) { System.out.println("(client null — bỏ qua)"); return; }

        // ---- A. namespace stats ----
        System.out.println("---- A. NAMESPACE STATS ----");
        try {
            String ns = Info.request(client.getNodes()[0], "namespace/" + NS);
            Map<String, String> kv = parseSemis(ns);
            String[] keys = {"objects", "memory-size", "memory_used_bytes", "memory_free_pct",
                    "device_total_bytes", "device_used_bytes", "device_free_pct", "device_available_pct",
                    "stop-writes", "stop_writes", "replication-factor", "storage-engine",
                    "data_total_bytes", "data_used_bytes", "data_used_pct", "data_avail_pct"};
            for (String k : keys) {
                if (kv.containsKey(k)) {
                    String v = kv.get(k);
                    boolean bytes = k.endsWith("_bytes") || k.equals("memory-size");
                    System.out.println("  " + k + " = " + v + (bytes ? "  (" + fmtSize(parseLongSafe(v)) + ")" : ""));
                }
            }
            // RAM free% nếu có memory-size + used
            Long memSize = parseLongSafe(kv.get("memory-size")), memUsed = parseLongSafe(kv.get("memory_used_bytes"));
            if (memSize != null && memUsed != null && memSize > 0) {
                System.out.printf("  → memory: used %s / %s (%.1f%% used, %.1f%% free)%n",
                        fmtSize(memUsed), fmtSize(memSize), 100.0 * memUsed / memSize, 100.0 * (memSize - memUsed) / memSize);
            }
        } catch (Exception e) {
            System.out.println("  A lỗi: " + e.getMessage());
        }
        // config thêm (replication-factor / storage-engine) qua get-config
        try {
            String cfg = Info.request(client.getNodes()[0], "get-config:context=namespace;id=" + NS);
            Map<String, String> kv = parseSemis(cfg);
            for (String k : new String[]{"replication-factor", "storage-engine", "storage-engine.type"}) {
                if (kv.containsKey(k)) System.out.println("  [cfg] " + k + " = " + kv.get(k));
            }
        } catch (Exception e) {
            System.out.println("  A-cfg lỗi: " + e.getMessage());
        }

        // ---- B. liệt kê MỌI set ----
        System.out.println("---- B. SETS (mọi set, không bỏ sót) ----");
        System.out.printf("  %-34s %12s %14s %14s%n", "set", "objects", "memory", "device/disk");
        try {
            String setsResp = Info.request(client.getNodes()[0], "sets/" + NS);
            for (String rec : setsResp.split(";")) {
                if (!rec.contains("set=")) continue;
                String name = "";
                long objects = 0, mem = 0, dev = 0;
                for (String f : rec.split(":")) {
                    int eq = f.indexOf('=');
                    if (eq < 0) continue;
                    String k = f.substring(0, eq), v = f.substring(eq + 1);
                    switch (k) {
                        case "set": name = v; break;
                        case "objects": objects = parseLongSafe(v) == null ? 0 : parseLongSafe(v); break;
                        case "memory_data_bytes": mem = parseLongSafe(v) == null ? 0 : parseLongSafe(v); break;
                        case "device_data_bytes": case "data_used_bytes": dev = parseLongSafe(v) == null ? 0 : parseLongSafe(v); break;
                        default: break;
                    }
                }
                if (name.isEmpty()) continue;
                setSink.put(name, objects);
                System.out.printf("  %-34s %12d %14s %14s%n", name, objects, fmtSize(mem), fmtSize(dev));
            }
        } catch (Exception e) {
            System.out.println("  B lỗi: " + e.getMessage());
        }

        // ---- C. chi tiết market set ----
        System.out.println("---- C. MARKET SET CHI TIẾT (sample) ----");
        seriesRange(client, "funding_data", "f_data");
        seriesRange(client, "open_interest", "oi_data");
        klineMonthRange(client, "kline_15m_btceth");
        klineMonthRange(client, "kline_4h_btceth");
        priceRealtimeSample(client);
        kline1mProbe(client);
    }

    /** Series Snappy(gson Map<ts,val>): đọc BTC/ETH → count + min/max ts. */
    private static void seriesRange(AerospikeClient client, String set, String bin) {
        for (String sym : new String[]{"BTCUSDT", "ETHUSDT"}) {
            try {
                Record r = client.get(null, new Key(NS, set, sym));
                if (r == null) { System.out.println("  " + set + " " + sym + ": KHÔNG record."); continue; }
                byte[] comp = (byte[]) r.getValue(bin);
                if (comp == null) { System.out.println("  " + set + " " + sym + ": bin " + bin + " null."); continue; }
                Map<String, Float> m = Utils.gson.fromJson(new String(Snappy.uncompress(comp), "UTF-8"), MAP_SF);
                if (m == null || m.isEmpty()) { System.out.println("  " + set + " " + sym + ": map rỗng."); continue; }
                long min = Long.MAX_VALUE, max = Long.MIN_VALUE;
                for (String k : m.keySet()) { long t = Long.parseLong(k); min = Math.min(min, t); max = Math.max(max, t); }
                System.out.printf("  %s %s: #điểm=%d · range %s → %s · bin=%s · comp=%s%n",
                        set, sym, m.size(), TS.format(new java.util.Date(min)), TS.format(new java.util.Date(max)), bin, fmtSize(comp.length));
            } catch (Exception e) {
                System.out.println("  " + set + " " + sym + " lỗi: " + e.getMessage());
            }
        }
    }

    /** kline 15m/4h: key SYMBOL-YYYYMM. Probe các tháng 202101..tháng-hiện-tại → range startMs + #record-tháng. */
    private static void klineMonthRange(AerospikeClient client, String set) {
        for (String sym : new String[]{"BTCUSDT", "ETHUSDT"}) {
            try {
                long min = Long.MAX_VALUE, max = Long.MIN_VALUE;
                int monthsPresent = 0, totalFrames = 0, sampleBytes = 0;
                int curYm = Integer.parseInt(mk("yyyyMM").format(new java.util.Date(System.currentTimeMillis())));
                for (int y = 2021; y <= curYm / 100; y++) {
                    for (int mo = 1; mo <= 12; mo++) {
                        int ym = y * 100 + mo;
                        if (ym > curYm) break;
                        Record r = client.get(null, new Key(NS, set, sym + "-" + String.format("%04d%02d", y, mo)));
                        if (r == null) continue;
                        byte[] comp = (byte[]) r.getValue("data");
                        if (comp == null) continue;
                        sampleBytes = Math.max(sampleBytes, comp.length);
                        TreeMap<Long, float[]> ser = Utils.gson.fromJson(new String(Snappy.uncompress(comp), "UTF-8"), MAP_KLINE);
                        if (ser == null || ser.isEmpty()) continue;
                        monthsPresent++;
                        totalFrames += ser.size();
                        min = Math.min(min, ser.firstKey());
                        max = Math.max(max, ser.lastKey());
                    }
                }
                if (monthsPresent == 0) { System.out.println("  " + set + " " + sym + ": KHÔNG record-tháng."); continue; }
                System.out.printf("  %s %s: #tháng=%d · #nến=%d · range %s → %s · max-comp=%s%n",
                        set, sym, monthsPresent, totalFrames,
                        TS.format(new java.util.Date(min)), TS.format(new java.util.Date(max)), fmtSize(sampleBytes));
            } catch (Exception e) {
                System.out.println("  " + set + " " + sym + " lỗi: " + e.getMessage());
            }
        }
    }

    /** price_realtime: sample BTC — bin + schema. */
    private static void priceRealtimeSample(AerospikeClient client) {
        try {
            Record r = client.get(null, new Key(NS, "price_realtime", "BTCUSDT"));
            if (r == null) { System.out.println("  price_realtime BTCUSDT: KHÔNG record."); return; }
            System.out.println("  price_realtime BTCUSDT: bins=" + r.bins.keySet());
        } catch (Exception e) {
            System.out.println("  price_realtime lỗi: " + e.getMessage());
        }
    }

    /**
     * kline_1m_opt range: probe key "yyyyMMdd-HHmm" tại 00:00. Earliest = năm 2019..nay (Jan-1) rồi tháng;
     * latest = lùi từ hôm nay vài ngày. Cho biết historical@host sâu tới đâu (đọc-only vài get).
     */
    private static void kline1mProbe(AerospikeClient client) {
        try {
            String set = "kline_1m_opt";
            // earliest year
            Integer firstYear = null;
            for (int y = 2019; y <= 2026; y++) {
                if (probe1m(client, set, String.format("%04d0101-0000", y))) { firstYear = y; break; }
            }
            String earliest = "?";
            int sampleBytes = 0;
            if (firstYear != null) {
                // earliest month trong năm đó
                int fm = 1;
                for (int mo = 1; mo <= 12; mo++) {
                    if (probe1m(client, set, String.format("%04d%02d01-0000", firstYear, mo))) { fm = mo; break; }
                }
                earliest = String.format("%04d-%02d (≈ngày 01)", firstYear, fm);
                Record r = client.get(null, new Key(NS, set, String.format("%04d%02d01-0000", firstYear, fm)));
                if (r != null && r.getValue("data") != null) sampleBytes = ((byte[]) r.getValue("data")).length;
            }
            // latest: lùi từ hôm nay 7 ngày
            String latest = "?";
            long now = System.currentTimeMillis();
            for (int d = 0; d <= 7; d++) {
                String k = mk("yyyyMMdd").format(new java.util.Date(now - (long) d * 24 * 3600_000L)) + "-0000";
                if (probe1m(client, set, k)) { latest = k.substring(0, 8) + " (có nến 00:00)"; break; }
            }
            System.out.printf("  kline_1m_opt: earliest≈%s · latest≈%s · sample-record(data)=%s · (mỗi key=1 phút, value=Snappy(MinuteDataFinal proto, mọi symbol))%n",
                    earliest, latest, fmtSize(sampleBytes));
        } catch (Exception e) {
            System.out.println("  kline_1m_opt probe lỗi: " + e.getMessage());
        }
    }

    private static boolean probe1m(AerospikeClient client, String set, String key) {
        try {
            Record r = client.get(null, new Key(NS, set, key));
            return r != null && r.getValue("data") != null;
        } catch (Exception e) {
            return false;
        }
    }

    private static Map<String, String> parseSemis(String resp) {
        Map<String, String> kv = new LinkedHashMap<>();
        if (resp == null) return kv;
        for (String part : resp.split(";")) {
            int eq = part.indexOf('=');
            if (eq > 0) kv.put(part.substring(0, eq).trim(), part.substring(eq + 1).trim());
        }
        return kv;
    }

    private static Long parseLongSafe(String s) {
        if (s == null) return null;
        try { return Long.parseLong(s.trim()); } catch (Exception e) { return null; }
    }

    private static String fmtSize(long size) {
        float kb = size / 1024f, mb = kb / 1024f, gb = mb / 1024f;
        if (gb >= 1) return String.format("%.2f GB", gb);
        if (mb >= 1) return String.format("%.2f MB", mb);
        return String.format("%.2f KB", kb);
    }
}
