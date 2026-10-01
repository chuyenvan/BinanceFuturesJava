package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.object.MarketDataObject;
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
 * <p><b>[EXPORT-FIX 2026-10-01] Sua bug "cat cut" (thieu gz trailer):</b> writer dung
 * {@code GZIPOutputStream(...,syncFlush=true)} + {@code flush()} moi dong => file LUON ket thuc bang
 * DEFLATE sync-flush block {@code 00 00 FF FF}, NHUNG trailer GZIP (CRC32+ISIZE) chi duoc ghi khi
 * {@code close()}. Truoc day {@code close()} CHI goi khi du REMAINING tick / cham 200 MB, KHONG co
 * shutdown hook => JVM restart giua chung => moi file thieu trailer. Nay: (1) dang ky shutdown hook
 * finalize (giong {@code LiveGateRollingRatio}); (2) Tuy chon xoay file theo phut qua key
 * {@code LIVE_FEAT_DUMP_ROTATE_MIN} (mac dinh 0 = TAT = hanh vi cu) de moi file luon duoc dong dung.
 *
 * <p><b>[EXPORT-FIX 2026-10-01] Them cot market 4/4 + selector cung tick:</b>
 * feat_dump duoc them 4 cot {@code rateDownAvg,rateUpAvg,rateDown15MAvg,rateUp15MAvg} (tu
 * {@link MarketDataObject}); va them 1 file {@code sel_dump_*.csv.gz} ghi
 * {@code ts,symbol,selectorScore,rank,gateValue,p15} de do selector/gate CUNG tick (khong can ONNX).
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
    private static final long ROTATE_MS; // [EXPORT-FIX] xoay file moi N phut; 0 => TAT (hanh vi cu)
    private static boolean disabled = false;
    private static long rowsWritten = 0;
    private static boolean hookInstalled = false;

    private static final GzSink mainSink = new GzSink("feat_dump");
    private static final GzSink selSink = new GzSink("sel_dump");

    static {
        int n = 0;
        try {
            n = Integer.parseInt(Cfg.getOr("LIVE_FEAT_DUMP", "0").trim());
        } catch (Exception e) {
            n = 0;
        }
        REMAINING = n;
        long rot = 0;
        try {
            rot = (long) (Double.parseDouble(Cfg.getOr("LIVE_FEAT_DUMP_ROTATE_MIN", "0").trim()) * 60_000L);
        } catch (Exception e) {
            rot = 0;
        }
        ROTATE_MS = rot < 0 ? 0 : rot;
        if (REMAINING > 0) {
            installShutdownHook();
            LOG.warn("🟠 [LIVE_FEAT_DUMP] BAT — se ghi toi da {} tick vao {}/*.csv.gz (tran {} MB, xoay={} phut). "
                    + "Chi ghi, khong doi logic.", REMAINING, DIR, MAX_BYTES / (1024 * 1024),
                    ROTATE_MS / 60_000L);
        }
    }

    private LiveFeatureDump() {
    }

    /** [EXPORT-FIX] dang ky 1 lan: dong + finalize writer khi JVM dung (tranh file thieu gz trailer). */
    private static synchronized void installShutdownHook() {
        if (hookInstalled) return;
        hookInstalled = true;
        try {
            Runtime.getRuntime().addShutdownHook(new Thread(new Runnable() {
                @Override
                public void run() {
                    finalizeOnShutdown();
                }
            }, "LiveFeatureDumpFinalize"));
        } catch (Throwable t) {
            LOG.warn("🟠 [LIVE_FEAT_DUMP] khong dang ky duoc shutdown hook (van chay binh thuong): {}", t.toString());
        }
    }

    private static synchronized void finalizeOnShutdown() {
        disabled = true;
        try {
            mainSink.close();
        } catch (Throwable ignore) {
        }
        try {
            selSink.close();
        } catch (Throwable ignore) {
        }
    }

    /**
     * Ghi 1 dong feature cua tick hien tai. KHONG khai key (hoac &lt;=0) => return ngay (y nguyen).
     * Moi loi IO deu bi nuot + tat dump: KHONG the anh huong duong LIVE.
     */
    public static synchronized void maybeDump(long timestamp, String symbol,
                                              MarketFeatures f, float p15Out) {
        maybeDump(timestamp, symbol, f, p15Out, null);
    }

    /** [EXPORT-FIX] them 4 cot market (rateDownAvg/rateUpAvg/rateDown15MAvg/rateUp15MAvg). */
    public static synchronized void maybeDump(long timestamp, String symbol,
                                              MarketFeatures f, float p15Out, MarketDataObject marketRate) {
        if (REMAINING <= 0 || disabled || f == null) return;
        try {
            if (mainSink.writer == null) openMain(timestamp);
            if (mainSink.writer == null) return;

            StringBuilder sb = new StringBuilder(256);
            sb.append(timestamp).append(',').append(symbol == null ? "BTCUSDT" : symbol);
            double[] v = values(f);
            for (double d : v) sb.append(',').append(String.format(Locale.ROOT, "%.9g", d));
            sb.append(',').append(String.format(Locale.ROOT, "%.9g", p15Out));
            // [EXPORT-FIX] 4 field market: rateDownAvg/rateUpAvg/rateDown15MAvg tu MarketDataObject;
            // rateUp15MAvg KHONG duoc tinh trong pipeline (MarketDataObject/calMarketData chi 3 field)
            // => 0, khop DEV store (market.bin cung chi 3 float).
            sb.append(',').append(fmt(marketRate == null ? 0f : marketRate.rateDownAvg));
            sb.append(',').append(fmt(marketRate == null ? 0f : marketRate.rateUpAvg));
            sb.append(',').append(fmt(marketRate == null ? 0f : marketRate.rateDown15MAvg));
            sb.append(',').append(fmt(0f));
            mainSink.write(sb.toString());
            rowsWritten++;
            if (rowsWritten >= REMAINING) {
                LOG.warn("🟠 [LIVE_FEAT_DUMP] DU TICK ({} dong, {} MB) -> DONG file {}.", rowsWritten,
                        mainSink.bytes() / (1024 * 1024), mainSink.name());
                disabled = true;
                finalizeOnShutdown();
            } else if (mainSink.bytes() >= MAX_BYTES) {
                LOG.warn("🟠 [LIVE_FEAT_DUMP] CHAM TRAN {} MB ({} dong) -> DUNG ghi, dong file {}.",
                        MAX_BYTES / (1024 * 1024), rowsWritten, mainSink.name());
                disabled = true;
                finalizeOnShutdown();
            } else if (rotateDue(timestamp)) {
                LOG.warn("🟠 [LIVE_FEAT_DUMP] XOAY file theo {} phut -> dong {} + {}", ROTATE_MS / 60_000L,
                        mainSink.name(), selSink.name());
                mainSink.close();
                selSink.close();
            }
        } catch (Throwable t) {
            disabled = true;
            LOG.error("🟠 [LIVE_FEAT_DUMP] loi IO -> TAT dump (khong anh huong live): {}", t.toString());
            try {
                finalizeOnShutdown();
            } catch (Exception ignore) {
            }
        }
    }

    /**
     * [EXPORT-FIX] Ghi 1 dong selector cung tick: {@code ts,symbol,selectorScore,rank,gateValue,p15}.
     * rank = thu tu 1-based trong pool selector cua tick (thap = tot). gateValue = gia tri cong entry
     * (symbolPred); p15 = predictData.return15M cua tick. Cung cong tac gate (REMAINING/disabled).
     */
    public static synchronized void maybeDumpSelector(long timestamp, String symbol,
                                                      float selectorScore, int rank,
                                                      float gateValue, float p15) {
        if (REMAINING <= 0 || disabled || symbol == null) return;
        try {
            if (selSink.writer == null) openSel(timestamp);
            if (selSink.writer == null) return;
            StringBuilder sb = new StringBuilder(96);
            sb.append(timestamp).append(',').append(symbol);
            sb.append(',').append(String.format(Locale.ROOT, "%.9g", selectorScore));
            sb.append(',').append(rank);
            sb.append(',').append(String.format(Locale.ROOT, "%.9g", gateValue));
            sb.append(',').append(String.format(Locale.ROOT, "%.9g", p15));
            selSink.write(sb.toString());
        } catch (Throwable t) {
            LOG.error("🟠 [LIVE_FEAT_DUMP] loi IO sel_dump (tat sel dump): {}", t.toString());
            try {
                selSink.close();
            } catch (Exception ignore) {
            }
        }
    }

    private static boolean rotateDue(long timestamp) {
        return ROTATE_MS > 0 && mainSink.openTs > 0 && (timestamp - mainSink.openTs) >= ROTATE_MS;
    }

    /** Mo file feat_dump moi + ghi header (1 lan). */
    private static void openMain(long timestamp) throws Exception {
        StringBuilder h = new StringBuilder("ts,symbol");
        for (String n : FEATURE_NAMES) h.append(',').append(n);
        h.append(",p15_out,rateDownAvg,rateUpAvg,rateDown15MAvg,rateUp15MAvg");
        mainSink.open(timestamp, h.toString());
        if (mainSink.writer != null) {
            LOG.warn("🟠 [LIVE_FEAT_DUMP] mo file {} ({} feature + ts/symbol/p15_out + 4 market).",
                    mainSink.path(), FEATURE_NAMES.length);
        }
    }

    /** Mo file sel_dump moi + ghi header (1 lan). */
    private static void openSel(long timestamp) throws Exception {
        selSink.open(timestamp, "ts,symbol,selectorScore,rank,gateValue,p15");
        if (selSink.writer != null) {
            LOG.warn("🟠 [LIVE_FEAT_DUMP] mo file {} (selector cung tick).", selSink.path());
        }
    }

    private static String fmt(float v) {
        return String.format(Locale.ROOT, "%.9g", v);
    }

    /** [EXPORT-FIX] 1 writer csv.gz + counter byte; tai dung cho ca feat_dump lan sel_dump. */
    private static final class GzSink {
        private final String prefix;
        File file = null;
        Counting counter = null;
        BufferedWriter writer = null;
        long openTs = 0;

        GzSink(String prefix) {
            this.prefix = prefix;
        }

        void open(long timestamp, String header) throws Exception {
            File dir = new File(DIR);
            if (!dir.exists() && !dir.mkdirs()) {
                throw new java.io.IOException("khong tao duoc thu muc " + DIR);
            }
            String ts = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.ROOT).format(new Date(timestamp));
            file = new File(dir, prefix + "_" + ts + ".csv.gz");
            // syncFlush=true => moi writer.flush() day 1 block xuong file: file doc duoc NGAY khi dang chay.
            counter = new Counting(new FileOutputStream(file));
            writer = new BufferedWriter(new OutputStreamWriter(
                    new GZIPOutputStream(counter, 16384, true), StandardCharsets.UTF_8));
            writer.write(header);
            writer.write('\n');
            writer.flush();
            openTs = timestamp;
        }

        void write(String line) throws Exception {
            writer.write(line);
            writer.write('\n');
            writer.flush();
        }

        long bytes() {
            return counter == null ? 0 : counter.count();
        }

        String name() {
            return file == null ? "?" : file.getName();
        }

        String path() {
            return file == null ? "?" : file.getPath();
        }

        void close() throws Exception {
            try {
                if (writer != null) writer.close();
            } finally {
                writer = null;
                counter = null;
                openTs = 0;
            }
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
