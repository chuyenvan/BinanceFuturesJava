package com.binance.chuyennd.c3live.client;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Locale;
import java.util.function.Function;

/**
 * [V12 C2] Cau hinh C3LiveClient (bat bien). Bien moi truong / system property:
 * LIVE_C3_KEYS_FILE (/root/.config/c3live/keys.env), LIVE_C3_KEYS_OWNER (root), LIVE_C3_BASE_URL (https://fapi.binance.com),
 * LIVE_C3_RECV_WINDOW_MS (5000), LIVE_C3_HTTP_CONNECT_TIMEOUT_MS (3000), LIVE_C3_HTTP_TIMEOUT_MS (10000),
 * LIVE_C3_TIME_SYNC_MS (600000), LIVE_C3_STOP_WORKING_TYPE (MARK_PRICE), LIVE_C3_RATE_MAX_WAIT_MS (2000),
 * LIVE_C3_CANCEL_COUNTS_AS_ORDER (1).
 */
public final class C3LiveClientConfig {
    public static final String DEFAULT_BASE_URL = "https://fapi.binance.com";

    private final Path keysFile;
    private final String keysOwner;
    private final String baseUrl;
    private final long recvWindowMs;
    private final long connectTimeoutMs;
    private final long requestTimeoutMs;
    private final long timeSyncIntervalMs;
    private final String stopWorkingType;
    private final long rateMaxWaitMs;
    private final boolean cancelCountsAsOrder;

    private C3LiveClientConfig(Builder b) {
        this.keysFile = b.keysFile;
        this.keysOwner = b.keysOwner;
        this.baseUrl = b.baseUrl.endsWith("/") ? b.baseUrl.substring(0, b.baseUrl.length() - 1) : b.baseUrl;
        this.recvWindowMs = b.recvWindowMs;
        this.connectTimeoutMs = b.connectTimeoutMs;
        this.requestTimeoutMs = b.requestTimeoutMs;
        this.timeSyncIntervalMs = b.timeSyncIntervalMs;
        this.stopWorkingType = b.stopWorkingType;
        this.rateMaxWaitMs = b.rateMaxWaitMs;
        this.cancelCountsAsOrder = b.cancelCountsAsOrder;
    }

    public static Builder builder() { return new Builder(); }

    /** System.getenv, fallback System.getProperty. */
    public static C3LiveClientConfig fromEnv() {
        return fromEnv(k -> {
            String v = System.getenv(k);
            return v != null ? v : System.getProperty(k);
        });
    }

    public static C3LiveClientConfig fromEnv(Function<String, String> env) {
        Builder b = builder();
        String f = trim(env.apply("LIVE_C3_KEYS_FILE"));
        if (f != null) b.keysFile(Paths.get(f));
        String o = trim(env.apply("LIVE_C3_KEYS_OWNER"));
        if (o != null) b.keysOwner(o);
        String u = trim(env.apply("LIVE_C3_BASE_URL"));
        if (u != null) b.baseUrl(u);
        b.recvWindowMs(lng(env, "LIVE_C3_RECV_WINDOW_MS", b.recvWindowMs, 1, 60_000));
        b.connectTimeoutMs(lng(env, "LIVE_C3_HTTP_CONNECT_TIMEOUT_MS", b.connectTimeoutMs, 100, 60_000));
        b.requestTimeoutMs(lng(env, "LIVE_C3_HTTP_TIMEOUT_MS", b.requestTimeoutMs, 100, 120_000));
        b.timeSyncIntervalMs(lng(env, "LIVE_C3_TIME_SYNC_MS", b.timeSyncIntervalMs, 10_000, 86_400_000));
        String w = trim(env.apply("LIVE_C3_STOP_WORKING_TYPE"));
        if (w != null) b.stopWorkingType(w.toUpperCase(Locale.ROOT));
        b.rateMaxWaitMs(lng(env, "LIVE_C3_RATE_MAX_WAIT_MS", b.rateMaxWaitMs, 0, 120_000));
        String c = trim(env.apply("LIVE_C3_CANCEL_COUNTS_AS_ORDER"));
        if (c != null) b.cancelCountsAsOrder(!"0".equals(c));
        return b.build();
    }

    private static String trim(String s) {
        if (s == null) return null;
        String t = s.trim();
        return t.isEmpty() ? null : t;
    }

    private static long lng(Function<String, String> env, String k, long def, long min, long max) {
        String s = trim(env.apply(k));
        if (s == null) return def;
        try {
            long v = Long.parseLong(s);
            return v < min || v > max ? def : v;
        } catch (NumberFormatException e) {
            return def;
        }
    }

    public Path keysFile() { return keysFile; }
    public String keysOwner() { return keysOwner; }
    public String baseUrl() { return baseUrl; }
    public long recvWindowMs() { return recvWindowMs; }
    public long connectTimeoutMs() { return connectTimeoutMs; }
    public long requestTimeoutMs() { return requestTimeoutMs; }
    public long timeSyncIntervalMs() { return timeSyncIntervalMs; }
    /** CONTRACT_PRICE (gia khop cuoi, khop sim dung close) | MARK_PRICE. */
    public String stopWorkingType() { return stopWorkingType; }
    public long rateMaxWaitMs() { return rateMaxWaitMs; }
    /** Bao thu: huy lenh cung tinh vao ngan sach lenh/10s, /1m. */
    public boolean cancelCountsAsOrder() { return cancelCountsAsOrder; }

    @Override
    public String toString() {
        return "C3LiveClientConfig{keysFile=" + keysFile + " owner=" + keysOwner + " base=" + baseUrl + " recvWindow=" + recvWindowMs
                + " connTo=" + connectTimeoutMs + " reqTo=" + requestTimeoutMs + " sync=" + timeSyncIntervalMs
                + " stopWorking=" + stopWorkingType + " rateWait=" + rateMaxWaitMs + " cancelAsOrder=" + cancelCountsAsOrder + "}";
    }

    public static final class Builder {
        private Path keysFile = Paths.get(C3LiveKeys.DEFAULT_PATH);
        private String keysOwner = C3LiveKeys.DEFAULT_OWNER;
        private String baseUrl = DEFAULT_BASE_URL;
        private long recvWindowMs = 5_000L;
        private long connectTimeoutMs = 3_000L;
        private long requestTimeoutMs = 10_000L;
        private long timeSyncIntervalMs = 600_000L;
        // [V12 MASTER 10-25] MARK_PRICE: stop sau arm kich theo gia danh dau (tranh rau nen gia last/contract khi
        //   thanh khoan mong lam kich stop gia); LIVE_C3_STOP_WORKING_TYPE=CONTRACT_PRICE de quay lai.
        private String stopWorkingType = "MARK_PRICE";
        private long rateMaxWaitMs = 2_000L;
        private boolean cancelCountsAsOrder = true;

        public Builder keysFile(Path v) { keysFile = v; return this; }
        public Builder keysOwner(String v) { keysOwner = v; return this; }
        public Builder baseUrl(String v) { baseUrl = v; return this; }
        public Builder recvWindowMs(long v) { recvWindowMs = v; return this; }
        public Builder connectTimeoutMs(long v) { connectTimeoutMs = v; return this; }
        public Builder requestTimeoutMs(long v) { requestTimeoutMs = v; return this; }
        public Builder timeSyncIntervalMs(long v) { timeSyncIntervalMs = v; return this; }
        public Builder stopWorkingType(String v) { stopWorkingType = v; return this; }
        public Builder rateMaxWaitMs(long v) { rateMaxWaitMs = v; return this; }
        public Builder cancelCountsAsOrder(boolean v) { cancelCountsAsOrder = v; return this; }
        public C3LiveClientConfig build() { return new C3LiveClientConfig(this); }
    }
}
