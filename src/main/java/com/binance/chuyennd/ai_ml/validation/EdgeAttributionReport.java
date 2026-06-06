package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.research.OrderTargetInfoTest;

import java.util.*;

/**
 * EdgeAttributionReport — tách CHẤT LƯỢNG ENTRY (leg đầu) khỏi cứu trợ DCA.
 *
 * Dùng chung cho các harness funding (monotonicity, ablation). Đọc allOrderDone (mỗi phần tử là 1 LEG;
 * leg đầu của 1 cụm có marketLevelChange = path mở cụm, leg DCA = DCA_LEVEL1). KHÔNG đo ở mức cụm
 * (DCA che chất lượng entry) — chỉ đo LEG ĐẦU theo path.
 *
 * MAE (Maximum Adverse Excursion) của 1 leg = (maeLow - priceEntry) / priceEntry — % sụt sâu nhất so
 * với GIÁ VÀO của chính leg đó. maeLow = đáy THẬT của cụm tính từ leg đầu (chỉ đi xuống, KHÔNG reset-lên).
 * CỐ Ý KHÔNG dùng minPrice: minPrice là tham chiếu trailing-stop, bị reset lên ở updateStatusNew/
 * updateTPSL/mergeOrder nên hụt MAE (verify: chỉ ~4.7% khớp đáy thật). Số ÂM = sụt.
 *
 * Mọi PnL lấy từ OrderTargetInfoTest.calTp() (đã net slippage 2 chân + fee sàn).
 */
public final class EdgeAttributionReport {

    private EdgeAttributionReport() {}

    /** Thống kê chất lượng 1 tập leg đầu. avgMaePct/worstMaePct là % (âm = sụt). */
    public static class LegStats {
        public int count = 0;
        public double avgMaePct = 0, worstMaePct = 0;   // % (âm)
        public double winRate = 0;                       // tỉ lệ leg có calTp > 0
        public double totalPnl = 0, avgPnl = 0;          // net
        public double payoff = 0;                        // avg(win) / avg(|loss|)
    }

    /** MAE% THẬT của 1 leg = (maeLow - entry)/entry. Âm = sụt. maeLow = đáy cụm từ leg đầu (không reset-lên).
     *  Fallback về minPrice cho dữ liệu cũ chưa có maeLow (order.data sinh trước khi thêm field). */
    public static float legMaePct(OrderTargetInfoTest o) {
        if (o.priceEntry == null || o.priceEntry <= 0) return 0f;
        Float low = (o.maeLow != null) ? o.maeLow : o.minPrice;
        if (low == null) return 0f;
        return (low - o.priceEntry) / o.priceEntry;
    }

    /** MAE% CŨ (SAI) dựa trên minPrice — CHỈ để đối chứng old vs new trong harness verify, đừng dùng để báo cáo. */
    public static float legMaePctOld(OrderTargetInfoTest o) {
        if (o.priceEntry == null || o.priceEntry <= 0 || o.minPrice == null) return 0f;
        return (o.minPrice - o.priceEntry) / o.priceEntry;
    }

    /** Lọc các LEG ĐẦU theo path (marketLevelChange == level). */
    public static List<OrderTargetInfoTest> firstLegsOf(Collection<OrderTargetInfoTest> allLegs, MarketLevelChange level) {
        List<OrderTargetInfoTest> out = new ArrayList<>();
        for (OrderTargetInfoTest o : allLegs) {
            if (o.marketLevelChange == level) out.add(o);
        }
        return out;
    }

    /** Thống kê first-leg cho 1 tập leg. */
    public static LegStats stats(Collection<OrderTargetInfoTest> legs) {
        LegStats s = new LegStats();
        s.count = legs.size();
        if (s.count == 0) return s;
        double sumMae = 0, worst = 0, sumPnl = 0, sumWin = 0, sumLossAbs = 0;
        int nWin = 0, nLoss = 0;
        for (OrderTargetInfoTest o : legs) {
            float mae = legMaePct(o);
            sumMae += mae;
            if (mae < worst) worst = mae;
            float pnl = o.calTp();
            sumPnl += pnl;
            if (pnl > 0) { sumWin += pnl; nWin++; } else { sumLossAbs += -pnl; nLoss++; }
        }
        s.avgMaePct = sumMae / s.count;
        s.worstMaePct = worst;
        s.totalPnl = sumPnl;
        s.avgPnl = sumPnl / s.count;
        s.winRate = (double) nWin / s.count;
        double avgWin = nWin > 0 ? sumWin / nWin : 0;
        double avgLoss = nLoss > 0 ? sumLossAbs / nLoss : 0;
        s.payoff = avgLoss > 0 ? avgWin / avgLoss : (avgWin > 0 ? Double.POSITIVE_INFINITY : 0);
        return s;
    }

    /**
     * Tỉ lệ cụm được DCA CỨU: trong các cụm mà leg đầu chìm sâu (MAE <= maeThreshold, vd -0.05),
     * tỉ lệ cụm đóng có LÃI (tổng calTp cụm > 0). Gom cụm theo (symbolId + '@' + timeUpdate)
     * — mọi leg cùng cụm chia chung timeUpdate lúc đóng. (Dùng cho ablation A vs SHUFFLE.)
     */
    public static double dcaRescueRate(Collection<OrderTargetInfoTest> allLegs, float maeThreshold) {
        Map<String, List<OrderTargetInfoTest>> clusters = new HashMap<>();
        for (OrderTargetInfoTest o : allLegs) {
            clusters.computeIfAbsent(o.symbolId + "@" + o.timeUpdate, k -> new ArrayList<>()).add(o);
        }
        int deep = 0, rescued = 0;
        for (List<OrderTargetInfoTest> legs : clusters.values()) {
            OrderTargetInfoTest first = null;
            float clusterPnl = 0;
            for (OrderTargetInfoTest o : legs) {
                clusterPnl += o.calTp();
                if (first == null || o.timeStart < first.timeStart) first = o;
            }
            if (first != null && legMaePct(first) <= maeThreshold) {
                deep++;
                if (clusterPnl > 0) rescued++;
            }
        }
        return deep > 0 ? (double) rescued / deep : 0.0;
    }
}
