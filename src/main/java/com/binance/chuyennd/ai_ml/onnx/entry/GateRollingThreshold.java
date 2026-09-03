package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.Map;
import java.util.TreeMap;

/**
 * NGUONG GATE TRUOT THEO PHAN VI (2026-09-02).
 *
 * <p>Van de do duoc: mean predReturn15M troi tu 0.0036 (2023Q3) len 0.0091 (2025Q4) — gap 2.5 lan.
 * Nguong CO DINH 0.008 lam ty le thoi gian gate mo dao dong 0.5% <-> 76% giua cac quy. Do la
 * phi-dung cua model gate, khong phai tin hieu thi truong.
 *
 * <p>Sua: nguong tai thoi diem t = phan vi p cua predReturn15M trong cua so [t - W, t) — CHI dung
 * du lieu TRUOC t (nhan qua, khong nhin truoc). Tinh san moi GIO luc init, tra bang floorEntry.
 *
 * <p>Bat bang env: SIM_GATE_ROLLING_PCT (0..1, vd 0.90; <=0 hoac rong = TAT -> hanh vi cu byte-identical),
 * SIM_GATE_ROLLING_DAYS (mac dinh 90). Khi bat, AIRejectFilter dung nguong nay thay Configs.MIN_MOMENTUM_15M.
 */
public final class GateRollingThreshold {
    private static final Logger LOG = LoggerFactory.getLogger(GateRollingThreshold.class);
    private static final long HOUR = 3600_000L;
    private static final long GRID = 15 * 60_000L;   // lay mau pred moi 15 phut cho cua so

    private static float pct = -1f;
    private static int days = 90;
    private static TreeMap<Long, Float> hour2thr = null;
    private static long nQuery = 0, nBeforeFirst = 0;

    private GateRollingThreshold() {}

    public static boolean isOn() {
        return hour2thr != null && pct > 0f;
    }

    /** Doc env va tinh san bang nguong theo gio. Goi 1 lan sau khi co predictionMap. Khong bat -> no-op. */
    public static synchronized void init(TreeMap<Long, AiPredictionData> predictionMap) {
        String v = com.binance.chuyennd.tradecore.Cfg.get("SIM_GATE_ROLLING_PCT");
        if (v == null || v.isBlank()) { hour2thr = null; return; }
        pct = Float.parseFloat(v.trim());
        if (pct <= 0f || pct >= 1f) { hour2thr = null; LOG.warn("[GATE-ROLL] SIM_GATE_ROLLING_PCT={} ngoai (0,1) -> TAT", pct); return; }
        String d = com.binance.chuyennd.tradecore.Cfg.get("SIM_GATE_ROLLING_DAYS");
        if (d != null && !d.isBlank()) days = Integer.parseInt(d.trim());
        if (predictionMap == null || predictionMap.isEmpty()) { hour2thr = null; LOG.warn("[GATE-ROLL] predictionMap rong -> TAT"); return; }

        long t0 = System.currentTimeMillis();
        // 1) chuoi pred tren luoi 15m (sap xep theo ts)
        int n = 0;
        for (Map.Entry<Long, AiPredictionData> e : predictionMap.entrySet()) if (e.getKey() % GRID == 0) n++;
        long[] ts = new long[n]; float[] val = new float[n];
        int i = 0;
        for (Map.Entry<Long, AiPredictionData> e : predictionMap.entrySet()) {
            if (e.getKey() % GRID != 0) continue;
            ts[i] = e.getKey(); val[i] = e.getValue().predReturn15M; i++;
        }
        // 2) moi gio h: phan vi cua val[ts in [h - W, h)]
        long W = (long) days * 24 * HOUR;
        long hStart = ((ts[0] + W) / HOUR + 1) * HOUR;      // gio dau tien co du cua so
        long hEnd = ts[n - 1];
        TreeMap<Long, Float> out = new TreeMap<>();
        int lo = 0, hi = 0;
        float[] buf = new float[n];
        for (long h = hStart; h <= hEnd; h += HOUR) {
            while (lo < n && ts[lo] < h - W) lo++;
            while (hi < n && ts[hi] < h) hi++;
            int m = hi - lo;
            if (m < 96 * 7) continue;                        // it hon 7 ngay du lieu -> bo
            System.arraycopy(val, lo, buf, 0, m);
            Arrays.sort(buf, 0, m);
            int k = Math.min(m - 1, Math.max(0, (int) Math.floor(pct * (m - 1))));
            out.put(h, buf[k]);
        }
        hour2thr = out;
        float mn = Float.MAX_VALUE, mx = -Float.MAX_VALUE;
        for (float f : out.values()) { mn = Math.min(mn, f); mx = Math.max(mx, f); }
        LOG.warn("*** [GATE-ROLL] BAT: pct={} window={}d | {} moc gio | nguong min={} max={} | tinh {} ms ***",
                pct, days, out.size(), String.format("%.5f", mn), String.format("%.5f", mx), System.currentTimeMillis() - t0);
    }

    /** Nguong tai thoi diem t (dung bang cua GIO <= t). Truoc moc dau tien -> fallback Configs.MIN_MOMENTUM_15M. */
    public static float threshold(long t) {
        nQuery++;
        Map.Entry<Long, Float> e = hour2thr.floorEntry(t);
        if (e == null) { nBeforeFirst++; return Configs.MIN_MOMENTUM_15M; }
        return e.getValue();
    }

    public static String stats() {
        return isOn() ? String.format("GATE-ROLL pct=%.2f days=%d query=%d beforeFirst=%d", pct, days, nQuery, nBeforeFirst)
                      : "GATE-ROLL off";
    }
}
