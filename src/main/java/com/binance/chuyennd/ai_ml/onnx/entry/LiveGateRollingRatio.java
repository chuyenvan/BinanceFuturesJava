package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.EntryGate;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

/**
 * GATE ROLLING "ĐỀU LỆNH" (GDV2) — nhánh LIVE. Mặc định TẮT (byte-identical HEAD).
 *
 * <p>Cùng lõi quantile {@link GateRatioBuffer} với {@link GateRollingRatio} (sim) ⇒ q_t và quyết định
 * pass <b>bit-identical</b> giữa sim và live với cùng chuỗi (ts, r) đầu vào (parity test).
 *
 * <p>Key (qua {@link Cfg}, prefix {@code LIVE_}): {@code LIVE_GATE_ROLLING_MODE=ratio} (bật),
 * {@code LIVE_GATE_ROLLING_PCT} (0..1), {@code LIVE_GATE_ROLLING_DAYS} (mặc định 90),
 * {@code LIVE_GATE_ROLLING_FILE} (mặc định {@code run/gate_ratio_live.bin}). Key vắng/pct ngoài (0,1)
 * ⇒ {@code isOn()=false} ⇒ live byte-identical HEAD.
 *
 * <p><b>Khác sim:</b>
 * <ul>
 *   <li><b>Persist</b> buffer `(ts, r)` ra file append-only (Snappy + CRC32, {@link GateRatioPersist})
 *       để sống qua restart {@code ThreadAutoRestartProgram} (JVM tự restart 4h/lần).</li>
 *   <li><b>Warm-up seed</b> từ dữ liệu quá khứ (p15 Aerospike {@code ai_pred_1m} + sp từ
 *       {@code storage/data/predictionSymbol/*}) — xem {@link #seedHistory} (sai khác khai rõ).</li>
 *   <li><b>Log</b> {@code [GATE-RATIO]} mỗi giờ (q_t, cỡ buffer, pass/eval trong giờ).</li>
 * </ul>
 */
public final class LiveGateRollingRatio {
    private static final Logger LOG = LoggerFactory.getLogger(LiveGateRollingRatio.class);

    private static final long DAY = 86_400_000L;
    private static final long HOUR = 3600_000L;
    private static final int FLUSH_BATCH = 4096;
    private static final String DEFAULT_FILE = "run/gate_ratio_live.bin";

    private static boolean inited = false;
    private static boolean on = false;
    private static float pct = 0f;
    private static int days = 90;
    private static String persistFile = DEFAULT_FILE;

    private static final GateRatioBuffer buffer = new GateRatioBuffer();
    private static boolean warnedBeforeFirst = false;

    // bộ đếm theo giờ (log mỗi giờ)
    private static long curHour = Long.MIN_VALUE;
    private static long hourEval = 0;
    private static long hourPass = 0;

    // pending batch cho persist (append-only)
    private static long[] pendingTs = new long[FLUSH_BATCH];
    private static float[] pendingR = new float[FLUSH_BATCH];
    private static int pendingCount = 0;
    private static boolean hookInstalled = false;

    private LiveGateRollingRatio() {
    }

    /** Đọc cấu hình + nạp persist + seed. Gọi MỘT lần lúc live initData(). */
    public static synchronized void init() {
        if (inited) return;
        inited = true;
        String mode = Cfg.get("LIVE_GATE_ROLLING_MODE");
        if (!"ratio".equalsIgnoreCase(mode == null ? "" : mode.trim())) {
            on = false;
            return;
        }
        String p = Cfg.get("LIVE_GATE_ROLLING_PCT");
        if (p == null || p.trim().isEmpty()) {
            LOG.warn("[GATE-RATIO] LIVE_GATE_ROLLING_MODE=ratio nhưng thiếu LIVE_GATE_ROLLING_PCT -> TAT");
            return;
        }
        pct = Float.parseFloat(p.trim());
        if (pct <= 0f || pct >= 1f) {
            LOG.warn("[GATE-RATIO] LIVE_GATE_ROLLING_PCT={} ngoài (0,1) -> TAT", pct);
            on = false;
            return;
        }
        String d = Cfg.get("LIVE_GATE_ROLLING_DAYS");
        if (d != null && !d.trim().isEmpty()) days = Integer.parseInt(d.trim());
        String f = Cfg.get("LIVE_GATE_ROLLING_FILE");
        if (f != null && !f.trim().isEmpty()) persistFile = f.trim();
        on = true;
        LOG.warn("*** [GATE-RATIO] LIVE BAT: mode=ratio pct={} window={}d file={} | warm-up 7d | "
                        + "quantile tren TY SO r (CAUSAL) ***",
                String.format("%.8f", pct), days, persistFile);
        loadPersistedAndSeed();
        installShutdownHook();
    }

    public static boolean isOn() {
        return on;
    }

    /** Đếm 1 candidate PREDICT đánh giá; đổi giờ thì log + reset bộ đếm giờ. No-op khi TẮT. */
    public static synchronized void noteCandidate(long ts) {
        if (!on) return;
        long h = (ts / HOUR) * HOUR;
        if (h != curHour) {
            if (curHour != Long.MIN_VALUE) logHour();
            curHour = h;
            hourEval = 0;
            hourPass = 0;
        }
        hourEval++;
    }

    /** Đếm 1 candidate PREDICT PASS. No-op khi TẮT. */
    public static synchronized void notePass(long ts) {
        if (!on) return;
        hourPass++;
    }

    /**
     * Nguồn thrBase cho nhánh PREDICT (sp != null) khi LIVE bật. Trả q_t (hoặc base nếu warm-up),
     * nạp (ts, r) vào buffer causal + persist.
     */
    public static synchronized float threshold(long ts, float p15, float sp) {
        float factor = Math.max(EntryGate.DYN_MIN, (sp / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
        float gs = EntryGate.GATE_REGIME_ADAPTIVE ? EntryGate.CURRENT_REGIME_SCALE : EntryGate.GATE_DYN_SCALE;
        float r = p15 / (factor * gs);
        float q = buffer.addAndQuery(ts, r, pct, days, Configs.MIN_MOMENTUM_15M);
        if (!warnedBeforeFirst && buffer.nBeforeFirst() > 0) {
            warnedBeforeFirst = true;
            LOG.warn("[GATE-RATIO] LIVE truy vấn TRƯỚC khi đủ 7 ngày dữ liệu (m={}) -> fallback base {}",
                    buffer.size(), Configs.MIN_MOMENTUM_15M);
        }
        appendRecord(ts, r);
        return q;
    }

    /** Lõi quantile (package-private cho parity test) — cùng {@link GateRatioBuffer}. */
    static float addAndQuery(long ts, float r) {
        return buffer.addAndQuery(ts, r, pct, days, Configs.MIN_MOMENTUM_15M);
    }

    /** Chỉ cho unit test: bật với pct/days, reset toàn bộ state (không đụng file persist thật). */
    static void configureForTest(float pctValue, int daysValue) {
        resetForTest();
        inited = true;
        on = true;
        pct = pctValue;
        days = daysValue;
    }

    /** Chỉ cho unit test: số mẫu r trong buffer live. */
    static int bufferSizeForTest() {
        return buffer.size();
    }

    /** Chỉ cho unit test: trả class về trạng thái chưa khởi tạo. */
    static void resetForTest() {
        inited = false;
        on = false;
        pct = 0f;
        days = 90;
        persistFile = DEFAULT_FILE;
        buffer.reset();
        warnedBeforeFirst = false;
        curHour = Long.MIN_VALUE;
        hourEval = hourPass = 0;
        pendingCount = 0;
    }

    // ============================================================
    // Persist (append-only) + seed
    // ============================================================

    private static void loadPersistedAndSeed() {
        long now = System.currentTimeMillis();
        long minTs = now - (long) days * DAY;
        GateRatioPersist.Records persisted = new GateRatioPersist.Records(new long[0], new float[0]);
        try {
            persisted = GateRatioPersist.load(persistFile, minTs);
        } catch (Exception e) {
            LOG.error("[GATE-RATIO] khong nap duoc persist {}: {} — se seed lai tu lich su",
                    persistFile, e.getMessage());
        }
        long persistedStart = persisted.ts.length > 0 ? persisted.ts[0] : now;
        boolean seeded = false;
        if (persistedStart > now - 7L * DAY) {
            // Persist < 7 ngày (hoặc rỗng) ⇒ seed khoảng TRƯỚC dữ liệu persist (best-effort).
            seeded = seedHistory(minTs, persistedStart);
        }
        buffer.bulkAdd(persisted.ts, persisted.r);
        // Compact CHỈ khi vừa seed (cold-start): ghi lại file gọn (seed + persist) để restart sau KHÔNG
        // phải seed lại. Steady-state (đủ dữ liệu) giữ APPEND-ONLY, không viết lại.
        if (seeded && buffer.size() > 0) {
            try {
                GateRatioPersist.writeFresh(persistFile, buffer.tsSnapshot(), buffer.rSnapshot());
            } catch (Exception e) {
                LOG.error("[GATE-RATIO] khong compact persist {}: {}", persistFile, e.getMessage());
            }
        }
        LOG.info("[GATE-RATIO] LIVE nạp buffer: size={} firstTs={} (warm-up={})",
                buffer.size(), buffer.firstTs() == Long.MIN_VALUE ? "-" : Utils.normalizeDateYYYYMMDDHHmm(buffer.firstTs()),
                buffer.firstTs() > now - 7L * DAY ? "chưa đủ 7d -> fallback base" : "armed");
    }

    /**
     * Warm-up seed (best-effort): tái tạo `r = p15 / (max(DYN_MIN, sp/SCORE_BASE*DYN_MULT) * gs)` cho
     * các tick selector trong [from, to), nạp vào buffer (ts tăng).
     *
     * <p><b>Nguồn:</b> p15 đọc từ Aerospike {@code ai_pred_1m} (do {@code saveAiPrediction1M} ghi);
     * sp (symbolPred = P(no-pump)) đọc từ {@code storage/data/predictionSymbol/yyyyMMdd/<ts>} (do
     * {@code predictAllCandidates} ghi mỗi tick selector).
     *
     * <p><b>Sai khác vs sim (khai rõ):</b> (1) KHÔNG tái tạo loại coin đang giữ (held-symbol bị skip ở
     * live; vị thế lịch sử không lưu đầy đủ) ⇒ seed có thể gồm/thiếu vài coin so tập ứng viên thật;
     * (2) tick thiếu p15/sp ⇒ bỏ qua tick; (3) sp = P(no-pump) Funding, đúng cho đường R4 (không C3).
     * Seed chỉ ảnh hưởng q_t KHỞI ĐẦU; live tự hiệu chỉnh khi tích lũy r thật.
     */
    private static boolean seedHistory(long from, long to) {
        int gridMin = Configs.LIVE_ENTRY_GRID_MIN > 0 ? Configs.LIVE_ENTRY_GRID_MIN : 15;
        int topK = Configs.SELECTOR_RANK_TOPK > 0 ? Configs.SELECTOR_RANK_TOPK : 16;
        List<Long> tsList = new ArrayList<>();
        List<Float> rList = new ArrayList<>();
        long t0 = (from / 60_000L) * 60_000L;
        int guard = 0;
        for (long t = t0; t < to && guard < 200_000; t += 60_000L, guard++) {
            if ((t / 60_000L) % gridMin != 0) continue;
            try {
                AiPredictionData p15 = DataManagerAerospikeFloatSim.getAiPredictionAtTime(t);
                if (p15 == null) continue;
                Map<String, Float> spMap = readSymbolPred(t);
                if (spMap == null || spMap.isEmpty()) continue;
                List<Map.Entry<String, Float>> sorted = new ArrayList<>(spMap.entrySet());
                sorted.sort(Map.Entry.comparingByValue());
                int n = Math.min(topK, sorted.size());
                float gs = EntryGate.GATE_REGIME_ADAPTIVE ? EntryGate.CURRENT_REGIME_SCALE : EntryGate.GATE_DYN_SCALE;
                for (int i = 0; i < n; i++) {
                    Float sp = sorted.get(i).getValue();
                    if (sp == null || Float.isNaN(sp)) continue;
                    float factor = Math.max(EntryGate.DYN_MIN, (sp / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
                    float r = p15.predReturn15M / (factor * gs);
                    tsList.add(t);
                    rList.add(r);
                }
            } catch (Exception e) {
                // best-effort: bỏ tick lỗi
            }
        }
        if (tsList.isEmpty()) {
            LOG.warn("[GATE-RATIO] seed lịch sử RỖNG (thiếu p15/sp?) -> dùng warm-up 7d (fallback base)");
            return false;
        }
        long[] ts = new long[tsList.size()];
        float[] r = new float[rList.size()];
        for (int i = 0; i < ts.length; i++) {
            ts[i] = tsList.get(i);
            r[i] = rList.get(i);
        }
        buffer.bulkAdd(ts, r);
        LOG.info("[GATE-RATIO] seed lịch sử: {} record ({}..{}) | nguồn p15=Aerospike ai_pred_1m, "
                        + "sp=predictionSymbol (P(no-pump)); sai khác vs sim: held-symbol + tick thiếu",
                ts.length,
                Utils.normalizeDateYYYYMMDDHHmm(ts[0]),
                Utils.normalizeDateYYYYMMDDHHmm(ts[ts.length - 1]));
        return true;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Float> readSymbolPred(long t) {
        String path = "storage/data/predictionSymbol/" + Utils.normalizeDateYYYYMMDD(t) + "/" + t;
        Object o = StorageSnappy.readObjectFromFile(path);
        if (o instanceof Map) {
            try {
                return (Map<String, Float>) o;
            } catch (Exception ignore) {
            }
        }
        return null;
    }

    private static void appendRecord(long ts, float r) {
        if (pendingCount == pendingTs.length) {
            pendingTs = Arrays.copyOf(pendingTs, pendingTs.length * 2);
            pendingR = Arrays.copyOf(pendingR, pendingR.length * 2);
        }
        pendingTs[pendingCount] = ts;
        pendingR[pendingCount] = r;
        pendingCount++;
        if (pendingCount >= FLUSH_BATCH) flush();
    }

    private static synchronized void flush() {
        if (pendingCount == 0) return;
        try {
            GateRatioPersist.append(persistFile,
                    Arrays.copyOf(pendingTs, pendingCount), Arrays.copyOf(pendingR, pendingCount));
            pendingCount = 0;
        } catch (Exception e) {
            LOG.error("[GATE-RATIO] khong ghi persist {}: {} — bo {} record pending (buffer RAM van giu)",
                    persistFile, e.getMessage(), pendingCount);
            pendingCount = 0;
        }
    }

    private static void logHour() {
        LOG.info("[GATE-RATIO] q_t={} buffer={} eval={} pass={}",
                String.format("%.6f", buffer.currentQ()), buffer.size(), hourEval, hourPass);
    }

    private static synchronized void installShutdownHook() {
        if (hookInstalled) return;
        hookInstalled = true;
        try {
            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                if (on) flush();
            }, "GateRatioPersistFlush"));
        } catch (Exception e) {
            LOG.warn("[GATE-RATIO] khong dang ky shutdown hook: {}", e.getMessage());
        }
    }
}
