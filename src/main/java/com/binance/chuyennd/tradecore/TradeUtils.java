package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.object.MarketLevelChange;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Set;

public class TradeUtils {
    public static final Logger LOG = LoggerFactory.getLogger(TradeUtils.class);

    public static void main(String[] args) {
//        for (int i = 0; i < 100; i++) {
//            Float rate = 0.01 + i * 0.001;
//        }
//        System.out.println(TradeUtils.calRateMinWithMaxChange60MForTradingStop(0d, null));
    }



    /**
     * [PRED-GAP] Gap trailing quyet dinh theo SELECTOR per-coin P(no-pump) (=1-sel) thay market gate pred.
     * Dau da xac minh (provenance): live symbol2FundingPred=prob[0]=P(no-pump). Coin KHO pump (pNoPump CAO)
     * -> siet gap (weak 0.03, chot som); coin DE chay (pNoPump thap) -> gap long (nuoi). weak khi pNoPump>thres.
     * Day la duong trailing DUY NHAT (nhanh cu calRateLossDynamicBuy da xoa 2026-09-03). Fallback: pNoPump null.
     */
    public static float calRateLossDynamicBuyPNoPump(float maxProfitRate, Float pNoPump, float pNoPumpWeakThres) {
        float maxGap = (pNoPump != null && pNoPump > pNoPumpWeakThres)
                ? Configs.TS_MAX_GAP_WEAK
                : Configs.TS_MAX_GAP;
        return trailFromCap(maxProfitRate, maxGap);
    }

    /**
     * [X3 2026-09-06] LOI CHUNG cua trailing: tach nguyen van ra khoi
     * {@link #calRateLossDynamicBuyPNoPump} (KHONG doi mot phep tinh nao) de nhanh rank dung lai
     * dung cong thuc + dung buoc lam tron => khi TS_CAP_STRONG_RANK = 0 ket qua byte-identical.
     */
    static float trailFromCap(float maxProfitRate, float maxGap) {
        float gap = Math.min(maxProfitRate * Configs.TS_GIVEBACK_RATIO, maxGap);
        float rate = maxProfitRate - gap;
        float step = 0.005f;
        rate = Math.round(rate / step) * step;
        return rate;
    }

    /**
     * [X3 2026-09-06] Gap trailing theo RANK cua coin trong tick (khong theo gia tri pNoPump).
     *
     * <p>{@code selRank} 1-based, do {@code SELECTOR_RANK_TOPK} sinh ra tai diem chon top-K.
     * {@code selRank <= capStrongRank} -> STRONG ({@code TS_MAX_GAP}); sau hon hoac null -> WEAK
     * ({@code TS_MAX_GAP_WEAK}). Ban le {@code TS_PNOPUMP_WEAK_THR} KHONG tham gia.
     */
    public static float calRateLossDynamicBuyRank(float maxProfitRate, Integer selRank, int capStrongRank) {
        boolean strong = (selRank != null && selRank <= capStrongRank);
        return trailFromCap(maxProfitRate, strong ? Configs.TS_MAX_GAP : Configs.TS_MAX_GAP_WEAK);
    }

    public static Float calRateMinWithPredReturn15MForTradingStop(Float predReturn15M) {
        // FROZEN v1 (2026-08-24): BỎ TS_DYNAMIC_K — ngưỡng arm = RATE_PROFIT_STOP_MARKET thuần.
        // (giữ tham số để không vỡ chữ ký caller; giá trị predReturn15M không còn tác động.)
        // [C3-SHADOW (a)] LIVE_PROFILE=c3_shadow -> nguong arm 0.07 (C3) thay 0.05 (live 242).
        // Co TAT (mac dinh) -> tra dung Configs.RATE_PROFIT_STOP_MARKET nhu HEAD.
        return com.binance.chuyennd.tradecore.selector.LiveProfileC3.armRate(Configs.RATE_PROFIT_STOP_MARKET);
    }

    /**
     * [L3 LEGACY 2026-09-06] Nhu tren nhung THEO SYMBOL: symbol LEGACY (vi the THAT cu tren 242)
     * LUON tra nguong HEAD {@code Configs.RATE_PROFIT_STOP_MARKET} ke ca khi
     * {@code LIVE_PROFILE=c3_shadow} bat. Chi symbol cua SO GIAY moi an nguong C3 0.07.
     */
    public static Float calRateMinWithPredReturn15MForTradingStop(Float predReturn15M, String symbol) {
        return com.binance.chuyennd.tradecore.selector.LiveProfileC3.armRateFor(
                symbol, Configs.RATE_PROFIT_STOP_MARKET);
    }

    public static Float managerBudget(Float budget, Float marginRunning, Float balanceBasic,
                                      MarketLevelChange levelChange) {


        // FROZEN v1 (2026-08-24): thay logic vách rời rạc (/3 /4 + ratio-tier = overfit) bằng
        //   THROTTLE LIÊN TỤC + trần margin cứng. 2 gene: F_BASE (% equity/lệnh) + U_MAX (trần margin).
        //     U = margin đang dùng / equity; U ≥ U_MAX → chặn lệnh mới (null).
        //     throttle = clamp(1 − U/U_MAX, 0, 1)  (càng gần trần càng nhỏ, KHÔNG vách).
        //     budget = equity × F_BASE × throttle / dcaGridTotalWeight()  (chừa chỗ đủ ladder DCA).
        if (balanceBasic == null || balanceBasic <= 0f) return null;
        float used = marginRunning != null ? marginRunning : 0f;
        float u = used / balanceBasic;
        if (u >= Configs.U_MAX) return null;
        float throttle = 1f - u / Configs.U_MAX;
        if (throttle < 0f) throttle = 0f; else if (throttle > 1f) throttle = 1f;
        float ladder = Configs.dcaGridTotalWeight();
        if (ladder <= 0f) ladder = 1f;
        return balanceBasic * Configs.F_BASE * throttle / ladder;
    }
}
