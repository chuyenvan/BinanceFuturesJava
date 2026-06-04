package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
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
 * TASK 1 — CHẨN ĐOÁN nguồn lỗ ĐUÔI (READ-ONLY). Chạy backtest mode C (RISK+MOM15, no MOM24),
 * KHÔNG breaker, rồi tái dựng CỤM từ các leg trong allOrderDone (gom theo symbolId + timeUpdate —
 * vì khi đóng, mọi leg cùng cụm chia chung timeUpdate/minPrice).
 *
 * Trả lời:
 *  1. worstLoss (leg đơn) thuộc levelChange nào? + quy lỗ theo levelChange.
 *  2. Phân bố số leg DCA của các CỤM lỗ nặng.
 *  3. Quỹ đạo cụm tệ nhất: worst unrealized DD%, margin cụm, số leg, thời lượng.
 *  4. maxDD danh mục xảy ra lúc nào, bao nhiêu cụm đang mở, tổng margin/vốn.
 *
 * KHÔNG sửa logic gì — chỉ đọc allOrderDone + BudgetManagerSimple sau khi chạy.
 */
public class RunTailLossDiagnostic {

    private static final Logger LOG = LoggerFactory.getLogger(RunTailLossDiagnostic.class);

    private static final String START_DATE = "20251001";
    private static final String END_DATE = "20260430";
    private static final float LOSS_BIG = -100f;   // ngưỡng "cụm lỗ nặng" để soi phân bố leg
    private static final int TOP_N = 15;

    public static void main(String[] args) {
        try {
            new RunTailLossDiagnostic().run();
        } catch (Exception e) {
            LOG.error("Diagnostic error", e);
        }
    }

    public void run() throws Exception {
        Configs.IS_HPO_MODE = false;
        Configs.IS_KAGGLE_MODE = false;
        Configs.TIME_RUN = START_DATE;
        // Filter: RISK + MOM15 + EARLY (MOM24 đã bỏ khỏi hệ). KHÔNG breaker.
        Configs.FILTER_MODE = "A";

        LOG.info("🔒 PRE-FLIGHT: BLOCK_INTRABAR_LOOKAHEAD={} APPLY_SLIPPAGE={} SLIPPAGE_RATE={} RATE_FEE={}",
                Configs.BLOCK_INTRABAR_LOOKAHEAD, Configs.APPLY_SLIPPAGE, Configs.SLIPPAGE_RATE, Configs.RATE_FEE);
        LOG.info("⚠️ Lưu ý: funding fee CHƯA tính (updateFundingFee comment) -> PnL tuyệt đối hơi lạc quan; đuôi ít phụ thuộc.");

        long startTime = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
        long endTime = Utils.sdfFile.parse(END_DATE).getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;

        SimpleSymbolMapper.getInstance().init();
        LOG.info("📥 Nạp data Aerospike...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();

        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();

        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());
        sim.simulatorWithInitEntry(startTime, endTime);

        analyze(sim);
    }

    private void analyze(SimulatorMarketLevelTicker1MStopLoss sim) {
        if (sim.allOrderDone == null || sim.allOrderDone.isEmpty()) {
            LOG.warn("⚠️ Không có lệnh nào trong allOrderDone.");
            return;
        }

        // ---------- (A) WORST SINGLE LEG (khớp 'worstLoss' của bảng ablation) ----------
        List<OrderTargetInfoTest> legs = new ArrayList<>(sim.allOrderDone.values());
        legs.sort(Comparator.comparingDouble(OrderTargetInfoTest::calTp));
        LOG.info("\n================ (A) WORST SINGLE LEG (top {}) ================", TOP_N);
        LOG.info(String.format(Locale.US, "%-12s %10s %14s %12s", "symbol", "pnl", "levelChange", "openDate"));
        for (int i = 0; i < Math.min(TOP_N, legs.size()); i++) {
            OrderTargetInfoTest o = legs.get(i);
            LOG.info(String.format(Locale.US, "%-12s %10.1f %14s %12s",
                    o.symbol, o.calTp(), lvl(o), Utils.normalizeDateYYYYMMDDHHmm(o.timeStart)));
        }

        // quy lỗ theo levelChange (theo LEG)
        Map<String, double[]> byLevel = new HashMap<>();  // level -> {sumLoss, countLoss, worst}
        for (OrderTargetInfoTest o : legs) {
            float p = o.calTp();
            if (p < 0) {
                double[] a = byLevel.computeIfAbsent(lvl(o), k -> new double[]{0, 0, 0});
                a[0] += p; a[1] += 1; a[2] = Math.min(a[2], p);
            }
        }
        LOG.info("\n-- Quy LỖ theo levelChange của leg --");
        LOG.info(String.format(Locale.US, "%-22s %12s %8s %12s", "levelChange", "sumLoss", "nLeg", "worstLeg"));
        byLevel.entrySet().stream().sorted(Comparator.comparingDouble(e -> e.getValue()[0])).forEach(e ->
                LOG.info(String.format(Locale.US, "%-22s %12.1f %8.0f %12.1f",
                        e.getKey(), e.getValue()[0], e.getValue()[1], e.getValue()[2])));

        // ---------- TÁI DỰNG CỤM: gom leg theo symbolId + timeUpdate ----------
        Map<String, Cluster> clusters = new HashMap<>();
        for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
            String key = o.symbolId + "@" + o.timeUpdate;
            Cluster c = clusters.computeIfAbsent(key, k -> new Cluster(o.symbol));
            c.legs++;
            c.pnl += o.calTp();
            c.margin += o.calMargin();
            // worst unrealized cụm: minPrice ở leg đã = đáy cụm lúc đóng
            if (o.minPrice != null) c.worstUnreal += o.quantity * (o.minPrice - o.priceEntry);
            c.closeTime = o.timeUpdate;
            if (o.timeStart < c.openTime) { c.openTime = o.timeStart; c.firstLevel = lvl(o); }
            c.levels.add(lvl(o));
        }
        List<Cluster> clusterList = new ArrayList<>(clusters.values());

        // ---------- (B) WORST CLUSTERS ----------
        clusterList.sort(Comparator.comparingDouble(c -> c.pnl));
        LOG.info("\n================ (B) WORST CLUSTERS (top {}) ================", TOP_N);
        LOG.info(String.format(Locale.US, "%-12s %10s %5s %-16s %10s %9s %7s %s",
                "symbol", "pnl", "legs", "firstLevel", "margin", "worstDD%", "hours", "levels"));
        for (int i = 0; i < Math.min(TOP_N, clusterList.size()); i++) {
            Cluster c = clusterList.get(i);
            float ddPct = c.margin > 0 ? c.worstUnreal / c.margin * 100f : 0f;
            float hours = (c.closeTime - c.openTime) / (float) Utils.TIME_HOUR;
            LOG.info(String.format(Locale.US, "%-12s %10.1f %5d %-16s %10.1f %9.1f %7.1f %s",
                    c.symbol, c.pnl, c.legs, c.firstLevel, c.margin, ddPct, hours, c.levels));
        }

        // ---------- (C) PHÂN BỐ SỐ LEG của cụm lỗ nặng (< LOSS_BIG) ----------
        int[] bucket = new int[5]; // [1] [2-3] [4-6] [7-10] [11+]
        int nLossBig = 0;
        double sumLossBig = 0;
        for (Cluster c : clusterList) {
            if (c.pnl < LOSS_BIG) {
                nLossBig++; sumLossBig += c.pnl;
                int L = c.legs;
                if (L <= 1) bucket[0]++;
                else if (L <= 3) bucket[1]++;
                else if (L <= 6) bucket[2]++;
                else if (L <= 10) bucket[3]++;
                else bucket[4]++;
            }
        }
        LOG.info("\n================ (C) PHÂN BỐ LEG của cụm lỗ < {} ================", LOSS_BIG);
        LOG.info("Số cụm lỗ nặng={} | tổng lỗ={} | phân bố leg: 1=[{}] 2-3=[{}] 4-6=[{}] 7-10=[{}] 11+=[{}]",
                nLossBig, String.format(Locale.US, "%.1f", sumLossBig),
                bucket[0], bucket[1], bucket[2], bucket[3], bucket[4]);

        // ---------- (D) maxDD DANH MỤC ----------
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        Float ddMin = bm.balanceIndex.unProfitMin;
        Long tMin = bm.balanceIndex.timeUnProfitMin;
        float capital = (bm.balanceBasic != null && bm.balanceBasic > 0) ? bm.balanceBasic : 1f;
        LOG.info("\n================ (D) maxDD DANH MỤC ================");
        if (ddMin != null && tMin != null) {
            // cụm đang mở tại thời điểm maxDD (xấp xỉ: dùng margin cuối cụm)
            int openCnt = 0; double openMargin = 0;
            for (Cluster c : clusterList) {
                if (c.openTime <= tMin && c.closeTime >= tMin) { openCnt++; openMargin += c.margin; }
            }
            Float marginMaxDay = bm.balanceIndex.date2MarginMax.get(Utils.getDate(tMin));
            LOG.info("maxDD(unProfitMin) = {} ({}% vốn) lúc {}", String.format(Locale.US, "%.1f", ddMin),
                    String.format(Locale.US, "%.1f", ddMin / capital * 100f), Utils.normalizeDateYYYYMMDDHHmm(tMin));
            LOG.info("Tại thời điểm đó: ~{} cụm đang mở, tổng margin cụm ~{} ({}% vốn) | marginMax NGÀY đó={} ({}% vốn)",
                    openCnt, String.format(Locale.US, "%.1f", openMargin),
                    String.format(Locale.US, "%.1f", openMargin / capital * 100f),
                    marginMaxDay != null ? String.format(Locale.US, "%.1f", marginMaxDay) : "n/a",
                    marginMaxDay != null ? String.format(Locale.US, "%.1f", marginMaxDay / capital * 100f) : "n/a");
        } else {
            LOG.info("Không có dữ liệu unProfitMin.");
        }

        LOG.info("\n📌 ĐỌC KẾT QUẢ: (A) worstLeg ở levelChange nào? (C) lỗ nặng có nhiều leg (DCA sâu) không? "
                + "(D) maxDD lúc bao nhiêu cụm mở + margin/vốn = bao nhiêu? -> chọn nơi đặt phanh (DCA depth / margin halt / BIG_DOWN guard).");
    }

    private static String lvl(OrderTargetInfoTest o) {
        return o.marketLevelChange != null ? o.marketLevelChange.toString() : "NULL";
    }

    private static class Cluster {
        final String symbol;
        int legs = 0;
        float pnl = 0f;
        float margin = 0f;
        float worstUnreal = 0f;
        long openTime = Long.MAX_VALUE;
        long closeTime = 0L;
        String firstLevel = "NULL";
        Set<String> levels = new HashSet<>();
        Cluster(String symbol) { this.symbol = symbol; }
    }
}
