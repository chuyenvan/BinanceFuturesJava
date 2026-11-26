package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.Map;
import java.util.TreeMap;

/**
 * NGUONG GATE TRUOT THEO PHAN VI — nhanh B4, cai lai 2026-09-03.
 *
 * <p>Ban goc viet 2026-09-02, bi xoa o commit {@code 5f40a90} (DOT 2 xoa co tro) vi luc do B4 da
 * bi dong. Nhanh mo lai theo {@code docs/CI_REAUDIT.md} HE QUA (ii): ca 3 hieu RG vs C2b nam TRONG
 * CI va maxDD ca 3 khong te hon C2b => cau "EV am" khong duoc du lieu ho tro. Co che va 3 bien the
 * duoc chot TRUOC o {@code docs/PREREG_B4.md} (commit a0c7ad6).
 *
 * <p>Van de do duoc: mean predReturn15M troi tu 0.0036 (2023Q3) len 0.0091 (2025Q4) — gap 2.5 lan.
 * Nguong CO DINH 0.008 lam ty le thoi gian gate mo dao dong manh giua cac quy. Do la phi-dung cua
 * model gate, khong phai tin hieu thi truong.
 *
 * <p>Co che (PREREG_B4 section 1.2): nguong tai thoi diem t = phan vi p cua predReturn15M trong cua
 * so NUA MO [t - W, t) — CHI dung du lieu TRUOC t (nhan qua, khong nhin truoc). Mau lay tren luoi
 * 15 phut. Bang {@code gio -> nguong} tinh san MOT LAN luc init, cap nhat moi GIO wall-clock, truy
 * van bang {@code floorEntry}. Phan vi khong noi suy: k = min(m-1, max(0, floor(p*(m-1)))).
 * Dau ky: moc dau tien phai co DU cua so W, va moc nao co m &lt; 96*7 mau thi bo; truy van truoc moc
 * dau tien tra ve {@code Configs.MIN_MOMENTUM_15M} (hanh vi cu) va LOG.warn MOT lan.
 *
 * <p>Chi thay nguong CO SO cua gate MOM15; phan nhan he so theo score trong
 * {@link AIRejectFilter#checkSignalDynamic} KHONG doi.
 *
 * <p>Tham so di qua cong {@link Cfg} (khai trong profile, KHONG doc System.getenv):
 * {@code SIM_GATE_ROLLING_PCT} (0..1, vd 0.95; khong khai bao / rong / ngoai (0,1) = TAT =&gt; hanh vi
 * byte-identical voi C2b), {@code SIM_GATE_ROLLING_DAYS} (mac dinh 90).
 */
public final class GateRollingThreshold {
    private static final Logger LOG = LoggerFactory.getLogger(GateRollingThreshold.class);
    private static final long HOUR = 3600_000L;
    private static final long GRID = 15 * 60_000L;   // lay mau pred moi 15 phut cho cua so
    private static final int MIN_SAMPLES = 96 * 7;   // < 7 ngay du lieu trong cua so -> bo moc gio

    private static float pct = -1f;
    private static int days = 90;
    private static TreeMap<Long, Float> hour2thr = null;
    private static long nQuery = 0, nBeforeFirst = 0;
    private static boolean warnedBeforeFirst = false;

    private GateRollingThreshold() {}

    public static boolean isOn() {
        return hour2thr != null && pct > 0f;
    }

    /** Doc cau hinh va tinh san bang nguong theo gio. Goi 1 lan sau khi co predictionMap. TAT -> no-op. */
    public static synchronized void init(TreeMap<Long, AiPredictionData> predictionMap) {
        hour2thr = null;
        nQuery = 0;
        nBeforeFirst = 0;
        warnedBeforeFirst = false;
        String v = Cfg.get("SIM_GATE_ROLLING_PCT");
        if (v == null || v.isBlank()) return;
        pct = Float.parseFloat(v.trim());
        if (pct <= 0f || pct >= 1f) {
            LOG.warn("[GATE-ROLL] SIM_GATE_ROLLING_PCT={} ngoai (0,1) -> TAT", pct);
            return;
        }
        String d = Cfg.get("SIM_GATE_ROLLING_DAYS");
        if (d != null && !d.isBlank()) days = Integer.parseInt(d.trim());
        if (predictionMap == null || predictionMap.isEmpty()) {
            LOG.warn("[GATE-ROLL] predictionMap rong -> TAT");
            return;
        }

        long t0 = System.currentTimeMillis();
        // 1) chuoi pred tren luoi 15m (TreeMap => da sap xep theo ts)
        int n = 0;
        for (Map.Entry<Long, AiPredictionData> e : predictionMap.entrySet()) if (e.getKey() % GRID == 0) n++;
        if (n < MIN_SAMPLES) {
            LOG.warn("[GATE-ROLL] chi co {} mau tren luoi 15m (< {}) -> TAT", n, MIN_SAMPLES);
            return;
        }
        long[] ts = new long[n];
        float[] val = new float[n];
        int i = 0;
        for (Map.Entry<Long, AiPredictionData> e : predictionMap.entrySet()) {
            if (e.getKey() % GRID != 0) continue;
            ts[i] = e.getKey();
            val[i] = e.getValue().predReturn15M;
            i++;
        }
        // 2) moi gio h: phan vi cua val[ts in [h - W, h)]
        long w = (long) days * 24 * HOUR;
        long hStart = ((ts[0] + w) / HOUR + 1) * HOUR;      // gio tron dau tien co DU cua so
        long hEnd = ts[n - 1];
        TreeMap<Long, Float> out = new TreeMap<>();
        int lo = 0, hi = 0;
        float[] buf = new float[n];
        for (long h = hStart; h <= hEnd; h += HOUR) {
            while (lo < n && ts[lo] < h - w) lo++;
            while (hi < n && ts[hi] < h) hi++;
            int m = hi - lo;
            if (m < MIN_SAMPLES) continue;
            System.arraycopy(val, lo, buf, 0, m);
            Arrays.sort(buf, 0, m);
            int k = Math.min(m - 1, Math.max(0, (int) Math.floor(pct * (m - 1))));
            out.put(h, buf[k]);
        }
        if (out.isEmpty()) {
            LOG.warn("[GATE-ROLL] khong sinh duoc moc gio nao (pct={} window={}d) -> TAT", pct, days);
            return;
        }
        hour2thr = out;
        float mn = Float.MAX_VALUE, mx = -Float.MAX_VALUE;
        for (float f : out.values()) {
            mn = Math.min(mn, f);
            mx = Math.max(mx, f);
        }
        LOG.warn("*** [GATE-ROLL] BAT: pct={} window={}d | {} moc gio | moc dau {} | nguong min={} max={} | tinh {} ms ***",
                pct, days, out.size(), out.firstKey(), String.format("%.5f", mn), String.format("%.5f", mx),
                System.currentTimeMillis() - t0);
    }

    /** Nguong tai thoi diem t (dung bang cua GIO &lt;= t). Truoc moc dau tien -> Configs.MIN_MOMENTUM_15M. */
    public static float threshold(long t) {
        nQuery++;
        Map.Entry<Long, Float> e = hour2thr.floorEntry(t);
        if (e == null) {
            nBeforeFirst++;
            if (!warnedBeforeFirst) {
                warnedBeforeFirst = true;
                LOG.warn("[GATE-ROLL] truy van t={} TRUOC moc gio dau tien {} -> fallback hang so MIN_MOMENTUM_15M={}",
                        t, hour2thr.firstKey(), Configs.MIN_MOMENTUM_15M);
            }
            return Configs.MIN_MOMENTUM_15M;
        }
        return e.getValue();
    }

    /** Thong ke cho log cuoi run (PREREG_B4 section 1.2 muc 5: bao cao phai in nBeforeFirst). */
    public static String stats() {
        return isOn()
                ? String.format("GATE-ROLL pct=%.2f days=%d moc=%d query=%d beforeFirst=%d",
                        pct, days, hour2thr.size(), nQuery, nBeforeFirst)
                : "GATE-ROLL off";
    }
}
