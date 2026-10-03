package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

/**
 * [LIVE-DCA-GRID 2026-10-03] DCA GRID cho SO GIAY C3 — <b>MAC DINH TAT</b> ({@code LIVE_DCA_GRID_ENABLED}).
 *
 * <p>VI SAO (docs/audit/PARITY_LIVE_VS_SIM_20261003.md muc E5): sim B0 chay {@code DCA_GRID_ENABLED=true}
 * (nhoi leg 1-3 khi gia rot -50/-75/-90% so voi gia vao leg DAU) nhung live chi co
 * {@code DcaProcessor.getDCAProduction} duyet vi the THAT ({@code BudgetManager.symbol2Pos}) — so giay
 * khong bao gio duoc nhoi.
 *
 * <p>Nhan ban DUNG ham sim, khong viet lai cong thuc:
 * <ul>
 *   <li>dieu kien: {@link DcaUtils#shouldDcaGrid}(firstEntryPrice, lastPrice, legCount) — cung ham
 *       {@code DcaProcessor.getDCA} nhanh DCA_GRID_ENABLED, cung 2 diem goi (levelChange != null va
 *       {@code isDcaAlt});</li>
 *   <li>size: leg di qua {@code createOrderBuyRequest(DCA_LEVEL1)} => managerBudget (U/U_MAX tren so
 *       giay) x {@code gridLegWeightRatio(legCount)} ({@link LiveGridSizing}) x tier, tran CONC_CAP_PERCOIN
 *       tren {@code ShadowBookC3.perCoinMargin} — giong sim;</li>
 *   <li>ghi: leg cong vao cum giay ({@code ShadowBookC3.openPos} -> addLeg) + mot dong {@code legs.csv}
 *       co {@code leg_idx}.</li>
 * </ul>
 * CHI so giay (profile C3 bat). Legacy/vi the THAT KHONG di qua day (lenh that di qua kill-switch
 * {@code LiveProfileC3.forceNoPush}).
 */
public final class LiveDcaGridC3 {

    private static final Logger LOG = LoggerFactory.getLogger(LiveDcaGridC3.class);

    public static final String KEY = "LIVE_DCA_GRID_ENABLED";

    private static final boolean ENABLED;

    static {
        String v = Cfg.get(KEY);
        ENABLED = v != null && "true".equalsIgnoreCase(v.trim());
        if (ENABLED) {
            LOG.info("[LIVE-DCA-GRID] {}=true profileC3={} levels={} legs={} weights={} scale={} applyRatio={}",
                    KEY, LiveProfileC3.on(), java.util.Arrays.toString(Configs.DCA_GRID_LEVELS),
                    Configs.dcaGridLegs(), java.util.Arrays.toString(Configs.DCA_GRID_WEIGHTS),
                    Configs.DCA_GRID_SCALE, LiveGridSizing.on());
            if (!LiveGridSizing.on()) {
                LOG.warn("[LIVE-DCA-GRID] LIVE_APPLY_GRID_RATIO TAT => leg DCA giay chi bang managerBudget "
                        + "(KHONG x ratio) => lech size so voi sim. Nen bat CA HAI.");
            }
            if (!LiveProfileC3.on()) {
                LOG.warn("[LIVE-DCA-GRID] profile C3 TAT => co nay KHONG co tac dung (chi so giay C3).");
            }
        }
    }

    private LiveDcaGridC3() {
    }

    /** Co env (khong xet profile) — dung de bat/tat ghi legs.csv. */
    public static boolean enabled() {
        return ENABLED;
    }

    /** Co hieu dung: co bat VA profile C3 bat. */
    public static boolean active() {
        return ENABLED && LiveProfileC3.on();
    }

    /** Trang thai grid cua mot cum giay (doc tu ShadowBookC3). */
    public static final class GridState {
        public final String symbol;
        public final float firstEntryPrice;
        public final int legCount;

        public GridState(String symbol, float firstEntryPrice, int legCount) {
            this.symbol = symbol;
            this.firstEntryPrice = firstEntryPrice;
            this.legCount = legCount;
        }
    }

    /**
     * Ung vien DCA-grid cua so giay o tick nay. {@code lastPrice} = gia dong nen 1' cua coin (giong
     * {@code order.lastPrice} cua sim). Co hieu dung TAT => list rong.
     */
    public static List<String> candidates(ShadowBookC3 book, Function<String, Float> lastPrice) {
        if (!active() || book == null) return Collections.emptyList();
        return dueSymbols(book.gridStates(), lastPrice, true);
    }

    /**
     * Thuan tinh toan: symbol nao den bac grid. CUNG ham {@link DcaUtils#shouldDcaGrid} voi sim.
     * {@code enabled=false} => rong.
     */
    static List<String> dueSymbols(List<GridState> states, Function<String, Float> lastPrice, boolean enabled) {
        if (!enabled || states == null || states.isEmpty()) return Collections.emptyList();
        List<String> out = new ArrayList<>();
        for (GridState g : states) {
            Float px = lastPrice.apply(g.symbol);
            if (px == null || px <= 0f) continue;
            if (DcaUtils.shouldDcaGrid(g.firstEntryPrice, px, g.legCount)) out.add(g.symbol);
        }
        return out;
    }

    /** legIdx cua leg DCA sap khop = so leg da khop (sim: gridLegCount = legs.size() khi DCA_SIGNAL_GATE tat). */
    public static int legIdxFor(int legCount) {
        return legCount;
    }

    /** Map tien ich cho test. */
    static Function<String, Float> priceOf(Map<String, Float> m) {
        return m::get;
    }
}
