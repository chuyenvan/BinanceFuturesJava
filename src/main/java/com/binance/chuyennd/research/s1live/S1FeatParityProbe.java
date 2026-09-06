package com.binance.chuyennd.research.s1live;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.BatchPolicy;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.tradecore.selector.S1FeatureLive;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * READ-ONLY probe: dung nguon LIVE (Aerospike 242 ns=ticker set=kline_1m_opt) dung len chuoi
 * close 1h, tinh 7 feature GIA cua S1 bang {@link S1FeatureLive}, ghi CSV de doi chung voi
 * {@code featv2/feat_v2_x1.parquet}.
 *
 * <p>Hai QUY UOC gop 1m -> 1h duoc do SONG SONG (H1_HOLDOUT_PREP muc 3 canh bao CLOSES_1H.bin
 * la kline 1h Vision co {@code open_time = t - 1h}):
 * <ul>
 *   <li><b>prev</b>: {@code close(t) = priceClose} cua nen 1m {@code open_time = t - 1m}
 *       (= close cua nen 1h phu [t-1h, t) = quy uoc Vision)</li>
 *   <li><b>open</b>: {@code close(t) = priceClose} cua nen 1m {@code open_time = t}</li>
 * </ul>
 *
 * <p>KHONG GHI GI len 242. Args: {@code <startUtcMs> <endUtcMs> <emitFromUtcMs> <outDir>}.
 */
public final class S1FeatParityProbe {

    private static final Logger LOG = LoggerFactory.getLogger(S1FeatParityProbe.class);
    private static final String NS = System.getenv().getOrDefault("PROBE_NS", "ticker");
    private static final String SET = "kline_1m_opt";
    private static final String HOST = System.getenv().getOrDefault("PROBE_HOST", "103.157.218.242");
    private static final int PORT = Integer.parseInt(System.getenv().getOrDefault("PROBE_PORT", "3222"));
    private static final String SYMMAP = System.getenv().getOrDefault("PROBE_SYMMAP",
            "/home/ubuntu/selector_pred_out/symbol_map.csv");
    private static final int CHUNK = 60;
    private static final long H = S1FeatureLive.HOUR_MS;
    private static final long MIN = 60_000L;

    public static void main(String[] args) throws Exception {
        long start = Long.parseLong(args[0]);
        long end = Long.parseLong(args[1]);
        long emitFrom = Long.parseLong(args[2]);
        String outDir = args[3];
        Files.createDirectories(Paths.get(outDir));

        Map<String, Integer> sym2id = loadSymbolMap();
        LOG.info("symbol_map: {} symbol", sym2id.size());

        int nH = (int) ((end - start) / H);
        LOG.info("luoi gio: {} moc, {} -> {}", nH, utc(start), utc(end));

        AerospikeClient cli = new AerospikeClient(HOST, PORT);
        BatchPolicy bp = new BatchPolicy();
        bp.totalTimeout = 300_000;
        bp.socketTimeout = 120_000;
        bp.maxRetries = 4;

        for (String variant : new String[]{"prev", "open"}) {
            long off = "prev".equals(variant) ? -MIN : 0L;
            Map<String, double[]> closes = new HashMap<>();
            int hit = 0;
            for (int c0 = 0; c0 < nH; c0 += CHUNK) {
                int c1 = Math.min(c0 + CHUNK, nH);
                Key[] keys = new Key[c1 - c0];
                for (int k = c0; k < c1; k++) keys[k - c0] = new Key(NS, SET, keyOf(start + k * H + off));
                Record[] recs = cli.get(bp, keys);
                if (recs == null) continue;
                for (int k = c0; k < c1; k++) {
                    Record rec = recs[k - c0];
                    if (rec == null) continue;
                    byte[] raw = (byte[]) rec.getValue("data");
                    if (raw == null) continue;
                    Map<String, KlineObjectOptimized> m = MinuteDataFinal.parseFrom(Snappy.uncompress(raw)).getTickersMap();
                    if (m.isEmpty()) continue;
                    hit++;
                    for (Map.Entry<String, KlineObjectOptimized> e : m.entrySet()) {
                        String sym = e.getKey().endsWith("USDT") ? e.getKey() : e.getKey() + "USDT";
                        if (!sym2id.containsKey(sym)) continue;
                        double[] arr = closes.get(sym);
                        if (arr == null) {
                            arr = new double[nH];
                            Arrays.fill(arr, Double.NaN);
                            closes.put(sym, arr);
                        }
                        float pc = e.getValue().getPriceClose();
                        if (pc > 0f) arr[k] = pc;
                    }
                }
            }
            LOG.info("[{}] doc duoc {}/{} moc phut, {} symbol", variant, hit, nH, closes.size());
            dump(outDir + "/live_feat_" + variant + ".csv", closes, sym2id, start, nH, emitFrom);
        }
        cli.close();
        LOG.info("DONE");
    }

    private static void dump(String path, Map<String, double[]> closes, Map<String, Integer> sym2id,
                             long start, int nH, long emitFrom) throws Exception {
        int i0 = (int) ((emitFrom - start) / H);
        long rows = 0;
        try (BufferedWriter w = new BufferedWriter(new FileWriter(path))) {
            w.write("ts,sym,vol_7d,dd_7d,rk_dd_7d,hrs_since_high_7d,ret_3d,rk_ret_3d,ret_14d\n");
            for (int i = Math.max(0, i0); i < nH; i++) {
                Map<String, double[]> f = S1FeatureLive.computeTick(closes, i, null, null);
                long ts = start + i * H;
                for (Map.Entry<String, double[]> e : f.entrySet()) {
                    double[] v = e.getValue();
                    boolean any = false;
                    for (int q = 0; q < 7; q++) if (!Double.isNaN(v[q])) any = true;
                    if (!any) continue;
                    w.write(ts + "," + sym2id.get(e.getKey())
                            + "," + s(v[S1FeatureLive.IDX_VOL_7D])
                            + "," + s(v[S1FeatureLive.IDX_DD_7D])
                            + "," + s(v[S1FeatureLive.IDX_RK_DD_7D])
                            + "," + s(v[S1FeatureLive.IDX_HRS_SINCE_HIGH_7D])
                            + "," + s(v[S1FeatureLive.IDX_RET_3D])
                            + "," + s(v[S1FeatureLive.IDX_RK_RET_3D])
                            + "," + s(v[S1FeatureLive.IDX_RET_14D]) + "\n");
                    rows++;
                }
            }
        }
        LOG.info("ghi {} rows -> {}", rows, path);
    }

    private static String s(double d) {
        return Double.isNaN(d) ? "" : Double.toString(d);
    }

    private static Map<String, Integer> loadSymbolMap() throws Exception {
        Map<String, Integer> m = new HashMap<>();
        List<String> lines = Files.readAllLines(Paths.get(SYMMAP), StandardCharsets.UTF_8);
        for (String ln : lines.subList(1, lines.size())) {
            String[] p = ln.trim().split(",");
            if (p.length < 2) continue;
            m.put(p[1], Integer.parseInt(p[0]));
        }
        return m;
    }

    private static String keyOf(long ms) {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd-HHmm");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        return f.format(new Date(ms));
    }

    private static String utc(long ms) {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        f.setTimeZone(TimeZone.getTimeZone("UTC"));
        return f.format(new Date(ms));
    }
}
