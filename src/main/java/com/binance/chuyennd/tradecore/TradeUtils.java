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
        float gap = Math.min(maxProfitRate * Configs.TS_GIVEBACK_RATIO, maxGap);
        float rate = maxProfitRate - gap;
        float step = 0.005f;
        rate = Math.round(rate / step) * step;
        return rate;
    }

    public static Float calRateMinWithPredReturn15MForTradingStop(Float predReturn15M) {
        // FROZEN v1 (2026-08-24): BỎ TS_DYNAMIC_K — ngưỡng arm = RATE_PROFIT_STOP_MARKET thuần.
        // (giữ tham số để không vỡ chữ ký caller; giá trị predReturn15M không còn tác động.)
        return Configs.RATE_PROFIT_STOP_MARKET;
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
