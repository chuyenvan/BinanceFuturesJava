package com.binance.chuyennd.aerospike;

import org.junit.Assume;
import org.junit.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TimeZone;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.stream.LongStream;

import static org.junit.Assert.assertEquals;

/**
 * HO4-P1: race {@code SimpleDateFormat} dung chung trong {@code parallelStream} cua
 * {@link DataManagerAerospikeFloatSim#saveMarketDataBatch} (key phut ghep sai/trung => mat phut ngau nhien).
 * Fix = {@link DataManagerAerospikeFloatSim#marketDataKey(long)} (ThreadLocal + pin GMT+7).
 */
public class MarketDataKeyRaceTest {

    private static final Logger LOG = LoggerFactory.getLogger(MarketDataKeyRaceTest.class);
    private static final long MIN = 60_000L;
    private static final long T0 = 1751302800000L;          // 2025-07-01 00:00 +07
    private static final int N_MIN = 30 * 1440;             // 30 ngay phut

    private static String expected(long ts) {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd-HHmm");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        return f.format(new Date(ts));
    }

    private static long[] minutes() {
        return LongStream.range(0, N_MIN).map(i -> T0 + i * MIN).toArray();
    }

    @Test
    public void fixedKey_parallelStream_duKey_khongTrung() {
        long[] ts = minutes();
        Map<Long, String> exp = new ConcurrentHashMap<>();
        for (long t : ts) exp.put(t, expected(t));
        for (int round = 0; round < 10; round++) {
            Map<Long, String> got = new ConcurrentHashMap<>();
            LongStream.of(ts).boxed().parallel().forEach(t -> got.put(t, DataManagerAerospikeFloatSim.marketDataKey(t)));
            Set<String> uniq = new HashSet<>(got.values());
            assertEquals("so key", N_MIN, got.size());
            assertEquals("key khong trung", N_MIN, uniq.size());
            for (long t : ts) assertEquals(exp.get(t), got.get(t));
        }
    }

    @Test
    public void fixedKey_16luong_duKey_khongTrung() throws Exception {
        long[] ts = minutes();
        ExecutorService ex = Executors.newFixedThreadPool(16);
        try {
            Map<Long, String> got = new ConcurrentHashMap<>();
            List<Future<?>> fs = new ArrayList<>();
            int chunk = (N_MIN + 15) / 16;
            for (int k = 0; k < 16; k++) {
                final int lo = k * chunk, hi = Math.min(N_MIN, lo + chunk);
                // moi luong chay het chunk cua minh 3 lan, xen ke voi luong khac
                fs.add(ex.submit(() -> {
                    for (int r = 0; r < 3; r++) {
                        for (int i = lo; i < hi; i++) got.put(ts[i], DataManagerAerospikeFloatSim.marketDataKey(ts[i]));
                    }
                }));
            }
            for (Future<?> f : fs) f.get();
            assertEquals(N_MIN, got.size());
            assertEquals(N_MIN, new HashSet<>(got.values()).size());
            for (long t : ts) assertEquals(expected(t), got.get(t));
        } finally {
            ex.shutdownNow();
        }
    }

    /** Tai hien race cua ma CU (fmt dung chung trong parallelStream). Xac suat => chi assume (khong lam test chap chon). */
    @Test
    public void legacySharedFormat_taiHienRace() {
        Assume.assumeTrue("can >= 2 CPU", Runtime.getRuntime().availableProcessors() >= 2);
        long[] ts = minutes();
        long bad = 0, lost = 0;
        for (int round = 0; round < 10; round++) {
            SimpleDateFormat shared = new SimpleDateFormat("yyyyMMdd-HHmm");
            shared.setTimeZone(TimeZone.getTimeZone("GMT+7"));
            Map<Long, String> got = new ConcurrentHashMap<>();
            LongStream.of(ts).boxed().parallel().forEach(t -> {
                String k;
                try {
                    k = shared.format(new Date(t));
                } catch (RuntimeException e) {
                    k = "EXC";
                }
                got.put(t, k);
            });
            for (long t : ts) if (!expected(t).equals(got.get(t))) bad++;
            lost += N_MIN - new HashSet<>(got.values()).size();
        }
        LOG.info("legacy shared SimpleDateFormat: key sai {} / {}, key trung (=> phut mat) {}", bad, 10L * N_MIN, lost);
        Assume.assumeTrue("race khong xuat hien lan nay (xac suat)", bad > 0);
    }

    /** Hanh vi khong doi tren host +07: GMT+7 == Asia/Ho_Chi_Minh moi phut 2020..2027. */
    @Test
    public void key_bangAsiaHoChiMinh_2020_2027() {
        SimpleDateFormat vn = new SimpleDateFormat("yyyyMMdd-HHmm");
        vn.setTimeZone(TimeZone.getTimeZone("Asia/Ho_Chi_Minh"));
        long lo = 1577811600000L, hi = 1798736400000L;    // 2020-01-01 .. 2027-01-01 +07
        for (long t = lo; t < hi; t += 37 * MIN) {
            assertEquals(vn.format(new Date(t)), DataManagerAerospikeFloatSim.marketDataKey(t));
        }
    }

    /** Key khong phu thuoc TZ mac dinh JVM (truoc fix: getMarketDataAtTime/saveMarketDataBatch theo TZ JVM). */
    @Test
    public void key_khongPhuThuocTzMacDinh() throws Exception {
        TimeZone old = TimeZone.getDefault();
        try {
            TimeZone.setDefault(TimeZone.getTimeZone("UTC"));
            final String[] out = new String[1];
            Thread th = new Thread(() -> out[0] = DataManagerAerospikeFloatSim.marketDataKey(T0));
            th.start();
            th.join();
            assertEquals("20250701-0000", out[0]);
        } finally {
            TimeZone.setDefault(old);
        }
    }
}
