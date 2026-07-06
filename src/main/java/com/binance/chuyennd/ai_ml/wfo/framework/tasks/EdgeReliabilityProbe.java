package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
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
 * TASK-136 — Điều tra ĐỘ TIN CẬY edge (nghi edge đo sai). Chạy backtest toàn kỳ, config baseline,
 * lấy allOrderDone, phân tích 4 kiểu "đo sai":
 *   K1 mẫu nhỏ/tập trung: phân bố lệnh theo THÁNG + theo COIN (bao nhiêu sự kiện độc lập).
 *   K2 vài lệnh khổng lồ gánh PnL: top 1%/5%/10% lệnh đóng góp bao nhiêu %; bỏ top ra còn lãi không.
 *   K3 win/loss & payoff: win-rate, lãi TB thắng, lỗ TB thua, max 1 lệnh, min 1 lệnh.
 *   K4 tập trung thời gian: PnL theo quý — 1 quý gánh tất hay đều.
 * Tách riêng nhánh PREDICT_SYMBOL (funding-selector) vs tổng.
 */
public class EdgeReliabilityProbe {
    private static final Logger LOG = LoggerFactory.getLogger(EdgeReliabilityProbe.class);

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
        LOG.info("TỔNG lệnh done={}", sim.allOrderDone.size());

        // gom PnL từng lệnh (tách nhánh PREDICT_SYMBOL vs all)
        List<Double> pnlAll = new ArrayList<>();
        List<Double> pnlPred = new ArrayList<>();
        TreeMap<String, Integer> byMonth = new TreeMap<>();
        TreeMap<String, Double> pnlByQuarter = new TreeMap<>();
        Map<Short, Integer> byCoin = new HashMap<>();
        Map<Short, Double> pnlByCoin = new HashMap<>();
        int win = 0, loss = 0;
        double sumWin = 0, sumLoss = 0;
        Calendar cal = Calendar.getInstance();

        for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
            double pnl = o.calTp();
            pnlAll.add(pnl);
            boolean isPred = o.marketLevelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE;
            cal.setTimeInMillis(o.timeStart);
            String ym = cal.get(Calendar.YEAR) + "-" + String.format("%02d", cal.get(Calendar.MONTH) + 1);
            String q = cal.get(Calendar.YEAR) + "Q" + (cal.get(Calendar.MONTH) / 3 + 1);
            if (isPred) {
                pnlPred.add(pnl);
                byMonth.merge(ym, 1, Integer::sum);
                byCoin.merge(o.symbolId, 1, Integer::sum);
                pnlByCoin.merge(o.symbolId, pnl, Double::sum);
            }
            pnlByQuarter.merge(q, pnl, Double::sum);
            if (pnl > 0) { win++; sumWin += pnl; } else { loss++; sumLoss += pnl; }
        }

        double totAll = pnlAll.stream().mapToDouble(d -> d).sum();
        double totPred = pnlPred.stream().mapToDouble(d -> d).sum();
        LOG.info("========== TỔNG QUAN ==========");
        LOG.info("  #lệnh all={} PnL all={}  | #lệnh PRED={} PnL PRED={} ({}% PnL tổng)",
                pnlAll.size(), fmt(totAll), pnlPred.size(), fmt(totPred), pct(totPred, totAll));

        // K2: top lệnh gánh PnL
        List<Double> sortedDesc = new ArrayList<>(pnlPred);
        sortedDesc.sort(Collections.reverseOrder());
        LOG.info("========== K2: TẬP TRUNG PnL (nhánh PRED, {} lệnh) ==========", pnlPred.size());
        for (double frac : new double[]{0.01, 0.05, 0.10, 0.20}) {
            int k = Math.max(1, (int) (pnlPred.size() * frac));
            double topSum = sortedDesc.subList(0, k).stream().mapToDouble(d -> d).sum();
            LOG.info("  top {}% ({} lệnh) = {} PnL ({}% tổng PRED) | bỏ top ra còn {}",
                    (int)(frac*100), k, fmt(topSum), pct(topSum, totPred), fmt(totPred - topSum));
        }

        // K3: win/loss payoff (nhánh PRED)
        int wP = 0, lP = 0; double swP = 0, slP = 0, maxW = 0, maxL = 0;
        for (double p : pnlPred) {
            if (p > 0) { wP++; swP += p; maxW = Math.max(maxW, p); }
            else { lP++; slP += p; maxL = Math.min(maxL, p); }
        }
        LOG.info("========== K3: WIN/LOSS (nhánh PRED) ==========");
        LOG.info("  win={} ({}%) loss={} | lãi TB thắng={} lỗ TB thua={} | max 1 lệnh={} | thua đậm nhất 1 lệnh={}",
                wP, pct(wP, wP + lP), lP, fmt(swP / Math.max(1, wP)), fmt(slP / Math.max(1, lP)), fmt(maxW), fmt(maxL));
        LOG.info("  payoff ratio (|lãiTB/lỗTB|)={}", fmt(Math.abs((swP/Math.max(1,wP)) / (slP/Math.max(1,lP)))));

        // K1: tập trung coin
        LOG.info("========== K1a: TẬP TRUNG COIN (nhánh PRED, {} coin) ==========", byCoin.size());
        List<Map.Entry<Short, Double>> coinPnl = new ArrayList<>(pnlByCoin.entrySet());
        coinPnl.sort((a, b) -> Double.compare(b.getValue(), a.getValue()));
        LOG.info("  Top 10 coin theo PnL:");
        for (int j = 0; j < Math.min(10, coinPnl.size()); j++) {
            short id = coinPnl.get(j).getKey();
            LOG.info("    {} : {} PnL, {} lệnh", SimpleSymbolMapper.getInstance().getSymbol(id),
                    fmt(coinPnl.get(j).getValue()), byCoin.get(id));
        }
        double top5coin = coinPnl.subList(0, Math.min(5, coinPnl.size())).stream().mapToDouble(Map.Entry::getValue).sum();
        LOG.info("  => top 5 coin = {} PnL ({}% tổng PRED)", fmt(top5coin), pct(top5coin, totPred));

        // K1b: tập trung tháng
        LOG.info("========== K1b: PHÂN BỐ LỆNH THEO THÁNG (nhánh PRED) ==========");
        int monthsActive = byMonth.size();
        int maxMonth = byMonth.values().stream().mapToInt(x -> x).max().orElse(0);
        LOG.info("  #tháng có lệnh PRED={} / tổng ~64 tháng | tháng đông nhất={} lệnh", monthsActive, maxMonth);
        LOG.info("  chi tiết: {}", byMonth);

        // K4: PnL theo quý
        LOG.info("========== K4: PnL THEO QUÝ (tổng) ==========");
        int qPos = 0, qNeg = 0;
        for (Map.Entry<String, Double> e : pnlByQuarter.entrySet()) {
            LOG.info("  {} : {}", e.getKey(), fmt(e.getValue()));
            if (e.getValue() > 0) qPos++; else qNeg++;
        }
        LOG.info("  => {}/{} quý dương", qPos, qPos + qNeg);
        LOG.info("========== HET EDGE-RELIABILITY ==========");
    }

    private static String fmt(double d) { return String.format("%.1f", d); }
    private static String pct(double a, double b) { return b != 0 ? String.format("%.1f", 100 * a / b) : "n/a"; }
}
