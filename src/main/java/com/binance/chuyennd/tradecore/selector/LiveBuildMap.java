package com.binance.chuyennd.tradecore.selector;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * QUANTILE-MAP CHAY LIVE — ban Java cua {@code research/pipeline/build_map.py}
 * (= {@code x1/x1_build_map.py} = {@code x1/c4_build_map.py}, ba ban giong nhau tung dong o
 * phan thuat toan).
 *
 * <p><b>Vi sao phai co lop nay.</b> Sim C3 KHONG dua gia tri model S1 vao gate. No dua
 * <i>phan phoi P(win) cua net015 trong tung tick</i> (multiset khong doi) va chi doi
 * <i>coin nao nhan gia tri nao</i> theo thu hang cua S1. Shadow truoc L4 dung thang
 * {@code pNoPump} cua {@code Funding_Classifier_Final.onnx} lam {@code symbolPred} — do la
 * model ho {@code maxFav}, hieu chuan lech 2 lan ({@code p_mean} 0.2268 vs 0.4642) va
 * {@code docs/experiment/G4_RECIPE_C4.md} muc 6.2 do duoc no lam admission x5.05 o tang gate.
 *
 * <h2>QUY UOC (rut TRUC TIEP tu build_map.py, khong dien giai)</h2>
 * <pre>
 *   sub["r_score"]  = sub.groupby("ts").score.rank(method="first")                  # 1 = TOT nhat
 *   sub["p_sorted"] = sub.groupby("ts").p.rank(method="first", ascending=False)     # 1 = p CAO nhat
 *   key             = sub.set_index(["ts","p_sorted"]).p
 *   sub["p_new"]    = key.reindex(list(zip(sub.ts, sub.r_score))).values
 * </pre>
 * Doc thanh loi: <b>coin xep hang k theo S1 (k=1 la tot nhat, score THAP nhat) nhan gia tri
 * P(win) LON THU k cua tick</b>. Multiset P(win) cua tick giu nguyen tuyet doi.
 *
 * <h2>DAO DAU — cho nay sai la hong ca he</h2>
 * Bins {@code predict_wf_*.bin} luu {@code p0 = P(win)} (cao = tot). Java KHONG dung thang do:
 * {@code WfoDataset.buildFundingFromWfFiles:248} lam {@code score = 1.0f - pwin; // DAO DAU}
 * roi sort TANG va lay K phan tu dau. Tuc:
 * <pre>
 *   symbolPred = 1 - P(win)      (THAP = tot = duoc chon truoc, gate dyn_thr de hon)
 * </pre>
 * Da kiem thuc nghiem tren fold {@code 20251001}: spearman per-tick giua
 * {@code score S1} (pred_s1a2x1.parquet) va {@code p0} cua {@code predwf_map_s1a2_x1}
 * bang <b>−1.000000 chinh xac</b> o moi tick — dung chieu tren.
 *
 * <h2>TIE-BREAK</h2>
 * {@code rank(method="first")} cua pandas pha the theo THU TU DONG trong DataFrame. Live khong
 * co "thu tu dong", nen caller PHAI truyen mot thu tu tat dinh qua {@code rowOrder}:
 * <ul>
 *   <li>duong LIVE: ten symbol tang dan (tat dinh, khong phu thuoc thu tu HashMap);</li>
 *   <li>harness REPLAY: dung thu tu dong CUA FILE bins, de doi chung duoc voi Python.</li>
 * </ul>
 * Cung {@code rowOrder} => Java va Python ra giong nhau TUNG GIA TRI (xem
 * {@code LiveBuildMapTest} va {@code research/pipeline/l4/build_map_parity.py}).
 */
public final class LiveBuildMap {

    private LiveBuildMap() {
    }

    /** Ket qua map cho mot tick. */
    public static final class Assigned {
        /** {@code symbol -> symbolPred = 1 - P(win) da map}. THAP = tot. */
        public final Map<String, Float> symbolPred;
        /** {@code symbol -> P(win) da map} (truoc khi dao dau) — de log/kiem multiset. */
        public final Map<String, Float> pwinMapped;
        /** {@code symbol -> rank S1} (1-based, 1 = tot nhat). */
        public final Map<String, Integer> rank;

        Assigned(Map<String, Float> symbolPred, Map<String, Float> pwinMapped,
                 Map<String, Integer> rank) {
            this.symbolPred = symbolPred;
            this.pwinMapped = pwinMapped;
            this.rank = rank;
        }

        public int size() {
            return symbolPred.size();
        }
    }

    /**
     * Map mot tick.
     *
     * @param rowOrder thu tu dong (pha the cua {@code rank(method="first")}). PHAI chua dung
     *                 tap khoa cua {@code s1Score} va {@code pwin}.
     * @param s1Score  {@code symbol -> score S1}, THAP = TOT (cung quy uoc pred_s1a2x1.parquet).
     * @param pwin     {@code symbol -> P(win)} cua net015 (cao = tot) — cung tap coin.
     * @return null khi input rong hoac lech tap khoa (caller giu duong cu, KHONG doan).
     */
    public static Assigned assign(List<String> rowOrder, Map<String, Float> s1Score,
                                  Map<String, Float> pwin) {
        if (rowOrder == null || rowOrder.isEmpty() || s1Score == null || pwin == null) return null;
        int n = rowOrder.size();
        String[] sym = new String[n];
        double[] sc = new double[n];
        double[] pw = new double[n];
        for (int i = 0; i < n; i++) {
            String s = rowOrder.get(i);
            Float a = s1Score.get(s);
            Float b = pwin.get(s);
            if (a == null || b == null || a.isNaN() || b.isNaN()) return null;
            sym[i] = s;
            sc[i] = a;
            pw[i] = b;
        }
        // r_score: rank(score, method="first")  -> 1 = score thap nhat
        int[] rScore = rankFirst(sc, true);
        // p_sorted: rank(p, method="first", ascending=False) -> 1 = p cao nhat
        int[] pSorted = rankFirst(pw, false);
        // key = p theo p_sorted;  p_new(i) = key[ r_score(i) ]
        double[] byPRank = new double[n + 1];
        for (int i = 0; i < n; i++) byPRank[pSorted[i]] = pw[i];

        Map<String, Float> outPred = new LinkedHashMap<>(n * 2);
        Map<String, Float> outPwin = new LinkedHashMap<>(n * 2);
        Map<String, Integer> outRank = new LinkedHashMap<>(n * 2);
        for (int i = 0; i < n; i++) {
            double pNew = byPRank[rScore[i]];
            outPwin.put(sym[i], (float) pNew);
            // DAO DAU — y het WfoDataset.buildFundingFromWfFiles:248
            outPred.put(sym[i], (float) (1.0f - (float) pNew));
            outRank.put(sym[i], rScore[i]);
        }
        return new Assigned(outPred, outPwin, outRank);
    }

    /**
     * Tuong duong {@code pandas.Series.rank(method="first", ascending=asc)}: tra rank 1-based,
     * the pha theo VI TRI DONG (index nho hon duoc rank nho hon). Khong co rank trung nhau.
     */
    static int[] rankFirst(double[] v, boolean asc) {
        int n = v.length;
        Integer[] idx = new Integer[n];
        for (int i = 0; i < n; i++) idx[i] = i;
        Arrays.sort(idx, (x, y) -> {
            int c = Double.compare(v[x], v[y]);
            if (!asc) c = -c;
            if (c != 0) return c;
            return Integer.compare(x, y);          // the -> thu tu dong
        });
        int[] r = new int[n];
        for (int k = 0; k < n; k++) r[idx[k]] = k + 1;
        return r;
    }

    /** Thu tu dong tat dinh cua duong LIVE: ten symbol tang dan. */
    public static List<String> liveRowOrder(java.util.Collection<String> syms) {
        List<String> l = new ArrayList<>(syms);
        java.util.Collections.sort(l);
        return l;
    }

    /** Phan vi (kieu {@code numpy.percentile} linear) — chi de LOG p10/p50/p90. */
    public static double pct(double[] sorted, double q) {
        if (sorted == null || sorted.length == 0) return Double.NaN;
        if (sorted.length == 1) return sorted[0];
        double pos = q / 100.0 * (sorted.length - 1);
        int lo = (int) Math.floor(pos);
        int hi = (int) Math.ceil(pos);
        if (lo == hi) return sorted[lo];
        return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
    }
}
