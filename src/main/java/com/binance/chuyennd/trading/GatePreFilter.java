package com.binance.chuyennd.trading;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.BiFunction;
import java.util.function.Function;
import java.util.function.Predicate;
import java.util.function.Supplier;

/**
 * [V12 R4h] Loc ung vien selector TRUOC cong gate (truoc khi nap r vao buffer GDV2) — y quy uoc sim
 * ({@code SimulatorMarketLevelTicker1MStopLoss}: vong top-K, {@code isSymbolRunning(targetId)} = symbol co cum DANG MO
 * trong {@code activeRunningIds} (them luc tao lenh, bo luc dong cum; sim khop/dong tuc thi nen khong co trang thai
 * cho/dang dong) ⇒ coin dang giu KHONG di qua gate, KHONG nap r; van DEM hang (cap-then-skip, :445-463)).
 *
 * <p>Nguon "dang giu" theo adapter (MASTER 10-30): {@code c3_live + LIVE_ADAPTER=live} ⇒ so c3 THAT
 * ({@code C3LiveHook.ownedSymbols}); {@code c3_live + dry} va {@code c3_shadow} ⇒ so giay twin ({@code ShadowBookC3.isHolding});
 * profile TAT (HEAD) ⇒ {@code symbol2Pos} nhu cu.
 *
 * <p>LEGACY: dem hang + qua gate (nap r) nhung KHONG vao lenh, GIU cho trong top-24 (khong lay hang 25 the) — quyet dinh MASTER
 * 10-30 (tap lenh live la tap con cua sim; ap toi luc cat LEGACY). TradFi/INDEX khi UNIVERSE_A1=1 ⇒ bo han.
 *
 * <p>[V12 R4j A1 MIN-4] vong selector production ({@code DetectEntrySignal2TradeNormal}) goi {@link #runSelector} ⇒ test chay
 * CUNG code vong lap (khong chi ham tach roi).
 */
public final class GatePreFilter {

    private static final Logger LOG = LoggerFactory.getLogger(GatePreFilter.class);

    public enum Action {
        /** khong thuoc universe (A1 loai): khong dem hang, khong gate. */
        DROP_UNIVERSE,
        /** dang giu / khong co ticker: DEM hang, khong gate (khong nap r). */
        SKIP_AFTER_RANK,
        /** LEGACY: DEM hang, qua gate (nap r) nhung KHONG vao lenh. */
        GATE_NO_ENTRY,
        /** ung vien binh thuong. */
        GATE
    }

    public enum HeldSource { HEAD_REAL_POSITIONS, C3_LIVE_BOOK, PAPER_TWIN }

    private GatePreFilter() {
    }

    public static HeldSource source(boolean profileOn, boolean c3HookEnabled, boolean liveAdapter) {
        if (!profileOn) return HeldSource.HEAD_REAL_POSITIONS;
        if (c3HookEnabled && liveAdapter) return HeldSource.C3_LIVE_BOOK;
        return HeldSource.PAPER_TWIN;
    }

    /** Thu tu kiem: universe -> dang giu -> ticker -> LEGACY. */
    public static Action decide(boolean a1Excluded, boolean held, boolean tickerMissing, boolean legacy) {
        if (a1Excluded) return Action.DROP_UNIVERSE;
        if (held || tickerMissing) return Action.SKIP_AFTER_RANK;
        if (legacy) return Action.GATE_NO_ENTRY;
        return Action.GATE;
    }

    private static volatile HeldSource lastLogged;
    /** Nguon so c3 THAT (prod: C3LiveHook.ownedSymbols); test tro vao LiveBookC3 that. */
    private static volatile Supplier<Set<String>> c3Owned = com.binance.chuyennd.c3live.runtime.C3LiveHook::ownedSymbols;

    /** CHI test: nguon so c3 that (null = mac dinh C3LiveHook). */
    public static void setC3OwnedSourceForTest(Supplier<Set<String>> s) {
        c3Owned = s != null ? s : com.binance.chuyennd.c3live.runtime.C3LiveHook::ownedSymbols;
    }

    /** Predicate "dang giu" cua tick (chup 1 lan/tick). Loi doc so => rong + WARN (khong chan vong lap). */
    public static Predicate<String> heldPredicate(HeldSource src, Set<String> realPositions) {
        if (src != lastLogged) {
            lastLogged = src;
            LOG.info("[GATE-PRE] nguon 'dang giu' truoc gate = {} (quy uoc sim isSymbolRunning)", src);
        }
        try {
            switch (src) {
                case C3_LIVE_BOOK: {
                    Set<String> own = c3Owned.get();
                    final Set<String> s = own == null ? Collections.<String>emptySet() : own;
                    return s::contains;
                }
                case PAPER_TWIN: {
                    final com.binance.chuyennd.tradecore.selector.ShadowBookC3 b =
                            com.binance.chuyennd.tradecore.selector.ShadowBookC3.getInstance();
                    return b::isHolding;
                }
                default: {
                    final Set<String> s = realPositions == null ? Collections.<String>emptySet() : realPositions;
                    return s::contains;
                }
            }
        } catch (RuntimeException e) {
            LOG.warn("[GATE-PRE] doc so '{}' loi {} => coi nhu khong giu gi o tick nay", src, e.toString());
            return s -> false;
        }
    }

    /** Diem goi cua vong selector (production: dump/markTopK/createOrderBuyRequest). */
    public interface SelectorSink<T> {
        /** truoc khi kiem tran top-K (production: LATEST_SEL_RANK = nextRank). */
        void beforeCap(String symbol, int nextRank);

        /** symbol da DEM hang (rank 1-based). */
        void counted(String symbol, Float key, Float symbolPred, int rank);

        /** symbol qua cong gate (nap r); LEGACY van vao day (khong vao lenh do createOrderBuyRequest0 chan). */
        void gate(String symbol, T ticker, Float symbolPred);
    }

    public static final class Result {
        public int rank;
        public int gateCand;
        public int held;
        public int legacy;
        public int a1;
        public final List<String> gated = new ArrayList<>();
        public final List<String> skippedHeld = new ArrayList<>();
    }

    /** Vong selector top-K (cap-then-skip nhu sim). */
    public static <T> Result runSelector(Iterable<Map.Entry<Float, String>> pool, int topK, Predicate<String> a1Excluded,
                                         Predicate<String> legacy, Predicate<String> held, Function<String, T> tickerOf,
                                         BiFunction<String, Float, Float> predOf, SelectorSink<T> sink) {
        Result r = new Result();
        for (Map.Entry<Float, String> e : pool) {
            String s = e.getValue();
            if (a1Excluded.test(s)) {
                r.a1++;   // sim A1 khong co symbol nay: khong dem hang, khong gate
                continue;
            }
            boolean lg = legacy.test(s);
            Float sp = predOf.apply(s, e.getKey());
            sink.beforeCap(s, r.rank + 1);
            if (topK > 0 && r.rank >= topK) break;
            r.rank++;
            sink.counted(s, e.getKey(), sp, r.rank);
            T t = tickerOf.apply(s);
            boolean h = held.test(s);
            Action a = decide(false, h, t == null, lg);
            if (a == Action.SKIP_AFTER_RANK) {
                if (h) {
                    r.held++;
                    r.skippedHeld.add(s);
                }
                continue;
            }
            if (a == Action.GATE_NO_ENTRY) r.legacy++;
            r.gateCand++;
            r.gated.add(s);
            sink.gate(s, t, sp);
        }
        return r;
    }
}
