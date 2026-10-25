package com.binance.chuyennd.c3live.risk;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.ops.EquitySource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.function.LongSupplier;

/**
 * [V12 Q1b] Equity c3_live = {@code totalMarginBalance} tai khoan con ({@code gateway.account()}, gom BFUSD/Multi-Assets),
 * cache <= 60 s. Von tinh size = min({@code LIVE_C3_PILOT_CAPITAL} (10 000), totalMarginBalance) — khong tu phinh theo lai.
 * La {@link EquitySource} cho A40 (kill-switch poll 15 s => toi da 1 call account / ttl).
 * Loi / gia tri khong hop le => null (KHONG dung so cu qua ttl) + bao C3 qua ApiObserver.
 */
public final class C3LiveEquity implements EquitySource {

    private static final Logger LOG = LoggerFactory.getLogger(C3LiveEquity.class);
    public static final long MAX_TTL_MS = 60_000L;
    public static final double DEFAULT_PILOT_CAPITAL = 10_000d;

    private final ExchangeGateway gw;
    private final double pilotCapital;
    private final long ttlMs;
    private final LongSupplier clock;
    private final C3LiveOrderExecutor.ApiObserver api;
    private Double cached;
    private long cachedAtMs = Long.MIN_VALUE / 2;
    private long lastWarnMs = Long.MIN_VALUE / 2;

    public C3LiveEquity(ExchangeGateway gw, double pilotCapital, long ttlMs, LongSupplier clock,
                        C3LiveOrderExecutor.ApiObserver api) {
        if (!(pilotCapital > 0d)) throw new IllegalArgumentException("pilotCapital phai > 0");
        this.gw = gw;
        this.pilotCapital = pilotCapital;
        this.ttlMs = Math.max(0L, Math.min(MAX_TTL_MS, ttlMs));
        this.clock = clock;
        this.api = api == null ? (a, ok) -> { } : api;
    }

    public double pilotCapital() {
        return pilotCapital;
    }

    /** totalMarginBalance (cache <= ttl). null = khong co so tin cay. */
    @Override
    public synchronized Double totalMarginBalance() {
        long now = clock.getAsLong();
        if (cached != null && now - cachedAtMs < ttlMs) return cached;
        try {
            AccountSnapshot a = gw.account();
            api.onApiResult("account", true);
            Double v = a == null || a.getTotalMarginBalance() == null ? null : a.getTotalMarginBalance().doubleValue();
            if (v == null || !Double.isFinite(v) || !(v > 0d)) {
                cached = null;
                warn(now, "totalMarginBalance khong hop le: " + v);
                return null;
            }
            cached = v;
            cachedAtMs = now;
            return v;
        } catch (RuntimeException e) {
            api.onApiResult("account", false);
            cached = null;
            warn(now, "account() loi: " + e);
            return null;
        }
    }

    /** Von tinh size = min(pilot, totalMarginBalance); null neu khong co equity. */
    public Double capital() {
        Double tmb = totalMarginBalance();
        if (tmb == null) return null;
        return Math.min(pilotCapital, tmb);
    }

    private void warn(long now, String m) {
        if (now - lastWarnMs < 600_000L) return;
        lastWarnMs = now;
        LOG.warn("[C3-LIVE-EQ] {} => khong co equity (chan mo moi, A40 giu trang thai)", m);
    }
}
