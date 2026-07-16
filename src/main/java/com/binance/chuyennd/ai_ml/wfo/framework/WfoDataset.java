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

    // Ten set nguon tren Aerospike 226 (provenance) - doc tu env de tro dataset vao set leak-free (v3wf) khong hardcode
    static final String SET_MARKET = envOr("WFO_SET_MARKET", "market_data");
    static final String SET_PRED = envOr("WFO_SET_PRED", "ai_pred_market_full_basket_v2");
    static final String SET_FUNDING = envOr("WFO_SET_FUNDING", "funding_selector_pred_1m_v2");

    public TreeMap<Long, MarketDataObject> market;
    public TreeMap<Long, AiPredictionData> pred;
    public TreeMap<Long, long[]> funding;

    /** Provenance stamping: doc env, default an toan neu chua set. Xem docs/PIPELINE_PROVENANCE.md muc 6. */
    private static String envOr(String name, String def) {
        String v = System.getenv(name);
        return (v != null && !v.isEmpty()) ? v : def;
    }

    // ======================= EXPORT (chạy 1 lần trên node có Aerospike) =======================
    /** Scan 3 khối từ Aerospike 226 → ghi file binary + manifest vào outDir. Chỉ chạy khi data nguồn đổi. */
    public static void export(String outDir) throws Exception {
        File dir = new File(outDir);
        if (!dir.exists() && !dir.mkdirs()) throw new IOException("Khong tao duoc outDir: " + outDir);

        LOG.info("EXPORT WFO dataset -> {}", outDir);
        TreeMap<Long, MarketDataObject> mkt = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> prd = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospikeSet(SET_PRED); // FIX 05/07: manifest tung noi doi (stamp env nhung scan hardcode) - MD5 v3==v2 bat duoc
        // FUNDING (selector pred): Uni chot 2026-07-08 -- BO Aerospike, doc THANG tu file Kaggle predict_wf_*.bin
        // (26B >q h 4f: ts, symId, p4h/p12h/p24h/p72h). Chon 1 horizon qua WFO_SEL_HORIZON_IDX (0=4h,1=12h,2=24h,3=72h;
        // mac dinh 1). Encode long[] = (symId<<32)|floatBits(1-P(win)) -- DAO DAU khop decodeSelectorMapToPrimitiveArray
        // (engine chon score THAP = P(win) CAO). WFO_FUNDING_PRED_DIR rong -> fallback Aerospike (luong cu).
        String fundingPredDir = envOr("WFO_FUNDING_PRED_DIR", "");
        TreeMap<Long, long[]> fnd;
        long fndRaw15mCount = -1;   // so moc 15m truoc forward-fill (trace vao manifest)
        if (!fundingPredDir.isEmpty()) {
            int horizonIdx = Integer.parseInt(envOr("WFO_SEL_HORIZON_IDX", "1"));
            TreeMap<Long, long[]> fnd15 = buildFundingFromWfFiles(fundingPredDir, horizonIdx);
            fndRaw15mCount = fnd15.size();
            // 🔥 BUG-FIX 2026-07-13: predict_wf_*.bin la luoi 15m; engine tra selector bang .get(time) KHOP
            // CHINH XAC phut -> thieu forward-fill = 93% phut khong co selector -> tan suat + BIG_DOWN sap.
            // Khoi phuc thiet ke da-verify (gen_funding_wf_predictions.py: forward-fill 15p->phut, align 100%
            // market). Carry-forward moc 15m ra moi phut market cho toi moc ke, chan staleness <=STALE_MS.
            // WFO_FUNDING_FILL=0 de tat (giu 15m cu, chi de so sanh/debug).
            if (!"0".equals(envOr("WFO_FUNDING_FILL", "1"))) {
                long staleMs = Long.parseLong(envOr("WFO_FUNDING_FILL_STALE_MS", String.valueOf(15L * 60_000L)));
                fnd = forwardFillToGrid(fnd15, mkt.navigableKeySet(), staleMs);
            } else {
                LOG.warn("WFO_FUNDING_FILL=0 -> GIU luoi 15m (KHONG forward-fill) - chi debug, KHONG dung cho WFO that");
                fnd = fnd15;
            }
        } else {
            LOG.warn("WFO_FUNDING_PRED_DIR khong set -> fallback Aerospike (luong cu).");
            fnd = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        }
        LOG.info("scan xong: market={} pred={} funding={} (raw15m={})", mkt.size(), prd.size(), fnd.size(), fndRaw15mCount);

        writeMarket(new File(dir, F_MARKET), mkt);
        writePred(new File(dir, F_PRED), prd);
        writeFunding(new File(dir, F_FUNDING), fnd);

        StringBuilder mani = new StringBuilder();
        mani.append("schemaVersion=").append(SCHEMA_VERSION).append("\n");
        mani.append("exportedAt=").append(new java.util.Date()).append("\n");
        mani.append("sourceMarketSet=").append(SET_MARKET).append("\n");
        mani.append("sourcePredSet=").append(SET_PRED).append("\n");
        mani.append("sourceFundingSet=").append(SET_FUNDING).append("\n");
        // Provenance (env-sourced; xem docs/PIPELINE_PROVENANCE.md muc 6): truy nguyen code+model+leak-free.
        mani.append("codeGitSha=").append(envOr("WFO_CODE_SHA", "unknown")).append("\n");
        mani.append("predSetProvenance=").append(envOr("WFO_PROV_PRED", "unknown-see-docs/PIPELINE_PROVENANCE.md")).append("\n");
        mani.append("fundingSetProvenance=").append(envOr("WFO_PROV_FUNDING", "unknown-see-docs/PIPELINE_PROVENANCE.md")).append("\n");
        mani.append("leakFreeFrom=").append(envOr("WFO_LEAKFREE_FROM", "unknown")).append("\n");
        mani.append("marketCount=").append(mkt.size()).append("\n");
        mani.append("predCount=").append(prd.size()).append("\n");
        mani.append("fundingCount=").append(fnd.size()).append("\n");
        if (fndRaw15mCount >= 0) mani.append("fundingRaw15mCount=").append(fndRaw15mCount).append("\n");
        if (!mkt.isEmpty()) mani.append("marketRange=").append(mkt.firstKey()).append("..").append(mkt.lastKey()).append("\n");
        mani.append("md5_market=").append(md5(new File(dir, F_MARKET))).append("\n");
        mani.append("md5_pred=").append(md5(new File(dir, F_PRED))).append("\n");
        mani.append("md5_funding=").append(md5(new File(dir, F_FUNDING))).append("\n");
        try (Writer w = new OutputStreamWriter(new FileOutputStream(new File(dir, F_MANIFEST)), StandardCharsets.UTF_8)) {
            w.write(mani.toString());
        }
        LOG.info("EXPORT xong. manifest:\n{}", mani);
    }

    // ======================= FUNDING tu file Kaggle (BO Aerospike, Uni chot 2026-07-08) =======================
    /**
     * Doc 16 file predict_wf_*.bin (26B big-endian: long ts, short symId, float p4h,p12h,p24h,p72h),
     * gom theo ts -> TreeMap<ts, long[]> cung format engine (funding.bin). Moi long =
     * (symId<<32) | floatBits(score), score = 1 - P(win)[horizonIdx] (DAO DAU: P(win) cao -> score thap ->
     * engine uu tien; khop decodeSelectorMapToPrimitiveArray). Bo entry P(win)=NaN. Sort tang theo score
     * KHONG bat buoc o day (engine preprocessFundingData tu sort truoc khi chay).
     *
     * @param predDir    thu muc chua predict_wf_*.bin
     * @param horizonIdx 0=4h,1=12h,2=24h,3=72h
     */
    static TreeMap<Long, long[]> buildFundingFromWfFiles(String predDir, int horizonIdx) throws IOException {
        File d = new File(predDir);
        File[] files = d.listFiles((dir, name) -> name.startsWith("predict_wf_") && name.endsWith(".bin"));
        if (files == null || files.length == 0)
            throw new IOException("Khong thay predict_wf_*.bin trong " + predDir);
        java.util.Arrays.sort(files);
        // gom theo ts -> list encoded long
        java.util.HashMap<Long, java.util.ArrayList<Long>> byTs = new java.util.HashMap<>(4_000_000);
        final int REC = 26;
        long totalRec = 0, kept = 0;
        for (File f : files) {
            byte[] all = java.nio.file.Files.readAllBytes(f.toPath());
            if (all.length % REC != 0)
                throw new IOException(f.getName() + ": " + all.length + " khong chia het " + REC);
            java.nio.ByteBuffer buf = java.nio.ByteBuffer.wrap(all); // big-endian mac dinh
            int nrec = all.length / REC;
            for (int i = 0; i < nrec; i++) {
                long ts = buf.getLong();
                short symId = buf.getShort();
                float p4 = buf.getFloat(), p12 = buf.getFloat(), p24 = buf.getFloat(), p72 = buf.getFloat();
                float pwin = horizonIdx == 0 ? p4 : horizonIdx == 1 ? p12 : horizonIdx == 2 ? p24 : p72;
                totalRec++;
                if (Float.isNaN(pwin)) continue;
                float score = 1.0f - pwin; // DAO DAU
                long encoded = ((long) symId << 32) | (Float.floatToRawIntBits(score) & 0xFFFFFFFFL);
                byTs.computeIfAbsent(ts, k -> new java.util.ArrayList<>()).add(encoded);
                kept++;
            }
            LOG.info("  doc {}: {} rec (tong kept={})", f.getName(), nrec, kept);
        }
        TreeMap<Long, long[]> out = new TreeMap<>();
        for (Map.Entry<Long, java.util.ArrayList<Long>> e : byTs.entrySet()) {
            java.util.ArrayList<Long> lst = e.getValue();
            long[] arr = new long[lst.size()];
            for (int i = 0; i < arr.length; i++) arr[i] = lst.get(i);
            out.put(e.getKey(), arr);
        }
        String[] hName = {"4h", "12h", "24h", "72h"};
        LOG.info("buildFundingFromWfFiles: horizon={} | {} file | {} rec doc, {} kept (bo NaN) | {} moc 15m",
                hName[horizonIdx], files.length, totalRec, kept, out.size());
        return out;
    }

    /**
     * FORWARD-FILL luoi 15m -> moi phut market (khoi phuc thiet ke gen_funding_wf_predictions.py).
     * Voi moi ts trong {@code grid} (khoa market, ~1 phut), lay {@code src15m.floorEntry(ts)} (moc selector
     * gan nhat <= ts) va carry-forward, MIEN LA khong qua han (ts - floorKey <= {@code staleMs}). Chia se
     * THAM CHIEU mang (nhieu phut lien tiep tro cung 1 long[]) -> RAM ~ so moc 15m, khong nhan 15x.
     *
     * <p>Vi sao chan staleMs: neu selector THIEU 1 moc 15m (gap >15m), khong carry stale qua lau -> de trong
     * (dung: khong bia tin hieu selector cu). Grid deu 15m => moi phut deu co floor <=15m => phu ~100%.
     */
    static TreeMap<Long, long[]> forwardFillToGrid(TreeMap<Long, long[]> src15m,
                                                   java.util.NavigableSet<Long> grid, long staleMs) {
        TreeMap<Long, long[]> out = new TreeMap<>();
        long filled = 0, beforeFirst = 0, skippedStale = 0;
        for (Long t : grid) {
            Map.Entry<Long, long[]> e = src15m.floorEntry(t);
            if (e == null) { beforeFirst++; continue; }          // truoc moc selector dau tien
            if (t - e.getKey() > staleMs) { skippedStale++; continue; } // qua han -> de trong
            out.put(t, e.getValue());                             // reference-share
            filled++;
        }
        LOG.info("forwardFillToGrid: grid={} filled={} beforeFirst={} skippedStale(>{}m)={} | src15m={} -> out={}",
                grid.size(), filled, beforeFirst, staleMs / 60000, src15m.size(), out.size());
        return out;
    }

    // ======================= LOAD (mọi worker, đọc file cục bộ) =======================
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
