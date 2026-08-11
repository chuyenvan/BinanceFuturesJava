package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV4;
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

/**
 * TASK-139 — Sweep RATE_PROFIT_STOP_MARKET (ngưỡng lãi kích hoạt trailing SL) — giả thuyết Uni:
 * 0.01032 làm trailing kích hoạt QUÁ SỚM → coin pump/dump giật xuống 1-3% là bị quét stop non
 * (median hold 7 phút), tự cắt cụt đuôi phải. Nâng lên ~0.03 cho coin "thở" tới pump thật.
 *
 * <p>Sweep base rate + đo: PnL, #lệnh, calmar, sortino, holding median lệnh PRED, %lệnh giữ >60 phút.
 * Nhiều khoảng độc lập. Config baseline, chỉ đổi RATE_PROFIT_STOP_MARKET.
 * ĐỌC: nếu nâng rate → holding median tăng + PnL/calmar tăng → giả thuyết Uni ĐÚNG (trailing cắt non).
 */
public class TrailingStopSweepProbe {
    private static final Logger LOG = LoggerFactory.getLogger(TrailingStopSweepProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());
        LOG.info("baseline RATE_PROFIT_STOP_MARKET={} TS_MAX_GAP={} TS_MAX_GAP_WEAK={}",
                Configs.RATE_PROFIT_STOP_MARKET, Configs.TS_MAX_GAP, Configs.TS_MAX_GAP_WEAK);

        // TASK (2026-07-31): thu hep sweep — 0.01032/0.02032 da bi bac boi cost-logic (round-trip
        // fee+slippage ~0.8%, SL dong bang duoi muc do la LO ke toan chac chan). Chi con so sanh
        // 0.03+ voi nhau. Them 1 period "2025Q4_crash" de thay ro anh huong cua black-swan 10/10-11/10/2025
        // (da xac nhan o EXIT_MACHINE PHAN 5) tach rieng, khong lan vao "toan_ky".
        // TASK (2026-07-31): env SWEEP_RATES (CSV) override cho phep chay 1 gia tri/1 process, phan
        // tan song song nhieu core (thay vi 1 JVM chay tuan tu ca 5 gia tri).
        String ratesEnv = System.getenv("SWEEP_RATES");
        float[] sweep;
        if (ratesEnv != null && !ratesEnv.isEmpty()) {
            String[] parts = ratesEnv.split(",");
            sweep = new float[parts.length];
            for (int i = 0; i < parts.length; i++) sweep[i] = Float.parseFloat(parts[i].trim());
        } else {
            sweep = new float[]{0.03f, 0.035f, 0.04f, 0.045f, 0.05f};
        }
        // TASK (2026-07-31, SUA LOI PHUONG PHAP): env SWEEP_PERIODS cho phep truyen danh sach fold
        // "name:start:end,name:start:end,...". Muc dich: chay tren CAC FOLD RIENG BIET de lam
        // walk-forward selection (chon tham so tren qua khu, cham tren tuong lai chua nhin) thay vi
        // doc thang PnL toan ky = toi uu IN-SAMPLE tren chinh du lieu dung de ket luan.
        String periodsEnv = System.getenv("SWEEP_PERIODS");
        String[][] periods;
        if (periodsEnv != null && !periodsEnv.isEmpty()) {
            String[] items = periodsEnv.split(",");
            periods = new String[items.length][3];
            for (int i = 0; i < items.length; i++) {
                String[] p = items[i].trim().split(":");
                periods[i][0] = p[0]; periods[i][1] = p[1]; periods[i][2] = p[2];
            }
        } else {
            periods = new String[][]{
                {"2024_bull", "20240101", "20241231"},
                {"2025Q2_phang", "20250401", "20250701"},
                {"2025Q4_crash", "20251001", "20260101"},
                {"toan_ky", "20210101", "20260501"},
            };
        }
        float saved = Configs.RATE_PROFIT_STOP_MARKET;

        LOG.info("APPLY_FUNDING_FEE={} TIME_STOP_HOURS={} HARD_SL_PCT={} BLOCK_INTRABAR_LOOKAHEAD={}",
                Configs.APPLY_FUNDING_FEE, Configs.TIME_STOP_HOURS, Configs.HARD_SL_PCT,
                Configs.BLOCK_INTRABAR_LOOKAHEAD);
        LOG.info("period | rateTS trades pnlTOTAL | closed nClosed pnlClosed | mtm %MTM pnlMtm | dd ddPct ddPctMtm MC | hold med %>60p %>7d");
        for (String[] pr : periods) {
            long from = Utils.sdfFile.parse(pr[1]).getTime() + 7 * Utils.TIME_HOUR;
            long to = Utils.sdfFile.parse(pr[2]).getTime() + 7 * Utils.TIME_HOUR;
            int windowDays = (int) Math.max(1, (to - from) / Utils.TIME_DAY);
            for (float ts : sweep) {
                Configs.RATE_PROFIT_STOP_MARKET = ts;
                BudgetManagerSimple.resetInstance();
                HistoryManager.getInstance().resetCache();
                CoinRankManager.getInstance().resetCache();
                AIRejectFilter.resetCounters();
                SimulatorMarketLevelTicker1MStopLoss.resetAuditCounters();   // F8/F9
                SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
                sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
                sim.simulatorWithInitEntry(from, to);
                HPOFitnessCalculatorV4.FitnessReport rep =
                        HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone, windowDays);
                // holding median + %hold>60p cho lệnh PRED
                // TASK (2026-07-31): THEM %hold>7d va %NEVER_ARMED. Ly do: PnL tang don dieu toi 0.10
                // khong thay dinh -> nghi van "giu lau = an beta thi truong tang 2021-2026" chu khong
                // phai exit tot len. 2 chi so nay phan biet:
                //  - pctOver7d: cham nguong rang buoc production MAX_PCT_HELD_OVER_7D=0.02 (fitness V4)
                //    -> config nao vuot 2% se bi harness that loai du PnL tho cao.
                //  - pctNeverArmed: lenh KHONG BAO GIO arm (priceSL==null) => KHONG CO EXIT NAO
                //    (HARD_STOP_LOSS_RATE=0, TIME_STOP_HOURS=0) => bi mark-to-market cuoi ky. Nang arm
                //    threshold cang cao thi cang nhieu lenh roi vao nhom nay = "khong quan tri rui ro",
                //    lai/lo phu thuoc gia cuoi ky chu khong phai cong thuc exit.
                java.util.List<Double> holds = new java.util.ArrayList<>();
                int over60 = 0, over7d = 0;
                // 🔴 FIX (2026-07-31, audit F5/F6): cot %noArm CU dem o.priceSL==null LA SAI (BalanceIndex
                //    ghi de priceSL/priceTP cua leg dang mo => anh chup ngau nhien). Thay bang status:
                //    lenh con MO cuoi ky KHONG duoc closeOrder() doi status => van la REQUEST.
                //    => tach PnL "da chot that" khoi PnL "mark-to-market cua bao tai lenh khong bao gio dong".
                //    Day la phep do QUYET DINH: neu %MTM tang theo rate-min thi "cai thien" chi la beta.
                int nMtm = 0, nClosed = 0;
                double pnlMtm = 0, pnlClosed = 0;
                for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
                    boolean isMtm = (o.status == com.binance.chuyennd.trading.OrderTargetStatus.REQUEST);
                    Float tp = o.calTp();
                    if (isMtm) { nMtm++; pnlMtm += (tp != null ? tp : 0f); }
                    else { nClosed++; pnlClosed += (tp != null ? tp : 0f); }
                    if (o.marketLevelChange != MarketLevelChange.PREDICT_SYMBOL_TRADE) continue;
                    double h = (o.timeUpdate - o.timeStart) / 60000.0;
                    holds.add(h);
                    if (h > 60) over60++;
                    if (h > 7 * 24 * 60) over7d++;
                }
                double holdMed = median(holds);
                double pctOver60 = holds.isEmpty() ? 0 : 100.0 * over60 / holds.size();
                double pctOver7d = holds.isEmpty() ? 0 : 100.0 * over7d / holds.size();
                int nAll = nMtm + nClosed;
                double pctMtm = nAll == 0 ? 0 : 100.0 * nMtm / nAll;
                // calmar THAT: dung maxDD mark-to-market (ddPctMtm) thay ddPct cu (= min unrealized,
                // bo qua realized, mau so von co dinh => gan nhu mu voi tham so exit - audit F1).
                double calmarMtm = rep.ddPctMtm > 0 ? (rep.totalProfit / (rep.ddPctMtm * 37756.0)) : 0;
                LOG.info(String.format(
                    "%-14s %8.5f %7d %10.1f | closed %7d %10.1f | mtm %6.1f%% %10.1f | dd %6.2f%% mtm %6.2f%% MC=%s | hold %8.1f %6.1f%% %6.1f%%",
                        pr[0], ts, rep.tradeCount, rep.totalProfit, nClosed, pnlClosed,
                        pctMtm, pnlMtm, rep.ddPct * 100, rep.ddPctMtm * 100, rep.marginCallHit,
                        holdMed, pctOver60, pctOver7d));
                // Dong CSV de gom bang script, khong phai parse log dinh dang cot.
                // F8/F9: neu 3 so nay khac 0 thi ket qua run nay KHONG so sanh duoc voi run khac.
                if (SimulatorMarketLevelTicker1MStopLoss.orderKeyCollisions > 0
                        || SimulatorMarketLevelTicker1MStopLoss.dayDataErrors > 0
                        || SimulatorMarketLevelTicker1MStopLoss.swallowedExceptions > 0) {
                    LOG.error("⚠️ AUDIT rate={} period={} -> {}", ts, pr[0],
                            SimulatorMarketLevelTicker1MStopLoss.auditCountersSummary());
                } else {
                    LOG.info("AUDIT rate={} period={} -> sach ({})", ts, pr[0],
                            SimulatorMarketLevelTicker1MStopLoss.auditCountersSummary());
                }
                Float fundTot = BudgetManagerSimple.getInstance().totalFundingFee;
                LOG.info(String.format("CSVROW,%.5f,%s,%d,%.2f,%d,%.2f,%d,%.2f,%.4f,%.4f,%.4f,%s,%.1f,%.2f,%.2f,%.2f",
                        ts, pr[0], rep.tradeCount, rep.totalProfit,
                        nClosed, pnlClosed, nMtm, pnlMtm,
                        rep.ddPct, rep.ddPctMtm, rep.minEquityMtmPct, rep.marginCallHit,
                        holdMed, pctOver60, pctOver7d, (fundTot != null ? fundTot : 0f)));
            }
            LOG.info("  ----");
        }
        Configs.RATE_PROFIT_STOP_MARKET = saved;
        LOG.info("========== HET TS-SWEEP ==========");
        System.exit(0); // TASK (2026-07-31): co non-daemon thread nao do treo JVM sau main() tra ve
                         // (bat gap khi chay song song, process khong thoat -> ket xargs -P4). Ep thoat.
    }

    private static double median(java.util.List<Double> a) {
        if (a.isEmpty()) return 0;
        java.util.List<Double> c = new java.util.ArrayList<>(a);
        java.util.Collections.sort(c);
        int m = c.size() / 2;
        return c.size() % 2 == 1 ? c.get(m) : (c.get(m-1) + c.get(m)) / 2;
    }
}
