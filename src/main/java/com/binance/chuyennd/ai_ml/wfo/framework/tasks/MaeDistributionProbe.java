package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
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
 * TASK (2026-08-01) — DO PHAN PHOI MAE (max adverse excursion) tren tap entry ma SELECTOR chon.
 *
 * <p>MUC DICH (Uni chi ra): selector chon coin bien dong manh (pump 500%) — chinh nhom do cung co the
 * DUMP 3-4 lan (-67% .. -75%). Voi thiet ke hold-to-die, dat moc DCA bang PHAN DOAN la hong ca cau truc.
 * Phai do THUC TE coin di sau bao nhieu, roi suy ra grid + ti trong tu du lieu.
 *
 * <p>Toan hoc da tinh tay (vao 100, coin sap ve 25 = dump 4x):
 * <pre>
 *   khong DCA                    -> avgEntry 100.0, can hoi +300% de hoa von
 *   grid deu   -15/-30/-45 1:1:1:1 -> avgEntry  73.8, can +195%
 *   grid gian  -15/-30/-60 1:1:1:1 -> avgEntry  65.5, can +162%
 *   grid sau   -20/-40/-70 1:1:1:1 -> avgEntry  55.2, can +121%
 *   DON DUOI   -20/-40/-70 1:1:2:6 -> avgEntry  39.1, can  +56%   <-- TI TRONG quan trong hon MOC
 * </pre>
 *
 * <p>DO GI: gom leg thanh CUM theo (symbol, timeUpdate) — cac leg cung cum chia se timeUpdate/maeLow/
 * priceTP do closeOrder chep sang. Voi moi cum tinh:
 * <ul>
 *   <li>MAE = maeLow / firstEntryPrice - 1  (day sau nhat so GIA VAO DAU, KHONG phai avgEntry)</li>
 *   <li>ket cuc = priceTP / avgEntry - 1    (cum lai hay lo khi dong / mark-to-market cuoi ky)</li>
 *   <li>so leg, thoi gian giu</li>
 * </ul>
 * Tach rieng BTC/ETH vs ALT de tra loi: co can PHAN TANG coin khong.
 */
public class MaeDistributionProbe {
    private static final Logger LOG = LoggerFactory.getLogger(MaeDistributionProbe.class);

    private static final double[] BUCKETS = {-0.10, -0.20, -0.30, -0.40, -0.50, -0.60, -0.70, -0.80, -0.90};

    static class Cluster {
        String symbol; double firstEntry, avgEntry, maeLow, priceTP;
        int nLegs; long tStart, tEnd; double notional;
    }

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/kaggle/working/wfo_ds");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());

        String from = System.getenv().getOrDefault("MAE_FROM", "20210101");
        String to   = System.getenv().getOrDefault("MAE_TO",   "20260501");
        long t0 = Utils.sdfFile.parse(from).getTime() + 7 * Utils.TIME_HOUR;
        long t1 = Utils.sdfFile.parse(to).getTime()   + 7 * Utils.TIME_HOUR;
        LOG.info("Range {}..{} | rate-min={} | DCA {}", from, to,
                Configs.RATE_PROFIT_STOP_MARKET, Configs.WFO_DISABLE_DCA ? "OFF" : "ON");

        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        AIRejectFilter.resetCounters();
        SimulatorMarketLevelTicker1MStopLoss.resetAuditCounters();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
        sim.simulatorWithInitEntry(t0, t1);
        LOG.info("SIM xong. legs={} audit={}", sim.allOrderDone.size(),
                SimulatorMarketLevelTicker1MStopLoss.auditCountersSummary());

        // ---- gom leg -> cum theo (symbol, timeUpdate) ----
        Map<String, Cluster> clusters = new HashMap<>();
        for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
            if (o.symbol == null || o.priceEntry == null || o.quantity == null) continue;
            String key = o.symbol + "@" + o.timeUpdate;
            Cluster c = clusters.get(key);
            if (c == null) {
                c = new Cluster();
                c.symbol = o.symbol;
                c.firstEntry = (o.firstEntryPrice != null) ? o.firstEntryPrice : o.priceEntry;
                c.maeLow = (o.maeLow != null) ? o.maeLow : o.priceEntry;
                c.priceTP = (o.priceTP != null) ? o.priceTP : o.lastPrice;
                c.tStart = o.timeStart; c.tEnd = o.timeUpdate;
                clusters.put(key, c);
            }
            // firstEntry = min timeStart cua cac leg
            if (o.timeStart < c.tStart) {
                c.tStart = o.timeStart;
                if (o.firstEntryPrice != null) c.firstEntry = o.firstEntryPrice;
            }
            c.nLegs++;
            c.notional += o.quantity * o.priceEntry;
            c.avgEntry += o.quantity * o.priceEntry;   // tam thoi = tong notional
        }
        // avgEntry = tong notional / tong qty -> can tong qty; tinh lai vong 2
        Map<String, Double> qty = new HashMap<>();
        for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
            if (o.symbol == null || o.quantity == null) continue;
            qty.merge(o.symbol + "@" + o.timeUpdate, (double) o.quantity, Double::sum);
        }
        for (Map.Entry<String, Cluster> e : clusters.entrySet()) {
            double q = qty.getOrDefault(e.getKey(), 0.0);
            if (q > 0) e.getValue().avgEntry = e.getValue().notional / q;
        }

        List<Cluster> all = new ArrayList<>(clusters.values());
        LOG.info("Gom duoc {} CUM tu {} leg (trung binh {} leg/cum)",
                all.size(), sim.allOrderDone.size(),
                String.format("%.2f", all.isEmpty() ? 0 : (double) sim.allOrderDone.size() / all.size()));

        report("TAT CA", all);
        report("BTC+ETH", filter(all, true));
        report("ALT", filter(all, false));

        LOG.info("========== HET MAE-DISTRIBUTION ==========");
        System.exit(0);
    }

    private static List<Cluster> filter(List<Cluster> in, boolean majorOnly) {
        List<Cluster> out = new ArrayList<>();
        for (Cluster c : in) {
            boolean major = c.symbol.startsWith("BTC") || c.symbol.startsWith("ETH");
            if (major == majorOnly) out.add(c);
        }
        return out;
    }

    private static void report(String title, List<Cluster> cs) {
        if (cs.isEmpty()) { LOG.info("--- {} : KHONG CO CUM ---", title); return; }
        LOG.info("");
        LOG.info("================ {} : {} cum ================", title, cs.size());
        LOG.info(String.format("%10s %8s %8s %10s %10s %10s %12s",
                "MAE sau hon", "so cum", "%tong", "%hoa von", "%lai", "leg tb", "giu tb (ngay)"));
        for (double b : BUCKETS) {
            List<Cluster> hit = new ArrayList<>();
            for (Cluster c : cs) {
                double mae = c.maeLow / c.firstEntry - 1.0;
                if (mae <= b) hit.add(c);
            }
            if (hit.isEmpty()) {
                LOG.info(String.format("%9.0f%% %8d %7.2f%% %10s %10s %10s %12s", b * 100, 0, 0.0, "-", "-", "-", "-"));
                continue;
            }
            int recovered = 0, profit = 0; double legs = 0, days = 0;
            for (Cluster c : hit) {
                double outcome = c.priceTP / c.avgEntry - 1.0;
                if (c.priceTP >= c.firstEntry) recovered++;   // ve lai GIA VAO DAU
                if (outcome > 0) profit++;                     // lai so avgEntry (nho DCA)
                legs += c.nLegs;
                days += (c.tEnd - c.tStart) / 86400000.0;
            }
            LOG.info(String.format("%9.0f%% %8d %7.2f%% %9.1f%% %9.1f%% %10.2f %12.1f",
                    b * 100, hit.size(), 100.0 * hit.size() / cs.size(),
                    100.0 * recovered / hit.size(), 100.0 * profit / hit.size(),
                    legs / hit.size(), days / hit.size()));
        }
        // percentile MAE
        double[] maes = new double[cs.size()];
        for (int i = 0; i < cs.size(); i++) maes[i] = cs.get(i).maeLow / cs.get(i).firstEntry - 1.0;
        Arrays.sort(maes);
        LOG.info("MAE percentile: p50={}%  p75={}%  p90={}%  p95={}%  p99={}%  worst={}%",
                pct(maes, 0.50), pct(maes, 0.25), pct(maes, 0.10), pct(maes, 0.05), pct(maes, 0.01),
                String.format("%.1f", maes[0] * 100));
        LOG.info("CSVMAE,{},{},{},{},{},{},{}", title, cs.size(),
                pct(maes, 0.50), pct(maes, 0.25), pct(maes, 0.10), pct(maes, 0.05), pct(maes, 0.01));
    }

    private static String pct(double[] sortedAsc, double q) {
        int i = (int) Math.floor(q * (sortedAsc.length - 1));
        return String.format("%.1f", sortedAsc[Math.max(0, Math.min(i, sortedAsc.length - 1))] * 100);
    }
}
