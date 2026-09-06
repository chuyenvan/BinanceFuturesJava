package com.binance.chuyennd.research.l4;

import com.binance.chuyennd.tradecore.selector.LiveBuildMap;
import com.binance.chuyennd.tradecore.selector.Net015ValueLive;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.DataOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.util.*;

/**
 * HARNESS REPLAY (L4) — chay DUNG cac lop cua duong live ({@link Net015ValueLive},
 * {@link LiveBuildMap}, ONNX S1 cua {@code S1RankerLive}) tren 3 ngay DEV, roi xuat
 * {@code (ts, symId, s1_rank, symbolPred_live)} de doi chung voi bins.
 *
 * <p>Input do {@code research/pipeline/l4/build_replay_input.py} sinh ra trong {@code /home/ubuntu/l4}:
 * {@code rows.bin} (ts,symId,hasScore,pwin_bins,pmap_bins,s1score — THU TU DONG CUA BINS),
 * {@code x45.f32}, {@code x9.f32} (big-endian).
 *
 * <p>KHONG cham 242, khong Aerospike, khong Binance. Chi doc file + chay ONNX.
 *
 * <p>Ba arm xuat ra (xem {@code docs/L4_LIVE_BUILDMAP.md}):
 * <ul>
 *   <li>{@code MAPONLY} — pwin = gia tri BINS, score = pred_s1a2x1 => co lap RIENG ban port
 *       {@code build_map} (phai trung bins gan nhu tuyet doi);</li>
 *   <li>{@code E2E} — pwin = net015 ONNX chay trong JAVA, score = S1 ONNX chay trong JAVA
 *       => cong end-to-end.</li>
 * </ul>
 */
public final class L4ReplayHarness {

    private static final Logger LOG = LoggerFactory.getLogger(L4ReplayHarness.class);
    private static final int NF45 = 45, NF9 = 9;

    public static void main(String[] args) throws Exception {
        String dir = args.length > 0 ? args[0] : "/home/ubuntu/l4";
        byte[] rb = Files.readAllBytes(new File(dir, "rows.bin").toPath());
        int rec = 8 + 4 + 4 + 4 + 4 + 4;                       // 28 B
        int n = rb.length / rec;
        LOG.info("[L4] doc {} dong tu {}", n, dir);
        long[] ts = new long[n];
        int[] symId = new int[n];
        int[] hasScore = new int[n];
        float[] pwinBins = new float[n], pmapBins = new float[n], s1 = new float[n];
        ByteBuffer bb = ByteBuffer.wrap(rb);                   // big-endian
        for (int i = 0; i < n; i++) {
            ts[i] = bb.getLong();
            symId[i] = bb.getInt();
            hasScore[i] = bb.getInt();
            pwinBins[i] = bb.getFloat();
            pmapBins[i] = bb.getFloat();
            s1[i] = bb.getFloat();
        }
        float[][] x45 = readMat(new File(dir, "x45.f32"), n, NF45);
        float[][] x9 = readMat(new File(dir, "x9.f32"), n, NF9);

        // ---- net015 trong JAVA (dung lop cua duong live) ----
        float[] pwinJava = batched(x45, 20000);
        // ---- S1 ONNX trong JAVA ----
        float[] s1Java = S1OnnxProbe.scoreAll(x9);

        writeArm(dir, "MAPONLY", ts, symId, hasScore, pwinBins, s1, pmapBins);
        if (pwinJava != null && s1Java != null) {
            writeArm(dir, "E2E", ts, symId, hasScore, pwinJava, s1Java, pmapBins);
            dumpVec(new File(dir, "pwin_java.f32"), pwinJava);
            dumpVec(new File(dir, "s1_java.f32"), s1Java);
        } else {
            LOG.error("[L4] thieu pwinJava/s1Java -> chi xuat MAPONLY");
        }
        LOG.info("[L4] XONG");
    }

    private static float[] batched(float[][] x, int bs) {
        Net015ValueLive m = Net015ValueLive.getInstance();
        if (!m.isReady()) return null;
        float[] out = new float[x.length];
        for (int i = 0; i < x.length; i += bs) {
            int hi = Math.min(x.length, i + bs);
            float[][] sub = Arrays.copyOfRange(x, i, hi);
            float[] p = m.pwin(sub);
            if (p == null) return null;
            System.arraycopy(p, 0, out, i, p.length);
            LOG.info("[L4] net015 {}/{}", hi, x.length);
        }
        return out;
    }

    /**
     * Chay {@link LiveBuildMap} theo TICK, dung quy uoc build_map.py: chi remap cac dong CO
     * score; dong khong co score giu nguyen gia tri bins.
     */
    private static void writeArm(String dir, String tag, long[] ts, int[] symId, int[] hasScore,
                                 float[] pwin, float[] s1, float[] pmapBins) throws Exception {
        int n = ts.length;
        // gom theo tick, GIU THU TU DONG (= thu tu file bins)
        LinkedHashMap<Long, List<Integer>> byTs = new LinkedHashMap<>();
        for (int i = 0; i < n; i++) byTs.computeIfAbsent(ts[i], k -> new ArrayList<>()).add(i);
        float[] outPred = new float[n];
        int[] outRank = new int[n];
        Arrays.fill(outRank, -1);
        int nTickOk = 0, nRowMapped = 0;
        StringBuilder log8 = new StringBuilder();
        for (Map.Entry<Long, List<Integer>> e : byTs.entrySet()) {
            List<Integer> rows = e.getValue();
            List<String> order = new ArrayList<>();
            Map<String, Float> sc = new HashMap<>(), pw = new HashMap<>();
            Map<String, Integer> back = new HashMap<>();
            for (int i : rows) {
                if (hasScore[i] == 0 || Float.isNaN(s1[i]) || Float.isNaN(pwin[i])) {
                    outPred[i] = 1.0f - pwin[i];             // giu nguyen (DAO DAU nhu WfoDataset)
                    continue;
                }
                String k = String.valueOf(symId[i]);
                order.add(k);
                sc.put(k, s1[i]);
                pw.put(k, pwin[i]);
                back.put(k, i);
            }
            if (order.isEmpty()) continue;
            LiveBuildMap.Assigned a = LiveBuildMap.assign(order, sc, pw);
            if (a == null) continue;
            nTickOk++;
            for (Map.Entry<String, Float> q : a.symbolPred.entrySet()) {
                int i = back.get(q.getKey());
                outPred[i] = q.getValue();
                outRank[i] = a.rank.get(q.getKey());
                nRowMapped++;
            }
            if (nTickOk <= 2) {
                double[] sorted = new double[a.size()];
                int j = 0;
                for (float v : a.symbolPred.values()) sorted[j++] = v;
                Arrays.sort(sorted);
                log8.append(String.format(Locale.US,
                        "[MAP] tick=%d n_coins=%d p10=%.4f p50=%.4f p90=%.4f%n", e.getKey(), a.size(),
                        LiveBuildMap.pct(sorted, 10), LiveBuildMap.pct(sorted, 50),
                        LiveBuildMap.pct(sorted, 90)));
            }
        }
        LOG.info("[L4][{}] tick map duoc {} | dong map {} / {}", tag, nTickOk, nRowMapped, n);
        LOG.info("\n{}", log8);
        try (DataOutputStream o = new DataOutputStream(new java.io.BufferedOutputStream(
                new FileOutputStream(new File(dir, "out_" + tag + ".bin"))))) {
            for (int i = 0; i < n; i++) {
                o.writeLong(ts[i]);
                o.writeInt(symId[i]);
                o.writeInt(outRank[i]);
                o.writeFloat(outPred[i]);
                o.writeFloat(pmapBins[i]);
            }
        }
    }

    private static float[][] readMat(File f, int n, int nc) throws Exception {
        byte[] b = Files.readAllBytes(f.toPath());
        if (b.length != (long) n * nc * 4) throw new IllegalStateException(
                f + ": " + b.length + " != " + ((long) n * nc * 4));
        ByteBuffer bb = ByteBuffer.wrap(b);
        float[][] x = new float[n][nc];
        for (int i = 0; i < n; i++) for (int j = 0; j < nc; j++) x[i][j] = bb.getFloat();
        return x;
    }

    private static void dumpVec(File f, float[] v) throws Exception {
        try (DataOutputStream o = new DataOutputStream(new java.io.BufferedOutputStream(
                new FileOutputStream(f)))) {
            for (float x : v) o.writeFloat(x);
        }
    }
}
