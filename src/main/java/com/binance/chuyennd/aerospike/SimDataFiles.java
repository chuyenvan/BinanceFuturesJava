package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

/**
 * [AS-FILE 2026-11-11] Bo phu thuoc Aerospike Oracle cho SIM (owner dong cong 3222): symbol mapper (global_id_map) va
 * funding fee (set funding_data) nap tu FILE dump khoa phien ban. Bat bang env hoac override {@code SYMBOL_MAPPER_FILE}
 * / {@code FUNDING_FEE_FILE}; vang => hanh vi Aerospike cu nguyen ven. Che do file: moi lan mo client Aerospike (doc/ghi)
 * bi chan + dem {@link #AS_CALLS_IN_FILE_MODE} + log "AS_IN_FILE_MODE" (kernel fail neu dem > 0).
 *
 * <p>Dinh dang (gzip, UTF-8, sort tang): mapper "symbol\tid"; funding "symbol\tts\tfloatBitsHex" (Float.floatToRawIntBits).
 */
public final class SimDataFiles {
    private static final Logger LOG = LoggerFactory.getLogger(SimDataFiles.class);
    public static final AtomicLong AS_CALLS_IN_FILE_MODE = new AtomicLong();
    private static volatile Map<String, TreeMap<Long, Float>> fundingCache = null;

    private SimDataFiles() {
    }

    private static String opt(String k) {
        String v = System.getenv(k);
        if (v == null || v.trim().isEmpty()) {
            try {
                v = Cfg.get(k);
            } catch (Throwable t) {
                v = null;
            }
        }
        return v == null || v.trim().isEmpty() ? null : v.trim();
    }

    public static String mapperFile() {
        return opt("SYMBOL_MAPPER_FILE");
    }

    public static String fundingFile() {
        return opt("FUNDING_FEE_FILE");
    }

    public static boolean fileMode() {
        return mapperFile() != null || fundingFile() != null;
    }

    /** Goi tai MOI cho mo client Aerospike: che do file => chan (fail-fast) + dem. */
    public static void guardAerospike(String what) {
        if (fileMode()) {
            long n = AS_CALLS_IN_FILE_MODE.incrementAndGet();
            LOG.error("AS_IN_FILE_MODE: {} goi Aerospike trong che do FILE (lan {}) -> CHAN", what, n);
            throw new IllegalStateException("AS_IN_FILE_MODE: " + what);
        }
    }

    public static String sha256(String path) throws IOException {
        try (InputStream in = new FileInputStream(path)) {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] b = new byte[1 << 20];
            int r;
            while ((r = in.read(b)) > 0) md.update(b, 0, r);
            StringBuilder sb = new StringBuilder();
            for (byte x : md.digest()) sb.append(String.format("%02x", x));
            return sb.toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IOException(e);
        }
    }

    private static BufferedReader reader(String path) throws IOException {
        return new BufferedReader(new InputStreamReader(new GZIPInputStream(new FileInputStream(path), 1 << 16), StandardCharsets.UTF_8));
    }

    private static Writer writer(String path) throws IOException {
        return new BufferedWriter(new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(path), 1 << 16), StandardCharsets.UTF_8));
    }

    public static Map<String, Short> loadMapper(String path) {
        Map<String, Short> m = new ConcurrentHashMap<>();
        try (BufferedReader br = reader(path)) {
            String ln;
            while ((ln = br.readLine()) != null) {
                if (ln.isEmpty()) continue;
                int t = ln.indexOf('\t');
                m.put(ln.substring(0, t), Short.parseShort(ln.substring(t + 1)));
            }
            LOG.info("✅ Loaded Symbol Mapper: {} symbols from FILE {} sha256={}", m.size(), path, sha256(path));
        } catch (IOException e) {
            throw new IllegalStateException("[AS-FILE] khong doc duoc mapper file " + path + ": " + e.getMessage(), e);
        }
        return m;
    }

    public static synchronized Map<String, TreeMap<Long, Float>> loadFunding(String path) {
        if (fundingCache != null) return fundingCache;
        Map<String, TreeMap<Long, Float>> m = new HashMap<>();
        long n = 0;
        try (BufferedReader br = reader(path)) {
            String ln;
            while ((ln = br.readLine()) != null) {
                if (ln.isEmpty()) continue;
                int a = ln.indexOf('\t'), b = ln.indexOf('\t', a + 1);
                m.computeIfAbsent(ln.substring(0, a), k -> new TreeMap<>())
                        .put(Long.parseLong(ln.substring(a + 1, b)), Float.intBitsToFloat((int) Long.parseLong(ln.substring(b + 1), 16)));
                n++;
            }
            LOG.info("✅ Loaded funding fee: {} symbols {} rows from FILE {} sha256={}", m.size(), n, path, sha256(path));
        } catch (IOException e) {
            throw new IllegalStateException("[AS-FILE] khong doc duoc funding file " + path + ": " + e.getMessage(), e);
        }
        fundingCache = m;
        return m;
    }

    /** Ban sao (giong getAllFundingMap tra map moi) — tranh caller sua cache. */
    public static Map<String, TreeMap<Long, Float>> fundingAllCopy(String path) {
        Map<String, TreeMap<Long, Float>> out = new HashMap<>();
        loadFunding(path).forEach((k, v) -> out.put(k, new TreeMap<>(v)));
        return out;
    }

    /** Giong getFundingMap(symbol) cua Aerospike: khong co => TreeMap rong. */
    public static TreeMap<Long, Float> fundingOne(String path, String symbol) {
        TreeMap<Long, Float> v = loadFunding(path).get(symbol);
        return v == null ? new TreeMap<>() : new TreeMap<>(v);
    }

    public static void writeMapper(Map<String, Short> m, String path) throws IOException {
        try (Writer w = writer(path)) {
            for (String s : new TreeSet<>(m.keySet())) w.write(s + "\t" + m.get(s) + "\n");
        }
    }

    public static void writeFunding(Map<String, TreeMap<Long, Float>> m, String path) throws IOException {
        try (Writer w = writer(path)) {
            for (String s : new TreeSet<>(m.keySet())) {
                for (Map.Entry<Long, Float> e : m.get(s).entrySet()) {
                    w.write(s + "\t" + e.getKey() + "\t" + Integer.toHexString(Float.floatToRawIntBits(e.getValue())) + "\n");
                }
            }
        }
    }

    static void resetCacheForTest() {
        fundingCache = null;
    }

    /**
     * Dump CHI DOC tu Aerospike Oracle (getReadClient, AEROSPIKE_READ_CLUSTER=226): {@code dump <mapper.tsv.gz> <funding.tsv.gz>}.
     * {@code verify <mapper> <funding>}: doc lai Aerospike + file, so TOAN BO (id tung symbol, bit float tung ban ghi).
     */
    public static void main(String[] a) throws Exception {
        if (fileMode()) throw new IllegalStateException("tool dump/verify phai chay KHONG co SYMBOL_MAPPER_FILE/FUNDING_FEE_FILE");
        Map<String, Short> mp = DataManagerAerospikeFloatSim.loadSymbolMapperAerospike();
        Map<String, TreeMap<Long, Float>> fd = DataManagerAerospikeFloatSim.getAllFundingMapAerospike();
        if ("dump".equals(a[0])) {
            writeMapper(mp, a[1]);
            writeFunding(fd, a[2]);
            long rows = fd.values().stream().mapToLong(TreeMap::size).sum();
            System.out.println("DUMP mapper=" + mp.size() + " sha256=" + sha256(a[1]) + " funding_symbols=" + fd.size()
                    + " rows=" + rows + " sha256=" + sha256(a[2]));
        } else if ("verify".equals(a[0])) {
            Map<String, Short> fm = loadMapper(a[1]);
            Map<String, TreeMap<Long, Float>> ff = loadFunding(a[2]);
            boolean okM = fm.equals(new HashMap<>(mp));
            boolean okF = ff.size() == fd.size();
            long bad = 0;
            for (Map.Entry<String, TreeMap<Long, Float>> e : fd.entrySet()) {
                TreeMap<Long, Float> x = ff.get(e.getKey());
                if (x == null || x.size() != e.getValue().size()) { bad++; continue; }
                for (Map.Entry<Long, Float> r : e.getValue().entrySet()) {
                    Float y = x.get(r.getKey());
                    if (y == null || Float.floatToRawIntBits(y) != Float.floatToRawIntBits(r.getValue())) { bad++; break; }
                }
            }
            System.out.println("VERIFY mapper_equal=" + okM + " (" + mp.size() + ") funding_size_equal=" + okF
                    + " funding_symbols_mismatch=" + bad);
            if (!okM || !okF || bad > 0) System.exit(3);
        }
        System.exit(0);
    }
}
