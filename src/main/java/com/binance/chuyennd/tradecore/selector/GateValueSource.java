package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * [TIER-1] CO chon NGUON gia tri gate (symbolPred) cho duong LIVE — MAC DINH TAT.
 *
 * <p>Bat bang {@code SELECTOR_GATE_NET015_RAW=true}. Khi BAT (va KHONG dung C3 mapped),
 * gate live dung {@code net015-raw = 1 - P(win)} thay cho pNoPump cua Funding_Classifier.
 * KHONG quantile-map (map can S1 rank / OI history = tier-2). Khi TAT: duong live
 * byte-identical HEAD.
 *
 * <p>Doc 1 LAN luc class nap (khong doc trong vong nong). Xem
 * docs/PREREG_SELECTOR_NET015_GATE.md + docs/AUDIT_SELECTOR_MODEL_PARITY.md.
 */
public final class GateValueSource {

    private static final Logger LOG = LoggerFactory.getLogger(GateValueSource.class);
    private static final boolean NET015_RAW;

    static {
        String v = Cfg.get("SELECTOR_GATE_NET015_RAW");
        NET015_RAW = v != null && ("true".equalsIgnoreCase(v.trim()) || "1".equals(v.trim()));
        if (NET015_RAW) {
            LOG.info("[SELECTOR_GATE_NET015_RAW=true] gate live dung net015-raw (1-P(win)), "
                    + "KHONG map. Chi tac dung khi khong dung C3 mapped.");
        }
    }

    private GateValueSource() {
    }

    /** true khi {@code SELECTOR_GATE_NET015_RAW=true}. */
    public static boolean net015Raw() {
        return NET015_RAW;
    }
}
