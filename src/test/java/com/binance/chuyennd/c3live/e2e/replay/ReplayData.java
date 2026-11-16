package com.binance.chuyennd.c3live.e2e.replay;

import com.binance.chuyennd.ai_ml.onnx.entry.E2eGateSupport;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.ExchangeInfoParser;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.GZIPInputStream;

/** [E2E_REPLAY §2] Du lieu vao co dinh (fixture do tools/e2e/prep_fixture.py dung). Chi doc. */
final class ReplayData {

    static final long MIN = 60_000L;
    /** [V12] cua so lay tu manifest.json cua fixture (10-30 dev: 1793232000000..1793491200000). */
    static long START = 1_793_232_000_000L;   // 2026-10-29 07:00 +07 (mac dinh fixture dev)
    static long END = 1_793_491_200_000L;     // 2026-11-01 07:00 +07

    static final class SelRow {
        final long ts;
        final String symbol;
        final float key;
        final int rank;
        final float gv;
        final float p15;

        SelRow(long ts, String symbol, float key, int rank, float gv, float p15) {
            this.ts = ts;
            this.symbol = symbol;
            this.key = key;
            this.rank = rank;
            this.gv = gv;
            this.p15 = p15;
        }
    }

    static final class Bar {
        final String[] s;   // o h l c (chuoi goc Vision)
        final float o, h, l, c;

        Bar(String o, String h, String l, String c) {
            this.s = new String[]{o, h, l, c};
            this.o = Float.parseFloat(o);
            this.h = Float.parseFloat(h);
            this.l = Float.parseFloat(l);
            this.c = Float.parseFloat(c);
        }

        BigDecimal bd(int i) {
            return new BigDecimal(s[i]);
        }
    }

    static final class BigDownLeg {
        final long ts;
        final String symbol;

        BigDownLeg(long ts, String symbol) {
            this.ts = ts;
            this.symbol = symbol;
        }
    }

    final File dir;
    final Map<Long, List<SelRow>> sel = new TreeMap<>();
    final List<BigDownLeg> bigDown = new ArrayList<>();
    final Map<String, Map<Long, Bar>> bars = new HashMap<>();
    final ExchangeInfo exInfo;
    final long[] bufTs;
    final float[] bufR;
    final Map<String, List<Long>> shadowOpens = new HashMap<>();
    final Map<String, List<Long>> shadowCloses = new HashMap<>();
    // [ERRATA1 N6] nen 1m MOI symbol (mkt.csv.gz, prep_fixture) cho dieu kien thi truong DCA - harness TU TINH (MarketReplay)
    String[] mSym = new String[0];
    final Map<String, Integer> mIdx = new HashMap<>();
    long mT0;
    int mN;
    float[][] mO, mH, mL, mC, mQ;
    // [ERRATA1 E1/N1 S-TS] luot tong hop: sau END fixture gia dung yen = close cuoi (time-stop 168 h)
    boolean flatExt;
    final Map<String, Bar> lastBar = new HashMap<>();

    ReplayData(File dir) throws Exception {
        this.dir = dir;
        com.google.gson.JsonObject man = com.google.gson.JsonParser.parseString(new String(Files.readAllBytes(
                new File(dir, "manifest.json").toPath()), StandardCharsets.UTF_8)).getAsJsonObject();
        START = man.get("START").getAsLong();
        END = man.get("END").getAsLong();
        for (String[] a : csv(new File(dir, "sel.csv.gz"))) {
            long ts = Long.parseLong(a[0]);
            sel.computeIfAbsent(ts, k -> new ArrayList<>()).add(new SelRow(ts, a[1], Float.parseFloat(a[2]),
                    Integer.parseInt(a[3].trim()), Float.parseFloat(a[4]), Float.parseFloat(a[5])));
        }
        for (String[] a : csv(new File(dir, "bigdown.csv"))) bigDown.add(new BigDownLeg(Long.parseLong(a[0]), a[1]));
        for (String[] a : csv(new File(dir, "klines.csv.gz"))) {
            bars.computeIfAbsent(a[0], k -> new HashMap<>()).put(Long.parseLong(a[1]), new Bar(a[2], a[3], a[4], a[5]));
        }
        exInfo = ExchangeInfoParser.parse(new String(Files.readAllBytes(new File(dir, "exinfo.json").toPath()),
                StandardCharsets.UTF_8));
        Object[] raw = E2eGateSupport.loadRaw(new File(dir, "gate_ratio_live.bin").getPath());
        bufTs = (long[]) raw[0];
        bufR = (float[]) raw[1];
        for (Map.Entry<String, Map<Long, Bar>> e : bars.entrySet()) {
            long best = Long.MIN_VALUE;
            for (long t : e.getValue().keySet()) if (t < END && t > best) best = t;
            if (best != Long.MIN_VALUE) {
                String c = e.getValue().get(best).s[3];
                lastBar.put(e.getKey(), new Bar(c, c, c, c));
            }
        }
        File mk = new File(dir, "mkt.csv.gz");
        if (mk.isFile()) loadMkt(mk, man.getAsJsonObject("mkt").get("from").getAsLong());
        Pattern p = Pattern.compile("^(\\S+ \\S+)\\.\\d+\\s+(open|closed) (\\S+)");
        SimpleDateFormat f = new SimpleDateFormat("dd/MM/yyyy HH:mm:ss");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        File sev = new File(dir, "shadow_events.txt");
        for (String ln : sev.isFile() ? Files.readAllLines(sev.toPath()) : Collections.<String>emptyList()) {
            Matcher m = p.matcher(ln);
            if (!m.find()) continue;
            (m.group(2).equals("open") ? shadowOpens : shadowCloses).computeIfAbsent(m.group(3), k -> new ArrayList<>())
                    .add(f.parse(m.group(1)).getTime());
        }
    }

    Bar bar(String sym, long t) {
        Map<Long, Bar> m = bars.get(sym);
        Bar x = m == null ? null : m.get(t);
        if (x == null && flatExt && t >= END) return lastBar.get(sym);
        return x;
    }

    void loadMkt(File f, long from) throws Exception {
        mT0 = from;
        mN = (int) ((END - mT0) / MIN);
        Map<String, float[][]> m = new TreeMap<>();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(new GZIPInputStream(new FileInputStream(f)),
                StandardCharsets.UTF_8), 1 << 20)) {
            String ln = br.readLine();
            while ((ln = br.readLine()) != null) {
                if (ln.isEmpty()) continue;
                String[] a = ln.split(",", -1);
                int j = (int) ((Long.parseLong(a[1]) - mT0) / MIN);
                if (j < 0 || j >= mN) continue;
                float[][] x = m.get(a[0]);
                if (x == null) {
                    x = new float[5][mN];
                    for (float[] r : x) java.util.Arrays.fill(r, Float.NaN);
                    m.put(a[0], x);
                }
                for (int k = 0; k < 5; k++) x[k][j] = Float.parseFloat(a[2 + k]);
            }
        }
        mSym = m.keySet().toArray(new String[0]);
        int n = mSym.length;
        mO = new float[n][];
        mH = new float[n][];
        mL = new float[n][];
        mC = new float[n][];
        mQ = new float[n][];
        for (int i = 0; i < n; i++) {
            float[][] x = m.get(mSym[i]);
            mO[i] = x[0];
            mH[i] = x[1];
            mL[i] = x[2];
            mC[i] = x[3];
            mQ[i] = x[4];
            mIdx.put(mSym[i], i);
        }
    }

    /** {o,h,l,c,qv} (ban sao) cua symbol thu i o phut t; null = khong co nen. */
    float[] mkt(int i, long t) {
        if (t < mT0) return null;
        long j = (t - mT0) / MIN;
        if (j >= mN || Float.isNaN(mC[i][(int) j])) return null;
        int k = (int) j;
        return new float[]{mO[i][k], mH[i][k], mL[i][k], mC[i][k], mQ[i][k]};
    }

    List<SelRow> selAt(long ts) {
        List<SelRow> l = sel.get(ts);
        return l == null ? Collections.<SelRow>emptyList() : l;
    }

    /** Ban ghi buffer live co ts trong [from, to). */
    List<long[]> bufferBetween(long from, long to) {
        List<long[]> out = new ArrayList<>();
        for (int i = 0; i < bufTs.length; i++) {
            if (bufTs[i] >= from && bufTs[i] < to) out.add(new long[]{bufTs[i], Float.floatToRawIntBits(bufR[i])});
        }
        return out;
    }

    /** gst_l.py held(): quyet dinh ~ ts + 66 s; mo truoc quyet dinh >= 1 s va chua dong toi luc quyet dinh (nhu R4h). */
    boolean shadowHeld(String sym, long t) {
        long dec = t + 66_000L;
        for (long to : shadowOpens.getOrDefault(sym, Collections.<Long>emptyList())) {
            if (to < dec - 1000L) {
                Long first = null;
                for (long c : shadowCloses.getOrDefault(sym, Collections.<Long>emptyList())) {
                    if (c > to && (first == null || c < first)) first = c;
                }
                if (first == null || first > dec) return true;
            }
        }
        return false;
    }

    static List<String[]> csv(File f) throws Exception {
        List<String[]> out = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(f.getName().endsWith(".gz")
                ? new GZIPInputStream(new FileInputStream(f)) : new FileInputStream(f), StandardCharsets.UTF_8))) {
            String ln = br.readLine();
            while ((ln = br.readLine()) != null) {
                if (ln.isEmpty()) continue;
                out.add(ln.split(",", -1));
            }
        }
        return out;
    }

    static Map<String, Object> info(ReplayData d) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("sel_minutes", d.sel.size());
        m.put("bigdown", d.bigDown.size());
        m.put("symbols_klines", d.bars.size());
        m.put("buffer_records", d.bufTs.length);
        m.put("mkt_symbols", d.mSym.length);
        m.put("mkt_from", d.mT0);
        m.put("flat_ext", d.flatExt);
        return m;
    }
}
