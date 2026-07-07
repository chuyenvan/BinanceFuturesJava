package com.binance.chuyennd.ai_ml.features.export;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.utils.Utils;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.lang.reflect.Type;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-135 - Aggregate 15m/4h BTC/ETH tu ticker kline_1m_opt -> set kline_15m_btceth/kline_4h_btceth
 * CHI GHI Oracle LOCAL (127.0.0.1:3222 ns=test). DOC LAP Aggregate15m4hBtcEth goc (ghi CA 226+242 -> dung 242 that).
 * Doc ticker truc tiep Aerospike local (khong qua DataManager getClient242). Bo validate doc-242.
 * Args: [host] [port] [ns]
 */
public class Aggregate15m4hLocal {
    private static final Logger LOG = LoggerFactory.getLogger(Aggregate15m4hLocal.class);
    private static final String[] SYMBOLS = {"BTCUSDT", "ETHUSDT"};
    private static final long MS_15M = 15L * 60_000L, MS_4H = 240L * 60_000L;
    private static final String SET_15M = "kline_15m_btceth", SET_4H = "kline_4h_btceth";
    private static final String START_DATE = "20210101";
    private static final Gson GSON = new Gson();

    private static class Acc {
        long openEpoch = Long.MAX_VALUE, closeEpoch = Long.MIN_VALUE;
        float open, close, high = Float.NEGATIVE_INFINITY, low = Float.POSITIVE_INFINITY, vol = 0f;
        void add(long epoch, KlineObjectOptimized k) {
            if (epoch < openEpoch) { openEpoch = epoch; open = k.getPriceOpen(); }
            if (epoch > closeEpoch) { closeEpoch = epoch; close = k.getPriceClose(); }
            high = Math.max(high, k.getMaxPrice()); low = Math.min(low, k.getMinPrice());
            vol += k.getTotalUsdt();
        }
        float[] ohlcv() { return new float[]{open, high, low, close, vol}; }
    }

    public static void main(String[] args) throws Exception {
        String host = args.length >= 1 ? args[0] : "127.0.0.1";
        int port = args.length >= 2 ? Integer.parseInt(args[1]) : 3222;
        String ns = args.length >= 3 ? args[2] : "test";
        LOG.info("Aggregate 15m/4h BTC/ETH -> {}:{} ns={} (LOCAL ONLY, khong dung 242)", host, port, ns);
        if (!"127.0.0.1".equals(host) && !"localhost".equals(host)) LOG.warn("host KHONG localhost ({})!", host);

        SimpleDateFormat kf = new SimpleDateFormat("yyyyMMdd-HHmm");
        kf.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        SimpleDateFormat monthF = new SimpleDateFormat("yyyyMM");
        monthF.setTimeZone(TimeZone.getTimeZone("GMT+7"));

        try (AerospikeClient client = new AerospikeClient(host, port)) {
            long start = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
            long end = System.currentTimeMillis();

            Map<String, TreeMap<Long, Acc>> acc15 = new HashMap<>(), acc4 = new HashMap<>();
            for (String s : SYMBOLS) { acc15.put(s, new TreeMap<>()); acc4.put(s, new TreeMap<>()); }

            int days = 0;
            for (long day = start; day < end; day += 24L * Utils.TIME_HOUR) {
                // doc 1 ngay ticker: 1440 key phut
                Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("GMT+7"));
                cal.setTimeInMillis(day);
                cal.set(Calendar.HOUR_OF_DAY, 0); cal.set(Calendar.MINUTE, 0); cal.set(Calendar.SECOND, 0); cal.set(Calendar.MILLISECOND, 0);
                long dayStart = cal.getTimeInMillis();
                boolean anyData = false;
                for (int min = 0; min < 1440; min++) {
                    long epoch = dayStart + min * 60_000L;
                    Key key = new Key(ns, "kline_1m_opt", kf.format(new Date(epoch)));
                    Record r = client.get(null, key);
                    if (r == null) continue;
                    byte[] data = (byte[]) r.getValue("data");
                    if (data == null) continue;
                    anyData = true;
                    Map<String, KlineObjectOptimized> m = MinuteDataFinal.parseFrom(Snappy.uncompress(data)).getTickersMap();
                    for (String s : SYMBOLS) {
                        KlineObjectOptimized k = m.get(s);
                        if (k == null || k.getTotalUsdt() <= 0) continue;
                        acc15.get(s).computeIfAbsent(epoch / MS_15M * MS_15M, x -> new Acc()).add(epoch, k);
                        acc4.get(s).computeIfAbsent(epoch / MS_4H * MS_4H, x -> new Acc()).add(epoch, k);
                    }
                }
                if (++days % 200 == 0) LOG.info("   ... {} ngay, {} (co data={})", days, Utils.normalizeDateYYYYMMDD(day), anyData);
            }

            WritePolicy wp = new WritePolicy();
            wp.expiration = 0; wp.sendKey = true; wp.recordExistsAction = RecordExistsAction.UPDATE;
            for (String s : SYMBOLS) {
                writeSeries(client, ns, s, SET_15M, toSeries(acc15.get(s)), monthF, wp);
                writeSeries(client, ns, s, SET_4H, toSeries(acc4.get(s)), monthF, wp);
            }
            // verify: doc lai 1 record-thang
            Record chk = client.get(null, new Key(ns, SET_15M, "BTCUSDT-202201"));
            LOG.info("VERIFY kline_15m_btceth BTCUSDT-202201: {}", chk != null ? "CO" : "NULL");
            LOG.info("✅ Aggregate 15m/4h LOCAL xong.");
        }
        System.exit(0);
    }

    private static TreeMap<Long, float[]> toSeries(TreeMap<Long, Acc> acc) {
        TreeMap<Long, float[]> out = new TreeMap<>();
        for (Map.Entry<Long, Acc> e : acc.entrySet()) out.put(e.getKey(), e.getValue().ohlcv());
        return out;
    }

    private static void writeSeries(AerospikeClient client, String ns, String symbol, String set,
                                    TreeMap<Long, float[]> series, SimpleDateFormat monthF, WritePolicy wp) throws Exception {
        Map<String, TreeMap<Long, float[]>> byMonth = new LinkedHashMap<>();
        for (Map.Entry<Long, float[]> e : series.entrySet())
            byMonth.computeIfAbsent(monthF.format(new Date(e.getKey())), k -> new TreeMap<>()).put(e.getKey(), e.getValue());
        int recs = 0;
        for (Map.Entry<String, TreeMap<Long, float[]>> e : byMonth.entrySet()) {
            byte[] comp = Snappy.compress(GSON.toJson(e.getValue()).getBytes("UTF-8"));
            client.put(wp, new Key(ns, set, symbol + "-" + e.getKey()), new Bin("data", comp));
            recs++;
        }
        LOG.info("💾 {}/{}: {} record-thang ({} nen)", set, symbol, recs, series.size());
    }
}
