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

import java.io.File;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;
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
    private static final String SYMBOL_PRED_DIR = "storage/data/predictionSymbol";

    private static boolean inited = false;
    private static boolean on = false;
    private static float pct = 0f;
    private static int days = 90;
    private static String persistFile = DEFAULT_FILE;

    private static final GateRatioBuffer buffer = new GateRatioBuffer();
    private static boolean warnedBeforeFirst = false;
    /** [FAIL-CLOSED audD 2026-10-23] so lan r/q khong huu han (REJECT). */
    static long nonFinite = 0;

    // bộ đếm theo giờ (log mỗi giờ)
    private static long curHour = Long.MIN_VALUE;
    private static long hourEval = 0;
    private static long hourPass = 0;

    // pending batch cho persist (append-only)
    private static long[] pendingTs = new long[FLUSH_BATCH];
    private static float[] pendingR = new float[FLUSH_BATCH];
    private static int pendingCount = 0;
    private static boolean hookInstalled = false;
    private static int seedCalls = 0;   // số lần seedHistory chạy (chỉ để unit test kiểm)

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
        long now0 = System.currentTimeMillis();
        initSeedBranch(Cfg.get(KEY_SEED), Cfg.get(KEY_SEED_MD5), parseLagHours(Cfg.get(KEY_SEED_MAX_LAG_H)), now0);
        installShutdownHook();
    }

    /**
     * [V12 R4j A1 MAJ-2] KHONG BAO GIO System.exit vi seed (JVM nay quan ly lenh/stop that). Seed vang => nhu cu. Seed co:
     * {@link #applySeedFile} (lan dau ap seed; lan sau persist THANG, bo qua seed + WARN). Seed hong o lan dau (chua co buffer
     * seed) => CHAN VAO LENH MOI ({@link #isSeedBlocked}: AIRejectFilter.entryGate REJECT moi leg), Telegram KHAN, van nap persist
     * va VAN quan ly vi the/stop. Tra true = dang chan.
     */
    static boolean initSeedBranch(String seedPath, String md5, int lagH, long now) {
        seedBlocked = false;
        if (seedPath == null || seedPath.trim().isEmpty()) {
            loadPersistedAndSeed(now);
            return false;
        }
        String problem = applySeedFile(seedPath.trim(), md5, lagH, now);
        if (problem != null) {
            seedBlocked = true;
            String m = "[GATE-SEED] KHAN: seed " + seedPath.trim() + " HONG (" + problem + ") — CHAN VAO LENH MOI, VAN quan ly vi the/stop;"
                    + " sua seed (md5/dinh dang/khoang) hoac go " + KEY_SEED + " roi restart";
            LOG.error("⛔ {}", m);
            try {
                seedAlert.accept(m);
            } catch (Throwable t) {
                LOG.warn("[GATE-SEED] alert loi: {}", t.toString());
            }
            loadPersistedAndSeed(now);
        }
        return seedBlocked;
    }

    private static volatile boolean seedBlocked = false;

    /** [V12 R4j] seed hong o lan dau => chan vao lenh moi (moi leg qua AIRejectFilter.entryGate bi REJECT). */
    public static boolean isSeedBlocked() {
        return seedBlocked;
    }

    /** Telegram KHAN (prod tren thread rieng); test thay. */
    static volatile java.util.function.Consumer<String> seedAlert = m -> {
        Thread t = new Thread(() -> {
            try {
                com.binance.chuyennd.utils.Utils.sendSms2Telegram(m);
            } catch (Throwable e) {
                LOG.warn("[GATE-SEED] gui Telegram loi: {}", e.toString());
            }
        }, "GATE-SEED-ALERT");
        t.setDaemon(true);
        t.start();
    };

    /** File danh dau "persist da nap seed" (canh persist). Co => persist THANG o moi lan khoi dong sau. */
    static File seedMarker() {
        return new File(persistFile + ".seeded");
    }

    // ============================================================ [V12 R4h] seed buffer 90 ngay dung san
    /** Duong dan file seed (cung dinh dang {@link GateRatioPersist}, vd gate_ratio_live.bin). Vang = TAT (mac dinh). */
    public static final String KEY_SEED = "GATE_BUFFER_SEED";
    /** md5 hex BAT BUOC cua file seed (khong khai / khac => fail-fast). */
    public static final String KEY_SEED_MD5 = "GATE_BUFFER_SEED_MD5";
    /** Ban ghi cuoi cua seed phai >= now - N gio (mac dinh 24). */
    public static final String KEY_SEED_MAX_LAG_H = "GATE_BUFFER_SEED_MAX_LAG_H";
    static final int DEFAULT_SEED_MAX_LAG_H = 24;

    static int parseLagHours(String raw) {
        if (raw == null || raw.trim().isEmpty()) return DEFAULT_SEED_MAX_LAG_H;
        try {
            int v = Integer.parseInt(raw.trim());
            return v > 0 && v <= 24 * 30 ? v : DEFAULT_SEED_MAX_LAG_H;
        } catch (NumberFormatException e) {
            return DEFAULT_SEED_MAX_LAG_H;
        }
    }

    static String md5Hex(File f) throws java.io.IOException {
        try {
            java.security.MessageDigest md = java.security.MessageDigest.getInstance("MD5");
            try (java.io.InputStream in = new java.io.FileInputStream(f)) {
                byte[] b = new byte[1 << 16];
                int n;
                while ((n = in.read(b)) > 0) md.update(b, 0, n);
            }
            StringBuilder sb = new StringBuilder();
            for (byte x : md.digest()) sb.append(String.format("%02x", x));
            return sb.toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new java.io.IOException(e);
        }
    }

    /**
     * Kiem file seed (THUAN, khong dung buffer): ton tai, md5 khop, dinh dang doc sach (0 chunk hong), ts tang dan, r huu han,
     * phu cua so (ban ghi dau &lt;= now - (days-1) ngay), khong o tuong lai (&lt;= now + 60 s), khong qua cu (cuoi &gt;= now - lag).
     * Tra null = dat; nguoc lai = ly do (log ro).
     */
    static String checkSeed(File f, String expectedMd5, GateRatioPersist.Records rec, long now, int daysWin, int maxLagH) {
        if (expectedMd5 == null || !expectedMd5.trim().matches("[0-9a-fA-F]{32}")) {
            return KEY_SEED_MD5 + " thieu/khong phai md5 hex 32 ky tu";
        }
        if (f == null || !f.isFile()) return "khong thay file seed";
        String got;
        try {
            got = md5Hex(f);
        } catch (java.io.IOException e) {
            return "doc file seed loi " + e.getMessage();
        }
        if (!got.equalsIgnoreCase(expectedMd5.trim())) return "md5 seed " + got + " != " + expectedMd5.trim();
        if (rec == null) return "khong doc duoc dinh dang seed (GateRatioPersist)";
        if (rec.droppedChunks > 0) return "seed co " + rec.droppedChunks + " chunk hong (" + rec.droppedBytes + " byte)";
        int n = rec.ts.length;
        if (n == 0) return "seed rong";
        for (int i = 0; i < n; i++) {
            if (i > 0 && rec.ts[i] < rec.ts[i - 1]) return "seed khong tang dan theo ts tai ban ghi " + i;
            if (!Float.isFinite(rec.r[i])) return "seed co r khong huu han tai ban ghi " + i;
        }
        long first = rec.ts[0], last = rec.ts[n - 1];
        if (first > now - (long) (daysWin - 1) * DAY) {
            return "seed khong phu cua so " + daysWin + "d: ban ghi dau " + Utils.normalizeDateYYYYMMDDHHmm(first);
        }
        if (last > now + 60_000L) return "seed co ban ghi o tuong lai " + Utils.normalizeDateYYYYMMDDHHmm(last);
        if (last < now - (long) maxLagH * HOUR) {
            return "seed qua cu: ban ghi cuoi " + Utils.normalizeDateYYYYMMDDHHmm(last) + " < now - " + maxLagH + "h";
        }
        return null;
    }

    /**
     * Nap seed: buffer = seed (ts &gt;= now - days) + persist co ts &gt; ban ghi cuoi cua seed (r live tich luy SAU seed).
     * Bo qua seed tu Aerospike. Persist khac (seed+sau) => sao luu {@code <file>.preseed_<ts>} roi viet lai file gon (lan restart
     * sau idempotent: phan &lt;= cuoi seed trung seed => khong viet lai). Tra null = OK; khac = ly do fail-fast.
     */
    static String applySeedFile(String path, String expectedMd5, int maxLagH, long now) {
        File marker = seedMarker();
        if (marker.isFile()) {
            // [V12 R4j A1 MAJ-2] restart/reboot/watchdog (env van con seed): persist THANG, KHONG kiem lag, KHONG fail
            String prev = "?";
            try {
                prev = new String(Files.readAllBytes(marker.toPath()), java.nio.charset.StandardCharsets.UTF_8).trim();
            } catch (Exception ignore) {
                prev = "?";
            }
            LOG.warn("[GATE-SEED] persist da nap seed truoc do ({}) => BO QUA seed {} (persist thang), chay tiep", prev, path);
            loadPersistedAndSeed(now);
            return null;
        }
        File f = new File(path);
        GateRatioPersist.Records rec = null;
        if (f.isFile()) {
            try {
                rec = GateRatioPersist.load(path, Long.MIN_VALUE);
            } catch (Exception e) {
                return "doc seed loi " + e.getMessage();
            }
        }
        String problem = checkSeed(f, expectedMd5, rec, now, days, maxLagH);
        if (problem != null) return problem;
        long minTs = now - (long) days * DAY;
        long seedLast = rec.ts[rec.ts.length - 1];
        GateRatioPersist.Records persisted = new GateRatioPersist.Records(new long[0], new float[0]);
        try {
            persisted = GateRatioPersist.load(persistFile, minTs);
        } catch (Exception e) {
            LOG.warn("[GATE-SEED] khong nap duoc persist {}: {} — chi dung seed", persistFile, e.getMessage());
        }
        int nSeed = 0;
        for (long t : rec.ts) if (t >= minTs) nSeed++;
        long[] mts = new long[nSeed];
        float[] mr = new float[nSeed];
        int k = 0;
        for (int i = 0; i < rec.ts.length; i++) {
            if (rec.ts[i] >= minTs) {
                mts[k] = rec.ts[i];
                mr[k] = rec.r[i];
                k++;
            }
        }
        int nPre = 0, nAfter = 0;
        for (long t : persisted.ts) {
            if (t > seedLast) nAfter++;
            else nPre++;
        }
        long[] ats = new long[nAfter];
        float[] ar = new float[nAfter];
        int j = 0;
        boolean persistSameAsSeed = persisted.droppedChunks == 0 && nPre == nSeed;
        int pi = 0;
        for (int i = 0; i < persisted.ts.length; i++) {
            if (persisted.ts[i] > seedLast) {
                ats[j] = persisted.ts[i];
                ar[j] = persisted.r[i];
                j++;
            } else if (persistSameAsSeed) {
                if (pi >= nSeed || persisted.ts[i] != mts[pi]
                        || Float.floatToIntBits(persisted.r[i]) != Float.floatToIntBits(mr[pi])) {
                    persistSameAsSeed = false;
                }
                pi++;
            }
        }
        buffer.reset();
        buffer.bulkAdd(mts, mr);
        buffer.bulkAdd(ats, ar);
        LOG.warn("*** [GATE-SEED] nap seed {} md5={} n={} [{} .. {}] + persist sau seed {} (bo {} ban ghi persist <= cuoi seed)"
                        + " => buffer {} ***", path, expectedMd5.trim(), nSeed, Utils.normalizeDateYYYYMMDDHHmm(mts.length > 0 ? mts[0] : seedLast),
                Utils.normalizeDateYYYYMMDDHHmm(seedLast), nAfter, nPre, buffer.size());
        if (!persistSameAsSeed) {
            File pf = new File(persistFile);
            if (pf.exists()) {
                File bak = new File(persistFile + ".preseed_" + new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date(now)));
                try {
                    Files.copy(pf.toPath(), bak.toPath(), StandardCopyOption.COPY_ATTRIBUTES);
                    LOG.warn("[GATE-SEED] sao luu persist cu -> {}", bak.getPath());
                } catch (Exception e) {
                    return "khong sao luu duoc persist cu " + persistFile + " -> " + bak.getPath() + ": " + e.getMessage();
                }
            }
            try {
                GateRatioPersist.writeFresh(persistFile, buffer.tsSnapshot(), buffer.rSnapshot());
            } catch (Exception e) {
                return "khong viet duoc persist moi " + persistFile + ": " + e.getMessage();
            }
        }
        try {   // [V12 R4j] danh dau: lan khoi dong sau persist thang
            Files.write(marker.toPath(), ("md5=" + expectedMd5.trim() + " seedLast=" + seedLast + " appliedAt=" + now + "\n")
                    .getBytes(java.nio.charset.StandardCharsets.UTF_8));
        } catch (Exception e) {
            LOG.warn("[GATE-SEED] khong ghi duoc file danh dau {}: {} — restart sau se ap lai seed", marker.getPath(), e.getMessage());
        }
        return null;
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
        // [FAIL-CLOSED audD 2026-10-23] r NaN/inf KHONG duoc vao buffer (quickselect voi NaN cho q sai/NaN, cache
        //   ca gio + persist qua restart). Tra NaN => AIRejectFilter.evaluate REJECT.
        if (!Float.isFinite(r)) {
            if (nonFinite++ % 1000 == 0) {
                LOG.warn("[GATE-RATIO] FAIL-CLOSED r khong huu han (p15={} sp={} factor={} gs={}) -> REJECT, khong nap (n={})",
                        p15, sp, factor, gs, nonFinite);
            }
            return Float.NaN;
        }
        float q = buffer.addAndQuery(ts, r, pct, days, Configs.MIN_MOMENTUM_15M);
        if (!warnedBeforeFirst && buffer.nBeforeFirst() > 0) {
            warnedBeforeFirst = true;
            LOG.warn("[GATE-RATIO] LIVE truy vấn TRƯỚC khi đủ 7 ngày dữ liệu (m={}) -> fallback base {}",
                    buffer.size(), Configs.MIN_MOMENTUM_15M);
        }
        appendRecord(ts, r);
        if (!Float.isFinite(q)) {
            if (nonFinite++ % 1000 == 0) {
                LOG.warn("[GATE-RATIO] FAIL-CLOSED q_t khong huu han ({}) size={} -> REJECT (n={})", q, buffer.size(), nonFinite);
            }
            return Float.NaN;
        }
        return q;
    }

    /**
     * [GKF-PHASE3 2026-10-07] docs/prereg/PREREG_GATE_K_FRONTIER.md §7 — như {@link #threshold} nhưng
     * KHÔNG nạp {@code (ts,r)} vào buffer (hạng &gt; {@code Configs.GATE_BUFFER_TOPK}). Cùng q_t nền.
     */
    public static synchronized float thresholdCheckOnly(long ts, float p15, float sp) {
        float factor = Math.max(EntryGate.DYN_MIN, (sp / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
        float gs = EntryGate.GATE_REGIME_ADAPTIVE ? EntryGate.CURRENT_REGIME_SCALE : EntryGate.GATE_DYN_SCALE;
        float r = p15 / (factor * gs);
        return buffer.queryOnly(ts, r, pct, days, Configs.MIN_MOMENTUM_15M);
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
        seedBlocked = false;
        buffer.reset();
        warnedBeforeFirst = false;
        curHour = Long.MIN_VALUE;
        hourEval = hourPass = 0;
        pendingCount = 0;
        seedCalls = 0;
    }

    /** Chỉ cho unit test: trỏ file persist sang đường dẫn tạm (không đụng file persist thật). */
    static void setPersistFileForTest(String path) {
        persistFile = path;
    }

    /** Chỉ cho unit test: số lần seedHistory đã chạy kể từ resetForTest. */
    static int seedCallsForTest() {
        return seedCalls;
    }

    // ============================================================
    // Persist (append-only) + seed
    // ============================================================

    /**
     * Nạp persist + seed (gọi từ {@link #init} với {@code now = System.currentTimeMillis()}; package-private
     * cho unit test với {@code now} giả).
     *
     * <p>[GATE-PERSIST-ROBUST 2026-10-12] Persist có chunk hỏng ({@code droppedChunks > 0}) ⇒ GIỮ các record
     * đọc được (KHÔNG seed lại toàn bộ chỉ vì có chunk hỏng — luật seed như cũ: chỉ khi
     * {@code persistedStart > now − 7d}); sao lưu file gốc sang {@code <file>.corrupt_<yyyyMMdd_HHmmss>}
     * (copy) rồi {@code writeFresh} buffer để file sạch. Sao lưu lỗi ⇒ KHÔNG ghi đè (giữ file gốc; lần nạp
     * sau vẫn resync được). Exception IO khác ⇒ hành vi cũ (seed lại từ lịch sử).
     */
    static void loadPersistedAndSeed(long now) {
        long minTs = now - (long) days * DAY;
        GateRatioPersist.Records persisted = new GateRatioPersist.Records(new long[0], new float[0]);
        try {
            persisted = GateRatioPersist.load(persistFile, minTs);
        } catch (Exception e) {
            LOG.error("[GATE-RATIO] khong nap duoc persist {}: {} — se seed lai tu lich su",
                    persistFile, e.getMessage());
        }
        boolean corrupt = persisted.droppedChunks > 0;
        if (corrupt) {
            LOG.error("[GATE-RATIO] persist hong: bo {} chunk ({} byte), giu {} record",
                    persisted.droppedChunks, persisted.droppedBytes, persisted.ts.length);
        }
        long persistedStart = persisted.ts.length > 0 ? persisted.ts[0] : now;
        boolean seeded = false;
        if (persistedStart > now - 7L * DAY) {
            // Persist < 7 ngày (hoặc rỗng) ⇒ seed khoảng TRƯỚC dữ liệu persist (best-effort).
            seeded = seedHistory(minTs, persistedStart);
        }
        buffer.bulkAdd(persisted.ts, persisted.r);
        // Compact khi vừa seed (cold-start): ghi lại file gọn (seed + persist) để restart sau KHÔNG phải seed
        // lại. Persist hỏng: ghi lại file sạch (sau khi sao lưu bản gốc). Steady-state giữ APPEND-ONLY.
        boolean rewrite = corrupt || (seeded && buffer.size() > 0);
        if (rewrite && corrupt && !backupCorruptFile(now)) {
            rewrite = false;
        }
        if (rewrite) {
            try {
                GateRatioPersist.writeFresh(persistFile, buffer.tsSnapshot(), buffer.rSnapshot());
                if (corrupt) {
                    LOG.warn("[GATE-RATIO] da viet lai persist sach {}: {} record", persistFile, buffer.size());
                }
            } catch (Exception e) {
                LOG.error("[GATE-RATIO] khong compact persist {}: {}", persistFile, e.getMessage());
            }
        }
        LOG.info("[GATE-RATIO] LIVE nạp buffer: size={} firstTs={} (warm-up={})",
                buffer.size(), buffer.firstTs() == Long.MIN_VALUE ? "-" : Utils.normalizeDateYYYYMMDDHHmm(buffer.firstTs()),
                buffer.firstTs() > now - 7L * DAY ? "chưa đủ 7d -> fallback base" : "armed");
    }

    /** Copy (không move) file persist gốc sang {@code <file>.corrupt_<yyyyMMdd_HHmmss>[_n]}. true nếu OK. */
    private static boolean backupCorruptFile(long now) {
        File src = new File(persistFile);
        if (!src.exists()) return true;
        String base = persistFile + ".corrupt_" + new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date(now));
        File dst = new File(base);
        for (int i = 1; dst.exists() && i < 1000; i++) {
            dst = new File(base + "_" + i);
        }
        try {
            Files.copy(src.toPath(), dst.toPath(), StandardCopyOption.COPY_ATTRIBUTES);
            LOG.warn("[GATE-RATIO] da sao luu persist hong -> {}", dst.getPath());
            return true;
        } catch (Exception e) {
            LOG.error("[GATE-RATIO] khong sao luu duoc persist hong {} -> {}: {} — KHONG viet lai file",
                    persistFile, dst.getPath(), e.getMessage());
            return false;
        }
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
     *
     * <p>[GATE-PERSIST-ROBUST 2026-10-12] Đọc sp (file local, rẻ) TRƯỚC p15 (Aerospike) và bỏ qua cả ngày
     * không có thư mục {@code predictionSymbol/<yyyyMMdd>} ⇒ không gọi Aerospike cho tick chắc chắn bị bỏ.
     * Tập record seed giống hệt bản cũ (tick thiếu sp/p15 vốn đã bị bỏ).
     */
    private static boolean seedHistory(long from, long to) {
        seedCalls++;
        int gridMin = Configs.LIVE_ENTRY_GRID_MIN > 0 ? Configs.LIVE_ENTRY_GRID_MIN : 15;
        int topK = Configs.SELECTOR_RANK_TOPK > 0 ? Configs.SELECTOR_RANK_TOPK : 16;
        long t0ms = System.currentTimeMillis();
        SeedResult res = collectSeed(from, to, gridMin, topK, new SeedSource() {
            @Override
            public boolean dayDirExists(String yyyyMMdd) {
                return new File(SYMBOL_PRED_DIR + "/" + yyyyMMdd).isDirectory();
            }

            @Override
            public Map<String, Float> symbolPred(long t) {
                return readSymbolPred(t);
            }

            @Override
            public AiPredictionData p15(long t) {
                return DataManagerAerospikeFloatSim.getAiPredictionAtTime(t);
            }
        });
        long elapsed = System.currentTimeMillis() - t0ms;
        LOG.info("[GATE-RATIO] seed quet [{}..{}): {} tick goi Aerospike, bo {} ngay khong co thu muc "
                        + "predictionSymbol, {} ms",
                Utils.normalizeDateYYYYMMDDHHmm(from), Utils.normalizeDateYYYYMMDDHHmm(to),
                res.aerospikeCalls, res.skippedDays, elapsed);
        long[] ts = res.ts;
        float[] r = res.r;
        if (ts.length == 0) {
            LOG.warn("[GATE-RATIO] seed lịch sử RỖNG (thiếu p15/sp?) -> dùng warm-up 7d (fallback base)");
            return false;
        }
        buffer.bulkAdd(ts, r);
        LOG.info("[GATE-RATIO] seed lịch sử: {} record ({}..{}) | nguồn p15=Aerospike ai_pred_1m, "
                        + "sp=predictionSymbol (P(no-pump)); sai khác vs sim: held-symbol + tick thiếu",
                ts.length,
                Utils.normalizeDateYYYYMMDDHHmm(ts[0]),
                Utils.normalizeDateYYYYMMDDHHmm(ts[ts.length - 1]));
        return true;
    }

    /** Nguồn dữ liệu cho seed (tách để unit test không cần Aerospike / thư mục thật). */
    interface SeedSource {
        boolean dayDirExists(String yyyyMMdd);

        Map<String, Float> symbolPred(long t);

        AiPredictionData p15(long t);
    }

    /** Kết quả quét seed. */
    static final class SeedResult {
        final long[] ts;
        final float[] r;
        final int aerospikeCalls;
        final int skippedDays;

        SeedResult(long[] ts, float[] r, int aerospikeCalls, int skippedDays) {
            this.ts = ts;
            this.r = r;
            this.aerospikeCalls = aerospikeCalls;
            this.skippedDays = skippedDays;
        }
    }

    /**
     * Lõi quét seed (package-private cho unit test). Thứ tự mỗi tick lưới: (1) ngày không có thư mục
     * predictionSymbol ⇒ bỏ (cache theo ngày); (2) sp rỗng/thiếu ⇒ bỏ; (3) mới gọi p15 (Aerospike), null ⇒ bỏ.
     * Lỗi bất kỳ ở một tick ⇒ bỏ tick (best-effort, như cũ).
     */
    static SeedResult collectSeed(long from, long to, int gridMin, int topK, SeedSource src) {
        List<Long> tsList = new ArrayList<>();
        List<Float> rList = new ArrayList<>();
        Map<String, Boolean> dayExists = new HashMap<>();
        int aerospikeCalls = 0;
        int skippedDays = 0;
        long t0 = (from / 60_000L) * 60_000L;
        int guard = 0;
        for (long t = t0; t < to && guard < 200_000; t += 60_000L, guard++) {
            if ((t / 60_000L) % gridMin != 0) continue;
            try {
                String day = Utils.normalizeDateYYYYMMDD(t);
                Boolean exists = dayExists.get(day);
                if (exists == null) {
                    exists = src.dayDirExists(day);
                    dayExists.put(day, exists);
                    if (!exists) skippedDays++;
                }
                if (!exists) continue;
                Map<String, Float> spMap = src.symbolPred(t);
                if (spMap == null || spMap.isEmpty()) continue;
                aerospikeCalls++;
                AiPredictionData p15 = src.p15(t);
                if (p15 == null) continue;
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
        long[] ts = new long[tsList.size()];
        float[] r = new float[rList.size()];
        for (int i = 0; i < ts.length; i++) {
            ts[i] = tsList.get(i);
            r[i] = rList.get(i);
        }
        return new SeedResult(ts, r, aerospikeCalls, skippedDays);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Float> readSymbolPred(long t) {
        String path = SYMBOL_PRED_DIR + "/" + Utils.normalizeDateYYYYMMDD(t) + "/" + t;
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
        double q = buffer.currentQ();
        // [V11] giu q_t=%.6f (parser cu) + them q_t9=%.9g de kiem duoc 1e-6
        LOG.info("[GATE-RATIO] q_t={} q_t9={} buffer={} eval={} pass={}",
                String.format("%.6f", q), fmtQ9(q), buffer.size(), hourEval, hourPass);
    }

    /** [V11] 9 chu so co nghia, Locale.ROOT (dau cham thap phan). */
    static String fmtQ9(double q) {
        return String.format(java.util.Locale.ROOT, "%.9g", q);
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
