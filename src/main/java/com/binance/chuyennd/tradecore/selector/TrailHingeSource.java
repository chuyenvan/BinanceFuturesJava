package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * [LIVE_EQ_SIM / TRAILING] CO chon net015 cho BAN LE trailing STRONG/WEAK cua vi the SHADOW/PAPER
 * (ShadowBookC3) — MAC DINH TAT.
 *
 * <p>Bat bang {@code TRAIL_HINGE_NET015=true}. Khi BAT, ban le trailing cua vi the SHADOW dung
 * net015-mapped cua symbol ({@code DetectEntrySignal2TradeNormal.LATEST_SEL_MAPPRED}, DUNG gia tri
 * gate + sim) thay cho {@code symbolPred} luc mo. Vi the LEGACY THAT di qua
 * {@code BinanceOrderTradingManager.tsGap} -> {@code LATEST_SEL_PNOPUMP} (Funding), KHONG qua day,
 * nen VAN dung Funding pNoPump. Khi TAT: byte-identical HEAD.
 *
 * <p>Doc 1 LAN luc class nap. Xem docs/prereg/PREREG_LIVE_EQ_SIM.md.
 */
public final class TrailHingeSource {

    private static final Logger LOG = LoggerFactory.getLogger(TrailHingeSource.class);
    private static final boolean NET015;

    static {
        String v = Cfg.get("TRAIL_HINGE_NET015");
        NET015 = v != null && ("true".equalsIgnoreCase(v.trim()) || "1".equals(v.trim()));
        if (NET015) {
            LOG.info("[TRAIL_HINGE_NET015=true] ban le trailing shadow dung net015-mapped "
                    + "(LATEST_SEL_MAPPRED); vi the legacy THAT VAN dung Funding pNoPump.");
        }
    }

    private TrailHingeSource() {
    }

    /** true khi {@code TRAIL_HINGE_NET015=true}. */
    public static boolean net015() {
        return NET015;
    }
}
