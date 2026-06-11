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
import java.util.Arrays;
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
            LOG.info("🔒 Cap ON dùng BREAKER_CLUSTER_DD_MAX={} | nhồi BIG_DOWN: DCA_LOSS_BIG_DOWN={} DCA_TIME_BIG_DOWN={}'",
                    Configs.BREAKER_CLUSTER_DD_MAX, Configs.DCA_LOSS_BIG_DOWN, Configs.DCA_TIME_BIG_DOWN);

            Result off = run(bars, false);
            Result on = run(bars, true);
            printTable(off, on);
        } catch (Exception e) {
            LOG.error("LunaDcaScenario lỗi", e);
        }
    }

    /** Một run: cap OFF (capOn=false) hoặc ON (capOn=true). */
    private static Result run(List<Bar> bars, boolean capOn) {
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

            // (2) veto CAP (chỉ ON) — sao y createOrderBUY L546-550.
            if (capOn && ddClose <= Configs.BREAKER_CLUSTER_DD_MAX) { veto++; continue; }

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
        r.capOn = capOn;
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

    private static void printTable(Result off, Result on) {
        LOG.info("\n\n================= 📊 LUNA DCA SCENARIO (cô lập 1 cụm, OFF vs cap ON -0.30) =================");
        LOG.info(String.format(Locale.US, "%-10s | %5s %4s | %12s | %12s | %12s | %8s | %11s | %11s | %10s",
                "MODE", "#nhồi", "veto", "tổng vốn cụm", "lỗ cuối", "maxDD cụm", "%vốn mất", "clusterDd-max", "avgEntry-cuối", "entry-đầu"));
        row(off);
        row(on);
        LOG.info("------------------------------------------------------------------------------------------");
        LOG.info("CÁCH ĐỌC:");
        LOG.info(" - clusterDd-max = đáy (close-avgEntry)/avgEntry. Nếu KHÔNG bao giờ ≤ -0.30 ⇒ cap (DCA mode) " +
                "KHÔNG bao giờ veto ⇒ cap vô dụng vì DCA hạ avgEntry bám giá. veto>0 ⇒ cap CÓ chặn.");
        LOG.info(" - lỗ cuối ~ -tổng vốn cụm (LUNA→0). %vốn mất = phần vốn {} bay theo cú về-0.", (long) BALANCE_BASIC);
        LOG.info(" - ON vs OFF: cap cắt bớt #nhồi/tổng vốn/lỗ bao nhiêu. ⚠️ 1 coin, KHÔNG phải tác động tổng 5 năm.");
    }

    private static void row(Result r) {
        LOG.info(String.format(Locale.US, "%-10s | %5d %4d | %12.0f | %12.0f | %12.0f | %7.1f%% | %11.3f | %11.5f | %10.4f%s",
                r.capOn ? "ON(-0.30)" : "OFF", r.nhoi, r.veto, r.clusterMargin, r.finalLoss, r.maxDdCluster,
                r.pctCapitalLost, r.clusterDdMax, r.avgEntryLast, r.entryFirst,
                r.stoppedByMargin ? "  [dừng do margin≥0.99]" : ""));
    }

    private static class Result {
        boolean capOn, stoppedByMargin;
        int nhoi, veto, legs;
        double clusterMargin, finalLoss, maxDdCluster, pctCapitalLost, clusterDdMax, avgEntryLast, entryFirst, totalQty;
    }
}
