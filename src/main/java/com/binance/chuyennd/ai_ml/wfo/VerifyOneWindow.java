package com.binance.chuyennd.ai_ml.wfo;

import com.binance.chuyennd.ai_ml.wfo.framework.*;
import com.binance.chuyennd.tradecore.Configs;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

/**
 * TASK-142 — ENTRYPOINT ĐO 1 WINDOW (read-only) để so BEFORE/AFTER khi bật RAM-cache ticker-file.
 *
 * <p>Chạy ĐÚNG logic {@link com.binance.chuyennd.ai_ml.wfo.framework.tasks.StrategyWfoTask#runJob}
 * cho MỘT window (seed cố định = SEED_BASE+winIdx như coordinator), in THỜI GIAN + các số then chốt
 * (oosPnl / wfe / oosTrades / oosNote) để đối chiếu jar chính (cache off) vs jar ram-cache (cache on):
 * số PHẢI trùng khít (cache chỉ đổi IO, không đổi kết quả), thời gian/window giảm.
 *
 * <p>KHÔNG chạm 2 process live; KHÔNG ghi dữ liệu. Dataset offline từ WFO_DATA_DIR (như WfoWorker).
 *
 * <p><b>Env</b> (giống WfoWorker để 2 nhánh so sánh cùng cấu hình):
 * <ul>
 *   <li>WFO_DATA_DIR (bắt buộc) — thư mục WfoDataset offline (market/pred/funding).</li>
 *   <li>TICKER_SOURCE=file + kaggle_data_hpo/ticker_YYYYMMDD.bin[.gz] — nguồn ticker.</li>
 *   <li>WFO_SMART_CACHE=1 → bật RAM-cache (AFTER). Bỏ trống → đọc thẳng (BEFORE).</li>
 *   <li>WFO_STATIC_RANK=1 + WFO_COINTIER_FILE — tier tĩnh (khớp worker).</li>
 *   <li>WFO_N_SAMPLES (mặc định 30), ABLATION_MODE (mặc định A).</li>
 * </ul>
 *
 * <p><b>Arg</b>: [winIdx=10]
 */
public class VerifyOneWindow {

    private static final Logger LOG = LoggerFactory.getLogger(VerifyOneWindow.class);

    public static void main(String[] args) {
        try {
            int winIdx = args.length > 0 ? Integer.parseInt(args[0].trim()) : 10;

            // ==== cấu hình khớp WfoWorker (để BEFORE/AFTER chỉ khác đúng cache) ====
            if ("1".equals(System.getenv("WFO_SMART_CACHE"))) Configs.USE_SMART_CACHE = true;
            if ("1".equals(System.getenv("WFO_STATIC_RANK"))) {
                Configs.WFO_STATIC_RANK = true;
                String tierFile = System.getenv("WFO_COINTIER_FILE");
                if (tierFile == null || tierFile.isBlank()) {
                    throw new IllegalStateException("WFO_STATIC_RANK=1 nhưng thiếu WFO_COINTIER_FILE");
                }
                com.binance.chuyennd.tradecore.CoinRankManager.getInstance()
                        .loadStaticTier(ExportCoinTierStatic.load(tierFile));
            }

            LOG.info("=== VerifyOneWindow winIdx={} | TICKER_SOURCE={} USE_SMART_CACHE={} STATIC_RANK={} ===",
                    winIdx, Configs.TICKER_SOURCE, Configs.USE_SMART_CACHE, Configs.WFO_STATIC_RANK);

            WfoTask task = WfoTaskRegistry.get("strategy_window");
            WfoDataset ds = WfoDataset.loadAuto();
            WfoContext ctx = new WfoContext(ds, "verify-one-window");

            // buildJobs sinh mọi window; chọn đúng winIdx cần đo
            WfoJob target = null;
            for (WfoJob j : task.buildJobs()) {
                if (new JSONObject(j.payload).getInt("winIdx") == winIdx) { target = j; break; }
            }
            if (target == null) {
                throw new IllegalStateException("Khong tim thay window winIdx=" + winIdx
                        + " (co the bi cap boi WFO_MAX_OOS_DATE / WFO_MAX_WINDOWS)");
            }

            long t0 = System.currentTimeMillis();
            String resultJson = task.runJob(target, ctx);
            long elapsedMs = System.currentTimeMillis() - t0;

            JSONObject r = new JSONObject(resultJson);
            LOG.info("================= KET QUA WINDOW w{} =================", winIdx);
            LOG.info("label={} oosPnl={} wfe={} oosFit={} oosTrades={} oosNote={} isFit={} reject={}/{}",
                    r.optString("label"), r.opt("oosPnl"), r.opt("wfe"), r.opt("oosFit"),
                    r.opt("oosTrades"), r.optString("oosNote"), r.opt("isFit"),
                    r.opt("rejectSamples"), r.opt("nSamples"));
            LOG.info("[TIMING] window w{} chay het {} ms ({} s) | cache={}",
                    winIdx, elapsedMs, elapsedMs / 1000, Configs.USE_SMART_CACHE ? "ON(ram)" : "OFF(read-thang)");
            LOG.info("RESULT_JSON " + resultJson);   // 1 dong de grep/so BEFORE vs AFTER
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("VerifyOneWindow FAIL", e);
            System.exit(1);
        }
    }
}
