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
 * TASK (2026-08-01) — CAU HOI CUA UNI: bao nhieu cum di qua CA 3 MOC DCA roi KHONG BAO GIO ngoi lai
 * duoc muc gia von trung binh? Day la ti le "chet that" cua hold-to-die, chua tung do.
 *
 * <p>Phan loai MOI cum theo SO LEG DA KHOP, roi trong tung nhom bao:
 * <ul>
 *   <li>% cham TP (thoat co lai)</li>
 *   <li>% CHUA HOI ve avgEntry o cuoi ky theo doi -> day la nhom "chon von"</li>
 *   <li>lo trung binh / p50 / p95 cua nhom chua hoi (tinh tren von DA ROT vao cum do)</li>
 *   <li>so ngay giu trung binh</li>
 * </ul>
 *
 * <p>Env: SUR_ENTRY_CSV, SUR_FROM, SUR_TO, SUR_HORIZON_DAYS (180), SUR_COOLDOWN_H (24),
 *         SUR_TP (0.10), SUR_LEVELS (CSV am, mac dinh -0.40,-0.65,-0.80),
 *         SUR_WEIGHTS (CSV, mac dinh 1,1,2,6).
 */
public class SurvivalProbe {
    private static final Logger LOG = LoggerFactory.getLogger(SurvivalProbe.class);

    public static void main(String[] args) throws Exception {
        String csvIn = System.getenv().getOrDefault("SUR_ENTRY_CSV", "/home/ubuntu/claudedata/entry_universe_g008.csv");
        String from  = System.getenv().getOrDefault("SUR_FROM", "20210101");
        String to    = System.getenv().getOrDefault("SUR_TO",   "20251231");
        int horizon  = Integer.parseInt(System.getenv().getOrDefault("SUR_HORIZON_DAYS", "180"));
        long cooldownMs = Long.parseLong(System.getenv().getOrDefault("SUR_COOLDOWN_H", "24")) * 3600_000L;
        double tp = Double.parseDouble(System.getenv().getOrDefault("SUR_TP", "0.10"));
        double[] levels = parse(System.getenv().getOrDefault("SUR_LEVELS", "-0.40,-0.65,-0.80"));
        double[] w      = parse(System.getenv().getOrDefault("SUR_WEIGHTS", "1,1,2,6"));
        double totW = 0; for (double x : w) totW += x;
        LOG.info("SurvivalProbe | levels={} weights={} TP={} horizon={}d",
                Arrays.toString(levels), Arrays.toString(w), tp, horizon);

        // === TU KIEM TRA PHEP TINH GIA VON TB (in ra de doi chieu tay) ===
        // tien chi o muc lv -> gia luc do = (1+lv) so gia vao dau. luong mua = tien/(1+lv).
        // gia von TB = tong tien / tong luong.
        {
            double money = 0, qty = 0;
            StringBuilder sb = new StringBuilder();
            for (int L = 0; L < w.length; L++) {
                double lv = (L == 0) ? 0.0 : levels[L - 1];
                double price = 1.0 + lv;
                money += w[L]; qty += w[L] / price;
                sb.append(String.format("\n    leg%d: gia %.4f  tien %.1f  luong %.4f  -> cong don: tien %.1f luong %.4f avg %.4f (%.1f%%)",
                        L + 1, price, w[L], w[L] / price, money, qty, money / qty, (money / qty - 1) * 100));
            }
            double avgAll = money / qty;
            LOG.info("KIEM TRA GIA VON TB (neu khop DU {} leg):{}", w.length, sb);
            LOG.info("  => gia von TB = {} = {}% so gia vao dau | de TP +{}% can gia len {} (tuc {}% so gia vao dau)",
                    String.format("%.4f", avgAll), String.format("%.1f", (avgAll - 1) * 100),
                    String.format("%.0f", tp * 100), String.format("%.4f", avgAll * (1 + tp)),
                    String.format("%.1f", (avgAll * (1 + tp) - 1) * 100));
            double bottom = 1.0 + levels[levels.length - 1];
            LOG.info("  => tu DAY (leg cuoi, gia {}) can bat len {}% moi cham TP",
                    String.format("%.4f", bottom), String.format("%.1f", (avgAll * (1 + tp) / bottom - 1) * 100));
        }

        long tFrom = Utils.sdfFile.parse(from).getTime() + 7 * Utils.TIME_HOUR;
        long tTo   = Utils.sdfFile.parse(to).getTime()   + 7 * Utils.TIME_HOUR;
        List<Long> tsL = new ArrayList<>(); List<Double> pxL = new ArrayList<>();
        List<Short> sidL = new ArrayList<>(); List<String> symL = new ArrayList<>();
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
                tsL.add(ts); pxL.add(Double.parseDouble(p[5].trim()));
                sidL.add(Short.parseShort(p[2].trim())); symL.add(sym);
            }
        }
        int n = tsL.size();
        Integer[] ord = new Integer[n]; for (int i = 0; i < n; i++) ord[i] = i;
        Arrays.sort(ord, Comparator.comparingLong(tsL::get));
        short[] sid = new short[n]; long[] ets = new long[n]; double[] epx = new double[n]; String[] sym = new String[n];
        for (int i = 0; i < n; i++) { int k = ord[i]; sid[i]=sidL.get(k); ets[i]=tsL.get(k); epx[i]=pxL.get(k); sym[i]=symL.get(k); }
        LOG.info("Nap {} entry", n);

        int[] nFilled = new int[n]; double[] deployed = new double[n], qtyUnit = new double[n];
        boolean[] tpHit = new boolean[n], active = new boolean[n], finished = new boolean[n];
        int[] tracked = new int[n], lastSeen = new int[n], legDay4 = new int[n];
        double[] lastRate = new double[n], minRate = new double[n];
        boolean[] delisted = new boolean[n];
        for (int i = 0; i < n; i++) { nFilled[i]=1; deployed[i]=w[0]; qtyUnit[i]=w[0]; minRate[i]=0; legDay4[i]=-1; }

        int pi = 0, dayIdx = 0;
        for (long day = tFrom; day <= tTo + 400L * Utils.TIME_DAY; day += Utils.TIME_DAY, dayIdx++) {
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
            double[] lo = new double[maxSid], hi = new double[maxSid], cl = new double[maxSid];
            boolean[] seen = new boolean[maxSid];
            Arrays.fill(lo, Double.MAX_VALUE);
            for (KlineObjectSimple[] a : t2t.values()) {
                if (a == null) continue;
                for (int s = 0; s < a.length && s < maxSid; s++) {
                    KlineObjectSimple k = a[s];
                    if (k == null) continue;
                    seen[s]=true;
                    if (k.minPrice < lo[s]) lo[s]=k.minPrice;
                    if (k.maxPrice > hi[s]) hi[s]=k.maxPrice;
                    cl[s] = k.priceClose;   // TreeMap duyet tang dan theo thoi gian -> gia tri cuoi = close ngay
                }
            }
            long dayEnd = day + Utils.TIME_DAY;
            int firstNew = pi;
            while (pi < n && ets[pi] < dayEnd) { active[pi]=true; lastSeen[pi]=dayIdx; pi++; }

            for (int i = 0; i < pi; i++) {
                if (!active[i] || finished[i]) continue;
                if (sid[i] >= maxSid || !seen[sid[i]]) {
                    if (dayIdx - lastSeen[i] >= 3) { delisted[i]=true; finished[i]=true; active[i]=false; }
                    continue;
                }
                lastSeen[i]=dayIdx;
                double rLo, rHi, rCl;
                if (i >= firstNew) {
                    double l=Double.MAX_VALUE, h=-Double.MAX_VALUE, c=Double.NaN;
                    for (Map.Entry<Long, KlineObjectSimple[]> en : t2t.tailMap(ets[i], true).entrySet()) {
                        KlineObjectSimple[] a = en.getValue();
                        if (a==null || sid[i]>=a.length) continue;
                        KlineObjectSimple k = a[sid[i]];
                        if (k==null) continue;
                        if (k.minPrice<l) l=k.minPrice;
                        if (k.maxPrice>h) h=k.maxPrice;
                        c = k.priceClose;
                    }
                    if (l==Double.MAX_VALUE) continue;
                    rLo=l/epx[i]-1.0; rHi=h/epx[i]-1.0; rCl=c/epx[i]-1.0;
                } else { rLo=lo[sid[i]]/epx[i]-1.0; rHi=hi[sid[i]]/epx[i]-1.0; rCl=cl[sid[i]]/epx[i]-1.0; }
                // 🔴 FIX: dinh gia cuoi ky bang CLOSE, khong phai HIGH. Dung high lam nhom "chon von"
                //    trong DO LO HON THUC TE.
                tracked[i]++; lastRate[i]=rCl;
                if (rLo < minRate[i]) minRate[i]=rLo;

                double avg = deployed[i]/qtyUnit[i] - 1.0;
                if (rHi >= (1.0+avg)*(1.0+tp) - 1.0) { tpHit[i]=true; finished[i]=true; active[i]=false; continue; }
                while (nFilled[i]-1 < levels.length && rLo <= levels[nFilled[i]-1]) {
                    double lv = levels[nFilled[i]-1], wl = w[nFilled[i]];
                    deployed[i]+=wl; qtyUnit[i]+=wl/(1.0+lv); nFilled[i]++;
                    if (nFilled[i] == w.length) legDay4[i]=tracked[i];
                }
                if (tracked[i] >= horizon) { finished[i]=true; active[i]=false; }
            }
            if (pi>=n) { boolean any=false; for (int i=0;i<n;i++) if (active[i]&&!finished[i]) {any=true;break;} if(!any) break; }
        }

        // ---- bao cao theo so leg da khop ----
        LOG.info("");
        LOG.info("=== PHAN LOAI {} CUM THEO SO LEG DA KHOP (grid {} / ti trong {} / TP {}%) ===",
                n, Arrays.toString(levels), Arrays.toString(w), tp*100);
        LOG.info(String.format("%6s %8s %7s %9s %11s %11s %11s %11s %9s",
                "so leg", "so cum", "%tong", "%cham TP", "%CHUA HOI", "lo TB", "lo p50", "lo p95", "ngay giu"));
        LOG.info("-".repeat(100));
        for (int L = 1; L <= w.length; L++) {
            List<Double> losses = new ArrayList<>();
            int cnt=0, tpc=0, stuck=0; double days=0;
            for (int i = 0; i < n; i++) {
                if (nFilled[i] != L) continue;
                cnt++; days += tracked[i];
                if (tpHit[i]) { tpc++; continue; }
                double avg = deployed[i]/qtyUnit[i] - 1.0;
                double pnlRate = (1.0+lastRate[i])/(1.0+avg) - 1.0;   // so voi gia von TB
                if (pnlRate < 0) { stuck++; losses.add(pnlRate); }
            }
            if (cnt == 0) { LOG.info(String.format("%6d %8d %6.1f%% %9s %11s %11s %11s %11s %9s", L,0,0.0,"-","-","-","-","-","-")); continue; }
            Collections.sort(losses);
            double lm = 0; for (double x : losses) lm += x;
            LOG.info(String.format("%6d %8d %6.1f%% %8.1f%% %10.1f%% %10.1f%% %10.1f%% %10.1f%% %9.0f",
                    L, cnt, 100.0*cnt/n, 100.0*tpc/cnt, 100.0*stuck/cnt,
                    losses.isEmpty()?0:100.0*lm/losses.size(),
                    losses.isEmpty()?0:100.0*losses.get(losses.size()/2),
                    losses.isEmpty()?0:100.0*losses.get((int)(0.05*losses.size())),
                    days/cnt));
        }

        // ---- nhom di qua CA 3 MOC ----
        int full = 0, fullTp = 0, fullStuck = 0, fullDelist = 0;
        double capFull = 0, lossFull = 0;
        List<Double> fullLosses = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            if (nFilled[i] != w.length) continue;
            full++; capFull += deployed[i]/totW;
            if (delisted[i]) fullDelist++;
            if (tpHit[i]) { fullTp++; continue; }
            double avg = deployed[i]/qtyUnit[i] - 1.0;
            double p = (1.0+lastRate[i])/(1.0+avg) - 1.0;
            if (p < 0) { fullStuck++; fullLosses.add(p); lossFull += p; }
        }
        LOG.info("");
        LOG.info("=== NHOM DI QUA CA {} MOC (tra loi truc tiep cau hoi) ===", levels.length);
        LOG.info("So cum khop DU {} leg          : {} / {} = {}%", w.length, full, n, String.format("%.2f", 100.0*full/n));
        if (full > 0) {
            Collections.sort(fullLosses);
            LOG.info("  trong do cham TP (thoat lai) : {} ({}%)", fullTp, String.format("%.1f", 100.0*fullTp/full));
            LOG.info("  CHUA HOI ve gia von TB       : {} ({}%)  <-- CHON VON", fullStuck, String.format("%.1f", 100.0*fullStuck/full));
            LOG.info("  bi delist khi dang chon      : {} ({}%)", fullDelist, String.format("%.1f", 100.0*fullDelist/full));
            if (!fullLosses.isEmpty()) {
                LOG.info("  lo cua nhom chon von: TB {}%  p50 {}%  p95 {}%  te nhat {}%",
                        String.format("%.1f", 100.0*lossFull/fullLosses.size()),
                        String.format("%.1f", 100.0*fullLosses.get(fullLosses.size()/2)),
                        String.format("%.1f", 100.0*fullLosses.get((int)(0.05*fullLosses.size()))),
                        String.format("%.1f", 100.0*fullLosses.get(0)));
            }
            LOG.info("  von bi giam giu (don vi tran/coin): {} = {}% tong von phan bo cho {} cum",
                    String.format("%.1f", capFull), String.format("%.2f", 100.0*capFull/n), n);
        }
        LOG.info("========== HET SURVIVAL-PROBE ==========");
        System.exit(0);
    }

    private static double[] parse(String s) {
        String[] p = s.split(",");
        double[] r = new double[p.length];
        for (int i = 0; i < p.length; i++) r[i] = Double.parseDouble(p[i].trim());
        return r;
    }
}
