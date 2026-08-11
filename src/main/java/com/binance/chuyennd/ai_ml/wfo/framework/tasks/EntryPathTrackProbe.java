package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.util.*;

/**
 * TASK (2026-08-01) — EXPORT PATH FORWARD cho tung entry ma selector chon.
 *
 * <p>VI SAO: dang thiet ke grid DCA cho hold-to-die. Uni chi ra selector chon coin bien dong manh nen
 * co the DUMP 3-4 lan. Dat moc grid bang phan doan = hong. Nhung chay full sim cho MOI cau hinh grid
 * thi qua cham (~20 phut/cau hinh).
 *
 * <p>DON BAY: export MOT LAN duong di gia sau moi entry -> sau do danh gia HANG TRAM cau hinh grid
 * OFFLINE trong vai giay (python). Tach thiet ke grid khoi simulator.
 *
 * <p>Cach chay: 1 luot duy nhat qua cac ngay. Moi ngay tinh dayLow/dayHigh cho tung symbol tu 1440 nen
 * 1m, roi cap nhat cac entry dang theo doi. Do phan giai NGAY la du cho viec dinh moc grid (-20/-40/-70%),
 * khong can chinh xac tung phut.
 *
 * <p>Env: PATH_ENTRY_CSV (mac dinh /home/ubuntu/claudedata/entry_universe_e0.csv),
 *         PATH_OUT (mac dinh /home/ubuntu/claudedata/entry_paths.csv),
 *         PATH_HORIZON_DAYS (mac dinh 180), PATH_COOLDOWN_H (mac dinh 24, dedup entry cung symbol),
 *         PATH_FROM / PATH_TO (yyyyMMdd).
 */
public class EntryPathTrackProbe {
    private static final Logger LOG = LoggerFactory.getLogger(EntryPathTrackProbe.class);
    private static final int[] HORIZONS = {1, 3, 7, 14, 30, 60, 90, 180};

    static class Track {
        String symbol; short sid; long entryTs; double entryPrice;
        double runMin, runMax;              // chay tu luc vao
        double[] maeAt = new double[HORIZONS.length];   // min-rate tai moc horizon
        double[] mfeAt = new double[HORIZONS.length];   // max-rate tai moc horizon
        int recoverDay = -1;                // ngay dau tien gia >= entryPrice SAU khi da tung < -10%
        boolean everDeep = false;           // da tung < -10%
        int daysTracked = 0;
        int lastSeenDay = 0;                // de phat hien delist
        boolean delisted = false;
        double lastPrice;
    }

    public static void main(String[] args) throws Exception {
        String csvIn  = System.getenv().getOrDefault("PATH_ENTRY_CSV", "/home/ubuntu/claudedata/entry_universe_e0.csv");
        String csvOut = System.getenv().getOrDefault("PATH_OUT", "/home/ubuntu/claudedata/entry_paths.csv");
        int horizonDays = Integer.parseInt(System.getenv().getOrDefault("PATH_HORIZON_DAYS", "180"));
        long cooldownMs = Long.parseLong(System.getenv().getOrDefault("PATH_COOLDOWN_H", "24")) * 3600_000L;
        String from = System.getenv().getOrDefault("PATH_FROM", "20210101");
        String to   = System.getenv().getOrDefault("PATH_TO",   "20260501");

        LOG.info("Doc entry tu {} | horizon={}d cooldown={}h | ticker source={}",
                csvIn, horizonDays, cooldownMs / 3600000, Configs.TICKER_SOURCE);

        // ---- 1. nap entry, dedup theo (symbol, cooldown) ----
        List<Track> pending = new ArrayList<>();
        Map<String, Long> lastEntryOf = new HashMap<>();
        long tFrom = Utils.sdfFile.parse(from).getTime() + 7 * Utils.TIME_HOUR;
        long tTo   = Utils.sdfFile.parse(to).getTime()   + 7 * Utils.TIME_HOUR;
        try (BufferedReader br = new BufferedReader(new FileReader(csvIn))) {
            String line = br.readLine();   // header
            while ((line = br.readLine()) != null) {
                String[] p = line.split(",");
                if (p.length < 6) continue;
                long ts = Long.parseLong(p[0].trim());
                if (ts < tFrom || ts > tTo) continue;
                short sid = Short.parseShort(p[2].trim());
                String sym = p[3].trim();
                double px = Double.parseDouble(p[5].trim());
                Long last = lastEntryOf.get(sym);
                if (last != null && ts - last < cooldownMs) continue;   // dedup
                lastEntryOf.put(sym, ts);
                Track t = new Track();
                t.symbol = sym; t.sid = sid; t.entryTs = ts; t.entryPrice = px;
                t.runMin = px; t.runMax = px; t.lastPrice = px;
                Arrays.fill(t.maeAt, Double.NaN);
                Arrays.fill(t.mfeAt, Double.NaN);
                pending.add(t);
            }
        }
        pending.sort(Comparator.comparingLong(a -> a.entryTs));
        LOG.info("Nap {} entry (sau dedup cooldown)", pending.size());
        if (pending.isEmpty()) { LOG.error("KHONG CO ENTRY -> dung"); System.exit(1); }

        // ---- 2. mot luot qua cac ngay ----
        List<Track> active = new ArrayList<>();
        List<Track> done = new ArrayList<>();
        int pi = 0, dayIdx = 0;
        long startTime = Utils.sdfFile.parse(from).getTime() + 7 * Utils.TIME_HOUR;
        long endTime   = Utils.sdfFile.parse(to).getTime()   + 7 * Utils.TIME_HOUR;

        for (long day = startTime; day <= endTime; day += Utils.TIME_DAY, dayIdx++) {
            TreeMap<Long, KlineObjectSimple[]> t2t;
            try {
                t2t = "aerospike".equals(Configs.TICKER_SOURCE)
                        ? DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(day)
                        : KaggleDataLoader.loadDailyTickersShort(day);
            } catch (Exception e) {
                LOG.warn("Ngay {} loi doc ticker -> bo qua", Utils.normalizeDateYYYYMMDD(day));
                continue;
            }
            if (t2t == null || t2t.isEmpty()) continue;

            // gop 1440 nen -> dayLow/dayHigh/dayClose theo symbolId
            int maxSid = 0;
            for (KlineObjectSimple[] arr : t2t.values()) { if (arr != null) { maxSid = Math.max(maxSid, arr.length); break; } }
            double[] lo = new double[maxSid], hi = new double[maxSid], cl = new double[maxSid];
            boolean[] seen = new boolean[maxSid];
            Arrays.fill(lo, Double.MAX_VALUE);
            for (KlineObjectSimple[] arr : t2t.values()) {
                if (arr == null) continue;
                for (int s = 0; s < arr.length && s < maxSid; s++) {
                    KlineObjectSimple k = arr[s];
                    if (k == null) continue;
                    seen[s] = true;
                    if (k.minPrice < lo[s]) lo[s] = k.minPrice;
                    if (k.maxPrice > hi[s]) hi[s] = k.maxPrice;
                    cl[s] = k.priceClose;
                }
            }

            // kich hoat entry moi cua ngay nay
            long dayEnd = day + Utils.TIME_DAY;
            while (pi < pending.size() && pending.get(pi).entryTs < dayEnd) {
                Track t = pending.get(pi++);
                t.lastSeenDay = dayIdx;
                active.add(t);
            }

            // cap nhat cac entry dang theo doi
            Iterator<Track> it = active.iterator();
            while (it.hasNext()) {
                Track t = it.next();
                if (t.sid < maxSid && seen[t.sid]) {
                    if (lo[t.sid] < t.runMin) t.runMin = lo[t.sid];
                    if (hi[t.sid] > t.runMax) t.runMax = hi[t.sid];
                    t.lastPrice = cl[t.sid];
                    t.lastSeenDay = dayIdx;
                    if (t.runMin / t.entryPrice - 1.0 <= -0.10) t.everDeep = true;
                    if (t.everDeep && t.recoverDay < 0 && hi[t.sid] >= t.entryPrice) t.recoverDay = t.daysTracked;
                } else if (dayIdx - t.lastSeenDay >= 3) {
                    t.delisted = true;    // mat du lieu >=3 ngay lien tiep khi dang theo doi
                }
                t.daysTracked++;
                for (int h = 0; h < HORIZONS.length; h++) {
                    if (t.daysTracked == HORIZONS[h]) {
                        t.maeAt[h] = t.runMin / t.entryPrice - 1.0;
                        t.mfeAt[h] = t.runMax / t.entryPrice - 1.0;
                    }
                }
                if (t.daysTracked >= horizonDays) { done.add(t); it.remove(); }
            }
            if (dayIdx % 180 == 0) {
                LOG.info("... {} | active={} done={} pending={}",
                        Utils.normalizeDateYYYYMMDD(day), active.size(), done.size(), pending.size() - pi);
            }
        }
        done.addAll(active);   // entry chua du horizon o cuoi ky
        LOG.info("Theo doi xong {} entry", done.size());

        // ---- 3. ghi CSV ----
        try (PrintWriter pw = new PrintWriter(new BufferedWriter(new FileWriter(csvOut)))) {
            StringBuilder hd = new StringBuilder("symbol,entryTs,entryDate,entryPrice,daysTracked,delisted,recoverDay,maeFinal,mfeFinal");
            for (int h : HORIZONS) hd.append(",mae").append(h).append("d");
            for (int h : HORIZONS) hd.append(",mfe").append(h).append("d");
            pw.println(hd);
            for (Track t : done) {
                StringBuilder sb = new StringBuilder();
                sb.append(t.symbol).append(',').append(t.entryTs).append(',')
                  .append(Utils.normalizeDateYYYYMMDD(t.entryTs)).append(',')
                  .append(String.format("%.10f", t.entryPrice)).append(',')
                  .append(t.daysTracked).append(',').append(t.delisted ? 1 : 0).append(',')
                  .append(t.recoverDay).append(',')
                  .append(String.format("%.4f", t.runMin / t.entryPrice - 1.0)).append(',')
                  .append(String.format("%.4f", t.runMax / t.entryPrice - 1.0));
                for (double v : t.maeAt) sb.append(',').append(Double.isNaN(v) ? "" : String.format("%.4f", v));
                for (double v : t.mfeAt) sb.append(',').append(Double.isNaN(v) ? "" : String.format("%.4f", v));
                pw.println(sb);
            }
        }
        LOG.info("GHI XONG {} ({} dong)", csvOut, done.size());

        // ---- 4. tom tat nhanh ngay tai day ----
        summarize("TAT CA", done);
        List<Track> major = new ArrayList<>(), alt = new ArrayList<>();
        for (Track t : done) ((t.symbol.startsWith("BTC") || t.symbol.startsWith("ETH")) ? major : alt).add(t);
        summarize("BTC+ETH", major);
        summarize("ALT", alt);
        LOG.info("========== HET ENTRY-PATH-TRACK ==========");
        System.exit(0);
    }

    private static void summarize(String title, List<Track> ts) {
        if (ts.isEmpty()) { LOG.info("--- {} : rong ---", title); return; }
        double[] mae = new double[ts.size()];
        int delist = 0, recov = 0, deep = 0;
        for (int i = 0; i < ts.size(); i++) {
            Track t = ts.get(i);
            mae[i] = t.runMin / t.entryPrice - 1.0;
            if (t.delisted) delist++;
            if (t.everDeep) { deep++; if (t.recoverDay >= 0) recov++; }
        }
        Arrays.sort(mae);
        LOG.info("");
        LOG.info("=== {} : {} entry | delist {} ({}%) | tung <-10%: {} | trong do hoi ve entry: {} ({}%)",
                title, ts.size(), delist, String.format("%.1f", 100.0 * delist / ts.size()),
                deep, recov, deep == 0 ? "-" : String.format("%.1f", 100.0 * recov / deep));
        LOG.info("MAE percentile: p50={} p75={} p90={} p95={} p99={} worst={}",
                q(mae, .50), q(mae, .25), q(mae, .10), q(mae, .05), q(mae, .01),
                String.format("%.1f%%", mae[0] * 100));
        int[] levels = {-10, -20, -30, -40, -50, -60, -70, -80};
        StringBuilder sb = new StringBuilder("Ti le cham moc: ");
        for (int lv : levels) {
            int c = 0;
            for (double m : mae) if (m <= lv / 100.0) c++;
            sb.append(lv).append("%=").append(String.format("%.1f%%", 100.0 * c / mae.length)).append("  ");
        }
        LOG.info(sb.toString());
    }

    private static String q(double[] asc, double p) {
        int i = (int) Math.floor(p * (asc.length - 1));
        return String.format("%.1f%%", asc[Math.max(0, Math.min(i, asc.length - 1))] * 100);
    }
}
