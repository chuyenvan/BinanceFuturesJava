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
 * TASK (2026-08-01) — DO SUC CHUA VON (capacity) o CAP DANH MUC, khong phai cap 1 cum.
 *
 * <p>CAU HOI CUA UNI: ladder 1:1:2:6 nghia la cuoi cung tong von gap 10 lan? Va no co hop ly khong?
 *
 * <p>VAN DE PHUONG PHAP: bang truoc do (GridEvalProbe) do PnL tren TUNG CUM roi lay trung binh
 * => ngam gia dinh phan DU TRU chua dung co the CHIA SE giua cac coin. Gia dinh do CHI DUNG neu cac
 * coin KHONG sap cung luc. Voi alt crypto thi tuong quan khi dump rat cao => dung luc can du tru nhat
 * thi MOI coin deu can => khong chia se duoc.
 *
 * <p>DO GI (theo TUNG NGAY, tren toan bo universe cung luc):
 * <ul>
 *   <li>tong von TRIEN KHAI dong thoi (theo don vi "tran von moi coin" = 1.0) -> DINH la bao nhieu</li>
 *   <li>so cum dang mo, so cum dang duoi -40% / -60% cung luc (do tuong quan duoi)</li>
 * </ul>
 * Neu dinh von trien khai vuot 100% thi ladder do BAT KHA THI du backtest per-cluster dep.
 *
 * <p>Env: CAP_ENTRY_CSV, CAP_FROM, CAP_TO, CAP_HORIZON_DAYS, CAP_COOLDOWN_H, CAP_TP,
 *         CAP_MAX_COINS (tran so coin dong thoi, mac dinh 25).
 */
public class CapacityProbe {
    private static final Logger LOG = LoggerFactory.getLogger(CapacityProbe.class);

    static class Cfg {
        String name; double[] levels; double[] w; double totW;
        Cfg(String n, double[] l, double[] w) {
            name = n; levels = l; this.w = w;
            double s = 0; for (double x : w) s += x; totW = s;
        }
    }

    public static void main(String[] args) throws Exception {
        String csvIn = System.getenv().getOrDefault("CAP_ENTRY_CSV", "/home/ubuntu/claudedata/entry_universe_g008.csv");
        String from  = System.getenv().getOrDefault("CAP_FROM", "20210101");
        String to    = System.getenv().getOrDefault("CAP_TO",   "20251231");
        int horizon  = Integer.parseInt(System.getenv().getOrDefault("CAP_HORIZON_DAYS", "180"));
        long cooldownMs = Long.parseLong(System.getenv().getOrDefault("CAP_COOLDOWN_H", "24")) * 3600_000L;
        double tp = Double.parseDouble(System.getenv().getOrDefault("CAP_TP", "0.10"));
        int maxCoins = Integer.parseInt(System.getenv().getOrDefault("CAP_MAX_COINS", "25"));

        List<Cfg> cfgs = Arrays.asList(
            new Cfg("deu 1:1:1:1 (-15/-30/-45)",    new double[]{-.15,-.30,-.45}, new double[]{1,1,1,1}),
            new Cfg("deu 1:1:1:1 (-20/-40/-60)",    new double[]{-.20,-.40,-.60}, new double[]{1,1,1,1}),
            new Cfg("1:1:2:3 (-30/-55/-75)",        new double[]{-.30,-.55,-.75}, new double[]{1,1,2,3}),
            new Cfg("1:1:2:6 (-20/-40/-70)",        new double[]{-.20,-.40,-.70}, new double[]{1,1,2,6}),
            new Cfg("1:1:2:6 (-40/-65/-80)",        new double[]{-.40,-.65,-.80}, new double[]{1,1,2,6}),
            new Cfg("2leg 1:4 (-50)",               new double[]{-.50},           new double[]{1,4})
        );
        LOG.info("CapacityProbe | TP={} | tran {} coin dong thoi | horizon={}d cooldown={}h",
                tp, maxCoins, horizon, cooldownMs / 3600000);

        long tFrom = Utils.sdfFile.parse(from).getTime() + 7 * Utils.TIME_HOUR;
        long tTo   = Utils.sdfFile.parse(to).getTime()   + 7 * Utils.TIME_HOUR;
        List<short[]> tmp = new ArrayList<>();
        List<Long> tsL = new ArrayList<>(); List<Double> pxL = new ArrayList<>();
        Map<String, Long> lastOf = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(csvIn))) {
            br.readLine(); String line;
            while ((line = br.readLine()) != null) {
                String[] p = line.split(",");
                if (p.length < 6) continue;
                long ts = Long.parseLong(p[0].trim());
                if (ts < tFrom || ts > tTo) continue;
                String sym = p[3].trim();
                Long last = lastOf.get(sym);
                if (last != null && ts - last < cooldownMs) continue;
                lastOf.put(sym, ts);
                tmp.add(new short[]{Short.parseShort(p[2].trim())});
                tsL.add(ts); pxL.add(Double.parseDouble(p[5].trim()));
            }
        }
        int n = tsL.size();
        Integer[] ord = new Integer[n]; for (int i = 0; i < n; i++) ord[i] = i;
        Arrays.sort(ord, Comparator.comparingLong(tsL::get));
        short[] sid = new short[n]; long[] ets = new long[n]; double[] epx = new double[n];
        for (int i = 0; i < n; i++) { int k = ord[i]; sid[i] = tmp.get(k)[0]; ets[i] = tsL.get(k); epx[i] = pxL.get(k); }
        LOG.info("Nap {} entry", n);

        int C = cfgs.size();
        byte[] nFilled = new byte[n * C];
        double[] deployed = new double[n * C], qtyUnit = new double[n * C];
        byte[] closed = new byte[n * C];
        boolean[] active = new boolean[n], finished = new boolean[n];
        int[] tracked = new int[n], lastSeen = new int[n];
        // ket qua theo cau hinh
        double[] peakDeploy = new double[C];
        String[] peakDay = new String[C];
        double[] sumDeploy = new double[C]; int[] nDays = new int[C];
        int peakOpen = 0, peakDeep40 = 0, peakDeep60 = 0;
        String peakDeepDay = "";

        for (int i = 0; i < n; i++)
            for (int c = 0; c < C; c++) {
                int ix = i * C + c;
                nFilled[ix] = 1; deployed[ix] = cfgs.get(c).w[0]; qtyUnit[ix] = cfgs.get(c).w[0];
            }

        int pi = 0, dayIdx = 0;
        long endTime = tTo + 200L * Utils.TIME_DAY;
        for (long day = tFrom; day <= endTime; day += Utils.TIME_DAY, dayIdx++) {
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
            int firstNew = pi;
            while (pi < n && ets[pi] < dayEnd) { active[pi] = true; lastSeen[pi] = dayIdx; pi++; }

            double[] dayDeploy = new double[C];
            int nOpen = 0, deep40 = 0, deep60 = 0;
            for (int i = 0; i < pi; i++) {
                if (!active[i] || finished[i]) continue;
                if (sid[i] >= maxSid || !seen[sid[i]]) {
                    if (dayIdx - lastSeen[i] >= 3) { finished[i] = true; active[i] = false; }
                    continue;
                }
                lastSeen[i] = dayIdx;
                double rLo, rHi;
                if (i >= firstNew) {
                    double l = Double.MAX_VALUE, h = -Double.MAX_VALUE;
                    for (Map.Entry<Long, KlineObjectSimple[]> en : t2t.tailMap(ets[i], true).entrySet()) {
                        KlineObjectSimple[] a = en.getValue();
                        if (a == null || sid[i] >= a.length) continue;
                        KlineObjectSimple k = a[sid[i]];
                        if (k == null) continue;
                        if (k.minPrice < l) l = k.minPrice;
                        if (k.maxPrice > h) h = k.maxPrice;
                    }
                    if (l == Double.MAX_VALUE) continue;
                    rLo = l / epx[i] - 1.0; rHi = h / epx[i] - 1.0;
                } else { rLo = lo[sid[i]] / epx[i] - 1.0; rHi = hi[sid[i]] / epx[i] - 1.0; }
                tracked[i]++;
                boolean anyOpen = false;
                if (rLo <= -0.40) deep40++;
                if (rLo <= -0.60) deep60++;
                for (int c = 0; c < C; c++) {
                    int ix = i * C + c;
                    if (closed[ix] == 1) continue;
                    Cfg cf = cfgs.get(c);
                    double avg = deployed[ix] / qtyUnit[ix] - 1.0;
                    if (rHi >= (1.0 + avg) * (1.0 + tp) - 1.0) { closed[ix] = 1; continue; }
                    while (nFilled[ix] - 1 < cf.levels.length && rLo <= cf.levels[nFilled[ix] - 1]) {
                        double lv = cf.levels[nFilled[ix] - 1], wl = cf.w[nFilled[ix]];
                        deployed[ix] += wl; qtyUnit[ix] += wl / (1.0 + lv); nFilled[ix]++;
                    }
                    dayDeploy[c] += deployed[ix] / cf.totW;   // don vi = tran von 1 coin
                    anyOpen = true;
                }
                if (anyOpen) nOpen++;
                if (tracked[i] >= horizon) { finished[i] = true; active[i] = false; }
            }
            // quy ve % tai khoan: moi coin duoc cap (100/maxCoins)% tai khoan
            for (int c = 0; c < C; c++) {
                double pctAcct = dayDeploy[c] * (100.0 / maxCoins);
                sumDeploy[c] += pctAcct; nDays[c]++;
                if (pctAcct > peakDeploy[c]) { peakDeploy[c] = pctAcct; peakDay[c] = Utils.normalizeDateYYYYMMDD(day); }
            }
            if (nOpen > peakOpen) peakOpen = nOpen;
            if (deep40 > peakDeep40) { peakDeep40 = deep40; peakDeepDay = Utils.normalizeDateYYYYMMDD(day); }
            if (deep60 > peakDeep60) peakDeep60 = deep60;
            if (dayIdx % 300 == 0) LOG.info("... {} | open={} deep40={} ", Utils.normalizeDateYYYYMMDD(day), nOpen, deep40);
            if (pi >= n) { boolean any = false; for (int i = 0; i < n; i++) if (active[i] && !finished[i]) { any = true; break; } if (!any) break; }
        }

        LOG.info("");
        LOG.info("=== TUONG QUAN DUOI (toan universe, khong phu thuoc ladder) ===");
        LOG.info("Dinh so cum mo dong thoi         : {}", peakOpen);
        LOG.info("Dinh so cum cung duoi -40% 1 ngay: {}  (ngay {})", peakDeep40, peakDeepDay);
        LOG.info("Dinh so cum cung duoi -60% 1 ngay: {}", peakDeep60);
        LOG.info("");
        LOG.info("=== SUC CHUA VON theo ladder (tran {} coin, moi coin duoc {}% tai khoan) ===", maxCoins, 100.0 / maxCoins);
        LOG.info(String.format("%-30s %14s %12s %14s %s", "ladder", "DINH %tai khoan", "TB %tk", "gap so voi TB", "ngay dinh"));
        LOG.info("-".repeat(92));
        for (int c = 0; c < C; c++) {
            double avg = sumDeploy[c] / Math.max(1, nDays[c]);
            LOG.info(String.format("%-30s %13.1f%% %11.1f%% %13.1fx %s",
                    cfgs.get(c).name, peakDeploy[c], avg, peakDeploy[c] / Math.max(0.01, avg), peakDay[c]));
        }
        LOG.info("");
        LOG.info("DOC: DINH > 100% => ladder BAT KHA THI voi tran {} coin (khong du von ngay xau nhat).", maxCoins);
        LOG.info("     'gap so voi TB' cao => von nam khong phan lon thoi gian, chi dung luc khung hoang.");
        LOG.info("========== HET CAPACITY-PROBE ==========");
        System.exit(0);
    }
}
