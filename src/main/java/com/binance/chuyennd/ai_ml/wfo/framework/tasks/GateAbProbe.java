package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV4;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * TASK-134 A/B — Gate MOM15 lọc ĐÚNG (giữ tinh hoa) hay lọc MÙ (loại lệnh tốt)?
 *
 * <p>3 arm, CÙNG khoảng + CÙNG genome baseline, CHỈ đổi FILTER_MODE:
 *   A   = MOM15+RISK (baseline hiện tại)
 *   E   = tắt MOM15, giữ RISK (nới nhánh funding-selector — BIG_DOWN vốn bỏ qua filter nên không đổi)
 *   OFF = tắt hết (trần trên tuyệt đối)
 *
 * <p>Đo đủ: PnL, #lệnh, ddPct, calmar, sortino, %năm-dương, entry theo nguồn. Chạy trên NHIỀU khoảng
 * độc lập (không chỉ toàn kỳ) → tránh kết luận từ 1 regime. Config baseline (KHÔNG tune genome) —
 * đo CƠ CHẾ gate, không đo hiệu năng tối ưu.
 *
 * <p>ĐỌC KẾT QUẢ:
 *   E >> A về PnL/calmar → gate lọc MÙ (loại lệnh tốt) → nới gate là hướng đúng.
 *   E << A → gate lọc ĐÚNG (99.9% bị loại phần lớn là rác) → KHÔNG nới, cải thiện selector/gate tinh hơn.
 *   E ≈ A → gate gần vô tác dụng lên PnL → đơn giản hóa.
 */
public class GateAbProbe {
    private static final Logger LOG = LoggerFactory.getLogger(GateAbProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());

        String[][] periods = {
            {"2022_crash", "20220101", "20221231"},
            {"2023_hoi_phuc", "20230101", "20231231"},
            {"2024_bull", "20240101", "20241231"},
            {"2025Q2_phang", "20250401", "20250701"},
            {"toan_ky", "20210101", "20260501"},
        };
        String[] modes = {"A", "E", "OFF"};

        // header
        LOG.info(String.format("%-14s %-4s %8s %10s %8s %8s %8s %7s %7s %8s %8s",
                "period", "mode", "trades", "pnl", "ddPct%", "calmar", "sortino", "posYr%", "note",
                "bigDown", "predSym"));

        for (String[] pr : periods) {
            long from = Utils.sdfFile.parse(pr[1]).getTime() + 7 * Utils.TIME_HOUR;
            long to = Utils.sdfFile.parse(pr[2]).getTime() + 7 * Utils.TIME_HOUR;
            int windowDays = (int) Math.max(1, (to - from) / Utils.TIME_DAY);

            for (String mode : modes) {
                Configs.FILTER_MODE = mode;   // cô lập trong tool, không đụng code sản xuất
                BudgetManagerSimple.resetInstance();
                HistoryManager.getInstance().resetCache();
                CoinRankManager.getInstance().resetCache();
                AIRejectFilter.resetCounters();

                SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
                sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
                sim.simulatorWithInitEntry(from, to);

                HPOFitnessCalculatorV4.FitnessReport rep =
                        HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone, windowDays);

                LOG.info(String.format("%-14s %-4s %8d %10.1f %8.1f %8.3f %8.3f %7.0f %-8s %8d %8d",
                        pr[0], mode, rep.tradeCount, rep.totalProfit, rep.ddPct * 100,
                        rep.calmar, rep.sortino, rep.posYearRatio * 100, rep.note,
                        sim.entryBigDown, sim.entryPredictSymbol));
            }
            LOG.info("  ----");
        }
        Configs.FILTER_MODE = "A";  // khôi phục
        LOG.info("========== HET A/B ==========");
    }
}
