package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * TASK-138 — Validate K2 (cờ đỏ đuôi phải) có phải LEAK không.
 *
 * <p>Giả thuyết leak: nếu top-PnL lệnh biết trước tương lai, chúng sẽ có MAE≈0 (không bao giờ lỗ tạm
 * trước khi thắng) — vì đã "biết" giá sẽ lên. Lệnh THẬT (không leak) phải có MAE âm đáng kể (chịu lỗ tạm
 * trước khi hồi). So MAE của top 5% lệnh vs phần còn lại:
 *   - top-PnL có MAE≈0 hoặc dương → NGHI LEAK (biết trước, không chịu drawdown).
 *   - top-PnL có MAE âm tương tự phần còn lại → KHÔNG leak, đúng long-vol (chịu lỗ tạm rồi pump).
 * Cũng đo holding time: leak thường vào-ra rất nhanh đúng đỉnh.
 */
public class TailLeakProbe {
    private static final Logger LOG = LoggerFactory.getLogger(TailLeakProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());

        long from = Utils.sdfFile.parse("20210101").getTime() + 7 * Utils.TIME_HOUR;
        long to = Utils.sdfFile.parse("20260501").getTime() + 7 * Utils.TIME_HOUR;
        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        AIRejectFilter.resetCounters();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
        sim.simulatorWithInitEntry(from, to);

        // gom lệnh PRED với: pnl, MAE% (maeLow so entry), holding (phút)
        List<double[]> rows = new ArrayList<>(); // [pnl, maePct, holdMin]
        for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
            if (o.marketLevelChange != MarketLevelChange.PREDICT_SYMBOL_TRADE) continue;
            if (o.priceEntry == null || o.priceEntry == 0) continue;
            double pnl = o.calTp();
            double maePct = (o.maeLow != null) ? (o.maeLow - o.priceEntry) / o.priceEntry * 100 : 0;
            double holdMin = (o.timeUpdate - o.timeStart) / 60000.0;
            rows.add(new double[]{pnl, maePct, holdMin});
        }
        LOG.info("Tổng lệnh PRED: {}", rows.size());

        // sắp theo pnl giảm dần
        rows.sort((a, b) -> Double.compare(b[0], a[0]));
        int n = rows.size();
        int top5 = Math.max(1, n / 20);

        // MAE trung bình + median cho top 5% vs phần còn lại
        double[] topMae = new double[top5];
        for (int i = 0; i < top5; i++) topMae[i] = rows.get(i)[1];
        double[] restMae = new double[n - top5];
        for (int i = top5; i < n; i++) restMae[i - top5] = rows.get(i)[1];

        LOG.info("========== K2-LEAK CHECK: MAE (max adverse excursion %) ==========");
        LOG.info("  TOP 5% lệnh ({}) : MAE trung bình={}%  median={}%  | %lệnh có MAE≈0 (>-0.5%)={}%",
                top5, fmt(mean(topMae)), fmt(median(topMae)), fmt(pctNearZero(topMae)));
        LOG.info("  PHẦN CÒN LẠI ({}) : MAE trung bình={}%  median={}%  | %lệnh có MAE≈0={}%",
                n - top5, fmt(mean(restMae)), fmt(median(restMae)), fmt(pctNearZero(restMae)));
        LOG.info("  => Nếu top MAE≈0 mà rest MAE âm sâu → NGHI LEAK. Nếu cả 2 âm tương tự → KHÔNG leak (long-vol thật).");

        // holding time
        double[] topHold = new double[top5];
        for (int i = 0; i < top5; i++) topHold[i] = rows.get(i)[2];
        double[] restHold = new double[n - top5];
        for (int i = top5; i < n; i++) restHold[i - top5] = rows.get(i)[2];
        LOG.info("========== HOLDING TIME (phút) ==========");
        LOG.info("  TOP 5% : median hold={} phút | PHẦN CÒN LẠI : median hold={} phút",
                fmt(median(topHold)), fmt(median(restHold)));
        LOG.info("========== HET TAIL-LEAK ==========");
    }

    private static double mean(double[] a) { double s = 0; for (double v : a) s += v; return a.length > 0 ? s / a.length : 0; }
    private static double median(double[] a) {
        if (a.length == 0) return 0;
        double[] c = a.clone(); Arrays.sort(c); int m = c.length / 2;
        return c.length % 2 == 1 ? c[m] : (c[m-1] + c[m]) / 2;
    }
    private static double pctNearZero(double[] a) {
        if (a.length == 0) return 0;
        int cnt = 0; for (double v : a) if (v > -0.5) cnt++;
        return 100.0 * cnt / a.length;
    }
    private static String fmt(double d) { return String.format("%.2f", d); }
}
