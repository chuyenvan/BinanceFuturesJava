package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV4;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoContext;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoJob;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoTask;
import com.binance.chuyennd.tradecore.Configs;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * WFO TASK loai CPCV (recipe v1 FROZEN) — moi JOB = 1 CELL (1 genome x 1 block) cua ma tran CPCV.
 * Noi CpcvBatchRunner (shard-file) vao jobstore Aerospike: cell lay tu jobstore thay vi file,
 * result ghi ve jobstore thay vi file. Engine backtest tai dung NGUYEN StrategyWfoTask
 * (applyGenomeByName + backtestRange, fitness v2). Determinism: cung genome+block+dataset -> byte-identical
 * voi CpcvBatchRunner (parity gate xac nhan truoc khi fanout full).
 *
 * <p>buildJobs (coordinator): doc env CPCV_CELLS (JSONL {seq,block,knobs,start,end}) -> 1 job / cell,
 * id="cpcv-{seq}-{block}", payload = dong cell nguyen.
 * <p>runJob (worker): set co FROZEN v1 -> applyGenomeByName -> backtestRange -> result JSON
 * {seq,block,knobs,metrics:{calmar,pnl,maxdd_pct,trades,note}} (khop schema CpcvBatchRunner).
 * <p>aggregate: dump moi result ra env CPCV_RESULTS_OUT (JSONL, cho Python run_cpcv_validation.py tinh
 * CPCV 28-path + DSR/PBO + verdict) + markdown dem cell/note.
 *
 * <p>LUU Y: SELECTOR_RANK_TOPK=8 la env-only (final trong Configs) -> worker PHAI launch voi env do,
 * va java PHAI co -Duser.timezone=Asia/Ho_Chi_Minh. Neu thieu -> ket qua SAI recipe (da can 1 lan).
 */
public class CpcvCellTask implements WfoTask {

    private static final Logger LOG = LoggerFactory.getLogger(CpcvCellTask.class);
    public static final String TYPE = "cpcv_v1";

    @Override
    public String type() { return TYPE; }

    // ======================= buildJobs (coordinator) =======================
    @Override
    public List<WfoJob> buildJobs() {
        String cellsPath = System.getenv("CPCV_CELLS");
        if (cellsPath == null || cellsPath.isBlank()) {
            throw new IllegalStateException("Thieu env CPCV_CELLS (JSONL cells cho buildJobs cpcv_v1)");
        }
        List<WfoJob> jobs = new ArrayList<>();
        try {
            for (String line : Files.readAllLines(new File(cellsPath).toPath())) {
                if (line.trim().isEmpty()) continue;
                JSONObject c = new JSONObject(line.trim());
                int seq = c.getInt("seq");
                String block = c.getString("block");
                // sanity: cell phai co start/end/knobs
                c.getLong("start"); c.getLong("end"); c.getJSONObject("knobs");
                String id = "cpcv-" + seq + "-" + block;
                jobs.add(new WfoJob(id, TYPE, c.toString()));
            }
        } catch (Exception e) {
            throw new RuntimeException("buildJobs cpcv_v1 doc CPCV_CELLS loi: " + cellsPath, e);
        }
        LOG.info("buildJobs cpcv_v1: {} cell tu {}", jobs.size(), cellsPath);
        return jobs;
    }

    // ======================= runJob (worker) =======================
    @Override
    public String runJob(WfoJob job, WfoContext ctx) throws Exception {
        // Co FROZEN v1 (khop CpcvBatchRunner.main) — set moi job, idempotent, chong lech recipe.
        Configs.DCA_GRID_ENABLED = true;
        Configs.DCA_GRID_SCALAR = true;
        Configs.APPLY_FUNDING_FEE = true;

        JSONObject c = new JSONObject(job.payload);
        int seq = c.getInt("seq");
        String block = c.getString("block");
        long start = c.getLong("start"), end = c.getLong("end");
        JSONObject k = c.getJSONObject("knobs");
        Map<String, Double> knobs = new HashMap<>();
        for (String key : k.keySet()) knobs.put(key, k.getDouble(key));

        StrategyWfoTask.applyGenomeByName(knobs);
        HPOFitnessCalculatorV4.FitnessReport rep = StrategyWfoTask.backtestRange(ctx, start, end);

        JSONObject m = new JSONObject();
        m.put("calmar", round4(rep.calmar));       // = Calmar_mtm (fitness v2)
        m.put("pnl", round4(rep.totalProfit));
        m.put("maxdd_pct", round4(rep.ddPctMtm));
        m.put("trades", rep.tradeCount);
        m.put("note", rep.note);
        JSONObject res = new JSONObject();
        res.put("seq", seq); res.put("block", block); res.put("knobs", k); res.put("metrics", m);
        LOG.info("cpcv cell seq={} block={} calmar={} note={} trades={}",
                seq, block, round4(rep.calmar), rep.note, rep.tradeCount);
        return res.toString();
    }

    // ======================= aggregate (coordinator) =======================
    @Override
    public String aggregate(List<WfoJob> doneJobs) {
        String outPath = System.getenv("CPCV_RESULTS_OUT");
        Map<String, Integer> notes = new TreeMap<>();
        List<JSONObject> rows = new ArrayList<>();
        for (WfoJob j : doneJobs) {
            if (j.result == null || j.result.isEmpty()) continue;
            JSONObject r = new JSONObject(j.result);
            rows.add(r);
            String note = r.getJSONObject("metrics").optString("note", "?");
            notes.merge(note, 1, Integer::sum);
        }
        int written = 0;
        if (outPath != null && !outPath.isBlank()) {
            try (BufferedWriter bw = new BufferedWriter(new FileWriter(new File(outPath), false))) {
                for (JSONObject r : rows) { bw.write(r.toString()); bw.newLine(); written++; }
                LOG.info("aggregate cpcv_v1: dump {} result -> {}", written, outPath);
            } catch (Exception e) {
                LOG.error("aggregate ghi CPCV_RESULTS_OUT loi: {}", outPath, e);
            }
        }
        StringBuilder md = new StringBuilder();
        md.append("# CPCV v1 — aggregate (dump-only, verdict o Python)\n\n");
        md.append("- Cell DONE: ").append(rows.size()).append("\n");
        md.append("- Note distribution: ").append(notes).append("\n");
        md.append("- Results JSONL -> ")
          .append(outPath == null ? "(CPCV_RESULTS_OUT chua set — khong dump)" : (outPath + " (" + written + " dong)"))
          .append("\n\n");
        md.append("VERDICT: chay `python3 run_cpcv_validation.py` tren results JSONL de tinh CPCV 28-path + DSR/PBO.\n");
        return md.toString();
    }

    private static double round4(double v) { return Math.round(v * 1e4) / 1e4; }
}
