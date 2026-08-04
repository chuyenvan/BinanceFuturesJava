package com.binance.chuyennd.research;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * TASK-041 A0 (BREADTH theo top-vol): đo cú sập THỊ TRƯỜNG RỘNG trên nhóm coin thanh khoản cao.
 *
 * <p>Tại mỗi mốc 15m t:
 *   1. xếp coin theo VOL 1D của NGÀY HÔM TRƯỚC (tránh look-ahead vol ngày sập) -> lấy TOP 50%.
 *   2. forward return H giờ moi coin top: ret = close[t+H]/close[t]-1.
 *   3. breadth = % coin top co ret <= -X.
 *   4. "cú sập" = breadth >= B (50%). Đếm số cú độc lập (de-overlap theo H).
 *
 * <p>Đọc per-15m cả rổ (getExistingTickersMap), tính 2 lượt: lượt 1 gom close+vol theo coin theo ts,
 * lượt 2 tính forward+breadth. Giữ theo coptimized: chỉ lưu close 15m + vol-1d theo (coin, dayIdx).
 *
 * <p>Args: [startYYYYMMDD=20210101] [endYYYYMMDD=now] [outCsv] [instance=226]
 * Quét lưới X∈{10,15,20}% × B∈{50%} × H∈{4h,12h,24h}; in ra số cú độc lập.
 */
public class ExportMarketBreadthCrash {

    static final Logger LOG = LoggerFactory.getLogger(ExportMarketBreadthCrash.class);
    static final String SET = "kline_1m_opt";
    static final long MIN = 60 * 1000L;
    static final long STEP = 15 * MIN;
    static final long DAY = 24 * 60 * MIN;
    static final int[] HSTEPS = {16, 48, 96};
    static final String[] HNAME = {"4h", "12h", "24h"};
    static final double[] XS = {0.10, 0.15, 0.20};
    static final double B = 0.50;          // nguong breadth
    static final double TOP_FRAC = 0.50;   // top 50% theo vol

    public static void main(String[] args) throws Exception {
        SimpleDateFormat day = new SimpleDateFormat("yyyyMMdd");
        long start = args.length > 0 ? day.parse(args[0]).getTime() : day.parse("20210101").getTime();
        long end = args.length > 1 ? day.parse(args[1]).getTime() : System.currentTimeMillis();
        String out = args.length > 2 ? args[2] : "/home/chuyennd/java/simulator/breadth_crash.csv";
        String inst = args.length > 3 ? args[3] : "226";
        AerospikeClient client = inst.equals("242")
                ? DataManagerAerospikeFloatSim.getClient242() : DataManagerAerospikeFloatSim.getClientOracle();
        SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");

        // close theo (ts -> (coin -> close)); luu chuoi 15m
        // de tinh forward can tra close[t+H]: luu Map<Long, Map<String,Float>> close15m
        // vol-1d: gom totalUsdt theo (coin, dayStart)
        Map<Long, Map<String, Float>> close15m = new HashMap<>();
        Map<Long, Map<String, Double>> volDay = new HashMap<>();  // dayStartMs -> coin -> sum totalUsdt
        LOG.info("Quet ticker [{} .. {}] inst={} step=15m", fmt.format(new Date(start)), fmt.format(new Date(end)), inst);

        long n = 0;
        for (long ts = start; ts <= end; ts += STEP) {
            n++;
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, SET, fmt.format(new Date(ts)));
            Record rec = client.get(null, key);
            if (rec == null) continue;
            byte[] data = (byte[]) rec.getValue("data");
            if (data == null) continue;
            Map<String, KlineObjectOptimized> m = MinuteDataFinal.parseFrom(Snappy.uncompress(data)).getTickersMap();
            Map<String, Float> cl = new HashMap<>(m.size());
            long dayStart = (ts / DAY) * DAY;
            Map<String, Double> vd = volDay.computeIfAbsent(dayStart, k -> new HashMap<>());
            for (Map.Entry<String, KlineObjectOptimized> e : m.entrySet()) {
                String sym = e.getKey();
                if (!sym.endsWith("USDT")) continue;
                float c = (float) e.getValue().getPriceClose();
                if (c <= 0) continue;
                cl.put(sym, c);
                vd.merge(sym, (double) e.getValue().getTotalUsdt(), Double::sum);
            }
            if (!cl.isEmpty()) close15m.put(ts, cl);
            if (n % 10000 == 0) LOG.info("  {} mocs | {} ts-close | ts {}", n, close15m.size(), fmt.format(new Date(ts)));
        }
        LOG.info("Doc xong: {} mocs co close, {} ngay co vol", close15m.size(), volDay.size());

        // tinh breadth-crash cho moi (H,X)
        try (BufferedWriter w = new BufferedWriter(new FileWriter(out))) {
            w.write("H,X,B,topFrac,nCrashMoc,nIndep,pctTime\n");
            List<Long> tss = new ArrayList<>(close15m.keySet());
            tss.sort(null);
            for (int hi = 0; hi < HSTEPS.length; hi++) {
                long Hms = (long) HSTEPS[hi] * STEP;
                for (double X : XS) {
                    List<Long> crash = new ArrayList<>();
                    for (long t : tss) {
                        // top 50% theo vol ngay hom truoc
                        long prevDay = ((t - DAY) / DAY) * DAY;
                        Map<String, Double> vd = volDay.get(prevDay);
                        if (vd == null || vd.isEmpty()) vd = volDay.get((t / DAY) * DAY); // fallback ngay hien tai
                        if (vd == null || vd.isEmpty()) continue;
                        Map<String, Float> clNow = close15m.get(t);
                        Map<String, Float> clFut = close15m.get(t + Hms);
                        if (clFut == null) continue;
                        // rank coin theo vol desc, lay top
                        List<Map.Entry<String, Double>> rank = new ArrayList<>(vd.entrySet());
                        rank.sort((a, b) -> Double.compare(b.getValue(), a.getValue()));
                        int topN = Math.max(1, (int) (rank.size() * TOP_FRAC));
                        int total = 0, down = 0;
                        for (int i = 0; i < topN; i++) {
                            String sym = rank.get(i).getKey();
                            Float c0 = clNow.get(sym), c1 = clFut.get(sym);
                            if (c0 == null || c1 == null || c0 <= 0) continue;
                            total++;
                            if (c1 / c0 - 1 <= -X) down++;
                        }
                        if (total >= 10 && (double) down / total >= B) crash.add(t);
                    }
                    crash.sort(null);
                    int indep = 0;
                    long last = Long.MIN_VALUE;
                    for (long t : crash) {
                        if (t > last + Hms) { indep++; last = t; }
                    }
                    double pct = 100.0 * crash.size() / Math.max(1, tss.size());
                    w.write(String.format("%s,%d,%d,%d,%d,%d,%.2f%n",
                            HNAME[hi], (int) (X * 100), (int) (B * 100), (int) (TOP_FRAC * 100),
                            crash.size(), indep, pct));
                    LOG.info("H={} X={}% B={}% top{}% : nCrashMoc={} nIndep={} %time={}",
                            HNAME[hi], (int) (X * 100), (int) (B * 100), (int) (TOP_FRAC * 100),
                            crash.size(), indep, String.format("%.2f", pct));
                }
            }
        }
        LOG.info("DONE -> {}", out);
    }
}
