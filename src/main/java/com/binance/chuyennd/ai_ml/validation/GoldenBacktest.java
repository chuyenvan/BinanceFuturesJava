package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.hpo.master.RunHpoMaster_Distributed;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;
import java.util.*;

/**
 * TASK-003 — GoldenBacktest: regression harness cho backtest (hiện thực ADR-0006).
 *
 * GỌI engine `SimulatorMarketLevelTicker1MStopLoss` qua `BacktestIntegrityGuard` (luật 1–3 CLAUDE.md),
 * thu metric + stamp input, ghi fingerprint JSON, so baseline đã duyệt; BÁO ĐỎ (exit≠0) khi STAMP-input
 * KHÔNG đổi mà metric đổi (regression / nondeterminism). KHÔNG sửa engine core, KHÔNG ingest.
 *
 * Mode (arg[0]): verify | FAST | FULL | FAST_CRASH | FAST_BULL | FAST_RECENT   (mặc định: verify)
 *  - verify: chạy FAST 2 lần cùng commit/config/data → fingerprint phải KHỚP (cổng tiên quyết bước 0).
 *  - FAST  : START=20251001 END=20260430. FULL: START=20210101 END=nay.
 *  - FAST_CRASH/BULL/RECENT (TASK-003.1): range regime theo mốc đã duyệt; mỗi lần tự chạy determinism
 *    gate (2x) rồi mới chụp fingerprint. CRASH=20220401–20221231, BULL=20231001–20231231, RECENT=FAST.
 * commit/dirty nhận qua env GOLDEN_COMMIT / GOLDEN_DIRTY (vì 226 không có git repo, chỉ có jar).
 * ⚠️ ĐỌC DATA: chạy trên 226 nên để IS_KAGGLE_MODE=IS_HPO_MODE=FALSE → Simulator đọc AEROSPIKE
 *    (ticker qua getReadClient→242, 226 whitelist được 242; market/pred/funding→226). KHÔNG set true:
 *    true = Simulator đọc FILE LOCAL qua KaggleDataLoader (không tồn tại trên 226 → sai/rỗng).
 * maxDD = balanceIndex.unProfitMin (nay = đáy per-tick thật, ADR-0001).
 *
 * ⚠️ nearLiq: engine KHÔNG mô hình thanh lý (leverage 1 long-only). Định nghĩa Ở ĐÂY (cần user xác nhận):
 *   nearLiq = số CỤM có drawdown thật (maeLow/avgEntry − 1) ≤ NEAR_LIQ_DD (−0.90) — tới sát xóa sổ.
 */
public class GoldenBacktest {

    private static final Logger LOG = LoggerFactory.getLogger(GoldenBacktest.class);

    private static final String FAST_START = "20251001", FAST_END = "20260430";
    private static final String FULL_START = "20210101";

    // TASK-003.1 — thư viện range theo regime (mốc ĐÃ user duyệt). Mỗi range = {start, end} yyyyMMdd.
    // Chạy qua mode tên-profile → runRangeGated: determinism gate (2x) + fingerprint trong 1 launch.
    private static final Map<String, String[]> RANGES = new LinkedHashMap<>();
    static {
        RANGES.put("FAST_CRASH",  new String[]{"20220401", "20221231"}); // 2022 Q2–Q4: LUNA(5/22)+FTT(11/22) — đo survivorship
        RANGES.put("FAST_BULL",   new String[]{"20231001", "20231231"}); // 2023Q4: uptrend sạch (rổ +142%, DD −14%)
        RANGES.put("FAST_RECENT", new String[]{"20251001", "20260430"}); // = baseline FAST (regime giảm/choppy)
    }
    private static final double NEAR_LIQ_DD = -0.90;     // <CẦN XÁC NHẬN định nghĩa nearLiq>
    private static final long HOLD_30D = 30L * Utils.TIME_DAY;
    private static final double EPS = 1e-4;              // dung sai metric tiền (determinism phải ~0)

    public static void main(String[] args) {
        try {
            String mode = args.length > 0 ? args[0] : "verify";
            new GoldenBacktest().run(mode);
            System.exit(0);   // batch job: thoát sạch (Aerospike client pool có thread non-daemon giữ JVM sống → treo nếu không exit; CI/script gọi harness phải nhận được exit code)
        } catch (Exception e) {
            LOG.error("❌ GoldenBacktest lỗi", e);
            System.exit(3);
        }
    }

    // ===== holder dữ liệu (load 1 lần, dùng lại cho 2 run determinism) =====
    private TreeMap<Long, MarketDataObject> mkt;
    private TreeMap<Long, AiPredictionData> pred;
    private TreeMap<Long, long[]> fund;

    private void loadData() {
        if (mkt != null) return;
        LOG.info("📥 Nạp data Aerospike (226)...");
        mkt = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        pred = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        fund = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("✅ market={} pred={} funding={}", mkt.size(), pred.size(), fund.size());
    }

    public void run(String mode) throws Exception {
        // Chạy trên 226: cả hai FALSE để Simulator đọc AEROSPIKE (KHÔNG đọc file local KaggleDataLoader).
        //   ticker → getReadClient → 242 (226 whitelist được 242); market/pred/funding → 226.
        // BREAKER OFF = chiến lược nền (golden chuẩn).
        Configs.IS_HPO_MODE = false;
        Configs.IS_KAGGLE_MODE = false;
        Configs.BREAKER_MODE = "OFF";
        LOG.info("🟡 PRE-FLIGHT: lookahead_block={} slippage_apply={} SLIPPAGE_RATE={} RATE_FEE={} FILTER_MODE={} CONFIG_VERSION={}",
                Configs.BLOCK_INTRABAR_LOOKAHEAD, Configs.APPLY_SLIPPAGE, Configs.SLIPPAGE_RATE,
                Configs.RATE_FEE, Configs.FILTER_MODE, RunHpoMaster_Distributed.CONFIG_VERSION);
        loadData();

        if ("verify".equalsIgnoreCase(mode)) {
            verifyDeterminism();
        } else {
            String p = mode.toUpperCase(Locale.US);
            if ("FAST".equals(p) || "FULL".equals(p)) {
                runProfile(p);
            } else if (RANGES.containsKey(p)) {
                runRangeGated(p);                       // determinism gate (2x) + fingerprint trong 1 launch
            } else {
                LOG.error("Mode không hợp lệ: {} (verify|FAST|FULL|{})", mode, String.join("|", RANGES.keySet()));
                System.exit(3);
            }
        }
    }

    /** Bước 0 — cổng tiên quyết: FAST 2 lần phải cho metric KHỚP HỆT. */
    private void verifyDeterminism() {
        LOG.info("\n================ DETERMINISM GATE (FAST x2) ================");
        long s = parse(FAST_START), e = parseEnd(FAST_END);
        Metrics m1 = runSim(s, e);
        Metrics m2 = runSim(s, e);
        List<String> diff = m1.diff(m2);
        if (diff.isEmpty()) {
            LOG.info("✅ DETERMINISM PASS — 2 lần FAST khớp tuyệt đối. {}", m1.brief());
            LOG.info("   → có thể dựng baseline/regression. Chạy lại với arg FAST hoặc FULL.");
        } else {
            LOG.error("🔴 DETERMINISM FAIL — 2 lần FAST LỆCH: {}", diff);
            LOG.error("   Nghi nguồn: thứ tự duyệt HashMap, parallelStream, timezone, static state chưa reset.");
            LOG.error("   DỪNG: KHÔNG dựng regression khi sim chưa deterministic.");
            System.exit(2);
        }
    }

    /** Chạy 1 profile (FAST/FULL) → fingerprint JSON → so baseline → phán quyết. */
    private void runProfile(String profile) throws Exception {
        long s, e; String start, end;
        if ("FAST".equals(profile)) { start = FAST_START; end = FAST_END; s = parse(start); e = parseEnd(end); }
        else { start = FULL_START; e = System.currentTimeMillis(); end = Utils.normalizeDateYYYYMMDD(e); s = parse(start); }
        emitFingerprint(profile, start, end, runSim(s, e));
    }

    /**
     * TASK-003.1 — 1 launch cho 1 range regime: determinism gate (chạy 2 lần khớp hệt) rồi mới chụp
     * fingerprint từ run2 + so baseline. Load data 1 lần (CRASH 9 tháng chạy lâu nên không load lặp).
     */
    private void runRangeGated(String profile) throws Exception {
        String[] r = RANGES.get(profile);
        String start = r[0], end = r[1];
        long s = parse(start), e = parseEnd(end);
        LOG.info("\n========= RANGE {} [{}→{}] — DETERMINISM GATE (x2) =========", profile, start, end);
        Metrics m1 = runSim(s, e);
        Metrics m2 = runSim(s, e);
        List<String> diff = m1.diff(m2);
        if (!diff.isEmpty()) {
            LOG.error("🔴 DETERMINISM FAIL [{}] — 2 lần LỆCH: {}", profile, diff);
            LOG.error("   DỪNG: KHÔNG chụp baseline khi range chưa deterministic.");
            System.exit(2);
        }
        LOG.info("✅ DETERMINISM PASS [{}] — 2 lần khớp tuyệt đối. {}", profile, m2.brief());
        emitFingerprint(profile, start, end, m2);
    }

    /** Ghi fingerprint JSON (outputs/golden/) + so baseline docs/golden/ (review/regression). */
    private void emitFingerprint(String profile, String start, String end, Metrics m) throws Exception {
        Fingerprint fp = stamp(profile, start, end, m);
        new File("outputs/golden").mkdirs();
        String run = "outputs/golden/" + profile + "-" + fp.commit + ".json";
        try (FileWriter w = new FileWriter(run)) { w.write(Utils.gson.toJson(fp)); }
        LOG.info("📝 Fingerprint: {}", run);
        LOG.info("   {}", m.brief());
        LOG.info("   stamp: commit={} dirty={} cfg={} sets[mkt={} fund={} ticker={}] slip={} fee={} filter={}",
                fp.commit, fp.dirty, fp.configVersion, fp.setMarket, fp.setFunding, fp.setTicker,
                fp.slippageRate, fp.rateFee, fp.filterMode);

        File base = new File("docs/golden/baseline-" + profile + ".json");
        if (!base.exists()) {
            LOG.warn("⚠️ Chưa có baseline {} → đây là fingerprint ĐẦU. Duyệt rồi promote: cp {} {} + commit.",
                    base.getPath(), run, base.getPath());
            return;
        }
        Fingerprint bl = Utils.gson.fromJson(new String(Files.readAllBytes(base.toPath())), Fingerprint.class);
        compareAndVerdict(fp, bl);
    }

    private void compareAndVerdict(Fingerprint cur, Fingerprint bl) {
        boolean stampSame = cur.stampEquals(bl);
        List<String> metricDiff = cur.metrics.diff(bl.metrics);
        if (stampSame) {
            if (metricDiff.isEmpty()) {
                LOG.info("✅ GOLDEN OK — STAMP-input khớp baseline & metric khớp. Không regression.");
            } else {
                LOG.error("🔴 REGRESSION — STAMP-input KHỚP baseline nhưng METRIC ĐỔI: {}", metricDiff);
                LOG.error("   => code/sim đổi hành vi hoặc nondeterministic. Phải điều tra TRƯỚC khi tin.");
                System.exit(1);
            }
        } else {
            LOG.warn("ℹ️ STAMP-input KHÁC baseline (diff stamp: {}) → đây là thay đổi CÓ CHỦ Ý, in Δ metric để review (KHÔNG tự ghi đè baseline):",
                    cur.stampDiff(bl));
            for (String d : (metricDiff.isEmpty() ? Collections.singletonList("(metric không đổi)") : metricDiff)) LOG.warn("   Δ {}", d);
            LOG.warn("   Nếu duyệt: cp outputs/golden/{}-{}.json docs/golden/baseline-{}.json + commit.", cur.profile, cur.commit, cur.profile);
        }
    }

    /** Reset state tịnh tiến → chạy sim → thu metric. */
    private Metrics runSim(long startTs, long endTs) {
        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        try {
            sim.initDataReady(mkt, pred, fund, new AIRejectFilter());
            sim.simulatorWithInitEntry(startTs, endTs);   // qua BacktestIntegrityGuard
        } catch (Exception ex) {
            LOG.error("❌ chạy sim lỗi", ex);
            throw new RuntimeException(ex);
        }
        return collect(sim);
    }

    private Metrics collect(SimulatorMarketLevelTicker1MStopLoss sim) {
        Metrics m = new Metrics();
        TreeMap<Long, OrderTargetInfoTest> done = sim.allOrderDone;
        m.numTrades = (done == null) ? 0 : done.size();
        m.perYearPnl = new TreeMap<>();
        Map<String, List<OrderTargetInfoTest>> clusters = new HashMap<>();
        if (done != null) {
            for (OrderTargetInfoTest o : done.values()) {
                double tp = o.calTp();
                m.totalPnl += tp;
                m.perYearPnl.merge(Utils.getYear(o.timeUpdate), tp, Double::sum);
                clusters.computeIfAbsent(o.symbolId + "@" + o.timeUpdate, k -> new ArrayList<>()).add(o);
            }
        }
        m.worstSingleLoss = 0;
        for (List<OrderTargetInfoTest> legs : clusters.values()) {
            double cPnl = 0, sumQE = 0, sumQ = 0;
            long first = Long.MAX_VALUE, close = 0;
            Float low = null;
            for (OrderTargetInfoTest o : legs) {
                cPnl += o.calTp();
                if (o.quantity != null && o.priceEntry != null) { sumQE += (double) o.priceEntry * o.quantity; sumQ += o.quantity; }
                first = Math.min(first, o.timeStart);
                close = Math.max(close, o.timeUpdate);
                if (o.maeLow != null) low = o.maeLow;   // mọi leg cùng cụm chia chung maeLow
            }
            if (close - first > HOLD_30D) m.clustersHeld30d++;
            if (cPnl < m.worstSingleLoss) m.worstSingleLoss = cPnl;
            if (low != null && sumQ > 0) {
                double avgE = sumQE / sumQ;
                if (avgE > 0 && (low / avgE - 1.0) <= NEAR_LIQ_DD) m.nearLiq++;
            }
        }
        Float un = BudgetManagerSimple.getInstance().balanceIndex.unProfitMin;
        m.maxDD = (un != null) ? un : 0f;
        return m;
    }

    private Fingerprint stamp(String profile, String start, String end, Metrics m) {
        Fingerprint f = new Fingerprint();
        f.profile = profile;
        f.start = start; f.end = end;
        f.commit = envOr("GOLDEN_COMMIT", "unknown");
        f.dirty = envOr("GOLDEN_DIRTY", "unknown");
        f.configVersion = RunHpoMaster_Distributed.CONFIG_VERSION;
        f.setMarket = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_MARKET_DATA;
        f.setFunding = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_FUNDING_PRED;
        f.setTicker = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER;
        f.readCluster = (Configs.IS_KAGGLE_MODE || Configs.IS_HPO_MODE) ? "226" : "242";
        f.slippageRate = Configs.SLIPPAGE_RATE;
        f.rateFee = Configs.RATE_FEE;
        f.applySlippage = Configs.APPLY_SLIPPAGE;
        f.blockLookahead = Configs.BLOCK_INTRABAR_LOOKAHEAD;
        f.filterMode = String.valueOf(Configs.FILTER_MODE);
        f.metrics = m;
        if ("unknown".equals(f.commit) || "true".equals(f.dirty))
            LOG.warn("⚠️ commit/dirty không xác định (env GOLDEN_COMMIT/GOLDEN_DIRTY) hoặc working-tree BẨN → fingerprint không gắn chắc với 1 commit. So baseline sẽ coi là STAMP-khác.");
        return f;
    }

    private static String envOr(String k, String d) { String v = System.getenv(k); return (v == null || v.isEmpty()) ? d : v; }
    private static long parse(String yyyymmdd) { try { return Utils.sdfFile.parse(yyyymmdd).getTime() + 7 * Utils.TIME_HOUR; } catch (Exception e) { throw new RuntimeException(e); } }
    private static long parseEnd(String yyyymmdd) { try { return Utils.sdfFile.parse(yyyymmdd).getTime() + 24 * Utils.TIME_HOUR - Utils.TIME_MINUTE; } catch (Exception e) { throw new RuntimeException(e); } }

    // ===== model =====
    static class Metrics {
        double totalPnl = 0, maxDD = 0, worstSingleLoss = 0;
        int numTrades = 0, clustersHeld30d = 0, nearLiq = 0;
        TreeMap<Integer, Double> perYearPnl = new TreeMap<>();

        List<String> diff(Metrics o) {
            List<String> d = new ArrayList<>();
            if (numTrades != o.numTrades) d.add("numTrades " + numTrades + " vs " + o.numTrades);
            if (clustersHeld30d != o.clustersHeld30d) d.add("clustersHeld30d " + clustersHeld30d + " vs " + o.clustersHeld30d);
            if (nearLiq != o.nearLiq) d.add("nearLiq " + nearLiq + " vs " + o.nearLiq);
            if (Math.abs(totalPnl - o.totalPnl) > EPS) d.add("totalPnl " + totalPnl + " vs " + o.totalPnl);
            if (Math.abs(maxDD - o.maxDD) > EPS) d.add("maxDD " + maxDD + " vs " + o.maxDD);
            if (Math.abs(worstSingleLoss - o.worstSingleLoss) > EPS) d.add("worstSingleLoss " + worstSingleLoss + " vs " + o.worstSingleLoss);
            return d;
        }

        String brief() {
            return String.format(Locale.US, "PnL=%.2f maxDD=%.2f worstLoss=%.2f numTrades=%d held>30d=%d nearLiq=%d",
                    totalPnl, maxDD, worstSingleLoss, numTrades, clustersHeld30d, nearLiq);
        }
    }

    static class Fingerprint {
        String profile, start, end, commit, dirty, configVersion, setMarket, setFunding, setTicker, readCluster, filterMode;
        float slippageRate, rateFee;
        boolean applySlippage, blockLookahead;
        Metrics metrics;

        boolean stampEquals(Fingerprint o) {
            return !"true".equals(dirty) && !"true".equals(o.dirty)
                    && eq(commit, o.commit) && eq(configVersion, o.configVersion)
                    && eq(setMarket, o.setMarket) && eq(setFunding, o.setFunding) && eq(setTicker, o.setTicker)
                    && eq(profile, o.profile) && eq(start, o.start) && eq(end, o.end) && eq(filterMode, o.filterMode)
                    && slippageRate == o.slippageRate && rateFee == o.rateFee
                    && applySlippage == o.applySlippage && blockLookahead == o.blockLookahead;
        }

        String stampDiff(Fingerprint o) {
            List<String> d = new ArrayList<>();
            if (!eq(commit, o.commit)) d.add("commit");
            if ("true".equals(dirty) || "true".equals(o.dirty)) d.add("dirty");
            if (!eq(configVersion, o.configVersion)) d.add("CONFIG_VERSION");
            if (!eq(setMarket, o.setMarket) || !eq(setFunding, o.setFunding) || !eq(setTicker, o.setTicker)) d.add("aerospike-set");
            if (slippageRate != o.slippageRate || rateFee != o.rateFee || applySlippage != o.applySlippage || blockLookahead != o.blockLookahead) d.add("cost/lookahead");
            if (!eq(filterMode, o.filterMode)) d.add("FILTER_MODE");
            if (!eq(start, o.start) || !eq(end, o.end)) d.add("range");
            return String.join(",", d);
        }

        private static boolean eq(Object a, Object b) { return Objects.equals(a, b); }
    }
}
