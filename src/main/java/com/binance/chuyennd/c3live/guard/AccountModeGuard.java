package com.binance.chuyennd.c3live.guard;

import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.SymbolConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

/**
 * [V12 C5] Kiem che do tai khoan con truoc khi c3_live dat lenh (owner chot 10-25: Multi-Assets BAT, one-way, CROSS 1x).
 * <ul>
 *   <li>{@link #checkGlobal()} luc start: multiAssetsMargin == true (sai -> CHI bao + chan, KHONG tu doi),
 *       dualSidePosition == false (sai -> dat lai 1 lan, doc lai).</li>
 *   <li>{@link #checkSymbol(String)} truoc leg DAU moi symbol: kiem lai 2 muc toan cuc (cache {@code globalTtlMs}, mac dinh 60 s,
 *       de dot 24 leg khong ton 24 x 60 weight) + marginType == CROSSED, leverage == 1 (sai -> dat lai 1 lan, doc lai).</li>
 *   <li>Van sai / loi doc (fail-closed) -> BLOCKED: global -> chan TOAN BO push; symbol -> chan symbol do. Moi BLOCKED -> alerter
 *       (Telegram o vong 2) + WARN.</li>
 * </ul>
 */
public final class AccountModeGuard {
    private static final Logger LOG = LoggerFactory.getLogger(AccountModeGuard.class);
    public static final long DEFAULT_GLOBAL_TTL_MS = 60_000L;

    /** Ket qua 1 lan kiem. */
    public static final class Result {
        private final boolean ok;
        private final String scope;
        private final List<String> problems;
        private final List<String> actions;

        Result(boolean ok, String scope, List<String> problems, List<String> actions) {
            this.ok = ok;
            this.scope = scope;
            this.problems = Collections.unmodifiableList(new ArrayList<>(problems));
            this.actions = Collections.unmodifiableList(new ArrayList<>(actions));
        }

        public boolean isOk() { return ok; }
        /** "GLOBAL" hoac ten symbol. */
        public String getScope() { return scope; }
        /** Van de CON LAI sau khi sua (rong neu ok). */
        public List<String> getProblems() { return problems; }
        /** Hanh dong da thu (dat lai ...). */
        public List<String> getActions() { return actions; }

        @Override
        public String toString() { return "[C5] " + scope + (ok ? " OK" : " BLOCKED " + problems) + (actions.isEmpty() ? "" : " actions=" + actions); }
    }

    private final ExchangeGateway gw;
    private final int expectedLeverage;
    private final Consumer<String> alerter;
    private final LongSupplier clock;
    private final long globalTtlMs;

    private volatile Boolean globalOk;
    private volatile long globalCheckedAtMs;
    private final Set<String> clearedSymbols = ConcurrentHashMap.newKeySet();
    private final Set<String> blockedSymbols = ConcurrentHashMap.newKeySet();

    public AccountModeGuard(ExchangeGateway gw, Consumer<String> alerter) {
        this(gw, 1, alerter, System::currentTimeMillis, DEFAULT_GLOBAL_TTL_MS);
    }

    public AccountModeGuard(ExchangeGateway gw, int expectedLeverage, Consumer<String> alerter, LongSupplier clock, long globalTtlMs) {
        this.gw = gw;
        this.expectedLeverage = expectedLeverage;
        this.alerter = alerter == null ? s -> { } : alerter;
        this.clock = clock == null ? System::currentTimeMillis : clock;
        this.globalTtlMs = Math.max(0L, globalTtlMs);
    }

    /** Kiem toan cuc (luc start). */
    public synchronized Result checkGlobal() {
        List<String> problems = new ArrayList<>();
        List<String> actions = new ArrayList<>();
        try {
            if (!gw.multiAssetsMargin()) {
                problems.add("multiAssetsMargin=false (yeu cau true; KHONG tu doi - owner chay set_c3live_multiassets.sh)");
            }
        } catch (GatewayException e) {
            problems.add("khong doc duoc multiAssetsMargin: " + e.getKind());
        }
        try {
            if (gw.dualSidePosition()) {
                actions.add("setDualSidePosition(false)");
                try {
                    gw.setDualSidePosition(false);
                } catch (GatewayException e) {
                    actions.add("loi dat dualSide: " + e.getKind() + ":" + e.getExchangeCode());
                }
                if (gw.dualSidePosition()) problems.add("dualSidePosition=true (hedge) sau 1 lan dat lai");
            }
        } catch (GatewayException e) {
            problems.add("khong doc duoc dualSidePosition: " + e.getKind());
        }
        boolean ok = problems.isEmpty();
        globalOk = ok;
        globalCheckedAtMs = clock.getAsLong();
        Result r = new Result(ok, "GLOBAL", problems, actions);
        report(r);
        return r;
    }

    /**
     * Kiem truoc leg dau cua symbol. Symbol da qua kiem -> tra OK ngay (khong goi san) cho toi {@link #resetSymbol}.
     */
    public synchronized Result checkSymbol(String symbol) {
        if (clearedSymbols.contains(symbol) && Boolean.TRUE.equals(globalOk)
                && clock.getAsLong() - globalCheckedAtMs <= globalTtlMs) {
            return new Result(true, symbol, Collections.emptyList(), Collections.emptyList());
        }
        if (globalOk == null || clock.getAsLong() - globalCheckedAtMs > globalTtlMs) checkGlobal();
        List<String> problems = new ArrayList<>();
        List<String> actions = new ArrayList<>();
        if (!Boolean.TRUE.equals(globalOk)) problems.add("GLOBAL BLOCKED");
        try {
            SymbolConfig sc = gw.symbolConfig(symbol);
            boolean fixed = false;
            if (!sc.isCrossed()) {
                actions.add("setMarginType(CROSSED) tu " + sc.getMarginType());
                try { gw.setMarginType(symbol, SymbolConfig.CROSSED); } catch (GatewayException e) { actions.add("loi: " + e.getKind() + ":" + e.getExchangeCode()); }
                fixed = true;
            }
            if (sc.getLeverage() != expectedLeverage) {
                actions.add("setLeverage(" + expectedLeverage + ") tu " + sc.getLeverage());
                try { gw.setLeverage(symbol, expectedLeverage); } catch (GatewayException e) { actions.add("loi: " + e.getKind() + ":" + e.getExchangeCode()); }
                fixed = true;
            }
            if (fixed) sc = gw.symbolConfig(symbol);
            if (!sc.isCrossed()) problems.add("marginType=" + sc.getMarginType() + " (yeu cau CROSSED) sau 1 lan dat lai");
            if (sc.getLeverage() != expectedLeverage) problems.add("leverage=" + sc.getLeverage() + " (yeu cau " + expectedLeverage + ") sau 1 lan dat lai");
        } catch (GatewayException e) {
            problems.add("khong doc/dat duoc symbolConfig: " + e.getKind());
        }
        boolean ok = problems.isEmpty();
        if (ok) {
            clearedSymbols.add(symbol);
            blockedSymbols.remove(symbol);
        } else {
            clearedSymbols.remove(symbol);
            blockedSymbols.add(symbol);
        }
        Result r = new Result(ok, symbol, problems, actions);
        report(r);
        return r;
    }

    private void report(Result r) {
        if (r.isOk()) {
            if (!r.getActions().isEmpty()) LOG.warn("{} (da sua)", r);
            else LOG.info("{}", r);
        } else {
            LOG.warn("{}", r);
            alerter.accept("[C3-LIVE C5] " + r.getScope() + " BLOCKED: " + String.join("; ", r.getProblems()));
        }
    }

    /** true = khong duoc push lenh MO MOI nao (toan cuc sai hoac chua kiem). */
    public boolean isGlobalBlocked() { return !Boolean.TRUE.equals(globalOk); }

    /** Symbol da qua kiem (va toan cuc OK). */
    public boolean isSymbolCleared(String symbol) { return !isGlobalBlocked() && clearedSymbols.contains(symbol); }

    public Set<String> blockedSymbols() { return Collections.unmodifiableSet(new TreeSet<>(blockedSymbols)); }

    /** Goi khi vi the symbol da dong het: leg dau ke tiep se kiem lai. */
    public void resetSymbol(String symbol) {
        clearedSymbols.remove(symbol);
    }
}
