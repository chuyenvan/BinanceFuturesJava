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
 * TASK (2026-08-01) — DANH GIA CAU HINH GRID DCA voi THU TU THOI GIAN CHINH XAC.
 *
 * <p>VI SAO khong dung file export + python: ban truoc dung MAE/MFE tong hop (min/max toan ky) nen
 * BO QUA THU TU — dinh co the den TRUOC day. Ket qua bi hong: moi cau hinh deu ra "100% cum lai".
 * Xuat chuoi ngay cho vai tram nghin entry thi file qua lon (100k x 180 = 18M dong).
 * => Danh gia NGAY TRONG vong lap ngay cua Java, noi da co dung thu tu.
 *
 * <p>QUY TAC MOI NGAY (bao thu, khong nhin truoc):
 * <ol>
 *   <li>Dung HIGH cua ngay kiem TP tren avgEntry cua NGAY HOM TRUOC (chua tinh leg nhoi hom nay)
 *       -> khong tu thuong cho viec nhoi va chot trong cung mot ngay.</li>
 *   <li>Dung LOW cua ngay de khop cac leg DCA con lai (theo dung thu tu moc).</li>
 * </ol>
 *
 * <p>Env: GRID_ENTRY_CSV, GRID_FROM, GRID_TO, GRID_HORIZON_DAYS (180), GRID_COOLDOWN_H (0 = khong dedup),
 *         GRID_TP (CSV cac muc TP, mac dinh 0.03), GRID_MAX_ENTRIES (0 = khong gioi han).
 */
public class GridEvalProbe {
    private static final Logger LOG = LoggerFactory.getLogger(GridEvalProbe.class);

    /** Mot cau hinh grid: moc nhoi (am, so GIA VAO DAU) + ti trong (ke ca leg dau) + TP. */
    static class Cfg {
        String name; double[] levels; double[] w; double tp; double totW;
        Cfg(String n, double[] l, double[] w, double tp) {
            this.name = n; this.levels = l; this.w = w; this.tp = tp;
            double s = 0; for (double x : w) s += x; this.totW = s;
        }
    }

    public static void main(String[] args) throws Exception {
        String csvIn = System.getenv().getOrDefault("GRID_ENTRY_CSV", "/home/ubuntu/claudedata/entry_universe_g008.csv");
        String from  = System.getenv().getOrDefault("GRID_FROM", "20210101");
        String to    = System.getenv().getOrDefault("GRID_TO",   "20251231");
        int horizon  = Integer.parseInt(System.getenv().getOrDefault("GRID_HORIZON_DAYS", "180"));
        long cooldownMs = Long.parseLong(System.getenv().getOrDefault("GRID_COOLDOWN_H", "0")) * 3600_000L;
        int maxEntries = Integer.parseInt(System.getenv().getOrDefault("GRID_MAX_ENTRIES", "0"));

        List<Cfg> cfgs = new ArrayList<>();
        double[] TPS = {0.03, 0.05, 0.10};
        for (double tp : TPS) {
            cfgs.add(new Cfg("noDCA",              new double[]{},                        new double[]{1},        tp));
            cfgs.add(new Cfg("deu -15/-30/-45",    new double[]{-.15,-.30,-.45},          new double[]{1,1,1,1},  tp));
            cfgs.add(new Cfg("deu -20/-40/-60",    new double[]{-.20,-.40,-.60},          new double[]{1,1,1,1},  tp));
            cfgs.add(new Cfg("sau -30/-55/-75",    new double[]{-.30,-.55,-.75},          new double[]{1,1,1,1},  tp));
            cfgs.add(new Cfg("donduoi -20/-40/-70",new double[]{-.20,-.40,-.70},          new double[]{1,1,2,6},  tp));
            cfgs.add(new Cfg("donduoi -30/-55/-75",new double[]{-.30,-.55,-.75},          new double[]{1,1,2,6},  tp));
            cfgs.add(new Cfg("donduoi -40/-65/-80",new double[]{-.40,-.65,-.80},          new double[]{1,1,2,6},  tp));
            cfgs.add(new Cfg("2leg -50 x4",        new double[]{-.50},                    new double[]{1,4},      tp));
            cfgs.add(new Cfg("2leg -60 x6",        new double[]{-.60},                    new double[]{1,6},      tp));
        }
        LOG.info("Danh gia {} cau hinh ({} grid x {} TP) | horizon={}d cooldown={}h",
                cfgs.size(), cfgs.size() / TPS.length, TPS.length, horizon, cooldownMs / 3600000);

        // ---- nap entry ----
        long tFrom = Utils.sdfFile.parse(from).getTime() + 7 * Utils.TIME_HOUR;
        long tTo   = Utils.sdfFile.parse(to).getTime()   + 7 * Utils.TIME_HOUR;
        List<String> symArr = new ArrayList<>();
        List<Short>  sidArr = new ArrayList<>();
        List<Long>   tsArr  = new ArrayList<>();
        List<Double> pxArr  = new ArrayList<>();
        Map<String, Long> lastOf = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(csvIn))) {
            br.readLine();
            String line;
            while ((line = br.readLine()) != null) {
                String[] p = line.split(",");
                if (p.length < 6) continue;
                long ts = Long.parseLong(p[0].trim());
                if (ts < tFrom || ts > tTo) continue;
                String sym = p[3].trim();
                if (cooldownMs > 0) {
                    Long last = lastOf.get(sym);
                    if (last != null && ts - last < cooldownMs) continue;
                    lastOf.put(sym, ts);
                }
                symArr.add(sym); sidArr.add(Short.parseShort(p[2].trim()));
                tsArr.add(ts);   pxArr.add(Double.parseDouble(p[5].trim()));
                if (maxEntries > 0 && symArr.size() >= maxEntries) break;
            }
        }
        int n = symArr.size();
        LOG.info("Nap {} entry tu {}", n, csvIn);
        if (n == 0) { LOG.error("KHONG CO ENTRY"); System.exit(1); }

        short[] sid = new short[n]; long[] ets = new long[n]; double[] epx = new double[n];
        String[] sym = new String[n];
        Integer[] order = new Integer[n];
        for (int i = 0; i < n; i++) order[i] = i;
        Arrays.sort(order, Comparator.comparingLong(tsArr::get));
        for (int i = 0; i < n; i++) {
            int k = order[i];
            sym[i] = symArr.get(k); sid[i] = sidArr.get(k); ets[i] = tsArr.get(k); epx[i] = pxArr.get(k);
        }

        int C = cfgs.size();
        // state per (entry, cfg) — mang phang
        byte[] nFilled = new byte[n * C];      // so leg da khop
        double[] deployed = new double[n * C]; // tong trong so da rot
        double[] qtyUnit  = new double[n * C]; // sum(w / (1+r)) -> avgEntry = deployed/qtyUnit (theo entryPrice=1)
        byte[] closed = new byte[n * C];
        double[] pnl = new double[n * C];      // lai/lo tren TONG von phan bo (totW)
        int[] daysHeld = new int[n * C];

        int[] trackedDays = new int[n];
        int[] lastSeen = new int[n];
        boolean[] active = new boolean[n];
        boolean[] finished = new boolean[n];
        double[] lastRate = new double[n];     // gia cuoi cung / entryPrice - 1

        for (int i = 0; i < n; i++) {
            for (int c = 0; c < C; c++) {
                int ix = i * C + c;
                nFilled[ix] = 1;
                deployed[ix] = cfgs.get(c).w[0];
                qtyUnit[ix] = cfgs.get(c).w[0];   // r=0 cho leg dau
            }
        }

        long startTime = tFrom, endTime = Utils.sdfFile.parse(to).getTime() + 7 * Utils.TIME_HOUR + 200L * Utils.TIME_DAY;
        int pi = 0, dayIdx = 0, nActive = 0;
        for (long day = startTime; day <= endTime; day += Utils.TIME_DAY, dayIdx++) {
            TreeMap<Long, KlineObjectSimple[]> t2t;
            try {
                t2t = "aerospike".equals(Configs.TICKER_SOURCE)
                        ? DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(day)
                        : KaggleDataLoader.loadDailyTickersShort(day);
            } catch (Exception e) { continue; }
            if (t2t == null || t2t.isEmpty()) continue;

            int maxSid = 0;
            for (KlineObjectSimple[] a : t2t.values()) if (a != null) { maxSid = a.length; break; }
            if (maxSid == 0) continue;
            double[] lo = new double[maxSid], hi = new double[maxSid];
            boolean[] seen = new boolean[maxSid];
            Arrays.fill(lo, Double.MAX_VALUE);
            for (KlineObjectSimple[] a : t2t.values()) {
                if (a == null) continue;
                for (int s = 0; s < a.length && s < maxSid; s++) {
                    KlineObjectSimple k = a[s];
                    if (k == null) continue;
                    seen[s] = true;
                    if (k.minPrice < lo[s]) lo[s] = k.minPrice;
                    if (k.maxPrice > hi[s]) hi[s] = k.maxPrice;
                }
            }

            long dayEnd = day + Utils.TIME_DAY;
            int firstNewIdx = pi;
            while (pi < n && ets[pi] < dayEnd) { active[pi] = true; lastSeen[pi] = dayIdx; pi++; nActive++; }

            for (int i = 0; i < pi; i++) {
                if (!active[i] || finished[i]) continue;
                if (sid[i] >= maxSid || !seen[sid[i]]) {
                    if (dayIdx - lastSeen[i] >= 3) { finished[i] = true; active[i] = false; nActive--; }
                    continue;
                }
                lastSeen[i] = dayIdx;
                double rLo, rHi;
                if (i >= firstNewIdx) {
                    // 🔴 FIX LOOK-AHEAD (2026-08-01): NGAY VAO LENH chi duoc dung cac phut TU THOI DIEM VAO
                    //    tro di. Ban truoc dung high/low CA NGAY -> bao gom ca phut TRUOC khi vao -> coin
                    //    bien dong 10-20%/ngay thi high ca ngay gan nhu luon vuot entry+3% => 99% "chot TP"
                    //    ngay ngay dau, 0 leg nhoi. Ket qua do la ao hoan toan.
                    double l = Double.MAX_VALUE, h = -Double.MAX_VALUE;
                    for (Map.Entry<Long, KlineObjectSimple[]> en : t2t.tailMap(ets[i], true).entrySet()) {
                        KlineObjectSimple[] a = en.getValue();
                        if (a == null || sid[i] >= a.length) continue;
                        KlineObjectSimple k = a[sid[i]];
                        if (k == null) continue;
                        if (k.minPrice < l) l = k.minPrice;
                        if (k.maxPrice > h) h = k.maxPrice;
                    }
                    if (l == Double.MAX_VALUE) continue;   // khong co phut nao sau khi vao
                    rLo = l / epx[i] - 1.0;
                    rHi = h / epx[i] - 1.0;
                } else {
                    rLo = lo[sid[i]] / epx[i] - 1.0;
                    rHi = hi[sid[i]] / epx[i] - 1.0;
                }
                lastRate[i] = rHi;
                trackedDays[i]++;

                for (int c = 0; c < C; c++) {
                    int ix = i * C + c;
                    if (closed[ix] == 1) continue;
                    Cfg cf = cfgs.get(c);
                    // (1) TP truoc, dung avgEntry TRUOC khi nhoi hom nay -> bao thu
                    double avg = deployed[ix] / qtyUnit[ix] - 1.0;   // rate so entryPrice
                    double need = (1.0 + avg) * (1.0 + cf.tp) - 1.0;
                    if (rHi >= need) {
                        closed[ix] = 1;
                        pnl[ix] = deployed[ix] * cf.tp / cf.totW;
                        daysHeld[ix] = trackedDays[i];
                        continue;
                    }
                    // (2) khop cac leg con lai bang LOW
                    while (nFilled[ix] - 1 < cf.levels.length && rLo <= cf.levels[nFilled[ix] - 1]) {
                        double lv = cf.levels[nFilled[ix] - 1];
                        double wl = cf.w[nFilled[ix]];
                        deployed[ix] += wl;
                        qtyUnit[ix]  += wl / (1.0 + lv);
                        nFilled[ix]++;
                    }
                }
                if (trackedDays[i] >= horizon) { finished[i] = true; active[i] = false; nActive--; }
            }
            if (dayIdx % 180 == 0)
                LOG.info("... {} | active={} pending={}", Utils.normalizeDateYYYYMMDD(day), nActive, n - pi);
            if (pi >= n && nActive == 0) break;
        }

        // ---- ket so: cum chua chot -> mark-to-market o gia cuoi ----
        LOG.info("");
        LOG.info(String.format("%-24s %5s %10s %9s %9s %9s %9s %9s",
                "cau hinh", "TP", "PnL/von", "%chot TP", "%von dung", "leg tb", "ngay giu", "p05"));
        LOG.info("-".repeat(96));
        for (int c = 0; c < C; c++) {
            Cfg cf = cfgs.get(c);
            double sum = 0, sumDep = 0, sumLeg = 0, sumDays = 0; int nTp = 0, cnt = 0;
            double[] all = new double[n];
            for (int i = 0; i < n; i++) {
                int ix = i * C + c;
                double p;
                if (closed[ix] == 1) { p = pnl[ix]; nTp++; sumDays += daysHeld[ix]; }
                else {
                    double avg = deployed[ix] / qtyUnit[ix] - 1.0;
                    p = deployed[ix] * ((1.0 + lastRate[i]) / (1.0 + avg) - 1.0) / cf.totW;
                    sumDays += trackedDays[i];
                }
                all[cnt++] = p; sum += p;
                sumDep += deployed[ix] / cf.totW;
                sumLeg += nFilled[ix];
            }
            Arrays.sort(all, 0, cnt);
            LOG.info(String.format("%-24s %4.0f%% %9.3f%% %8.1f%% %8.1f%% %9.2f %9.0f %8.2f%%",
                    cf.name, cf.tp * 100, 100.0 * sum / cnt, 100.0 * nTp / cnt,
                    100.0 * sumDep / cnt, sumLeg / cnt, sumDays / cnt,
                    100.0 * all[(int) (0.05 * cnt)]));
        }
        LOG.info("========== HET GRID-EVAL (n={}) ==========", n);
        System.exit(0);
    }
}
