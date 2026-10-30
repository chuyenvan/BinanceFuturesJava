package com.binance.chuyennd.trading;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;
import java.util.Set;
import java.util.function.Predicate;

/**
 * [V12 R4h] Loc ung vien selector TRUOC cong gate (truoc khi nap r vao buffer GDV2) — y quy uoc sim
 * ({@code SimulatorMarketLevelTicker1MStopLoss}: vong top-K, {@code isSymbolRunning(targetId)} = symbol co cum DANG MO
 * trong {@code activeRunningIds} (them luc tao lenh, bo luc dong cum; sim khop/dong tuc thi nen khong co trang thai
 * cho/dang dong) ⇒ coin dang giu KHONG di qua gate, KHONG nap r; van DEM hang (cap-then-skip, :445-463)).
 *
 * <p>Truoc R4h: live/shadow chi loai {@code BudgetManager.symbol2Pos} (vi the THAT) ⇒ coin dang giu trong so giay van qua gate
 * va nap r (10-30: 93 pass, 67 la coin da giu ⇒ q gio 04 = 0,009502 thay vi 0,007564 theo quy uoc sim).
 *
 * <p>Nguon "dang giu" theo adapter (MASTER 10-30): {@code c3_live + LIVE_ADAPTER=live} ⇒ so c3 THAT
 * ({@code C3LiveHook.ownedSymbols}: cum co qty / leg cho / dang dong — xap xi "cum dang mo" cua sim); {@code c3_live + dry} va
 * {@code c3_shadow} ⇒ so giay twin ({@code ShadowBookC3.isHolding}); profile TAT (HEAD) ⇒ {@code symbol2Pos} nhu cu.
 *
 * <p>LEGACY (vi the that cu, chi khi profile bat): sim KHONG co LEGACY ⇒ symbol do la ung vien binh thuong trong sim ⇒ live
 * DEM hang + qua gate (nap r) nhung KHONG vao lenh ({@link Action#GATE_NO_ENTRY}). TradFi/INDEX khi UNIVERSE_A1=1: sim A1
 * khong co symbol do trong du lieu (PREREG_HO2026_NOTF V1) ⇒ BO han (khong dem hang, khong gate).
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

    /** Predicate "dang giu" cua tick (chup 1 lan/tick). Loi doc so => rong + WARN (khong chan vong lap). */
    public static Predicate<String> heldPredicate(HeldSource src, Set<String> realPositions) {
        if (src != lastLogged) {
            lastLogged = src;
            LOG.info("[GATE-PRE] nguon 'dang giu' truoc gate = {} (quy uoc sim isSymbolRunning)", src);
        }
        try {
            switch (src) {
                case C3_LIVE_BOOK: {
                    Set<String> own = com.binance.chuyennd.c3live.runtime.C3LiveHook.ownedSymbols();
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
}
