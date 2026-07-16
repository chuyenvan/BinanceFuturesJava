package com.binance.chuyennd.ai_ml.validation.data;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.TreeMap;

/**
 * TASK-154 Phần A [PATH-TRUTH ENTRY] — đo PRECISION path 1m THẬT (không xấp xỉ) của selector predict_wf
 * cho cơ chế "arm SL+1% rồi target +3%": đi tuần tự từng nến 1m từ mốc entry, chạm +1% thì arm SL cứng
 * +1%; rớt dưới +1% TRƯỚC khi chạm +3% = FAIL (SL quét); chạm +3% trước = SUCCESS. So selector (top-5/kỳ
 * theo score) vs random baseline (5 coin ngẫu nhiên/kỳ, N_REPS lần, seed cố định) — H ∈ {4h,24h,72h}.
 * Kỳ = block H-giờ KHÔNG chồng lấn, giống hệt cách chia của kernel Kaggle task-153
 * (entry-label-precision-153.py: edges = arange(t0, t1+step, step), t0/t1 = min/max ts của tập candidate).
 *
 * READ-ONLY. KHÔNG đụng jar sim/engine. Dữ liệu: ticker 1m Aerospike (set kline_1m_opt, qua
 * {@link DataManagerAerospikeFloatSim#readDataFromAerospike1M(long)} — client theo AEROSPIKE_READ_CLUSTER
 * trong config.properties) + score predict_wf_*.bin (struct big-endian {@code >qh4f}: ts,symId,
 * score_4h/12h/24h/72h) + symbol_map.csv (symId,symbol).
 *
 * Quét MỘT LẦT tuần tự theo ngày (giống {@code SimulatorMarketLevelTicker1MStopLoss}), giữ danh sách
 * lệnh đang "active" (đã tới mốc entry, chưa resolve) — tránh đọc lại Aerospike nhiều lần cho từng entry.
 *
 * Env: PRED_DIR(/home/ubuntu/claudedata/wf_pred_ret2) SYMBOL_MAP_CSV(/home/ubuntu/kaggle_selector_ds/symbol_map.csv)
 *      OUT_DIR(/home/ubuntu/team_path/out) TOPN(5) N_REPS(20) SEED(42) ARM_RATE(0.01) TARGET_RATE(0.03)
 *      HORIZON_HOURS_CSV(4,24,72)
 */
public class PathTruthEntryProbe {
    private static final Logger LOG = LoggerFactory.getLogger(PathTruthEntryProbe.class);

    enum Outcome {SUCCESS, FAIL_SL_HIT, FAIL_TIMEOUT_ARMED, FAIL_TIMEOUT_NEVER_ARMED, NO_DATA_ENTRY, NO_DATA_END}

    /** Một hàng score predict_wf: ts (mốc 15 phút) + symbol (đã map từ symId) + 3 score horizon 4h/24h/72h (bỏ 12h — ngoài scope). */
    static class PredRow {
        long ts;
        String symbol;
        float s4h, s24h, s72h;
    }

    static class Trade {
        String symbol;
        long entryTs;
        long deadline;
        int horizonIdx;
        boolean isSelector; // false = random baseline
        float entryPrice = -1f;
        boolean armed = false;
        boolean trueAHit = false; // đã từng chạm +3% (bất kể có bị quét SL hay không) — đối chiếu định nghĩa A cũ
        Outcome outcome = null;
    }

    public static void main(String[] args) {
        try {
            run();
            System.exit(0);
        } catch (Exception e) {
            LOG.error("FATAL", e);
            System.exit(1);
        }
    }

    static void run() throws Exception {
        String predDir = System.getenv().getOrDefault("PRED_DIR", "/home/ubuntu/claudedata/wf_pred_ret2");
        String symMapCsv = System.getenv().getOrDefault("SYMBOL_MAP_CSV", "/home/ubuntu/kaggle_selector_ds/symbol_map.csv");
        String outDir = System.getenv().getOrDefault("OUT_DIR", "/home/ubuntu/team_path/out");
        int topN = Integer.parseInt(System.getenv().getOrDefault("TOPN", "5"));
        int nReps = Integer.parseInt(System.getenv().getOrDefault("N_REPS", "20"));
        long seed = Long.parseLong(System.getenv().getOrDefault("SEED", "42"));
        double armRate = Double.parseDouble(System.getenv().getOrDefault("ARM_RATE", "0.01"));
        double targetRate = Double.parseDouble(System.getenv().getOrDefault("TARGET_RATE", "0.03"));
        int[] horizonHours = parseIntCsv(System.getenv().getOrDefault("HORIZON_HOURS_CSV", "4,24,72"));

        Files.createDirectories(Paths.get(outDir));
        LOG.info("START PathTruthEntryProbe predDir={} symMapCsv={} outDir={} topN={} nReps={} seed={} arm={} target={} horizons={}",
                predDir, symMapCsv, outDir, topN, nReps, seed, armRate, targetRate, Arrays.toString(horizonHours));

        Map<Integer, String> id2sym = loadSymbolMap(symMapCsv);
        LOG.info("symbol_map: {} entries", id2sym.size());

        List<PredRow> rows = loadPredictRows(predDir, id2sym);
        rows.sort((a, b) -> Long.compare(a.ts, b.ts));
        LOG.info("predict_wf: {} dong (sau map symId->symbol, sort theo ts)", rows.size());

        List<Trade> allTrades = new ArrayList<>();
        TreeMap<Long, List<Trade>> entryIndex = new TreeMap<>();
        long[][] periodStats = new long[horizonHours.length][2]; // [nPeriods, sumCandidates]

        for (int hIdx = 0; hIdx < horizonHours.length; hIdx++) {
            long stepMs = horizonHours[hIdx] * 3600_000L;
            List<PredRow> filtered = filterValid(rows, hIdx);
            if (filtered.isEmpty()) {
                LOG.warn("H={}h: KHONG co dong score hop le — bo qua", horizonHours[hIdx]);
                continue;
            }
            long t0 = filtered.get(0).ts;
            long t1 = filtered.get(filtered.size() - 1).ts;
            LOG.info("H={}h: {} dong hop le, t0={} t1={}", horizonHours[hIdx], filtered.size(),
                    Utils.normalizeDateYYYYMMDDHHmm(t0), Utils.normalizeDateYYYYMMDDHHmm(t1));

            Random rng = new Random(seed);
            int cursor = 0;
            int n = filtered.size();
            long nPeriods = 0, sumCandidates = 0;
            for (long lo = t0; lo <= t1; lo += stepMs) {
                long hi = lo + stepMs;
                int start = cursor;
                while (cursor < n && filtered.get(cursor).ts < hi) cursor++;
                int end = cursor;
                int count = end - start;
                if (count < topN) continue;
                nPeriods++;
                sumCandidates += count;

                final int hIdxFinal = hIdx;
                final List<PredRow> filteredFinal = filtered;
                Integer[] localIdx = new Integer[count];
                for (int i = 0; i < count; i++) localIdx[i] = start + i;
                Integer[] sortedByScore = localIdx.clone();
                Arrays.sort(sortedByScore, (a, b) -> Float.compare(
                        scoreOf(filteredFinal.get(b), hIdxFinal), scoreOf(filteredFinal.get(a), hIdxFinal)));

                for (int i = 0; i < topN; i++) {
                    PredRow r = filtered.get(sortedByScore[i]);
                    addTrade(allTrades, entryIndex, r, hIdx, stepMs, true);
                }

                for (int rep = 0; rep < nReps; rep++) {
                    HashSet<Integer> picked = new HashSet<>();
                    while (picked.size() < topN) {
                        picked.add(start + rng.nextInt(count));
                    }
                    for (int p : picked) {
                        PredRow r = filtered.get(p);
                        addTrade(allTrades, entryIndex, r, hIdx, stepMs, false);
                    }
                }
            }
            periodStats[hIdx][0] = nPeriods;
            periodStats[hIdx][1] = sumCandidates;
            LOG.info("H={}h: n_ky={} n_candidate_tb={}", horizonHours[hIdx], nPeriods,
                    nPeriods == 0 ? 0 : sumCandidates / nPeriods);
        }
        LOG.info("TONG SO TRADE (selector+random, ca 3 horizon): {}", allTrades.size());

        if (allTrades.isEmpty()) {
            LOG.error("KHONG co trade nao duoc tao — dung, kiem tra predict_wf/symbol_map");
            return;
        }

        long minEntryTs = Long.MAX_VALUE, maxDeadline = Long.MIN_VALUE;
        for (Trade t : allTrades) {
            if (t.entryTs < minEntryTs) minEntryTs = t.entryTs;
            if (t.deadline > maxDeadline) maxDeadline = t.deadline;
        }
        LOG.info("QUET 1M: {} .. {} (+3 ngay dem)", Utils.normalizeDateYYYYMMDDHHmm(minEntryTs),
                Utils.normalizeDateYYYYMMDDHHmm(maxDeadline));

        List<Trade> activeTrades = new ArrayList<>();
        long day = minEntryTs;
        long endScan = maxDeadline + 3 * Utils.TIME_DAY;
        long dayCount = 0;
        long t0Wall = System.currentTimeMillis();
        while (day <= endScan) {
            TreeMap<Long, Map<String, KlineObjectSimple>> dayData = DataManagerAerospikeFloatSim.readDataFromAerospike1M(day);
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> minuteEntry : dayData.entrySet()) {
                long t = minuteEntry.getKey();
                Map<String, KlineObjectSimple> bars = minuteEntry.getValue();

                List<Trade> starting = entryIndex.get(t);
                if (starting != null) {
                    for (Trade tr : starting) {
                        KlineObjectSimple bar = bars.get(tr.symbol);
                        if (bar == null || !Utils.isTickerAvailable(bar)) {
                            tr.outcome = Outcome.NO_DATA_ENTRY;
                            continue;
                        }
                        tr.entryPrice = bar.priceClose;
                        activeTrades.add(tr);
                    }
                }

                if (!activeTrades.isEmpty()) {
                    Iterator<Trade> it = activeTrades.iterator();
                    while (it.hasNext()) {
                        Trade tr = it.next();
                        if (t > tr.deadline) {
                            tr.outcome = tr.armed ? Outcome.FAIL_TIMEOUT_ARMED : Outcome.FAIL_TIMEOUT_NEVER_ARMED;
                            it.remove();
                            continue;
                        }
                        KlineObjectSimple bar = bars.get(tr.symbol);
                        if (bar == null || !Utils.isTickerAvailable(bar)) continue; // gap 1 phut, giu nguyen trang thai
                        double retHigh = bar.maxPrice / tr.entryPrice - 1.0;
                        double retLow = bar.minPrice / tr.entryPrice - 1.0;
                        if (retHigh >= targetRate) tr.trueAHit = true;
                        if (tr.armed && retLow <= armRate) {
                            tr.outcome = Outcome.FAIL_SL_HIT;
                            it.remove();
                            continue;
                        }
                        if (retHigh >= targetRate) {
                            tr.outcome = Outcome.SUCCESS;
                            it.remove();
                            continue;
                        }
                        if (!tr.armed && retHigh >= armRate) tr.armed = true;
                    }
                }
            }
            dayCount++;
            if (dayCount % 60 == 0) {
                long elapsedS = (System.currentTimeMillis() - t0Wall) / 1000;
                LOG.info("[PROGRESS] day={} ({}) active={} elapsedS={}", dayCount,
                        Utils.normalizeDateYYYYMMDDHHmm(day), activeTrades.size(), elapsedS);
                writeCheckpoint(outDir, allTrades, horizonHours, periodStats, day, dayCount, false);
            }
            day += Utils.TIME_DAY;
        }

        for (Trade tr : activeTrades) tr.outcome = Outcome.NO_DATA_END;
        for (Trade tr : allTrades) if (tr.outcome == null) tr.outcome = Outcome.NO_DATA_ENTRY;

        LOG.info("QUET XONG. Ghi ket qua...");
        writeCheckpoint(outDir, allTrades, horizonHours, periodStats, day, dayCount, true);
        LOG.info("DONE PathTruthEntryProbe");
    }

    static float scoreOf(PredRow r, int hIdx) {
        switch (hIdx) {
            case 0: return r.s4h;
            case 1: return r.s24h;
            case 2: return r.s72h;
            default: throw new IllegalArgumentException("hIdx=" + hIdx);
        }
    }

    static void addTrade(List<Trade> allTrades, TreeMap<Long, List<Trade>> entryIndex, PredRow r, int hIdx,
                          long stepMs, boolean isSelector) {
        Trade tr = new Trade();
        tr.symbol = r.symbol;
        tr.entryTs = r.ts;
        tr.deadline = r.ts + stepMs;
        tr.horizonIdx = hIdx;
        tr.isSelector = isSelector;
        allTrades.add(tr);
        entryIndex.computeIfAbsent(r.ts, k -> new ArrayList<>()).add(tr);
    }

    static List<PredRow> filterValid(List<PredRow> rows, int hIdx) {
        List<PredRow> out = new ArrayList<>(rows.size());
        for (PredRow r : rows) {
            float s = scoreOf(r, hIdx);
            if (!Float.isNaN(s)) out.add(r);
        }
        return out;
    }

    static Map<Integer, String> loadSymbolMap(String path) throws Exception {
        Map<Integer, String> m = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(path))) {
            String line;
            boolean first = true;
            while ((line = br.readLine()) != null) {
                if (first) {
                    first = false;
                    if (line.startsWith("symId")) continue;
                }
                String[] p = line.split(",");
                if (p.length >= 2) {
                    try {
                        m.put(Integer.parseInt(p[0].trim()), p[1].trim());
                    } catch (NumberFormatException ignored) {
                    }
                }
            }
        }
        return m;
    }

    static List<PredRow> loadPredictRows(String dir, Map<Integer, String> id2sym) throws Exception {
        File d = new File(dir);
        File[] files = d.listFiles((dd, name) -> name.startsWith("predict_wf_") && name.endsWith(".bin"));
        if (files == null || files.length == 0) {
            throw new IllegalStateException("Khong tim thay predict_wf_*.bin trong " + dir);
        }
        Arrays.sort(files);
        List<PredRow> out = new ArrayList<>();
        int dropped = 0;
        final int REC = 26;
        for (File f : files) {
            byte[] data = Files.readAllBytes(f.toPath());
            if (data.length % REC != 0) {
                throw new IllegalStateException(f + ": size " + data.length + " khong chia het " + REC);
            }
            ByteBuffer buf = ByteBuffer.wrap(data); // default big-endian, khop Python struct ">qh4f"
            int nRec = data.length / REC;
            for (int i = 0; i < nRec; i++) {
                long ts = buf.getLong();
                short symId = buf.getShort();
                float p4 = buf.getFloat();
                float p12 = buf.getFloat();
                float p24 = buf.getFloat();
                float p72 = buf.getFloat();
                String sym = id2sym.get((int) symId);
                if (sym == null) {
                    dropped++;
                    continue;
                }
                PredRow r = new PredRow();
                r.ts = ts;
                r.s4h = p4;
                r.s24h = p24;
                r.s72h = p72;
                r.symbol = sym;
                out.add(r);
            }
            LOG.info("doc {} : {} record", f.getName(), nRec);
        }
        LOG.info("predict_wf: {} file, {} dong giu, {} dong bo (symId khong co trong symbol_map)",
                files.length, out.size(), dropped);
        // gán symbol string vào field dùng chung — Trade.symbol đọc qua PredRowSym
        return out;
    }

    static int[] parseIntCsv(String s) {
        String[] p = s.split(",");
        int[] out = new int[p.length];
        for (int i = 0; i < p.length; i++) out[i] = Integer.parseInt(p[i].trim());
        return out;
    }

    static void writeCheckpoint(String outDir, List<Trade> allTrades, int[] horizonHours, long[][] periodStats,
                                 long dayCursor, long dayCount, boolean isFinal) throws Exception {
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"final\": ").append(isFinal).append(",\n");
        sb.append("  \"dayCount\": ").append(dayCount).append(",\n");
        sb.append("  \"dayCursor\": \"").append(Utils.normalizeDateYYYYMMDDHHmm(dayCursor)).append("\",\n");
        sb.append("  \"horizons\": [\n");
        for (int hIdx = 0; hIdx < horizonHours.length; hIdx++) {
            long[] agg = aggregate(allTrades, hIdx);
            // agg: nSel, selSuccess, selSlHit, selTimeoutArmed, selTimeoutNeverArmed, selNoDataEntry, selNoDataEnd, selTrueA,
            //      nRnd, rndSuccess, rndSlHit, rndTimeoutArmed, rndTimeoutNeverArmed, rndNoDataEntry, rndNoDataEnd, rndTrueA
            sb.append("    {\n");
            sb.append("      \"horizonHours\": ").append(horizonHours[hIdx]).append(",\n");
            sb.append("      \"nPeriods\": ").append(periodStats[hIdx][0]).append(",\n");
            sb.append("      \"avgCandidatesPerPeriod\": ")
                    .append(periodStats[hIdx][0] == 0 ? 0 : periodStats[hIdx][1] / periodStats[hIdx][0]).append(",\n");
            sb.append("      \"selector\": ").append(outcomeJson(agg, 0)).append(",\n");
            sb.append("      \"random\": ").append(outcomeJson(agg, 8)).append("\n");
            sb.append("    }").append(hIdx == horizonHours.length - 1 ? "\n" : ",\n");
        }
        sb.append("  ]\n");
        sb.append("}\n");
        String name = isFinal ? "task154_partA_result.json" : "task154_partA_progress.json";
        Files.write(Paths.get(outDir, name), sb.toString().getBytes());
    }

    static String outcomeJson(long[] agg, int off) {
        long n = agg[off], succ = agg[off + 1], sl = agg[off + 2], toArmed = agg[off + 3],
                toNever = agg[off + 4], noEntry = agg[off + 5], noEnd = agg[off + 6], trueA = agg[off + 7];
        long resolved = n - noEntry - noEnd;
        return String.format(
                "{\"n\": %d, \"success\": %d, \"fail_sl_hit\": %d, \"fail_timeout_armed\": %d, "
                        + "\"fail_timeout_never_armed\": %d, \"no_data_entry\": %d, \"no_data_end\": %d, "
                        + "\"trueA_hit\": %d, \"precision_B\": %s, \"precision_A\": %s}",
                n, succ, sl, toArmed, toNever, noEntry, noEnd, trueA,
                resolved == 0 ? "null" : String.format("%.6f", succ / (double) resolved),
                resolved == 0 ? "null" : String.format("%.6f", trueA / (double) resolved));
    }

    /** @return mảng 16 phần tử: [0..7]=selector(n,success,slHit,toArmed,toNever,noEntry,noEnd,trueA), [8..15]=random tương tự. */
    static long[] aggregate(List<Trade> allTrades, int hIdx) {
        long[] a = new long[16];
        for (Trade tr : allTrades) {
            if (tr.horizonIdx != hIdx) continue;
            if (tr.outcome == null) continue; // dang active/pending — chi tinh khi da resolve (progress snapshot bo qua)
            int off = tr.isSelector ? 0 : 8;
            a[off]++;
            if (tr.trueAHit) a[off + 7]++;
            switch (tr.outcome) {
                case SUCCESS: a[off + 1]++; break;
                case FAIL_SL_HIT: a[off + 2]++; break;
                case FAIL_TIMEOUT_ARMED: a[off + 3]++; break;
                case FAIL_TIMEOUT_NEVER_ARMED: a[off + 4]++; break;
                case NO_DATA_ENTRY: a[off + 5]++; break;
                case NO_DATA_END: a[off + 6]++; break;
                default: break;
            }
        }
        return a;
    }
}
