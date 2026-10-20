package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.sw.KlineObjectSimple;

import java.time.LocalDate;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

/**
 * [TS-MKT-EXT v1.1] Chi so ALT_EW 1m + co ngay "ca thi truong alt dang sap" — port DUNG luat sim
 * ({@code docs/plan/V11_TS_MKT_EXT_LIVE.md} §1 S7–S9; nguon: {@code edge_attr_build.py} logret/build_index,
 * {@code tsx_flags.py}, {@code tsx_ho.py:flags()}).
 *
 * <ul>
 *   <li>Return phut t cua symbol s = ln close(t) − ln close(t−1m), chi khi co nen lien ke (Δts = 60 000),
 *       {@code qv > 0} ca hai nen, return huu han, s ∉ {BTCUSDT, ETHUSDT}; cat ±0,5.</li>
 *   <li>EW(t) = trung binh DEU cac return hop le cua phut t (khong co return hop le ⇒ phut khong co EW).</li>
 *   <li>Bien thang (S9): sim tinh logret TUNG THANG ⇒ phut dau thang khong co return. Tai lap bang cach xoa trang
 *       thai nen truoc moi khi doi thang UTC.</li>
 *   <li>S_j = Σ EW phut cua ngay UTC j; co(D) ⟺ exp(P(D−1) − max_{k∈[D−31, D−1]} P(k)) − 1 ≤ −0,30 voi
 *       P(k) = Σ_{j=D−30..k} S_j, P(D−31) = 0 (= {@code eod − eod.rolling(31).max()} cua sim).</li>
 * </ul>
 * Lop THUAN tinh toan (khong I/O, khong env) — dung chung cho live va harness offline.
 */
public final class AltEwIndex {

    public static final long MIN = 60_000L;
    public static final long DAY = 86_400_000L;
    public static final double CLIP = 0.5;
    /** Nguong drawdown ALT_EW so dinh 31 ngay (luat X14 dong bang). */
    public static final double DD_THRESHOLD = -0.30;
    /** So ngay S_j can de tinh co(D): [D−30, D−1]. */
    public static final int WINDOW_DAYS = 30;
    /** Chat luong du lieu live: ngay co it hon so phut EW nay ⇒ co NA (OFF). 90 % cua 1440. */
    public static final int MIN_MINUTES_PER_DAY = 1296;

    /** Trang thai co mot ngay. NA = thieu du lieu (live coi nhu OFF). */
    public enum State { ON, OFF, NA }

    /** Tong EW cua mot ngay UTC. */
    public static final class DayStat {
        public final long day;
        public final double sum;
        public final int n;

        public DayStat(long day, double sum, int n) {
            this.day = day;
            this.sum = sum;
            this.n = n;
        }
    }

    /** Ket qua co cho ngay {@code flagDay} (dua tren ngay flagDay−1). */
    public static final class FlagResult {
        public final long flagDay;
        public final State state;
        /** dd(flagDay−1); NaN khi NA. */
        public final double dd;
        /** P(flagDay−1) = tong 30 ngay. */
        public final double p;
        public final double maxP;
        public final long maxDay;
        public final int minN;
        public final String reason;

        FlagResult(long flagDay, State state, double dd, double p, double maxP, long maxDay, int minN, String reason) {
            this.flagDay = flagDay;
            this.state = state;
            this.dd = dd;
            this.p = p;
            this.maxP = maxP;
            this.maxDay = maxDay;
            this.minN = minN;
            this.reason = reason;
        }
    }

    // ---------------- bo tich luy phut ----------------
    private final Map<String, Integer> ids = new HashMap<>();
    private long[] prevTs = new long[0];
    private double[] prevLc = new double[0];
    private double[] prevQv = new double[0];
    private boolean[] excluded = new boolean[0];
    private long curMonth = Long.MIN_VALUE;
    private long monthDay = Long.MIN_VALUE;
    private long curDay = Long.MIN_VALUE;
    private double daySum = 0d;
    private double dayComp = 0d;
    private int dayN = 0;
    private final TreeMap<Long, DayStat> days = new TreeMap<>();

    /** Id on dinh cho symbol (cap phat lan dau). BTCUSDT/ETHUSDT danh dau loai khoi EW. */
    public int id(String sym) {
        Integer v = ids.get(sym);
        if (v != null) return v;
        int i = ids.size();
        ids.put(sym, i);
        if (i >= prevTs.length) {
            int cap = Math.max(1024, prevTs.length * 2);
            prevTs = Arrays.copyOf(prevTs, cap);
            Arrays.fill(prevTs, i, cap, Long.MIN_VALUE);
            prevLc = Arrays.copyOf(prevLc, cap);
            prevQv = Arrays.copyOf(prevQv, cap);
            excluded = Arrays.copyOf(excluded, cap);
        }
        excluded[i] = "BTCUSDT".equals(sym) || "ETHUSDT".equals(sym);
        prevTs[i] = Long.MIN_VALUE;
        return i;
    }

    private static long monthIndex(long epochDay) {
        LocalDate d = LocalDate.ofEpochDay(epochDay);
        return d.getYear() * 12L + d.getMonthValue();
    }

    /**
     * Nap MOT phut (ts tang dan). {@code symIds[i]} lay tu {@link #id}. Tra EW cua phut hoac NaN neu khong co
     * return hop le. Chi tich luy vao ngay khi EW huu han.
     */
    public double feed(long ts, int[] symIds, double[] close, double[] qv, int n) {
        long day = Math.floorDiv(ts, DAY);
        if (day != monthDay) {
            long m = monthIndex(day);
            monthDay = day;
            if (m != curMonth) {
                curMonth = m;
                Arrays.fill(prevTs, Long.MIN_VALUE);   // S9: sim tinh logret theo tung thang
            }
        }
        double sum = 0d;
        double comp = 0d;
        int cnt = 0;
        for (int i = 0; i < n; i++) {
            int id = symIds[i];
            double lc = Math.log(close[i]);
            double q = qv[i];
            if (prevTs[id] == ts - MIN && !excluded[id]) {
                double r = lc - prevLc[id];
                if (q > 0d && prevQv[id] > 0d && Double.isFinite(r)) {
                    double c = r > CLIP ? CLIP : (r < -CLIP ? -CLIP : r);
                    double y = c - comp;          // Kahan (pandas group_mean cung bu sai so)
                    double t = sum + y;
                    comp = (t - sum) - y;
                    sum = t;
                    cnt++;
                }
            }
            prevTs[id] = ts;
            prevLc[id] = lc;
            prevQv[id] = q;
        }
        if (cnt == 0) return Double.NaN;
        double ew = sum / cnt;
        if (day != curDay) {
            flushDay();
            curDay = day;
        }
        double y = ew - dayComp;
        double t = daySum + y;
        dayComp = (t - daySum) - y;
        daySum = t;
        dayN++;
        return ew;
    }

    /** Adapter live: mot record phut Aerospike (symbol day du, gia float32) ⇒ {@link #feed}. */
    public double feed(long ts, Map<String, KlineObjectSimple> bars) {
        if (bars == null || bars.isEmpty()) return Double.NaN;
        int n = bars.size();
        int[] sid = new int[n];
        double[] c = new double[n];
        double[] q = new double[n];
        int k = 0;
        for (Map.Entry<String, KlineObjectSimple> e : bars.entrySet()) {
            KlineObjectSimple b = e.getValue();
            if (b == null || e.getKey() == null) continue;
            sid[k] = id(e.getKey());
            c[k] = b.priceClose;
            q[k] = b.totalUsdt;
            k++;
        }
        return feed(ts, sid, c, q, k);
    }

    private void flushDay() {
        if (curDay != Long.MIN_VALUE && dayN > 0) days.put(curDay, new DayStat(curDay, daySum, dayN));
        daySum = 0d;
        dayComp = 0d;
        dayN = 0;
    }

    /** Chot ngay dang tich luy va tra toan bo tong ngay (ban sao). */
    public TreeMap<Long, DayStat> finish() {
        flushDay();
        curDay = Long.MIN_VALUE;
        return new TreeMap<>(days);
    }

    /** So phut toi da co EW cua ngay UTC (ngay 1 thang: 1439 do S9). */
    public static int expectedMinutes(long epochDay) {
        return LocalDate.ofEpochDay(epochDay).getDayOfMonth() == 1 ? 1439 : 1440;
    }

    /** Co cho ngay {@code flagDay} tu tong ngay [flagDay−30, flagDay−1]. Thieu/ngay mong ⇒ NA. */
    public static FlagResult flagFor(long flagDay, Map<Long, DayStat> days) {
        long d = flagDay - 1;
        double p = 0d;
        double maxP = 0d;
        long maxDay = d - WINDOW_DAYS;
        int minN = Integer.MAX_VALUE;
        for (long j = d - WINDOW_DAYS + 1; j <= d; j++) {
            DayStat s = days == null ? null : days.get(j);
            if (s == null) {
                return new FlagResult(flagDay, State.NA, Double.NaN, Double.NaN, Double.NaN, -1L, 0,
                        "missing " + LocalDate.ofEpochDay(j));
            }
            if (s.n < MIN_MINUTES_PER_DAY) {
                return new FlagResult(flagDay, State.NA, Double.NaN, Double.NaN, Double.NaN, -1L, s.n,
                        "lowcov " + LocalDate.ofEpochDay(j) + " n=" + s.n);
            }
            p += s.sum;
            if (p > maxP) {
                maxP = p;
                maxDay = j;
            }
            if (s.n < minN) minN = s.n;
        }
        double dd = Math.exp(p - maxP) - 1.0;
        State st = dd <= DD_THRESHOLD ? State.ON : State.OFF;
        return new FlagResult(flagDay, st, dd, p, maxP, maxDay, minN, "ok");
    }
}
