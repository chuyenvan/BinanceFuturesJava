package com.binance.chuyennd.ai_ml.validation.ablation.dca;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * TASK-006.1 — scenario stress-test TẦNG DCA trên cú về-0 của LUNA (2022).
 *
 * Cô lập 1 cụm long-only LUNA. TÁI DÙNG logic thật:
 *  - {@link DcaUtils#shouldDca} — quyết định nhồi (BIG_DOWN: isAll=true, ngưỡng DCA_LOSS_BIG_DOWN=-0.15,
 *    giãn DCA_TIME_BIG_DOWN=8' tính từ leg cuối).
 *  - {@link TradeUtils#managerBudget} — sizing DE-escalating (base / DIVIDER theo marginRatio; null khi >=0.99).
 *  - sao y avgEntry vol-weighted (mergeOrder: Σ(entry·qty)/Σqty) + veto cap (createOrderBUY L543-552:
 *    clusterDd=(close-avgEntry)/avgEntry <= BREAKER_CLUSTER_DD_MAX -0.30 => chặn leg).
 *
 * Chạy 2 lần: cap OFF vs ON(-0.30). Đọc CSV data.binance.vision, KHÔNG đụng Aerospike/242/prediction.
 * ⚠️ Deviation có chủ đích (cô lập tầng DCA): qty=budget·lev/entry KHÔNG normalize (LUNA delist, không có
 *    exchange-info); tierMultiplier=1.0; marginRunning = margin RIÊNG cụm này (không có cụm khác); ép cụm
 *    BIG_DOWN thủ công (bỏ entry-signal/gate/prediction). Đây là test CƠ CHẾ 1 coin, KHÔNG phải tần suất 5 năm.
 */
public class LunaDcaScenario {

    private static final Logger LOG = LoggerFactory.getLogger(LunaDcaScenario.class);

    private static final String CSV_DIR = "luna_csv/";
    private static final String[] CSV_FILES = {
            "LUNAUSDT-1m-2022-03.csv", "LUNAUSDT-1m-2022-04.csv", "LUNAUSDT-1m-2022-05.csv"};
    private static final double BALANCE_BASIC = 35000d;                 // vốn (Configs CAPITAL_START)
    private static final double BASE_BUDGET = BALANCE_BASIC / Configs.number_order_budget; // = vốn/50 = 700
    private static final int LEVERAGE = Configs.LEVERAGE_ORDER;          // = 1

    /** 1 nến: thời gian (ms), close, low. */
    private static class Bar { long t; double close, low; }

    public static void main(String[] args) {
        try {
            List<Bar> bars = loadBars();
            if (bars.isEmpty()) { LOG.error("⛔ Không đọc được nến LUNA — kiểm tra {}.", CSV_DIR); return; }
            LOG.info("📥 LUNA bars={} | từ close={} (t0) → close={} (cuối). BASE_BUDGET={} vốn={} lev={}",
                    bars.size(), bars.get(0).close, bars.get(bars.size() - 1).close,
                    BASE_BUDGET, BALANCE_BASIC, LEVERAGE);

            // === ADR-0008 bước 3: so các CAP NEO-CỐ-ĐỊNH (mốc không trôi theo nhồi) vs cap cũ vô hiệu ===
            // mỗi Policy bật ĐÚNG 1 ràng buộc để cô lập tác động.
            List<Result> results = new ArrayList<>();
            results.add(run(bars, Policy.off()));
            results.add(run(bars, Policy.capAvgEntry(-0.30f)));   // cũ (ADR-0008: vô hiệu cấu trúc)
            results.add(run(bars, Policy.ddVsFirst(-0.30f)));     // (i) DD vs entry-đầu (mốc cố định)
            results.add(run(bars, Policy.ddVsFirst(-0.50f)));     // (i) nới hơn
            results.add(run(bars, Policy.maxLegs(5)));            // (ii) trần 5 leg
            results.add(run(bars, Policy.maxLegs(10)));           // (ii) trần 10 leg
            results.add(run(bars, Policy.maxCapital(0.05f)));     // (iii) trần 5% vốn/cụm
            results.add(run(bars, Policy.maxCapital(0.10f)));     // (iii) trần 10% vốn/cụm
            printTable(results);
        } catch (Exception e) {
            LOG.error("LunaDcaScenario lỗi", e);
        }
    }

    /** Mô tả ràng buộc cap để cô lập từng cơ chế. */
    private static class Policy {
        String name;
        boolean capAvgEntry = false; float avgEntryThres = 0f;   // cũ: (close-avgEntry)/avgEntry <= thres
        boolean ddVsFirst = false;   float firstThres = 0f;      // (i): (close-entryFirst)/entryFirst <= thres
        boolean maxLegs = false;     int legCap = 0;             // (ii): tổng leg <= legCap
        boolean maxCapital = false;  float capRatio = 0f;        // (iii): clusterMargin/balance >= ratio => ngừng

        static Policy off() { Policy p = new Policy(); p.name = "OFF"; return p; }
        static Policy capAvgEntry(float t) { Policy p = new Policy(); p.name = "cũ avgEntry " + t; p.capAvgEntry = true; p.avgEntryThres = t; return p; }
        static Policy ddVsFirst(float t) { Policy p = new Policy(); p.name = "(i) ddVsFirst " + t; p.ddVsFirst = true; p.firstThres = t; return p; }
        static Policy maxLegs(int n) { Policy p = new Policy(); p.name = "(ii) maxLegs " + n; p.maxLegs = true; p.legCap = n; return p; }
        static Policy maxCapital(float r) { Policy p = new Policy(); p.name = "(iii) maxCap " + (int)(r*100) + "%"; p.maxCapital = true; p.capRatio = r; return p; }
    }

    /** Một run với 1 Policy cap. */
    private static Result run(List<Bar> bars, Policy pol) {
        List<double[]> legs = new ArrayList<>();   // [entry, qty]
        // leg đầu: ÉP mở BIG_DOWN tại t0 (bỏ entry-signal/gate). budget qua managerBudget (marginRatio=0).
        Bar b0 = bars.get(0);
        Float bud0 = TradeUtils.managerBudget((float) BASE_BUDGET, 0f, (float) BALANCE_BASIC, MarketLevelChange.BIG_DOWN);
        legs.add(new double[]{b0.close, bud0 / LEVERAGE / b0.close});   // qty = budget·lev/entry (lev=1)

        double entryFirst = b0.close;
        long lastLegTime = b0.t;
        MarketLevelChange lastLevel = MarketLevelChange.BIG_DOWN;   // = mergeOrder: level của leg cuối
        int nhoi = 0, veto = 0;
        double clusterDdMax = 0d;     // (close-avgEntry)/avgEntry âm nhất gặp
        double maxDdCluster = 0d;     // unrealized âm nhất (mark theo low)
        boolean stoppedByMargin = false;

        for (Bar bar : bars) {
            double[] cl = cluster(legs);          // {avgEntry, totalQty, clusterMargin}
            double avgEntry = cl[0], totalQty = cl[1], clusterMargin = cl[2];

            // đo DD theo đáy nến (mark-to-market xấu nhất trong phút)
            double unrealLow = totalQty * (bar.low - avgEntry);
            if (unrealLow < maxDdCluster) maxDdCluster = unrealLow;
            double ddClose = (bar.close - avgEntry) / avgEntry;
            if (ddClose < clusterDdMax) clusterDdMax = ddClose;

            if (bar.t <= lastLegTime) continue;   // bỏ qua chính nến mở leg gần nhất

            // (1) shouldDca? — TÁI DÙNG logic thật. currentRateLoss = (close-avgEntry)/avgEntry.
            float rateLoss = (float) ((bar.close - avgEntry) / avgEntry);
            boolean should = DcaUtils.shouldDca((float) clusterMargin, rateLoss, lastLevel, lastLegTime,
                    MarketLevelChange.BIG_DOWN, bar.t, (float) BASE_BUDGET);
            if (!should) continue;

            // (2) veto CAP theo Policy — cô lập từng cơ chế.
            double ddFirst = (bar.close - entryFirst) / entryFirst;
            double capRatioNow = clusterMargin / BALANCE_BASIC;
            if (pol.capAvgEntry && ddClose <= pol.avgEntryThres) { veto++; continue; }
            if (pol.ddVsFirst && ddFirst <= pol.firstThres) { veto++; continue; }
            if (pol.maxLegs && legs.size() >= pol.legCap) { veto++; continue; }
            if (pol.maxCapital && capRatioNow >= pol.capRatio) { veto++; continue; }

            // (3) sizing — TÁI DÙNG managerBudget. null => marginRatio>=0.99 => DỪNG nhồi (giữ cụm).
            Float bud = TradeUtils.managerBudget((float) BASE_BUDGET, (float) clusterMargin,
                    (float) BALANCE_BASIC, MarketLevelChange.BIG_DOWN);
            if (bud == null) { stoppedByMargin = true; continue; }

            legs.add(new double[]{bar.close, bud / LEVERAGE / bar.close});
            nhoi++;
            lastLegTime = bar.t;
            lastLevel = MarketLevelChange.DCA_LEVEL1;   // leg DCA => level cuối = DCA_LEVEL1 (giãn 8')
        }

        double[] fin = cluster(legs);
        Result r = new Result();
        r.name = pol.name;
        r.nhoi = nhoi;
        r.veto = veto;
        r.legs = legs.size();
        r.clusterMargin = fin[2];
        r.avgEntryLast = fin[0];
        r.entryFirst = entryFirst;
        r.totalQty = fin[1];
        Bar last = bars.get(bars.size() - 1);
        r.finalLoss = fin[1] * (last.close - fin[0]);   // mark-to-market giá cuối (~0)
        r.maxDdCluster = maxDdCluster;
        r.clusterDdMax = clusterDdMax;
        r.pctCapitalLost = -r.finalLoss / BALANCE_BASIC * 100d;
        r.stoppedByMargin = stoppedByMargin;
        return r;
    }

    /** Trả {avgEntry vol-weighted, totalQty, clusterMargin=Σentry·qty/lev}. */
    private static double[] cluster(List<double[]> legs) {
        double sumEntryQty = 0d, sumQty = 0d;
        for (double[] l : legs) { sumEntryQty += l[0] * l[1]; sumQty += l[1]; }
        double avgEntry = sumEntryQty / sumQty;
        return new double[]{avgEntry, sumQty, sumEntryQty / LEVERAGE};
    }

    private static List<Bar> loadBars() throws Exception {
        List<Bar> bars = new ArrayList<>();
        for (String f : CSV_FILES) {
            try (BufferedReader br = new BufferedReader(new FileReader(CSV_DIR + f))) {
                String line;
                while ((line = br.readLine()) != null) {
                    String[] c = line.split(",");
                    if (c.length < 5) continue;
                    long t;
                    try { t = Long.parseLong(c[0].trim()); } catch (NumberFormatException e) { continue; } // bỏ header
                    Bar b = new Bar();
                    b.t = t; b.low = Double.parseDouble(c[3]); b.close = Double.parseDouble(c[4]);
                    bars.add(b);
                }
            }
        }
        bars.sort((a, b) -> Long.compare(a.t, b.t));
        return bars;
    }

    private static void printTable(List<Result> rs) {
        LOG.info("\n\n================= 📊 LUNA DCA SCENARIO — so các CAP NEO-CỐ-ĐỊNH (cô lập 1 cụm LUNA→0) =================");
        LOG.info(String.format(Locale.US, "%-18s | %5s %5s | %12s | %12s | %8s | %12s | %11s",
                "POLICY", "#nhồi", "veto", "tổng vốn cụm", "lỗ cuối", "%vốn mất", "maxDD cụm", "clusterDd-max"));
        for (Result r : rs) row(r);
        LOG.info("----------------------------------------------------------------------------------------------------");
        LOG.info("CÁCH ĐỌC:");
        LOG.info(" - OFF/cũ avgEntry: chứng cứ ADR-0008 — cap-vs-avgEntry veto nhiều nhưng %vốn mất ~ y hệt OFF (vô hiệu cấu trúc).");
        LOG.info(" - (i) ddVsFirst / (ii) maxLegs / (iii) maxCap: mốc CỐ ĐỊNH → veto SỚM khi giá còn cao → %vốn mất GIẢM THẬT.");
        LOG.info(" - So '%vốn mất' giữa các policy: cái nào kéo {}%% (OFF) xuống thấp nhất = cap cứu ruin tốt nhất. ⚠️ 1 coin, KHÔNG phải tác động tổng 5 năm.", "~79");
    }

    private static void row(Result r) {
        LOG.info(String.format(Locale.US, "%-18s | %5d %5d | %12.0f | %12.0f | %7.1f%% | %12.0f | %11.3f%s",
                r.name, r.nhoi, r.veto, r.clusterMargin, r.finalLoss,
                r.pctCapitalLost, r.maxDdCluster, r.clusterDdMax,
                r.stoppedByMargin ? "  [dừng margin≥0.99]" : ""));
    }

    private static class Result {
        String name;
        boolean stoppedByMargin;
        int nhoi, veto, legs;
        double clusterMargin, finalLoss, maxDdCluster, pctCapitalLost, clusterDdMax, avgEntryLast, entryFirst, totalQty;
    }
}
