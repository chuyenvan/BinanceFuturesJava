package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiMetricSets;
import com.binance.chuyennd.research.oibackfill.VisionMetricsClient;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.zip.GZIPOutputStream;

// TASK-038 phan A (A2): xuat OI/LS/taker PER-COIN (#41..#45) file RIENG, MERGE vao funding v3 o train 039.
// Loop-THEO-COIN RAM-aware (nhu 018): 1 coin/lan, giu oiZ EXPANDING no-leak, RAM = 4 map cua 1 coin.
// Output binary gzip (long ts, short symId, 5xfloat) cung key voi .bin.gz. NaN cho o thieu (KHONG fill 0).
public class ExportFundingOiPerCoin {

    private static final Logger LOG = LoggerFactory.getLogger(ExportFundingOiPerCoin.class);
    private static final long STALE_MS = 60L * 60_000L;
    private static final long DAY = 24L * 3600_000L;
    private static final String DEFAULT_SYMFILE = "/tmp/oisyms.txt";

    public static void main(String[] args) {
        try {
            Configs.IS_HPO_MODE = false;
            Configs.IS_KAGGLE_MODE = true;
            SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd HH:mm");
            SimpleDateFormat sdfFile = new SimpleDateFormat("yyyyMMdd");
            long start = sdf.parse("20210101 07:00").getTime();
            long end = System.currentTimeMillis();
            String symfile = DEFAULT_SYMFILE;
            boolean useVision = false;   // source=vision: doc THANG tu data.binance.vision (day du, khong qua Aerospike)
            int visionThreads = 8;
            List<String> pos = new ArrayList<>();
            for (String a : args) {
                String al = a.toLowerCase();
                if (al.startsWith("symfile=")) symfile = a.substring(8).trim();
                else if (al.equals("source=vision")) useVision = true;
                else if (al.startsWith("vthreads=")) visionThreads = Integer.parseInt(a.substring(9).trim());
                else pos.add(a);
            }
            if (pos.size() >= 1 && pos.get(0).length() == 8) start = sdf.parse(pos.get(0) + " 07:00").getTime();
            if (pos.size() >= 2 && pos.get(1).length() == 8) end = sdf.parse(pos.get(1) + " 07:00").getTime();
            List<String> universe = readUniverse(symfile);
            if (universe.isEmpty()) throw new IllegalStateException("Universe rong: " + symfile);
            Map<String, Short> symbolMap = DataManagerAerospikeFloatSim.loadSymbolMapper();
            String outputDir = "features_oi_percoin_v1/";
            new File(outputDir).mkdirs();
            String outPath = outputDir + "oi_percoin_" + sdfFile.format(new Date(start)) + "_to_" + sdfFile.format(new Date(end)) + ".bin.gz";
            LOG.info("TASK-038/A2 OI per-coin | universe={} | [{} .. {}] -> {}", universe.size(), sdf.format(new Date(start)), sdf.format(new Date(end)), outPath);
            // TASK-103 fix: ping Aerospike 226 truoc vong loop coin de tranh connection stale tu Tool1
            // (Tool1 chay ~24 phut lam client idle -> Error -8 Cluster empty -> moi getMetricMap226 tra null -> 0 dong)
            try {
                DataManagerAerospikeFloatSim.getMetricMap226(OiMetricSets.OI.set, OiMetricSets.OI.bin, "BTCUSDT");
                LOG.info("Aerospike 226 ping OK truoc Tool2");
            } catch (Exception pingEx) {
                LOG.warn("Aerospike 226 ping loi (se tu reconnect): {}", pingEx.getMessage());
            }
            DataOutputStream dos = new DataOutputStream(new BufferedOutputStream(new GZIPOutputStream(new FileOutputStream(outPath)), 1024 * 1024));
            LOG.info("NGUON OI = {}", useVision ? "VISION (data.binance.vision, toan lich su moi coin)" : "AEROSPIKE 226");
            VisionMetricsClient vision = useVision ? new VisionMetricsClient() : null;
            long emitted = 0; int done = 0, coinsWithOi = 0; long[] nullCnt = new long[5];
            for (String coin : universe) {
                Short id = symbolMap.get(coin);
                if (id == null) continue;
                TreeMap<Long, Float> oi, lsg, lst, tk;
                if (useVision) {
                    // Tai TOAN lich su coin (khong range) de oiZ expanding khong thieu warmup; writeCoin tu loc emit [start,end].
                    VisionMetricsClient.SymbolMetrics m = vision.fetchSymbol(coin, visionThreads);
                    oi = m.maps[0]; lst = m.maps[1]; lsg = m.maps[3]; tk = m.maps[4];
                } else {
                    oi = DataManagerAerospikeFloatSim.getMetricMap226(OiMetricSets.OI.set, OiMetricSets.OI.bin, coin);
                    lsg = DataManagerAerospikeFloatSim.getMetricMap226(OiMetricSets.LS_GLOBAL_ACC.set, OiMetricSets.LS_GLOBAL_ACC.bin, coin);
                    lst = DataManagerAerospikeFloatSim.getMetricMap226(OiMetricSets.LS_TOPTRADER_ACC.set, OiMetricSets.LS_TOPTRADER_ACC.bin, coin);
                    tk = DataManagerAerospikeFloatSim.getMetricMap226(OiMetricSets.TAKER_VOL.set, OiMetricSets.TAKER_VOL.bin, coin);
                }
                long e = writeCoin(dos, coin, id, oi, lsg, lst, tk, start, end, nullCnt);
                if (e > 0) { coinsWithOi++; emitted += e; }
                if (++done % 100 == 0) LOG.info("  {}/{} coin (emitted={})", done, universe.size(), emitted);
            }
            dos.close();
            LOG.info("HOAN TAT: {} dong x5 feat, {}/{} coin co OI -> {}", emitted, coinsWithOi, universe.size(), outPath);
            LOG.info("null-count(oiDelta24h,oiZ,lsGlobal,lsToptrader,takerBuyRatio)={}", Arrays.toString(nullCnt));
        } catch (Exception ex) {
            LOG.error("ExportFundingOiPerCoin loi", ex);
            System.exit(1);
        }
        System.exit(0);
    }

    private static long writeCoin(DataOutputStream dos, String coin, short id,
                                  TreeMap<Long, Float> oi, TreeMap<Long, Float> lsg,
                                  TreeMap<Long, Float> lst, TreeMap<Long, Float> tk,
                                  long start, long end, long[] nullCnt) throws IOException {
        if (oi == null || oi.isEmpty()) return 0;
        double sum = 0, sumSq = 0; int n = 0; long emitted = 0;
        for (Map.Entry<Long, Float> en : oi.entrySet()) {
            long t = en.getKey();
            float oiVal = en.getValue();
            sum += oiVal; sumSq += (double) oiVal * oiVal; n++;
            if (t < start || t >= end) continue;
            Float oiDelta = null;
            Map.Entry<Long, Float> past = oi.floorEntry(t - DAY);
            if (past != null && (t - DAY - past.getKey()) <= STALE_MS && past.getValue() != 0f)
                oiDelta = oiVal / past.getValue() - 1f;
            float z = Float.NaN;
            if (n >= 2) {
                double mean = sum / n;
                double var = (sumSq - (sum * sum) / n) / (n - 1);
                if (var > 0) z = (float) ((oiVal - mean) / Math.sqrt(var));
            }
            Float lg = floorStale(lsg, t);
            Float lt = floorStale(lst, t);
            Float r = floorStale(tk, t);
            Float takerBuy = (r != null && r >= 0f) ? r / (1f + r) : null;
            dos.writeLong(t);
            dos.writeShort(id);
            dos.writeFloat(oiDelta == null ? Float.NaN : oiDelta);
            dos.writeFloat(z);
            dos.writeFloat(lg == null ? Float.NaN : lg);
            dos.writeFloat(lt == null ? Float.NaN : lt);
            dos.writeFloat(takerBuy == null ? Float.NaN : takerBuy);
            if (oiDelta == null) nullCnt[0]++;
            if (Float.isNaN(z)) nullCnt[1]++;
            if (lg == null) nullCnt[2]++;
            if (lt == null) nullCnt[3]++;
            if (takerBuy == null) nullCnt[4]++;
            emitted++;
        }
        return emitted;
    }

    private static Float floorStale(TreeMap<Long, Float> m, long t) {
        if (m == null || m.isEmpty()) return null;
        Map.Entry<Long, Float> e = m.floorEntry(t);
        if (e == null || (t - e.getKey()) > STALE_MS) return null;
        return e.getValue();
    }

    private static List<String> readUniverse(String path) throws Exception {
        List<String> out = new ArrayList<>();
        for (String line : Files.readAllLines(Paths.get(path))) {
            String s = line.trim().toUpperCase();
            if (s.matches("^[A-Z0-9]+USDT$")) out.add(s);
        }
        return out;
    }
}
