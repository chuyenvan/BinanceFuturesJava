package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

/**
 * [V12 R4 R2/R8] Lam moi tap LEGACY-busy moi chu ky ({@link #PERIOD_MS} = 60 s; ~85 weight: positionRisk 5 + openOrders 40 +
 * openAlgoOrders 40) bang doc TOAN tai khoan CHI DOC, va dua vi the tho cho {@link C3MergedGuard}. Doc loi => giu anh chup cu
 * (qua {@link C3Scope#LEGACY_MAX_AGE_MS} => chan MO MOI, fail-closed); lan dau (khoi dong) => MERGED danh gia ngay.
 */
public final class C3LegacyRefresher {

    private static final Logger LOG = LoggerFactory.getLogger(C3LegacyRefresher.class);
    public static final long PERIOD_MS = 60_000L;

    private final C3ScopedGateway gw;
    private final C3Scope scope;
    private final C3MergedGuard merged;
    private final C3LiveOrderExecutor.ApiObserver api;
    private final Consumer<String> alert;
    private final LongSupplier clock;
    private long lastMs = Long.MIN_VALUE / 2;
    private boolean first = true;
    private int lastLoggedCount = Integer.MIN_VALUE;

    public C3LegacyRefresher(C3ScopedGateway gw, C3Scope scope, C3MergedGuard merged, C3LiveOrderExecutor.ApiObserver api,
                             Consumer<String> alert, LongSupplier clock) {
        this.gw = gw;
        this.scope = scope;
        this.merged = merged;
        this.api = api == null ? (a, ok) -> { } : api;
        this.alert = alert == null ? m -> { } : alert;
        this.clock = clock == null ? System::currentTimeMillis : clock;
    }

    /** Goi moi nhip ops; tu han che theo chu ky. @return true neu da lam moi thanh cong luot nay. */
    public synchronized boolean tick() {
        long now = clock.getAsLong();
        if (!first && now - lastMs < PERIOD_MS) return false;
        return refreshNow();
    }

    /** Lam moi NGAY (khoi dong / test). */
    public synchronized boolean refreshNow() {
        long now = clock.getAsLong();
        lastMs = now;
        List<PositionInfo> ps;
        List<OrderInfo> os;
        List<OrderInfo> as;
        try {
            ps = gw.positionsAll();
            os = gw.openOrdersAll();
            as = gw.openStopsAll();
            api.onApiResult("positions", true);
        } catch (RuntimeException e) {
            api.onApiResult("positions", false);
            LOG.warn("[C3-LIVE-SCOPE] doc toan tai khoan (LEGACY-busy) loi {} => giu anh chup cu ({}); qua {} s => chan mo moi",
                    e.toString(), scope.legacyAtMs(), C3Scope.LEGACY_MAX_AGE_MS / 1000);
            return false;
        }
        scope.refreshLegacy(ps, os, as, now);
        boolean startup = first;
        first = false;
        if (merged != null) merged.observe(ps, startup);
        int n = scope.legacyPositionCount();
        if (startup || n != lastLoggedCount) {
            String m = "[C3-LIVE-SCOPE] LEGACY tren tai khoan chinh: " + n + " vi the (foreign DA BIET, khong phai cum ma, khong chan"
                    + " (A)); LEGACY-busy=" + scope.legacyBusySymbols().size() + " symbol; lenh/algo mo ca tai khoan: " + os.size() + "/"
                    + as.size() + "; MERGED=" + scope.merged().keySet();
            if (startup) {
                LOG.warn("{}", m);
                alert.accept(m);
            } else {
                LOG.info("{}", m);
            }
            lastLoggedCount = n;
        }
        return true;
    }
}
