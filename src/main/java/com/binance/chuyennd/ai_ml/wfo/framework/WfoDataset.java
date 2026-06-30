package com.binance.chuyennd.ai_ml.wfo.framework;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Map;
import java.util.TreeMap;

/**
 * WFO FRAMEWORK — TẦNG DỮ LIỆU OFFLINE (Uni chốt: dữ liệu lớn + bất biến → FILE, KHÔNG Aerospike trên
 * đường chạy; Aerospike chỉ dùng EXPORT 1 lần + state nhỏ).
 *
 * <p>3 khối dữ liệu BẤT BIẾN cho strategy-WFO: market / ai-pred (market) / funding-pred. Mỗi khối hiện
 * scanAll từ Aerospike 226 (~25-40s/JVM); phân tán nhiều worker → nghẽn 226 (yếu). Giải: EXPORT 1 lần ra
 * file binary + manifest md5; mọi worker LOAD file cục bộ (VPS: file tĩnh; Kaggle: Kaggle Dataset).
 *
 * <p><b>Định dạng file</b> (tuần tự, tự mô tả):
 * <ul>
 *   <li>market.bin : [count:int] rồi count × [ts:long][3 float: down,up,down15m]</li>
 *   <li>pred.bin   : [count:int] rồi count × [ts:long][predReturn15M:float][predRisk4H:float]</li>
 *   <li>funding.bin: [count:int] rồi count × [ts:long][len:int][len × long]</li>
 *   <li>manifest.txt: key=value (md5 từng file, count, range, source set, ngày export, schemaVersion)</li>
 * </ul>
 *
 * <p><b>Chống lệch (leak L3):</b> load() KIỂM md5 từng file theo manifest → fail-fast nếu lệch. Mọi node
 * dùng CÙNG snapshot. Manifest ghi provenance (source set + ngày) — tái lập được.
 */
public class WfoDataset {

    private static final Logger LOG = LoggerFactory.getLogger(WfoDataset.class);
    public static final int SCHEMA_VERSION = 1;

    public static final String F_MARKET = "market.bin";
    public static final String F_PRED = "pred.bin";
    public static final String F_FUNDING = "funding.bin";
    public static final String F_MANIFEST = "manifest.txt";

    // Tên set nguồn trên Aerospike 226 (provenance)
    static final String SET_MARKET = "market_data";
    static final String SET_PRED = "ai_pred_market_full_basket_v2";
    static final String SET_FUNDING = "funding_selector_pred_1m_v2";

    public TreeMap<Long, MarketDataObject> market;
    public TreeMap<Long, AiPredictionData> pred;
    public TreeMap<Long, long[]> funding;

    // ======================= EXPORT (chạy 1 lần trên node có Aerospike) =======================
    /** Scan 3 khối từ Aerospike 226 → ghi file binary + manifest vào outDir. Chỉ chạy khi data nguồn đổi. */
    public static void export(String outDir) throws Exception {
        File dir = new File(outDir);
        if (!dir.exists() && !dir.mkdirs()) throw new IOException("Khong tao duoc outDir: " + outDir);

        LOG.info("EXPORT WFO dataset -> {}", outDir);
        TreeMap<Long, MarketDataObject> mkt = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> prd = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> fnd = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("scan xong: market={} pred={} funding={}", mkt.size(), prd.size(), fnd.size());

        writeMarket(new File(dir, F_MARKET), mkt);
        writePred(new File(dir, F_PRED), prd);
        writeFunding(new File(dir, F_FUNDING), fnd);

        StringBuilder mani = new StringBuilder();
        mani.append("schemaVersion=").append(SCHEMA_VERSION).append("\n");
        mani.append("exportedAt=").append(new java.util.Date()).append("\n");
        mani.append("sourceMarketSet=").append(SET_MARKET).append("\n");
        mani.append("sourcePredSet=").append(SET_PRED).append("\n");
        mani.append("sourceFundingSet=").append(SET_FUNDING).append("\n");
        mani.append("marketCount=").append(mkt.size()).append("\n");
        mani.append("predCount=").append(prd.size()).append("\n");
        mani.append("fundingCount=").append(fnd.size()).append("\n");
        if (!mkt.isEmpty()) mani.append("marketRange=").append(mkt.firstKey()).append("..").append(mkt.lastKey()).append("\n");
        mani.append("md5_market=").append(md5(new File(dir, F_MARKET))).append("\n");
        mani.append("md5_pred=").append(md5(new File(dir, F_PRED))).append("\n");
        mani.append("md5_funding=").append(md5(new File(dir, F_FUNDING))).append("\n");
        try (Writer w = new OutputStreamWriter(new FileOutputStream(new File(dir, F_MANIFEST)), StandardCharsets.UTF_8)) {
            w.write(mani.toString());
        }
        LOG.info("EXPORT xong. manifest:\n{}", mani);
    }

    // ======================= LOAD (mọi worker, đọc file cục bộ) =======================
    /** Load 3 khối từ file trong dataDir. KIỂM md5 theo manifest (fail-fast nếu lệch — chống data drift L3). */
    public static WfoDataset load(String dataDir) throws Exception {
        File dir = new File(dataDir);
        Map<String, String> mani = readManifest(new File(dir, F_MANIFEST));
        int schema = Integer.parseInt(mani.getOrDefault("schemaVersion", "-1"));
        if (schema != SCHEMA_VERSION)
            throw new IOException("schemaVersion lech: file=" + schema + " code=" + SCHEMA_VERSION);

        verifyMd5(new File(dir, F_MARKET), mani.get("md5_market"), "market");
        verifyMd5(new File(dir, F_PRED), mani.get("md5_pred"), "pred");
        verifyMd5(new File(dir, F_FUNDING), mani.get("md5_funding"), "funding");

        WfoDataset ds = new WfoDataset();
        ds.market = readMarket(new File(dir, F_MARKET));
        ds.pred = readPred(new File(dir, F_PRED));
        ds.funding = readFunding(new File(dir, F_FUNDING));
        LOG.info("LOAD offline OK: market={} pred={} funding={} (md5 verified) src[{}]",
                ds.market.size(), ds.pred.size(), ds.funding.size(), mani.get("exportedAt"));
        return ds;
    }

    /** Nguồn dữ liệu: nếu env WFO_DATA_DIR set → load offline; nếu không → fallback scanAll Aerospike. */
    public static WfoDataset loadAuto() throws Exception {
        String dir = System.getenv("WFO_DATA_DIR");
        if (dir != null && !dir.isEmpty()) return load(dir);
        LOG.warn("WFO_DATA_DIR khong set → FALLBACK scanAll Aerospike (chi nen dung khi test don may).");
        WfoDataset ds = new WfoDataset();
        ds.market = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        ds.pred = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        ds.funding = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        return ds;
    }

    // ======================= writers =======================
    private static void writeMarket(File f, TreeMap<Long, MarketDataObject> m) throws IOException {
        try (DataOutputStream o = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(f), 1 << 20))) {
            o.writeInt(m.size());
            for (Map.Entry<Long, MarketDataObject> e : m.entrySet()) {
                o.writeLong(e.getKey());
                MarketDataObject d = e.getValue();
                o.writeFloat(d.rateDownAvg); o.writeFloat(d.rateUpAvg); o.writeFloat(d.rateDown15MAvg);
            }
        }
    }
    private static void writePred(File f, TreeMap<Long, AiPredictionData> m) throws IOException {
        try (DataOutputStream o = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(f), 1 << 20))) {
            o.writeInt(m.size());
            for (Map.Entry<Long, AiPredictionData> e : m.entrySet()) {
                o.writeLong(e.getKey());
                o.writeFloat(e.getValue().predReturn15M); o.writeFloat(e.getValue().predRisk4H);
            }
        }
    }
    private static void writeFunding(File f, TreeMap<Long, long[]> m) throws IOException {
        try (DataOutputStream o = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(f), 1 << 20))) {
            o.writeInt(m.size());
            for (Map.Entry<Long, long[]> e : m.entrySet()) {
                o.writeLong(e.getKey());
                long[] a = e.getValue();
                o.writeInt(a.length);
                for (long v : a) o.writeLong(v);
            }
        }
    }

    // ======================= readers =======================
    private static TreeMap<Long, MarketDataObject> readMarket(File f) throws IOException {
        TreeMap<Long, MarketDataObject> m = new TreeMap<>();
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(new FileInputStream(f), 1 << 20))) {
            int n = in.readInt();
            for (int i = 0; i < n; i++) {
                long ts = in.readLong();
                float down = in.readFloat(), up = in.readFloat(), down15 = in.readFloat();
                m.put(ts, new MarketDataObject(down, up, down15));
            }
        }
        return m;
    }
    private static TreeMap<Long, AiPredictionData> readPred(File f) throws IOException {
        TreeMap<Long, AiPredictionData> m = new TreeMap<>();
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(new FileInputStream(f), 1 << 20))) {
            int n = in.readInt();
            for (int i = 0; i < n; i++) {
                long ts = in.readLong();
                float p15 = in.readFloat(), r4 = in.readFloat();
                m.put(ts, new AiPredictionData(ts, p15, r4));
            }
        }
        return m;
    }
    private static TreeMap<Long, long[]> readFunding(File f) throws IOException {
        TreeMap<Long, long[]> m = new TreeMap<>();
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(new FileInputStream(f), 1 << 20))) {
            int n = in.readInt();
            for (int i = 0; i < n; i++) {
                long ts = in.readLong();
                int len = in.readInt();
                long[] a = new long[len];
                for (int j = 0; j < len; j++) a[j] = in.readLong();
                m.put(ts, a);
            }
        }
        return m;
    }

    // ======================= manifest + md5 =======================
    private static Map<String, String> readManifest(File f) throws IOException {
        if (!f.exists()) throw new IOException("Thieu manifest: " + f.getAbsolutePath());
        Map<String, String> m = new java.util.LinkedHashMap<>();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
            String line;
            while ((line = r.readLine()) != null) {
                int eq = line.indexOf('=');
                if (eq > 0) m.put(line.substring(0, eq).trim(), line.substring(eq + 1).trim());
            }
        }
        return m;
    }
    private static void verifyMd5(File f, String expect, String name) throws Exception {
        if (expect == null) throw new IOException("manifest thieu md5_" + name);
        String got = md5(f);
        if (!got.equalsIgnoreCase(expect))
            throw new IOException("MD5 LECH " + name + ": file=" + got + " manifest=" + expect
                    + " → data drift, DUNG (chong leak L3). Re-export hoac copy lai dataset.");
    }
    private static String md5(File f) throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
        try (InputStream in = new BufferedInputStream(new FileInputStream(f), 1 << 20)) {
            byte[] buf = new byte[1 << 16];
            int r;
            while ((r = in.read(buf)) != -1) md.update(buf, 0, r);
        }
        StringBuilder sb = new StringBuilder();
        for (byte b : md.digest()) sb.append(String.format("%02x", b));
        return sb.toString();
    }
}
