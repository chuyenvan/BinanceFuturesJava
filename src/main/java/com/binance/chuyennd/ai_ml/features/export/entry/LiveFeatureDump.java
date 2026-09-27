package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.zip.GZIPOutputStream;

/**
 * INSTRUMENT dev-side (MAC DINH TAT) — ghi vector 33 feature cua duong LIVE ra 1 file csv.gz
 * de doi chieu (offline) voi export DEV (vd {@code claudedata/gate15m_v2_full.csv}).
 *
 * <p><b>Bat/tat:</b> key {@code LIVE_FEAT_DUMP} (int = SO TICK ghi). KHONG khai hoac {@code <=0}
 * => {@link #maybeDump} return NGAY, khong tao file, khong doi bat ky hanh vi nao khac.
 * Vi {@code LIVE_} la trading-prefix trong {@link Cfg}, khi co {@code TRADING_PROFILE} thi key phai
 * khai trong profile; khong co profile (vd shadow chay bang env.sh) thi doc tu env nhu cu.
 *
 * <p><b>Tran cung dung luong: 200 MB (file nen).</b> Cham tran => tu dong ghi them dong cuoi roi DONG file.
 * Ngoai ra con tran so tick = gia tri key. Chi ghi, KHONG doc/sua logic, KHONG anh huong gate/ONNX.
 *
 * <p><b>Thu tu 33 feature</b> PHAI mirror {@code OnnxInferenceManager.extractFeaturesV3Full}
 * (src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/OnnxInferenceManager.java:67-80) vi model
 * an input theo DUNG thu tu nay. Header co TEN tung cot => tool doi chieu align theo TEN, khong theo vi tri.
 */
public final class LiveFeatureDump {

    private static final Logger LOG = LoggerFactory.getLogger(LiveFeatureDump.class);

    /** Thu tu V3FULL — COPY tu OnnxInferenceManager.extractFeaturesV3Full:67-80 (nguon su that). */
    private static final String[] FEATURE_NAMES = new String[]{
            "momentum1M", "momentum5M", "momentum15M", "momentum1H",
            "momentum4H", "momentum24H", "momentumAcceleration",
            "trendStrengthETH", "trendConsistency",
            "volatility1M", "volatility15M", "volatility1H",
            "volatility24H", "volatilityTermStructure",
            "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown",
            "marketBreadthStrength", "btcDominance",
            "rsi14", "volumeSpike", "distMA20",
            "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
            "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
            "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike"
    };

    private static final long MAX_BYTES = 200L * 1024L * 1024L; // tran cung 200 MB (file nen)
    private static final String DIR = "feat_dump";

    private static final int REMAINING; // so tick con lai; <=0 => TAT hoan toan
    private static boolean disabled = false;
    private static long bytesWritten = 0;
    private static long rowsWritten = 0;
    private static File outFile = null;
    private static Counting counter = null;
    private static BufferedWriter writer = null;

    static {
        int n = 0;
        try {
            n = Integer.parseInt(Cfg.getOr("LIVE_FEAT_DUMP", "0").trim());
        } catch (Exception e) {
            n = 0;
        }
        REMAINING = n;
        if (REMAINING > 0) {
            LOG.warn("🟠 [LIVE_FEAT_DUMP] BAT — se ghi toi da {} tick vao {}/*.csv.gz (tran {} MB). "
                    + "Chi ghi, khong doi logic.", REMAINING, DIR, MAX_BYTES / (1024 * 1024));
        }
    }

    private LiveFeatureDump() {
    }

    /**
     * Ghi 1 dong feature cua tick hien tai. KHONG khai key (hoac &lt;=0) => return ngay (y nguyen).
     * Moi loi IO deu bi nuot + tat dump: KHONG the anh huong duong LIVE.
     */
    public static synchronized void maybeDump(long timestamp, String symbol,
                                              MarketFeatures f, float p15Out) {
        if (REMAINING <= 0 || disabled || f == null) return;
        try {
            if (writer == null) open(timestamp, p15Out);
            if (writer == null) return;

            StringBuilder sb = new StringBuilder(256);
            sb.append(timestamp).append(',').append(symbol == null ? "BTCUSDT" : symbol);
            double[] v = values(f);
            for (double d : v) sb.append(',').append(String.format(Locale.ROOT, "%.9g", d));
            sb.append(',').append(String.format(Locale.ROOT, "%.9g", p15Out));
            writer.write(sb.toString());
            writer.write('\n');
            writer.flush();
            rowsWritten++;
            // Dem BYTE THUC GHI ra file (gzip buffer nen file.length() bao THIEU => tran se khong bao gio cham).
            bytesWritten = counter == null ? 0 : counter.count();
            if (rowsWritten >= REMAINING) {
                LOG.warn("🟠 [LIVE_FEAT_DUMP] DU TICK ({} dong, {} MB) -> DONG file {}.", rowsWritten,
                        bytesWritten / (1024 * 1024), outFile.getName());
                disabled = true;
                close();
            } else if (bytesWritten >= MAX_BYTES) {
                LOG.warn("🟠 [LIVE_FEAT_DUMP] CHAM TRAN {} MB ({} dong) -> DUNG ghi, dong file {}.",
                        MAX_BYTES / (1024 * 1024), rowsWritten, outFile.getName());
                disabled = true;
                close();
            }
        } catch (Throwable t) {
            disabled = true;
            LOG.error("🟠 [LIVE_FEAT_DUMP] loi IO -> TAT dump (khong anh huong live): {}", t.toString());
            try {
                close();
            } catch (Exception ignore) {
            }
        }
    }

    /** Mo file moi + ghi header (1 lan). */
    private static void open(long timestamp, float p15Out) throws Exception {
        File dir = new File(DIR);
        if (!dir.exists() && !dir.mkdirs()) {
            disabled = true;
            LOG.error("🟠 [LIVE_FEAT_DUMP] khong tao duoc thu muc {} -> TAT dump.", DIR);
            return;
        }
        String ts = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.ROOT).format(new Date(timestamp));
        outFile = new File(dir, "feat_dump_" + ts + ".csv.gz");
        // syncFlush=true => moi writer.flush() day 1 block xuong file: file doc duoc NGAY khi dang chay.
        counter = new Counting(new FileOutputStream(outFile));
        writer = new BufferedWriter(new OutputStreamWriter(
                new GZIPOutputStream(counter, 16384, true), StandardCharsets.UTF_8));
        StringBuilder h = new StringBuilder("ts,symbol");
        for (String n : FEATURE_NAMES) h.append(',').append(n);
        h.append(",p15_out");
        writer.write(h.toString());
        writer.write('\n');
        writer.flush();
        bytesWritten = counter.count();
        LOG.warn("🟠 [LIVE_FEAT_DUMP] mo file {} ({} feature + ts/symbol/p15_out).", outFile.getPath(),
                FEATURE_NAMES.length);
    }

    private static void close() throws Exception {
        try {
            if (writer != null) writer.close();
        } finally {
            writer = null;
            counter = null;
        }
    }

    /** Dem BYTE thuc su ghi ra file (khong them dependency). */
    private static final class Counting extends java.io.FilterOutputStream {
        private long count;

        Counting(java.io.OutputStream out) {
            super(out);
        }

        @Override
        public void write(int b) throws java.io.IOException {
            out.write(b);
            count++;
        }

        @Override
        public void write(byte[] b, int off, int len) throws java.io.IOException {
            out.write(b, off, len);
            count += len;
        }

        long count() {
            return count;
        }
    }

    /** 33 gia tri THEO DUNG THU TU V3FULL. */
    private static double[] values(MarketFeatures f) {
        return new double[]{
                f.momentum1M, f.momentum5M, f.momentum15M, f.momentum1H,
                f.momentum4H, f.momentum24H, f.momentumAcceleration,
                f.trendStrengthETH, f.trendConsistency,
                f.volatility1M, f.volatility15M, f.volatility1H,
                f.volatility24H, f.volatilityTermStructure,
                f.advanceDeclineRatio, f.percentAboveMA20, f.volumeRatioUpDown,
                f.marketBreadthStrength, f.btcDominance,
                f.rsi14, f.volumeSpike, f.distMA20,
                f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend,
                f.hourOfDay, f.dayOfWeek, f.weekOfMonth, f.monthOfYear,
                f.basketMomentum15M, f.basketMomentum1H, f.basketRsi14, f.basketVolSpike
        };
    }

    /** Ten 33 feature theo dung thu tu model an — dung cho test/tool. */
    public static String[] featureNames() {
        return FEATURE_NAMES.clone();
    }
}
