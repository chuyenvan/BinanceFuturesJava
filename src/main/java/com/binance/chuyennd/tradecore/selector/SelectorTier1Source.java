package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * [LIVE_EQ_SIM / TIER-1] CO chon net015 cho TANG-1 (loc universe/pool + maxThres cho ENTRY MOI)
 * cua duong LIVE — MAC DINH TAT.
 *
 * <p>Bat bang {@code SELECTOR_TIER1_NET015=true}. Khi BAT, tang-1 dung {@code net015-raw = 1 - P(win)}
 * (Net015ValueLive tren CUNG float[45] da cho vao Funding_Classifier) lam diem so cho
 * selectorRankPool + maxThres + sortedCandidates, khop cach SIM dung universe. Funding VAN chay de
 * nuoi {@code LATEST_SEL_PNOPUMP} cho duong LEGACY THAT. Khi TAT: duong live byte-identical HEAD.
 *
 * <p>Doc 1 LAN luc class nap. Xem docs/PREREG_LIVE_EQ_SIM.md + docs/AUDIT_SELECTOR_MODEL_PARITY.md.
 */
public final class SelectorTier1Source {

    private static final Logger LOG = LoggerFactory.getLogger(SelectorTier1Source.class);
    private static final boolean NET015;

    static {
        String v = Cfg.get("SELECTOR_TIER1_NET015");
        NET015 = v != null && ("true".equalsIgnoreCase(v.trim()) || "1".equals(v.trim()));
        if (NET015) {
            LOG.info("[SELECTOR_TIER1_NET015=true] tang-1 universe/pool + maxThres dung net015-raw "
                    + "(1-P(win)); Funding VAN nuoi LATEST_SEL_PNOPUMP cho legacy.");
        }
    }

    private SelectorTier1Source() {
    }

    /** true khi {@code SELECTOR_TIER1_NET015=true}. */
    public static boolean net015() {
        return NET015;
    }
}
