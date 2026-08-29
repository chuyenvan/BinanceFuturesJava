package com.binance.chuyennd.ai_ml.wfo;

import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV4;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoContext;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import com.binance.chuyennd.ai_ml.wfo.framework.tasks.StrategyWfoTask;
import com.binance.chuyennd.tradecore.Configs;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * CpcvBatchRunner (FROZEN v1, 2026-08-24) — 1 JVM nạp dataset 1 LẦN, chạy hết ma trận (genome × block).
 * Python (run_cpcv_validation.py) sinh cells + đọc results; Java CHỈ apply genome + backtestRange (fitness v2).
 * Env: CPCV_CELLS (JSONL vào: {seq,knobs,block,start,end}) · CPCV_OUT (JSONL ra, append + resume) ·
 *      WFO_DATA_DIR / WFO_FUNDING_PRED_DIR (WfoDataset.loadAuto). Cờ FROZEN v1 set cứng trong main.
 */
public class CpcvBatchRunner {
    private static final Logger LOG = LoggerFactory.getLogger(CpcvBatchRunner.class);

    public static void main(String[] args) throws Exception {
        // Cờ FROZEN v1 (set cứng để genome grid có tác dụng, không phụ thuộc env)
        Configs.DCA_GRID_ENABLED = true;
        Configs.DCA_GRID_SCALAR = true;
        Configs.OFF_FLAT_HARD = true;
        Configs.FILTER_MODE = "A";
        Configs.ABLATION_MODE = "A";
        Configs.BREAKER_MODE = "OFF";
        Configs.APPLY_FUNDING_FEE = true;
        if ("1".equals(System.getenv("WFO_SMART_CACHE"))) Configs.USE_SMART_CACHE = true;

        String cellsPath = req("CPCV_CELLS");
        String outPath = req("CPCV_OUT");

        WfoDataset ds = WfoDataset.loadAuto();
        WfoContext ctx = new WfoContext(ds, "cpcv-batch");

        // resume: đọc (seq,block) đã có trong out
        Set<String> done = new HashSet<>();
        File outF = new File(outPath);
        if (outF.exists()) {
            for (String line : Files.readAllLines(outF.toPath())) {
                if (line.trim().isEmpty()) continue;
                JSONObject o = new JSONObject(line.trim());
                done.add(o.optInt("seq") + "|" + o.optString("block"));
            }
            LOG.info("resume: {} cell da co trong {}", done.size(), outPath);
        }

        List<String> cells = Files.readAllLines(new File(cellsPath).toPath());
        try (BufferedWriter bw = new BufferedWriter(new FileWriter(outF, true))) {
            int n = 0, skip = 0;
            for (String line : cells) {
                if (line.trim().isEmpty()) continue;
                JSONObject c = new JSONObject(line.trim());
                int seq = c.getInt("seq");
                String block = c.getString("block");
                if (done.contains(seq + "|" + block)) { skip++; continue; }
                long start = c.getLong("start"), end = c.getLong("end");
                JSONObject k = c.getJSONObject("knobs");
                Map<String, Double> knobs = new HashMap<>();
                for (String key : k.keySet()) knobs.put(key, k.getDouble(key));

                StrategyWfoTask.applyGenomeByName(knobs);
                HPOFitnessCalculatorV4.FitnessReport rep = StrategyWfoTask.backtestRange(ctx, start, end);
                LOG.info("[DETAIL] seq={} block={} winRate={} pf={} avgWin={} avgLoss={} medTradePnl={} cost/trade={} avgHoldH={} maxHoldH={} held>14d={} pctHeld>7d={}",
                        seq, block, round4(rep.winRate), round4(rep.profitFactor), round4(rep.avgWin), round4(rep.avgLoss),
                        round4(rep.medianTradePnl), round4(rep.costPerTrade), round4(rep.avgHoldHours),
                        round4(rep.maxHoldHours), rep.heldOver14d, round4(rep.pctHeldOver7d));

                JSONObject m = new JSONObject();
                m.put("calmar", round4(rep.calmar));      // = Calmar_mtm (fitness v2)
                m.put("pnl", round4(rep.totalProfit));
                m.put("maxdd_pct", round4(rep.ddPctMtm));
                m.put("trades", rep.tradeCount);
                m.put("note", rep.note);
                m.put("hold_raw", round4(rep.holdPenaltyRaw));   // fitness v3 hold-penalty raw
                m.put("maxhold_h", round4(rep.maxHoldHours));    // fitness v3 / leak-check
                m.put("daily_n", rep.dailyN);                    // DSR proper-T: daily-PnL moments
                m.put("daily_mean", round4(rep.dailyMean));
                m.put("daily_std", round4(rep.dailyStd));
                m.put("daily_skew", round4(rep.dailySkew));
                m.put("daily_kurt", round4(rep.dailyKurt));
                JSONObject res = new JSONObject();
                res.put("seq", seq); res.put("block", block); res.put("knobs", k); res.put("metrics", m);
                bw.write(res.toString()); bw.newLine(); bw.flush();
                n++;
                LOG.info("cell seq={} block={} calmar={} note={} trades={} ({} done)",
                        seq, block, round4(rep.calmar), rep.note, rep.tradeCount, n);
            }
            LOG.info("XONG: chay {} cell, bo qua {} (resume). out={}", n, skip, outPath);
        }
    }

    private static String req(String key) {
        String v = System.getenv(key);
        if (v == null || v.isBlank()) throw new IllegalStateException("Thieu env " + key);
        return v;
    }
    private static double round4(double v) { return Math.round(v * 1e4) / 1e4; }
}
