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
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * TASK-154 Phần B [FAIL-RECOVERY] — thống kê hồi-phục-từ-điểm-lỗ trên PATH 1m thật, làm nền cho tầng 3
 * (DCA/SL). Lấy điểm "entry-fail thật": entry = candidate selector (top-5/kỳ theo score s24h, cùng cách
 * chọn `PathTruthEntryProbe` Phần A), đi tuần tự 1m từ entry; lần đầu retLow chạm mỗi ngưỡng lỗ −Y% (Y ∈
 * DEPTHS) TRƯỚC KHI retHigh chạm +3% (target) = "điểm lỗ" (nếu +3% chạm trước → coi là DISQUALIFIED_BY_SUCCESS,
 * loại khỏi mẫu lỗ ở ngưỡng Y đó — công bằng vì lúc đó lệnh đã thắng, không còn ở trạng thái "đang lỗ"). Từ
 * mỗi điểm lỗ, đọc tiếp path 1m tới H giờ (H ∈ HORIZONS) đo: P(hồi hoà vốn/+1%/+3%), độ sâu lỗ TIẾP theo
 * (p50/p90, tuyệt đối so entry gốc) + kỳ vọng PnL 3 hành động (giữ nguyên / DCA-1-lần-ở-−Y% / cắt lỗ ngay).
 *
 * READ-ONLY, KHÔNG đụng jar sim/engine. Nguồn: ticker 1m Aerospike (set kline_1m_opt qua
 * {@link DataManagerAerospikeFloatSim#readDataFromAerospike1M(long)}) + score predict_wf_*.bin (struct
 * big-endian {@code >qh4f}) + symbol_map.csv — giống hệt nguồn Phần A.
 *
 * Env: PRED_DIR SYMBOL_MAP_CSV OUT_DIR PERIOD_HOURS(24) TOPN(5) DEPTHS_PCT_CSV(5,10,15,20,30)
 *      HORIZON_HOURS_CSV(24,72,168) CAP_DAYS(40) TARGET_RATE(0.03)
 */
public class FailRecoveryProbe {
    private static final Logger LOG = LoggerFactory.getLogger(FailRecoveryProbe.class);

    enum DepthStatus {PENDING, CROSSED, DISQUALIFIED_BY_SUCCESS, TIMEOUT_NO_CROSS, NO_DATA_ENTRY}

    static class PredRow {
        long ts;
        String symbol;
        float s24h;
    }

    static class HorizonState {
        int hours;
        long deadline = -1;
        boolean resolved = false;
        boolean recoveredBreakeven = false, recovered1pct = false, recovered3pct = false;
        double minRetInWindow = Double.NaN; // đáy tuyệt đối (so entry gốc) trong cửa sổ, đóng băng khi hồi hoà vốn
        double retAtDeadline = Double.NaN; // PnL "giữ nguyên" tại mốc H
    }

    static class DepthState {
        double y; // 0.05 / 0.10 / ...
        DepthStatus status = DepthStatus.PENDING;
        long crossTs = -1;
        double crossRet = Double.NaN; // return tại nến chạm (retLow), ~ -y hoặc sâu hơn
        HorizonState[] horizons;
    }

    static class Entry {
        String symbol;
        long entryTs;
        long capDeadline;
        float entryPrice = -1f;
        boolean started = false;
        boolean hit3pct = false;
        double lastKnownRet = 0.0;
        DepthState[] depths;
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
        int periodHours = Integer.parseInt(System.getenv().getOrDefault("PERIOD_HOURS", "24"));
        int topN = Integer.parseInt(System.getenv().getOrDefault("TOPN", "5"));
        double[] depthsPct = parseDoubleCsv(System.getenv().getOrDefault("DEPTHS_PCT_CSV", "5,10,15,20,30"));
        int[] horizonHours = parseIntCsv(System.getenv().getOrDefault("HORIZON_HOURS_CSV", "24,72,168"));
        int capDays = Integer.parseInt(System.getenv().getOrDefault("CAP_DAYS", "40"));
        double targetRate = Double.parseDouble(System.getenv().getOrDefault("TARGET_RATE", "0.03"));

        Files.createDirectories(Paths.get(outDir));
        LOG.info("START FailRecoveryProbe predDir={} outDir={} periodH={} topN={} depths%={} horizonsH={} capDays={} target={}",
                predDir, outDir, periodHours, topN, Arrays.toString(depthsPct), Arrays.toString(horizonHours), capDays, targetRate);

        Map<Integer, String> id2sym = loadSymbolMap(symMapCsv);
        List<PredRow> rows = loadPredictRows(predDir, id2sym);
        rows.sort((a, b) -> Long.compare(a.ts, b.ts));
        LOG.info("predict_wf: {} dong", rows.size());

        List<PredRow> filtered = new ArrayList<>();
        for (PredRow r : rows) if (!Float.isNaN(r.s24h)) filtered.add(r);
        if (filtered.isEmpty()) throw new IllegalStateException("Khong co dong score s24h hop le");
        long t0 = filtered.get(0).ts, t1 = filtered.get(filtered.size() - 1).ts;
        long stepMs = periodHours * 3600_000L;
        LOG.info("Periodization: {} dong hop le, t0={} t1={}", filtered.size(),
                Utils.normalizeDateYYYYMMDDHHmm(t0), Utils.normalizeDateYYYYMMDDHHmm(t1));

        List<Entry> allEntries = new ArrayList<>();
        TreeMap<Long, List<Entry>> entryIndex = new TreeMap<>();
        int cursor = 0, n = filtered.size();
        long nPeriods = 0;
        long capMs = capDays * Utils.TIME_DAY;
        for (long lo = t0; lo <= t1; lo += stepMs) {
            long hi = lo + stepMs;
            int start = cursor;
            while (cursor < n && filtered.get(cursor).ts < hi) cursor++;
            int end = cursor;
            int count = end - start;
            if (count < topN) continue;
            nPeriods++;
            Integer[] localIdx = new Integer[count];
            for (int i = 0; i < count; i++) localIdx[i] = start + i;
            Arrays.sort(localIdx, (a, b) -> Float.compare(filtered.get(b).s24h, filtered.get(a).s24h));
            for (int i = 0; i < topN; i++) {
                PredRow r = filtered.get(localIdx[i]);
                Entry e = new Entry();
                e.symbol = r.symbol;
                e.entryTs = r.ts;
                e.capDeadline = r.ts + capMs;
                e.depths = new DepthState[depthsPct.length];
                for (int di = 0; di < depthsPct.length; di++) {
                    DepthState d = new DepthState();
                    d.y = depthsPct[di] / 100.0;
                    d.horizons = new HorizonState[horizonHours.length];
                    for (int hi2 = 0; hi2 < horizonHours.length; hi2++) {
                        HorizonState h = new HorizonState();
                        h.hours = horizonHours[hi2];
                        d.horizons[hi2] = h;
                    }
                    e.depths[di] = d;
                }
                allEntries.add(e);
                entryIndex.computeIfAbsent(r.ts, k -> new ArrayList<>()).add(e);
            }
        }
        LOG.info("Tao {} entry (nPeriods={} x topN={})", allEntries.size(), nPeriods, topN);
        if (allEntries.isEmpty()) return;

        long minEntryTs = Long.MAX_VALUE, maxCap = Long.MIN_VALUE;
        for (Entry e : allEntries) {
            if (e.entryTs < minEntryTs) minEntryTs = e.entryTs;
            if (e.capDeadline > maxCap) maxCap = e.capDeadline;
        }
        LOG.info("QUET 1M: {} .. {}", Utils.normalizeDateYYYYMMDDHHmm(minEntryTs), Utils.normalizeDateYYYYMMDDHHmm(maxCap));

        List<Entry> active = new ArrayList<>();
        long day = minEntryTs;
        long endScan = maxCap;
        long dayCount = 0;
        long t0Wall = System.currentTimeMillis();
        while (day <= endScan) {
            TreeMap<Long, Map<String, KlineObjectSimple>> dayData = DataManagerAerospikeFloatSim.readDataFromAerospike1M(day);
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> minuteEntry : dayData.entrySet()) {
                long t = minuteEntry.getKey();
                Map<String, KlineObjectSimple> bars = minuteEntry.getValue();

                List<Entry> starting = entryIndex.get(t);
                if (starting != null) {
                    for (Entry e : starting) {
                        KlineObjectSimple bar = bars.get(e.symbol);
                        if (bar == null || !Utils.isTickerAvailable(bar)) {
                            markNoDataEntry(e);
                            continue;
                        }
                        e.entryPrice = bar.priceClose;
                        e.started = true;
                        active.add(e);
                    }
                }

                if (active.isEmpty()) continue;
                Iterator<Entry> it = active.iterator();
                while (it.hasNext()) {
                    Entry e = it.next();
                    if (t > e.capDeadline) {
                        finalizeEntry(e);
                        it.remove();
                        continue;
                    }
                    // đóng các horizon đã tới deadline TRƯỚC khi áp dụng nến hiện tại (dùng lastKnownRet cũ)
                    for (DepthState d : e.depths) {
                        if (d.status != DepthStatus.CROSSED) continue;
                        for (HorizonState h : d.horizons) {
                            if (!h.resolved && h.deadline >= 0 && t > h.deadline) {
                                h.retAtDeadline = e.lastKnownRet;
                                h.resolved = true;
                            }
                        }
                    }
                    KlineObjectSimple bar = bars.get(e.symbol);
                    if (bar == null || !Utils.isTickerAvailable(bar)) continue; // gap, giu nguyen trang thai
                    double retHigh = bar.maxPrice / e.entryPrice - 1.0;
                    double retLow = bar.minPrice / e.entryPrice - 1.0;
                    e.lastKnownRet = bar.priceClose / e.entryPrice - 1.0;

                    if (!e.hit3pct) {
                        for (DepthState d : e.depths) {
                            if (d.status == DepthStatus.PENDING && retLow <= -d.y) {
                                d.status = DepthStatus.CROSSED;
                                d.crossTs = t;
                                d.crossRet = retLow;
                                for (HorizonState h : d.horizons) {
                                    h.deadline = t + h.hours * 3600_000L;
                                    h.minRetInWindow = retLow;
                                }
                            }
                        }
                        if (retHigh >= targetRate) e.hit3pct = true;
                    }
                    for (DepthState d : e.depths) {
                        if (d.status != DepthStatus.CROSSED) continue;
                        for (HorizonState h : d.horizons) {
                            if (h.resolved) continue;
                            if (!h.recoveredBreakeven) h.minRetInWindow = Math.min(h.minRetInWindow, retLow);
                            if (!h.recoveredBreakeven && retHigh >= 0.0) h.recoveredBreakeven = true;
                            if (!h.recovered1pct && retHigh >= 0.01) h.recovered1pct = true;
                            if (!h.recovered3pct && retHigh >= targetRate) h.recovered3pct = true;
                        }
                    }
                    if (isEntryFullyDone(e)) {
                        finalizeEarly(e);
                        it.remove();
                    }
                }
            }
            dayCount++;
            if (dayCount % 60 == 0) {
                long elapsedS = (System.currentTimeMillis() - t0Wall) / 1000;
                LOG.info("[PROGRESS] day={} ({}) active={} elapsedS={}", dayCount,
                        Utils.normalizeDateYYYYMMDDHHmm(day), active.size(), elapsedS);
                writeCheckpoint(outDir, allEntries, depthsPct, horizonHours, day, dayCount, false);
            }
            day += Utils.TIME_DAY;
        }
        for (Entry e : active) finalizeEntry(e);

        LOG.info("QUET XONG. Ghi ket qua...");
        writeCheckpoint(outDir, allEntries, depthsPct, horizonHours, day, dayCount, true);
        LOG.info("DONE FailRecoveryProbe");
    }

    static void markNoDataEntry(Entry e) {
        for (DepthState d : e.depths) d.status = DepthStatus.NO_DATA_ENTRY;
    }

    /** hit3pct đã bật (không còn crossing MỚI nào xảy ra) và mọi depth đã CROSSED đều đã resolved đủ horizon. */
    static boolean isEntryFullyDone(Entry e) {
        if (!e.hit3pct) return false;
        for (DepthState d : e.depths) {
            if (d.status != DepthStatus.CROSSED) continue;
            for (HorizonState h : d.horizons) if (!h.resolved) return false;
        }
        return true;
    }

    /** Entry dừng sớm (hit3pct + mọi crossed-depth đã resolved) — depth chưa từng CROSSED = DISQUALIFIED_BY_SUCCESS. */
    static void finalizeEarly(Entry e) {
        for (DepthState d : e.depths) if (d.status == DepthStatus.PENDING) d.status = DepthStatus.DISQUALIFIED_BY_SUCCESS;
    }

    /** Cap (capDeadline) hoặc hết dữ liệu quét — depth chưa CROSSED = TIMEOUT_NO_CROSS; horizon CROSSED chưa resolved = chốt bằng lastKnownRet. */
    static void finalizeEntry(Entry e) {
        if (!e.started) return; // NO_DATA_ENTRY đã đánh dấu ở markNoDataEntry, không cần chốt thêm
        for (DepthState d : e.depths) {
            if (d.status == DepthStatus.PENDING) {
                d.status = DepthStatus.TIMEOUT_NO_CROSS;
            } else if (d.status == DepthStatus.CROSSED) {
                for (HorizonState h : d.horizons) {
                    if (!h.resolved) {
                        h.retAtDeadline = e.lastKnownRet;
                        h.resolved = true;
                    }
                }
            }
        }
    }

    static double dcaReturn(double retAtDeadline, double crossRet) {
        double r1 = retAtDeadline, rc = crossRet;
        return (1 + r1) * (1 + 1.0 / (1 + rc)) / 2.0 - 1.0;
    }

    static double percentile(List<Double> sorted, double p) {
        if (sorted.isEmpty()) return Double.NaN;
        int idx = (int) Math.ceil(p * sorted.size()) - 1;
        idx = Math.max(0, Math.min(sorted.size() - 1, idx));
        return sorted.get(idx);
    }

    static double mean(List<Double> v) {
        if (v.isEmpty()) return Double.NaN;
        double s = 0;
        for (double x : v) s += x;
        return s / v.size();
    }

    static void writeCheckpoint(String outDir, List<Entry> allEntries, double[] depthsPct, int[] horizonHours,
                                 long dayCursor, long dayCount, boolean isFinal) throws Exception {
        StringBuilder sb = new StringBuilder();
        sb.append("{\n  \"final\": ").append(isFinal).append(",\n");
        sb.append("  \"dayCount\": ").append(dayCount).append(",\n");
        sb.append("  \"dayCursor\": \"").append(Utils.normalizeDateYYYYMMDDHHmm(dayCursor)).append("\",\n");
        sb.append("  \"nEntries\": ").append(allEntries.size()).append(",\n");
        sb.append("  \"cells\": [\n");
        boolean firstCell = true;
        for (int di = 0; di < depthsPct.length; di++) {
            long nCrossed = 0, nDisq = 0, nTimeout = 0, nNoData = 0;
            for (Entry e : allEntries) {
                DepthState d = e.depths[di];
                switch (d.status) {
                    case CROSSED: nCrossed++; break;
                    case DISQUALIFIED_BY_SUCCESS: nDisq++; break;
                    case TIMEOUT_NO_CROSS: nTimeout++; break;
                    case NO_DATA_ENTRY: nNoData++; break;
                    default: break;
                }
            }
            for (int hi = 0; hi < horizonHours.length; hi++) {
                List<Double> holdRets = new ArrayList<>(), dcaRets = new ArrayList<>(), cutRets = new ArrayList<>();
                List<Double> furtherDepthAbs = new ArrayList<>();
                long nResolved = 0, nBreakeven = 0, n1pct = 0, n3pct = 0;
                for (Entry e : allEntries) {
                    DepthState d = e.depths[di];
                    if (d.status != DepthStatus.CROSSED) continue;
                    HorizonState h = d.horizons[hi];
                    if (!h.resolved) continue;
                    nResolved++;
                    if (h.recoveredBreakeven) nBreakeven++;
                    if (h.recovered1pct) n1pct++;
                    if (h.recovered3pct) n3pct++;
                    holdRets.add(h.retAtDeadline);
                    dcaRets.add(dcaReturn(h.retAtDeadline, d.crossRet));
                    cutRets.add(d.crossRet);
                    furtherDepthAbs.add(Math.abs(h.minRetInWindow));
                }
                Collections.sort(furtherDepthAbs);
                if (!firstCell) sb.append(",\n");
                firstCell = false;
                sb.append("    {\n");
                sb.append("      \"depthPct\": ").append(depthsPct[di]).append(",\n");
                sb.append("      \"horizonHours\": ").append(horizonHours[hi]).append(",\n");
                sb.append("      \"nCrossedTotal\": ").append(nCrossed).append(",\n");
                sb.append("      \"nDisqualifiedBySuccess\": ").append(nDisq).append(",\n");
                sb.append("      \"nTimeoutNoCross\": ").append(nTimeout).append(",\n");
                sb.append("      \"nNoDataEntry\": ").append(nNoData).append(",\n");
                sb.append("      \"nResolved\": ").append(nResolved).append(",\n");
                sb.append("      \"p_breakeven\": ").append(fmtRatio(nBreakeven, nResolved)).append(",\n");
                sb.append("      \"p_1pct\": ").append(fmtRatio(n1pct, nResolved)).append(",\n");
                sb.append("      \"p_3pct\": ").append(fmtRatio(n3pct, nResolved)).append(",\n");
                sb.append("      \"furtherDepthAbs_p50\": ").append(fmtD(percentile(furtherDepthAbs, 0.5))).append(",\n");
                sb.append("      \"furtherDepthAbs_p90\": ").append(fmtD(percentile(furtherDepthAbs, 0.9))).append(",\n");
                sb.append("      \"pnlEnd_hold_mean\": ").append(fmtD(mean(holdRets))).append(",\n");
                sb.append("      \"pnlEnd_dca_mean\": ").append(fmtD(mean(dcaRets))).append(",\n");
                sb.append("      \"pnlEnd_cut_mean\": ").append(fmtD(mean(cutRets))).append("\n");
                sb.append("    }");
            }
        }
        sb.append("\n  ]\n}\n");
        String name = isFinal ? "task154_partB_result.json" : "task154_partB_progress.json";
        Files.write(Paths.get(outDir, name), sb.toString().getBytes());
    }

    static String fmtRatio(long num, long den) {
        return den == 0 ? "null" : String.format("%.6f", num / (double) den);
    }

    static String fmtD(double v) {
        return Double.isNaN(v) ? "null" : String.format("%.6f", v);
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
        if (files == null || files.length == 0) throw new IllegalStateException("Khong tim thay predict_wf_*.bin trong " + dir);
        Arrays.sort(files);
        List<PredRow> out = new ArrayList<>();
        int dropped = 0;
        final int REC = 26;
        for (File f : files) {
            byte[] data = Files.readAllBytes(f.toPath());
            if (data.length % REC != 0) throw new IllegalStateException(f + ": size " + data.length + " khong chia het " + REC);
            ByteBuffer buf = ByteBuffer.wrap(data);
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
                r.s24h = p24;
                r.symbol = sym;
                out.add(r);
            }
            LOG.info("doc {} : {} record", f.getName(), nRec);
        }
        LOG.info("predict_wf: {} file, {} dong giu, {} dong bo", files.length, out.size(), dropped);
        return out;
    }

    static int[] parseIntCsv(String s) {
        String[] p = s.split(",");
        int[] out = new int[p.length];
        for (int i = 0; i < p.length; i++) out[i] = Integer.parseInt(p[i].trim());
        return out;
    }

    static double[] parseDoubleCsv(String s) {
        String[] p = s.split(",");
        double[] out = new double[p.length];
        for (int i = 0; i < p.length; i++) out[i] = Double.parseDouble(p[i].trim());
        return out;
    }
}
