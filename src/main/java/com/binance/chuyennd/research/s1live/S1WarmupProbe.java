package com.binance.chuyennd.research.s1live;

import com.aerospike.client.Key;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.selector.S1FeatureLive;
import com.binance.chuyennd.tradecore.selector.S1RankerLive;

import java.text.SimpleDateFormat;
import java.util.*;

/**
 * [L5] CHAN DOAN warm-up S1 ? dem so coin co du chuoi close 1h tren cum Aerospike-242.
 *
 * <p>Doc DUNG duong ma {@code S1RankerLive.refresh()} doc: client {@code getClient242()}
 * ({@code AEROSPIKE_HOST}/{@code AEROSPIKE_PORT}), ns {@link S1RankerLive#NS_242},
 * set {@code kline_1m_opt}, key phut {@code yyyyMMdd-HHmm} GMT+7, quy uoc VISION
 * {@code close(gio t) = priceClose cua nen 1m open_time = t - 1m}.
 *
 * <pre>
 *   java -Xmx512m -cp target/binance-java-sdk-1.2.4.jar \
 *        com.binance.chuyennd.research.s1live.S1WarmupProbe [gioDoc] [minMoc]
 * </pre>
 * Mac dinh {@code gioDoc = 384} (= WARMUP_HOURS 336 + 48), {@code minMoc = 336}.
 */
public final class S1WarmupProbe {

    private static final long H = S1FeatureLive.HOUR_MS;
    private static final long MIN = 60_000L;
    private static final String SET = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER;

    private S1WarmupProbe() {
    }

    private static String minuteKey(long ms) {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd-HHmm");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        return f.format(new Date(ms));
    }

    public static void main(String[] args) {
        int hours = args.length > 0 ? Integer.parseInt(args[0]) : S1FeatureLive.WARMUP_HOURS + 48;
        int minPts = args.length > 1 ? Integer.parseInt(args[1]) : S1FeatureLive.WARMUP_HOURS;
        // arg[2] = "raw" -> dung THANG Configs.AEROSPIKE_NAMESPACE_242 (hanh vi TRUOC khi sua)
        // de tai lap loi tren box thieu key; mac dinh dung NS_242 da resolve.
        boolean raw = args.length > 2 && "raw".equalsIgnoreCase(args[2]);
        final String ns = raw ? Configs.AEROSPIKE_NAMESPACE_242 : S1RankerLive.NS_242;
        long now = System.currentTimeMillis();
        long last = (now / H) * H;
        long from = last - (long) (hours - 1) * H;

        System.out.println("=== S1 WARM-UP PROBE ===");
        System.out.println("nguon      : " + Configs.AEROSPIKE_HOST_242 + ":" + Configs.AEROSPIKE_PORT_242
                + " ns=" + ns + " set=" + SET + (raw ? "   [MODE=raw, tai lap code CU]" : ""));
        System.out.println("cfg ns_242 : " + Configs.AEROSPIKE_NAMESPACE_242
                + "   (null = config.properties THIEU key AEROSPIKE_NAMESPACE_242)");
        System.out.println("cua so     : " + hours + " moc gio, " + new Date(from) + " -> " + new Date(last));
        System.out.println("nguong     : >= " + minPts + " moc close 1h / coin");

        Map<String, Integer> cnt = new HashMap<>();
        Map<String, Long> firstTs = new HashMap<>();
        Map<String, Long> lastTs = new HashMap<>();
        int hoursOk = 0;
        long t0 = System.currentTimeMillis();
        for (long t = from; t <= last; t += H) {
            Map<String, KlineObjectOptimized> m;
            try {
                m = DataManagerAerospikeFloatSim.getExistingTickersMap(new Key(ns, SET, minuteKey(t - MIN)));
            } catch (Throwable e) {
                System.out.println("EXCEPTION tai " + minuteKey(t - MIN) + ": " + e);
                break;
            }
            if (m.isEmpty()) continue;
            hoursOk++;
            for (Map.Entry<String, KlineObjectOptimized> e : m.entrySet()) {
                if (e.getValue().getPriceClose() <= 0f) continue;
                String sym = e.getKey().endsWith("USDT") ? e.getKey() : e.getKey() + "USDT";
                cnt.merge(sym, 1, Integer::sum);
                firstTs.putIfAbsent(sym, t);
                lastTs.put(sym, t);
            }
        }
        long ms = System.currentTimeMillis() - t0;

        int ready = 0;
        for (int v : cnt.values()) if (v >= minPts) ready++;
        System.out.println("--- KET QUA ---");
        System.out.println("moc gio doc duoc : " + hoursOk + "/" + hours);
        System.out.println("tong coin        : " + cnt.size());
        System.out.println("coin du >= " + minPts + " : " + ready);
        System.out.println("coin THIEU       : " + (cnt.size() - ready));
        System.out.println("thoi gian        : " + ms + " ms");
        List<String> syms = new ArrayList<>(cnt.keySet());
        Collections.sort(syms);
        System.out.println("--- 3 coin mau ---");
        for (int i = 0; i < syms.size() && i < 3; i++) {
            String s = syms.get(i);
            System.out.println("  " + s + " : " + cnt.get(s) + " moc, tu " + new Date(firstTs.get(s))
                    + " den " + new Date(lastTs.get(s)));
        }
        System.out.println("=== HET ===");
        System.exit(0);
    }
}
