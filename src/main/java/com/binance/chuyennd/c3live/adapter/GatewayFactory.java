package com.binance.chuyennd.c3live.adapter;

import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.ExchangeInfoParser;
import com.binance.chuyennd.c3live.client.C3LiveClient;
import com.binance.chuyennd.c3live.client.C3LiveClientConfig;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.rate.ProductionRatePolicy;
import com.binance.chuyennd.c3live.rate.RateGuard;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.function.Function;
import java.util.function.LongSupplier;
import java.util.function.Supplier;
import java.util.zip.GZIPInputStream;

/**
 * [V12 C12] Chon gateway theo {@code LIVE_ADAPTER}: {@code dry} => {@link DryGateway} (khong mang; exchangeInfo tu file
 * {@code LIVE_C3_EXCHANGEINFO_FILE}, mac dinh {@code run/c3live_exchangeInfo.json}, .gz duoc); {@code live} =>
 * {@link C3LiveClient#create} (key file root-only). Key loi / tao client loi => gateway null + ly do (KHONG crash JVM,
 * KHONG log key). Gia tri khac => OFF.
 */
public final class GatewayFactory {

    private static final Logger LOG = LoggerFactory.getLogger(GatewayFactory.class);
    public static final String KEY_ADAPTER = "LIVE_ADAPTER";
    public static final String KEY_EXCHANGEINFO_FILE = "LIVE_C3_EXCHANGEINFO_FILE";
    public static final String DEFAULT_EXCHANGEINFO_FILE = "run/c3live_exchangeInfo.json";
    /** [V12 2b] file trang thai dry (vi the/stop gia lap song qua restart); khong dat => chi RAM. */
    public static final String KEY_DRY_STATE_FILE = "LIVE_C3_DRY_STATE_FILE";
    /** [V12 2b] phi taker gia lap cua dry (mac dinh 0,05 %). */
    public static final String KEY_DRY_FEE_RATE = "LIVE_C3_DRY_FEE_RATE";

    public enum Mode {
        OFF, DRY, LIVE;

        public static Mode parse(String raw) {
            if (raw == null) return OFF;
            String v = raw.trim().toLowerCase(Locale.ROOT);
            if ("dry".equals(v)) return DRY;
            if ("live".equals(v)) return LIVE;
            return OFF;
        }
    }

    public static final class Result {
        public final Mode mode;
        public final ExchangeGateway gateway;
        public final RateGuard rateGuard;
        public final String reason;

        Result(Mode mode, ExchangeGateway gateway, RateGuard rateGuard, String reason) {
            this.mode = mode;
            this.gateway = gateway;
            this.rateGuard = rateGuard;
            this.reason = reason;
        }
    }

    private GatewayFactory() {
    }

    public static Result create(Mode mode, Function<String, String> env, Function<String, BigDecimal> refPrice,
                                BigDecimal dryEquity, LongSupplier clock, OrderAuditLog audit) {
        if (mode == null || mode == Mode.OFF) return new Result(Mode.OFF, null, null, "LIVE_ADAPTER tat");
        if (mode == Mode.DRY) {
            String f = env.apply(KEY_EXCHANGEINFO_FILE);
            File file = new File(f == null || f.trim().isEmpty() ? DEFAULT_EXCHANGEINFO_FILE : f.trim());
            String sf = env.apply(KEY_DRY_STATE_FILE);
            File state = sf == null || sf.trim().isEmpty() ? null : new File(sf.trim());
            if (state == null) LOG.warn("[C3-LIVE] dry: {} khong dat => vi the gia lap CHI trong RAM (mat khi restart)",
                    KEY_DRY_STATE_FILE);
            DryGateway g = new DryGateway(fileSource(file), refPrice, dryEquity, audit, clock, state,
                    parseFee(env.apply(KEY_DRY_FEE_RATE)));
            if (!file.exists()) {
                LOG.warn("[C3-LIVE] dry: chua co file exchangeInfo {} => universe rong, khong leg nao vao (chi WARN)",
                        file.getPath());
            }
            return new Result(Mode.DRY, g, null, "dry exchangeInfo=" + file.getPath());
        }
        try {
            RateGuard rg = ProductionRatePolicy.guard(env, RateGuard.SYSTEM);   // [V12 R4 R5] chinh sach 3i (IP chung LEGACY)
            C3LiveClient c = C3LiveClient.create(C3LiveClientConfig.fromEnv(env), rg);
            return new Result(Mode.LIVE, c, rg, "live");
        } catch (Exception e) {
            // C3LiveKeyException: thong diep chi ve duong dan/quyen, khong chua key
            return new Result(Mode.LIVE, null, null, "khong tao duoc C3LiveClient: " + e.getClass().getSimpleName() + ": "
                    + e.getMessage());
        }
    }

    static double parseFee(String raw) {
        if (raw == null || raw.trim().isEmpty()) return DryGateway.DEFAULT_FEE_RATE;
        try {
            double v = Double.parseDouble(raw.trim());
            return Double.isFinite(v) && v >= 0d && v < 0.01d ? v : DryGateway.DEFAULT_FEE_RATE;
        } catch (NumberFormatException e) {
            return DryGateway.DEFAULT_FEE_RATE;
        }
    }

    /** [V12 R4n MAJ-X A1 R4M] sidecar canh file exchangeInfo: {"fetchedAtMs":..,"sha256":"..","n_symbols":..} (cron/deploy ghi). */
    public static final String META_SUFFIX = ".meta";
    /** [V12 R4n] fetchedAt o tuong lai qua muc nay (lech dong ho / file sai) => tu choi. */
    static final long FETCHED_FUTURE_TOL_MS = 5L * 60_000L;
    /** [V12 R4n] serverTime lech fetchedAt qua muc nay => CHI canh bao (serverTime la anh chup cache cua san, KHONG phai dong ho). */
    static final long SERVERTIME_WARN_MS = 24L * 3_600_000L;

    /**
     * [V12 R4e MAJOR-1 + R4n MAJ-X] R7 khi UNIVERSE_A1=1 (dry VA live): doc CUNG file raw exchangeInfo voi bo loc tin hieu (cron lam
     * moi tren 242), kem kiem tuoi theo LUC TAI (fetchedAt): sidecar {@code <file>.meta} (sha256 + n_symbols phai khop file; hong /
     * lech => nem, fail-closed) hoac mtime khi KHONG co sidecar. Tuoi &gt; {@code maxAgeMs} / fetchedAt o tuong lai &gt; 5' / file thieu
     * / hong / thieu serverTime => nem (R7 giu snapshot cu; qua han => STALE, khong mua). serverTime cua san la anh chup cache (do
     * 10-31/11-02: cu 9-88', co luc lui vai ms) => KHONG dung lam dong ho, chi canh bao khi lech &gt; 24 h.
     * Khong bao gio doc API => R7 va A1 khong the lech nguon.
     */
    public static Supplier<ExchangeInfo> freshFileSource(File file, java.util.function.LongSupplier clock, long maxAgeMs) {
        final Supplier<ExchangeInfo> base = fileSource(file);
        final File meta = new File(file.getPath() + META_SUFFIX);
        final long[] warnedFetched = {Long.MIN_VALUE};
        return () -> {
            ExchangeInfo ei = base.get();
            if (ei == null) throw new IllegalStateException("khong doc duoc exchangeInfo " + file.getPath());
            if (ei.getServerTime() <= 0L) {
                throw new IllegalStateException("exchangeInfo " + file.getPath() + " thieu serverTime (khong phai raw /fapi/v1/exchangeInfo)");
            }
            long fetched = fetchedAtMs(file, meta, ei);
            long now = clock.getAsLong();
            long age = now - fetched;
            if (age > maxAgeMs || fetched > now + FETCHED_FUTURE_TOL_MS) {
                throw new IllegalStateException("exchangeInfo " + file.getPath() + " CU: tai luc fetchedAt=" + fetched + " ("
                        + (meta.exists() ? "sidecar" : "mtime") + ") tuoi " + age / 60_000L + "' > " + maxAgeMs / 60_000L
                        + "' hoac o tuong lai (cron lam moi tren 242?)");
            }
            long skew = Math.abs(fetched - ei.getServerTime());
            if (skew > SERVERTIME_WARN_MS && warnedFetched[0] != fetched) {
                warnedFetched[0] = fetched;
                LOG.warn("[C3-LIVE] exchangeInfo {}: serverTime={} lech luc tai {} h (> 24 h) — CHI canh bao (serverTime la anh chup cache)",
                        file.getPath(), ei.getServerTime(), skew / 3_600_000L);
            }
            return ei;
        };
    }

    /** [V12 R4n] luc tai: sidecar (fail-closed khi hong/lech file) hoac mtime khi khong co sidecar. */
    static long fetchedAtMs(File file, File meta, ExchangeInfo ei) {
        if (!meta.exists()) {
            long m = file.lastModified();
            if (m <= 0L) throw new IllegalStateException("exchangeInfo " + file.getPath() + " khong doc duoc mtime");
            return m;
        }
        final JsonObject o;
        final byte[] raw;
        try {
            o = JsonParser.parseString(new String(Files.readAllBytes(meta.toPath()), StandardCharsets.UTF_8)).getAsJsonObject();
            raw = Files.readAllBytes(file.toPath());
        } catch (Exception e) {
            throw new IllegalStateException("sidecar " + meta.getPath() + " HONG (" + e.getClass().getSimpleName() + ") => tu choi");
        }
        long fa;
        String sha;
        long n;
        try {
            fa = o.get("fetchedAtMs").getAsLong();
            sha = o.get("sha256").getAsString();
            n = o.get("n_symbols").getAsLong();
        } catch (RuntimeException e) {
            throw new IllegalStateException("sidecar " + meta.getPath() + " thieu/sai truong fetchedAtMs/sha256/n_symbols => tu choi");
        }
        if (fa <= 0L || sha == null || !sha.matches("[0-9a-f]{64}") || n <= 0L) {
            throw new IllegalStateException("sidecar " + meta.getPath() + " gia tri khong hop le => tu choi");
        }
        String got = sha256Hex(raw);
        if (!sha.equals(got)) {
            throw new IllegalStateException("sidecar " + meta.getPath() + " sha256 KHONG khop file (" + sha.substring(0, 12) + " != "
                    + got.substring(0, 12) + ") => tu choi");
        }
        if (n != ei.getSymbols().size()) {
            throw new IllegalStateException("sidecar " + meta.getPath() + " n_symbols=" + n + " != file " + ei.getSymbols().size() + " => tu choi");
        }
        return fa;
    }

    static String sha256Hex(byte[] b) {
        try {
            byte[] d = MessageDigest.getInstance("SHA-256").digest(b);
            StringBuilder sb = new StringBuilder(64);
            for (byte x : d) sb.append(String.format("%02x", x & 0xff));
            return sb.toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IllegalStateException("khong co SHA-256", e);
        }
    }

    /** Doc exchangeInfo tu file (cache theo mtime). File thieu/hong => null. */
    public static Supplier<ExchangeInfo> fileSource(File file) {
        return new Supplier<ExchangeInfo>() {
            private long mtime = Long.MIN_VALUE;
            private ExchangeInfo cached;

            @Override
            public synchronized ExchangeInfo get() {
                if (!file.exists()) return null;
                long m = file.lastModified();
                if (cached != null && m == mtime) return cached;
                try {
                    String json;
                    if (file.getName().endsWith(".gz")) {
                        try (InputStream in = new GZIPInputStream(Files.newInputStream(file.toPath()))) {
                            ByteArrayOutputStream bo = new ByteArrayOutputStream();
                            byte[] buf = new byte[65536];
                            int n;
                            while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                            json = new String(bo.toByteArray(), StandardCharsets.UTF_8);
                        }
                    } else {
                        json = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
                    }
                    cached = ExchangeInfoParser.parse(json);
                    mtime = m;
                    return cached;
                } catch (Exception e) {
                    LOG.warn("[C3-LIVE] dry: khong doc duoc exchangeInfo {}: {}", file.getPath(), e.toString());
                    return null;
                }
            }
        };
    }
}
