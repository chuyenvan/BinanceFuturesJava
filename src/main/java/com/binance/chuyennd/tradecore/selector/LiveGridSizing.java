package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * [LIVE-SIZING 2026-10-03] Nhan {@link DcaUtils#gridLegWeightRatio(int)} vao budget leg tren DUONG LIVE
 * — <b>MAC DINH TAT</b> ({@code LIVE_APPLY_GRID_RATIO} khong dat / khac "true" => tra dung managerBudget,
 * byte-identical HEAD).
 *
 * <p>VI SAO (docs/audit/PARITY_LIVE_VS_SIM_20261003.md muc E2): sim
 * ({@code SimulatorMarketLevelTicker1MStopLoss:1439}) tinh margin leg = {@code managerBudget x tier x
 * gridLegWeightRatio(legIdx)} (FIX_B2: ratio = w[legIdx] x DCA_GRID_SCALE = 1 x 6), con live
 * ({@code DetectEntrySignal2TradeNormal}) chi lay {@code managerBudget} => leg dau live = 1/6 sim
 * (131.25 vs 787.5 USDT @equity 35000, F_BASE 0.015, luoi 1,1,1,1). Shadow tung bu bang env
 * {@code SIM_F_BASE=0.09}; khi co nay BAT thi F_BASE phai tra ve 0.015 (khong duoc bu hai lan).
 *
 * <p>Pham vi: ap cho MOI leg di qua {@code createOrderBuyRequest} (so giay C3 lan lenh that).
 * {@code legIdx}: 0 = leg mo cum (entry/BIG_DOWN/selector); leg DCA-grid cua so giay = so leg da khop
 * (giong {@code gridLegCount} cua sim khi DCA_SIGNAL_GATE tat). Leg DCA cua vi the THAT cu (legacy,
 * {@code DcaProcessor.getDCAProduction}) KHONG biet legIdx => truyen {@code legIdx < 0} => KHONG nhan
 * ratio (giu hanh vi cu) + WARN mot lan.
 */
public final class LiveGridSizing {

    private static final Logger LOG = LoggerFactory.getLogger(LiveGridSizing.class);

    public static final String KEY = "LIVE_APPLY_GRID_RATIO";

    private static final boolean APPLY;
    private static volatile boolean warnedUnknownLeg = false;

    static {
        String v = Cfg.get(KEY);
        APPLY = v != null && "true".equalsIgnoreCase(v.trim());
        if (APPLY) {
            LOG.info("[LIVE-SIZING] {}=true — budget leg live = managerBudget x DcaUtils.gridLegWeightRatio(legIdx) "
                            + "(DCA_GRID_SCALE={} FIX_B2={} weights={} ratio(leg0)={} F_BASE={}). "
                            + "LUU Y: F_BASE phai la gia tri sim (0.015), KHONG con bu x SCALE.",
                    KEY, Configs.DCA_GRID_SCALE, Configs.FIX_B2,
                    java.util.Arrays.toString(Configs.DCA_GRID_WEIGHTS), DcaUtils.gridLegWeightRatio(0),
                    Configs.F_BASE);
        }
    }

    private LiveGridSizing() {
    }

    /** true khi {@code LIVE_APPLY_GRID_RATIO=true}. */
    public static boolean on() {
        return APPLY;
    }

    /** Budget leg theo co hieu dung cua JVM. Co TAT => tra dung {@code managerBudget} (cung tham chieu). */
    public static Float legBudget(Float managerBudget, int legIdx) {
        return legBudget(managerBudget, legIdx, APPLY);
    }

    /**
     * Thuan tinh toan (test duoc khi khong doi env trong JVM dang chay).
     * {@code apply=false} hoac {@code managerBudget=null} => tra nguyen {@code managerBudget}.
     * {@code legIdx < 0} (leg DCA vi the that, khong biet bac) => tra nguyen + WARN mot lan.
     * Nguoc lai = {@code managerBudget * gridLegWeightRatio(legIdx)} (phep nhan float nhu sim
     * {@code budget *= ratio}); het bac grid => ratio 0 => 0 => bi chan o check {@code budget < 5}.
     */
    static Float legBudget(Float managerBudget, int legIdx, boolean apply) {
        if (!apply || managerBudget == null) return managerBudget;
        if (legIdx < 0) {
            if (!warnedUnknownLeg) {
                warnedUnknownLeg = true;
                LOG.warn("[LIVE-SIZING] leg DCA tren vi the THAT (legacy) khong co legIdx => KHONG nhan ratio "
                        + "(giu managerBudget). Chi canh bao mot lan.");
            }
            return managerBudget;
        }
        float ratio = DcaUtils.gridLegWeightRatio(legIdx);
        return managerBudget * ratio;
    }
}
