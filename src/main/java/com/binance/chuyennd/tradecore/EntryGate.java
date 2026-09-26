package com.binance.chuyennd.tradecore;

/**
 * CONG ENTRY TANG 2 — MOT cho duy nhat quyet dinh "tin hieu 15m co du manh de vao lenh khong",
 * dung chung cho BACKTEST ({@code SimulatorMarketLevelTicker1MStopLoss.createOrder}) va LIVE
 * ({@code DetectEntrySignal2TradeNormal.createOrderBuyRequest}).
 *
 * <p><b>Vi sao co class nay</b> (L7, docs/experiment/L7_LEAN_GATE.md + docs/audit/LEAN_GATE_AUDIT.md): cong nay
 * tung nam o HAI ban sao trong {@code AIRejectFilter} ({@code checkSignalDynamic} va
 * {@code dynThreshold}) va duoc goi tu hai duong khac nhau, da troi khoi nhau 3 tuan
 * (commit {@code 311bb29}) ma khong ai thay — lech 95.62% slot entry tren 48 thang,
 * 77/78 entry so giay 242 (docs/audit/AUDIT_GATE_DYN_PARITY.md). Nay chi con MOT bieu thuc.
 *
 * <p><b>Cong thuc — GIU NGUYEN TUNG PHEP NHAN, khong duoc "rut gon"</b>:
 * <pre>
 *   thr(symbolPred) = thrBase * max(DYN_MIN, (symbolPred / SCORE_BASE) * DYN_MULT)
 *   PASS  &lt;=&gt;  !(predReturn15M &lt; thr)
 * </pre>
 * Dang rut gon {@code predReturn15M >= K * symbolPred} voi {@code K = thrBase*DYN_MULT/SCORE_BASE}
 * = 0.0686720 **DA BI BAC BO** o docs/audit/LEAN_GATE_AUDIT.md muc 3:
 * <ol>
 *   <li>floor {@code DYN_MIN} CO bind that (1 slot / 140,244 moc 15m x top-8 tren 48 thang:
 *       2024-08-05 13:30 GMT+7, symId 261, symbolPred 0.024885) => khong phai dong nhat thuc;</li>
 *   <li>nhan {@code float} KHONG ket hop: {@code base*((sp/RMAX)*MULT)} lech
 *       {@code (base*MULT/RMAX)*sp} co the 1 ULP — do duoc ngay tren tick do (rank2
 *       delta = -0.0000000) — va gate so sanh {@code >=} nen 1 ULP du doi mot quyet dinh.</li>
 * </ol>
 * Ai doi thu tu phep nhan o day = doi hanh vi da duoc kiem 48 thang. DUNG DOI.
 *
 * <p><b>Ba he so la HANG SO, co chu dich</b>: chung tung la {@code Configs.AI_DYNAMIC_MIN} /
 * {@code PREDICT_SYMBOL_RATE_MAX_THRESHOLD} / {@code AI_DYNAMIC_MULTIPLIER} doc qua key
 * {@code SIM_AI_DYNAMIC_*} — nhung KHONG profile/env nao tung khai bao chung (do o
 * docs/audit/LEAN_GATE_AUDIT.md muc 2.3), tuc chung la hang so tra hinh cau hinh. Nay chot cung o day:
 * gate chi con DUNG MOT knob la {@code Configs.MIN_MOMENTUM_15M} (key {@code SIM_MIN_MOMENTUM_15M},
 * da co san trong {@code conf/env.sh} cua 242 => deploy KHONG phai sua env).
 *
 * <p><b>KHONG lien quan {@code Configs.AI_DYNAMIC_MAX}</b>: bien do la TRAN UNG VIEN o TANG 1
 * cua selector ({@code maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MAX}), va tang 1
 * bi bo hoan toan khi {@code SELECTOR_RANK_TOPK > 0}. No khong bao gio la tran cua nguong nay.
 */
public final class EntryGate {

    /** Can DUOI cua he so nhan nguong (cu: {@code Configs.AI_DYNAMIC_MIN}). */
    public static final float DYN_MIN = 0.26787f;
    /** Mau so chuan hoa score selector (cu: {@code Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD}). */
    public static final float SCORE_BASE = 0.15f;
    /** He so nhan (cu: {@code Configs.AI_DYNAMIC_MULTIPLIER}). */
    public static final float DYN_MULT = 1.28760f;

    /**
     * He so nhan them vao KET QUA dyn_thr da tinh (docs/prereg/PREREG_GATESCALE.md). Doc DUNG MOT LAN
     * luc {@code Configs} nap (key {@code SIM_GATE_DYN_SCALE}); khong khai / {@code <=0} => 1.0f
     * => {@code x*1.0f} IEEE-exact => byte-identical. {@code >1} = gate CHAT hon (it lenh),
     * {@code <1} = LONG hon (nhieu lenh). KHONG doc Cfg moi lan goi (nong). Chi ap o nhanh dyn
     * ({@code symbolPred != null}); nhanh nguong CO SO ({@code symbolPred == null}: BIG_DOWN /
     * DCA_LEVEL1 / leg market-signal) KHONG bi scale.
     */
    public static float GATE_DYN_SCALE = 1.0f;

    /** [REGIME] docs/prereg/PREREG_REGIME_GATE.md: gate scale doi theo regime BTC 30d. default OFF => byte-identical. */
    public static boolean GATE_REGIME_ADAPTIVE = false;
    /** Scale khi regime UP (uptrend BTC 30d): mac dinh T100 (pre-reg Buoc 2). TASK B2 Buoc 4
     *  (docs/prereg/PREREG_REGIME_UPDOWN.md) can up-gate CHAT hon (1.2/1.4), nen bo final, doc duoc
     *  qua Configs (key SIM_REGIME_SCALE_UP). Khong khai bao key nay thi giu nguyen 1.00f,
     *  byte-identical voi vong Buoc 2 (va voi OFF, vi OFF dung nhanh GATE_DYN_SCALE khac han). */
    public static float REGIME_SCALE_UP = 1.00f;
    /** Scale khi regime NOT-UP (chop/down): = T170. HANG SO pre-reg, KHONG fit. */
    public static final float REGIME_SCALE_NOTUP = 1.70f;
    /** Scale theo-tick do simulator dat moi tick khi GATE_REGIME_ADAPTIVE bat (RegimeSchedule.scaleForTime). */
    public static float CURRENT_REGIME_SCALE = REGIME_SCALE_NOTUP;

    // =========================================================================
    // [GATE-RECAL 2026-09-26] docs/prereg/PREREG_GATE_RECAL.md — nguong gate bieu dien theo
    //   PHAN VI CUON cua chinh chuoi p15 cua NGUON DANG CHAY (thay vi hang so tuyet doi hieu
    //   chuan tren bo pred DEV). Key `SIM_GATE_P15_Q` (float, doc 1 lan o Configs).
    //   KHONG khai / <=0 => P15_Q = 0f => moi bieu thuc duoi day KHONG duoc cham
    //   => hanh vi cu BYTE-IDENTICAL.
    //   PASS <=> !(predReturn15M < thr); thr = max(MIN_MOMENTUM_15M, quantile_W(p15_past, Q));
    //   nhanh symbolPred != null: thr_final = max(rolling_thr, threshold(sp)) — CHI siet, KHONG noi long.
    // =========================================================================

    /** Q cua phan vi cuon (0 = OFF => byte-identical). Doc 1 lan o {@code Configs} tu key {@code SIM_GATE_P15_Q}. */
    public static float P15_Q = 0f;

    /** W = so NGAY cua so truot — HANG SO pre-reg, KHONG fit, khong doc tu config. */
    public static final int P15_W_DAYS = 30;

    /** Thoi diem TICK hien tai cua sim (do simulator dat moi tick). Chi dung khi {@code P15_Q > 0}. */
    public static long CURRENT_P15_TIME = Long.MIN_VALUE;

    /** Moc thoi gian cua tung mau p15 (sort tang). Rong khi OFF. */
    private static long[] p15RollTime = null;
    /** Nguong cuon tuong ung tung moc (CAUSAL: cua so [t-W, t)). null khi OFF. */
    private static float[] p15RollThr = null;

    /** Do simulator dat moi tick (truoc moi createOrder cua tick do). */
    public static void setCurrentTime(long time) {
        CURRENT_P15_TIME = time;
    }

    /**
     * Dung chuoi p15 cua nguon dang chay thanh NGUONG CUON CAUSAL.
     *
     * @param t      moc thoi gian tung mau (PHai sort tang dan)
     * @param v      gia tri p15 tung mau ({@code predReturn15M})
     * @param q      Q phan vi (vd 0.995)
     * @param wDays  W ngay cua so truot
     *               <p>Cua so tai mau i = {j : t[i]-W &lt;= t[j] &lt; t[i]} — CHI QUA KHU, khong nhin tuong lai.
     *               Phan vi theo ky phap NEAREST-RANK: chi so 1-based = ceil(q*n), lam tron vao [1,n].
     */
    public static void buildP15Rolling(long[] t, float[] v, float q, int wDays) {
        int n = t.length;
        long[] rt = new long[n];
        float[] rv = new float[n];
        java.util.TreeMap<Float, Integer> cnt = new java.util.TreeMap<>();
        int lo = 0, hi = 0;
        long wms = (long) wDays * 86400000L;
        for (int i = 0; i < n; i++) {
            long ti = t[i];
            while (hi < i) {
                cnt.merge(v[hi], 1, Integer::sum);
                hi++;
            }
            long cut = ti - wms;
            while (lo < hi && t[lo] < cut) {
                float x = v[lo];
                Integer c = cnt.get(x);
                if (c == null || c <= 1) cnt.remove(x);
                else cnt.put(x, c - 1);
                lo++;
            }
            rt[i] = ti;
            int m = hi - lo;
            if (m <= 0) {
                rv[i] = Float.NEGATIVE_INFINITY;
                continue;
            }
            int rank = (int) Math.ceil((double) q * m);
            if (rank < 1) rank = 1;
            if (rank > m) rank = m;
            int need = m - rank + 1;              // so phan tu ke tu DINH xuong
            int acc = 0;
            float val = Float.NaN;
            for (java.util.Map.Entry<Float, Integer> e : cnt.descendingMap().entrySet()) {
                acc += e.getValue();
                if (acc >= need) {
                    val = e.getKey();
                    break;
                }
            }
            rv[i] = val;
        }
        p15RollTime = rt;
        p15RollThr = rv;
    }

    /** Nguong cuon tai {@code time} (moc lon nhat &lt;= time). Chua co cua so =&gt; -inf (san base se ap). */
    public static float rollingThrAt(long time) {
        long[] rt = p15RollTime;
        if (rt == null || rt.length == 0) return Float.NEGATIVE_INFINITY;
        int lo = 0, hi = rt.length - 1, best = -1;
        while (lo <= hi) {
            int mid = (lo + hi) >>> 1;
            if (rt[mid] <= time) {
                best = mid;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        return best < 0 ? Float.NEGATIVE_INFINITY : p15RollThr[best];
    }

    private EntryGate() {
    }

    /**
     * Nguong 15m THAT SU ap cho mot ung vien.
     *
     * @param thrBase    nguong co so = {@code Configs.MIN_MOMENTUM_15M}
     * @param symbolPred score selector cua coin; {@code null} = khong di qua sleeve selector
     *                   (BIG_DOWN / DCA_LEVEL1 / leg market-signal) => nguong CO SO, y nhu cu
     */
    public static float threshold(float thrBase, Float symbolPred) {
        // [GATE-RECAL 2026-09-26] P15_Q = 0 (mac dinh) => KHONG vao nhanh nay => bieu thuc cu nguyen ven.
        if (P15_Q > 0f) {
            // thr = max(base, quantile_cuon): san base luon giu; cua so rong => -inf => = base.
            float roll = Math.max(thrBase, rollingThrAt(CURRENT_P15_TIME));
            if (symbolPred == null) return roll;
            float sc = (symbolPred / SCORE_BASE) * DYN_MULT;
            float gs = GATE_REGIME_ADAPTIVE ? CURRENT_REGIME_SCALE : GATE_DYN_SCALE;
            // max(rolling, dyn): CHI siet them so voi hanh vi dang co, KHONG bao gio noi long.
            return Math.max(roll, thrBase * Math.max(DYN_MIN, sc) * gs);
        }
        if (symbolPred == null) return thrBase;
        float scale = (symbolPred / SCORE_BASE) * DYN_MULT;
        float gateScale = GATE_REGIME_ADAPTIVE ? CURRENT_REGIME_SCALE : GATE_DYN_SCALE;
        return thrBase * Math.max(DYN_MIN, scale) * gateScale;
    }

    /** Nguong voi {@code thrBase} lay thang tu cau hinh dang chay. */
    public static float threshold(Float symbolPred) {
        return threshold(Configs.MIN_MOMENTUM_15M, symbolPred);
    }

    /**
     * Quyet dinh cong entry. Viet dang {@code !(x < thr)} chu KHONG phai {@code x >= thr}:
     * hai dang khac nhau khi {@code predReturn15M} la NaN, va dang {@code <} la dang goc da chay
     * 48 thang ({@code AIRejectFilter.evaluate}).
     */
    public static boolean pass(float predReturn15M, float thrBase, Float symbolPred) {
        return !(predReturn15M < threshold(thrBase, symbolPred));
    }
}
