package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Map;
import java.util.TimeZone;
import java.util.zip.GZIPOutputStream;

/**
 * [V11 2026-10-20] docs/plan/V11_COLLECTOR_SETTLE.md — INSTRUMENT: dump 9 feature S1 (dung mang float da cho vao ONNX)
 * + score + moc OI dung + thoi diem nap OI, de khoanh phan lech S1 live vs offline (PARITY_1020: 41 % dong lech).
 *
 * <p>Cong {@code LIVE_S1_DUMP} = N (ghi moi N phut; 0 = tat). KHONG khai => mac dinh 1 neu {@code LIVE_FEAT_DUMP > 0}
 * (shadow dang dump feature), nguoc lai 0. File {@code s1_dump/s1_dump_<yyyyMMdd_HHmm luc mo>.csv.gz} (GMT+7),
 * xoay moi gio, tran 200 MB (khong nen) moi file. Moi loi IO => LOG.error + tat dump, KHONG anh huong duong live.
 */
public final class S1FeatDump {

    private static final Logger LOG = LoggerFactory.getLogger(S1FeatDump.class);
    public static final String KEY = "LIVE_S1_DUMP";
    static final String DIR = "s1_dump";
    static final long MAX_BYTES = 200L * 1024L * 1024L;
    static final String HEADER = "ts,symbol,f0,f1,f2,f3,f4,f5,f6,f7,f8,score,oi_ref_ts,oi_hour,oi_loaded_ms,oi_src";

    static final int EVERY = resolveEvery(Cfg.get(KEY), Cfg.getOr("LIVE_FEAT_DUMP", "0"));

    private static PrintWriter w;
    private static long fileHour = Long.MIN_VALUE;
    private static long bytes = 0;
    private static boolean disabled = false;
    private static boolean hook = false;

    static {
        if (EVERY > 0) {
            LOG.warn("[S1-DUMP] BAT: ghi 9 feature S1 + OI moi {} phut vao {}/*.csv.gz (chi ghi, khong doi logic)", EVERY, DIR);
        }
    }

    private S1FeatDump() {
    }

    /** Thuan (unit test): key khai => dung key; khong khai => 1 neu LIVE_FEAT_DUMP>0 nguoc lai 0. */
    static int resolveEvery(String key, String featDump) {
        int def = 0;
        try {
            def = Integer.parseInt(featDump == null ? "0" : featDump.trim()) > 0 ? 1 : 0;
        } catch (NumberFormatException e) {
            def = 0;
        }
        if (key == null || key.trim().isEmpty()) return def;
        try {
            return Math.max(0, Integer.parseInt(key.trim()));
        } catch (NumberFormatException e) {
            LOG.error("[S1-DUMP] {}='{}' khong phai so -> {}", KEY, key, def);
            return def;
        }
    }

    /** Mot dong CSV (float in Float.toString = bieu dien float32 chinh xac). */
    static String row(long ts, String sym, float[] f, float score, Long oiRef, long oiHour, long oiLoadedMs, String oiSrc) {
        StringBuilder sb = new StringBuilder(160);
        sb.append(ts).append(',').append(sym);
        for (int j = 0; j < 9; j++) sb.append(',').append(f != null && j < f.length ? Float.toString(f[j]) : "");
        sb.append(',').append(Float.toString(score));
        sb.append(',').append(oiRef == null ? "" : String.valueOf(oiRef));
        sb.append(',').append(oiHour).append(',').append(oiLoadedMs).append(',').append(oiSrc == null ? "" : oiSrc);
        return sb.toString();
    }

    static boolean due(long now, int every) {
        return every > 0 && (now / 60_000L) % every == 0;
    }

    public static synchronized void maybeDump(long now, String[] syms, float[][] x, float[] raw, Map<String, Long> oiRef,
                                              long oiHour, long oiLoadedMs, String oiSrc) {
        if (disabled || !due(now, EVERY) || syms == null || x == null || raw == null) return;
        try {
            long hour = now / 3_600_000L;
            if (w == null || hour != fileHour || bytes > MAX_BYTES) open(now, hour);
            for (int i = 0; i < syms.length && i < raw.length; i++) {
                String r = row(now, syms[i], x[i], -raw[i], oiRef == null ? null : oiRef.get(syms[i]), oiHour, oiLoadedMs, oiSrc);
                w.println(r);
                bytes += r.length() + 1;
            }
            w.flush();
        } catch (Throwable t) {
            disabled = true;
            LOG.error("[S1-DUMP] loi ghi -> TAT dump (live khong anh huong): {}", t.toString());
            closeQuietly();
        }
    }

    private static void open(long now, long hour) throws Exception {
        closeQuietly();
        File d = new File(DIR);
        if (!d.exists() && !d.mkdirs()) throw new IllegalStateException("khong tao duoc thu muc " + DIR);
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd_HHmm");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        File out = new File(d, "s1_dump_" + f.format(new Date(now)) + ".csv.gz");
        w = new PrintWriter(new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(out), true),
                StandardCharsets.UTF_8));
        w.println(HEADER);
        fileHour = hour;
        bytes = HEADER.length() + 1;
        if (!hook) {
            hook = true;
            Runtime.getRuntime().addShutdownHook(new Thread(S1FeatDump::closeQuietlySync, "S1FeatDumpFinalize"));
        }
        LOG.info("[S1-DUMP] mo file {}", out.getPath());
    }

    private static synchronized void closeQuietlySync() {
        closeQuietly();
    }

    private static void closeQuietly() {
        if (w != null) {
            try {
                w.close();
            } catch (Throwable ignore) {
                // dong file dump that bai khong anh huong live
            }
            w = null;
        }
    }
}
