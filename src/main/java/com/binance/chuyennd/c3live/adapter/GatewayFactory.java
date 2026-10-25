package com.binance.chuyennd.c3live.adapter;

import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.ExchangeInfoParser;
import com.binance.chuyennd.c3live.client.C3LiveClient;
import com.binance.chuyennd.c3live.client.C3LiveClientConfig;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.rate.RateGuard;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
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
            DryGateway g = new DryGateway(fileSource(file), refPrice, dryEquity, audit, clock);
            if (!file.exists()) {
                LOG.warn("[C3-LIVE] dry: chua co file exchangeInfo {} => universe rong, khong leg nao vao (chi WARN)",
                        file.getPath());
            }
            return new Result(Mode.DRY, g, null, "dry exchangeInfo=" + file.getPath());
        }
        try {
            RateGuard rg = RateGuard.defaults();
            C3LiveClient c = C3LiveClient.create(C3LiveClientConfig.fromEnv(env), rg);
            return new Result(Mode.LIVE, c, rg, "live");
        } catch (Exception e) {
            // C3LiveKeyException: thong diep chi ve duong dan/quyen, khong chua key
            return new Result(Mode.LIVE, null, null, "khong tao duoc C3LiveClient: " + e.getClass().getSimpleName() + ": "
                    + e.getMessage());
        }
    }

    /** Doc exchangeInfo tu file (cache theo mtime). File thieu/hong => null. */
    static Supplier<ExchangeInfo> fileSource(File file) {
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
