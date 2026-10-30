package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.trading.GatePreFilter;
import org.junit.Assume;
import org.junit.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.GZIPInputStream;

import static org.junit.Assert.*;

/**
 * [V12 R4h] Replay 10-30 (quy uoc v1.1, du lieu agent gate ~/claude_master/gst1030): coin DANG GIU khong qua gate/khong nap r
 * (GatePreFilter, quy uoc sim isSymbolRunning). Bo r cua coin dang giu trong dot sap 1 (03:30–04:00 +07) khoi buffer
 * (gate_ratio_live.bin md5 4e29c20c…) ⇒ q gio 04 = 0,00756445155 (truoc: 0,00950214919); dot 2 (04:00–11:00, q gio 04)
 * = 29 pass, coin moi = CAP, CT, DOS, IDOL, IRYS, NIL, PARTI, Q. Khong co thu muc du lieu (CI) ⇒ bo qua.
 */
public class GateHeldReplay1030R4hTest {

    private static final Logger LOG = LoggerFactory.getLogger(GateHeldReplay1030R4hTest.class);
    static final long H = 3_600_000L;
    static final float PCT = 0.999950829f;
    static final String BIN_MD5 = "4e29c20ce6b4d6bb9aa60e3601eed070";
    static final float Q_EXPECT = 0.00756445155f;

    static final class Row {
        final long ts;
        final String sym;
        final float r;

        Row(long ts, String sym, float r) {
            this.ts = ts;
            this.sym = sym;
            this.r = r;
        }
    }

    static File dir() {
        String d = System.getenv("GST1030_DIR");
        return new File(d != null ? d : System.getProperty("user.home") + "/claude_master/gst1030");
    }

    static long ms7(String s) throws Exception {
        SimpleDateFormat f = new SimpleDateFormat("dd/MM/yyyy HH:mm:ss");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        return f.parse(s).getTime();
    }

    static long hhmm7(String s) throws Exception {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        return f.parse(s).getTime();
    }

    @Test
    public void heldExcludedBeforeGate_q04AndWave2() throws Exception {
        File d = dir();
        File bin = new File(d, "gate_ratio_live_2242.bin");
        Assume.assumeTrue("khong co du lieu gst1030 => bo qua", bin.isFile());
        assertEquals("md5 buffer 10-30 22:42", BIN_MD5, LiveGateRollingRatio.md5Hex(bin));

        // su kien so giay (gio +07, bo phan ms nhu gst_l.py)
        Map<String, List<Long>> opens = new HashMap<>(), closes = new HashMap<>();
        Pattern p = Pattern.compile("^(\\S+ \\S+)\\.\\d+\\s+(open|closed) (\\S+)");
        for (String ln : Files.readAllLines(new File(d, "shadow_events.txt").toPath())) {
            Matcher m = p.matcher(ln);
            if (!m.find()) continue;
            (m.group(2).equals("open") ? opens : closes).computeIfAbsent(m.group(3), k -> new ArrayList<>()).add(ms7(m.group(1)));
        }
        // sel_dump (top-24, bo trung (ts,symbol) giu dong dau theo thu tu file)
        File[] fs = new File(d, "sel").listFiles((x, n) -> n.endsWith(".csv.gz"));
        assertNotNull(fs);
        Arrays.sort(fs);
        Set<String> seen = new HashSet<>();
        List<Row> rows = new ArrayList<>();
        for (File f : fs) {
            try (BufferedReader br = new BufferedReader(new InputStreamReader(new GZIPInputStream(new FileInputStream(f)),
                    StandardCharsets.UTF_8))) {
                String ln = br.readLine();   // header ts,symbol,selectorScore,rank,gateValue,p15
                while ((ln = br.readLine()) != null) {
                    String[] a = ln.split(",");
                    if (a.length < 6) continue;
                    if (!seen.add(a[0] + "|" + a[1])) continue;
                    if (Integer.parseInt(a[3].trim()) > 24) continue;
                    float gv = Float.parseFloat(a[4]), p15 = Float.parseFloat(a[5]);
                    float fac = Math.max(0.26787f, (gv / 0.15f) * 1.2876f);
                    rows.add(new Row(Long.parseLong(a[0]), a[1], p15 / (fac * 1.55f)));
                }
            }
        }
        long b0 = hhmm7("2026-10-30 03:30"), h4 = hhmm7("2026-10-30 04:00"), w1 = hhmm7("2026-10-30 11:00");
        // r cua coin DANG GIU trong dot 1 => KHONG nap (GatePreFilter)
        Map<String, Integer> drop = new HashMap<>();
        int heldRows = 0;
        for (Row r : rows) {
            if (r.ts < b0 || r.ts >= h4) continue;
            boolean held = held(opens, closes, r.sym, r.ts);
            if (GatePreFilter.decide(false, held, false, false) == GatePreFilter.Action.SKIP_AFTER_RANK) {
                heldRows++;
                drop.merge(r.ts + "|" + Float.floatToIntBits(r.r), 1, Integer::sum);
            }
        }
        GateRatioPersist.Records rec = GateRatioPersist.load(bin.getPath(), Long.MIN_VALUE);
        assertEquals(0, rec.droppedChunks);
        long[] ts = rec.ts.clone();
        float[] rr = rec.r.clone();
        Integer[] idx = new Integer[ts.length];
        for (int i = 0; i < idx.length; i++) idx[i] = i;
        Arrays.sort(idx, Comparator.comparingLong(i -> ts[i]));   // on dinh nhu argsort stable
        List<long[]> keepTs = new ArrayList<>();
        int nKeep = 0, matched = 0;
        long[] kt = new long[ts.length];
        float[] kr = new float[ts.length];
        long[] at = new long[ts.length];
        float[] ar = new float[ts.length];
        int nAll = 0;
        for (Integer i : idx) {
            if (ts[i] >= h4) continue;
            at[nAll] = ts[i];
            ar[nAll] = rr[i];
            nAll++;
            String k = ts[i] + "|" + Float.floatToIntBits(rr[i]);
            Integer c = ts[i] >= b0 ? drop.get(k) : null;
            if (c != null && c > 0) {
                drop.put(k, c - 1);
                matched++;
                continue;
            }
            kt[nKeep] = ts[i];
            kr[nKeep] = rr[i];
            nKeep++;
        }
        GateRatioBuffer before = new GateRatioBuffer();
        before.bulkAdd(Arrays.copyOf(at, nAll), Arrays.copyOf(ar, nAll));
        float qOld = before.queryOnly(h4, 0f, PCT, 90, 0.008f);
        GateRatioBuffer buf = new GateRatioBuffer();
        buf.bulkAdd(Arrays.copyOf(kt, nKeep), Arrays.copyOf(kr, nKeep));
        float q = buf.queryOnly(h4, 0f, PCT, 90, 0.008f);
        LOG.info("[R4H-REPLAY] dot1 dong_dang_giu={} khop_ban_ghi_buffer={} | q04 cu={} moi={} (ky vong {})", heldRows, matched,
                qOld, q, Q_EXPECT);
        assertEquals("q gio 04 truoc sua (log live)", Float.floatToIntBits(0.00950214919f), Float.floatToIntBits(qOld));
        assertEquals("q gio 04 sau sua", Q_EXPECT, q, Math.abs(Q_EXPECT) * 1e-9);

        int pass = 0;
        TreeSet<String> newSyms = new TreeSet<>();
        for (Row r : rows) {
            if (r.ts < h4 || r.ts >= w1) continue;
            if (r.r >= q) {
                pass++;
                if (!held(opens, closes, r.sym, r.ts)) newSyms.add(r.sym.replace("USDT", ""));
            }
        }
        LOG.info("[R4H-REPLAY] dot2 pass={} moi={}", pass, newSyms);
        assertEquals(29, pass);
        assertEquals(new TreeSet<>(Arrays.asList("CAP", "CT", "DOS", "IDOL", "IRYS", "NIL", "PARTI", "Q")), newSyms);
    }

    /** gst_l.py held(): quyet dinh ~ ts + 66 s; mo truoc quyet dinh >= 1 s va chua dong toi luc quyet dinh. */
    static boolean held(Map<String, List<Long>> opens, Map<String, List<Long>> closes, String sym, long t) {
        long dec = t + 66_000L;
        for (long to : opens.getOrDefault(sym, Collections.<Long>emptyList())) {
            if (to < dec - 1000L) {
                Long first = null;
                for (long c : closes.getOrDefault(sym, Collections.<Long>emptyList())) {
                    if (c > to && (first == null || c < first)) first = c;
                }
                if (first == null || first > dec) return true;
            }
        }
        return false;
    }
}
