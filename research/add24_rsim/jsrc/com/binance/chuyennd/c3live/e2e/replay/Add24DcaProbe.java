package com.binance.chuyennd.c3live.e2e.replay;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.DcaUtils;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.util.TreeMap;
import java.util.zip.GZIPInputStream;

/** ADD24 3b (DEV-B): thoi diem DCA cua JAR (ham jar: getMarketStatus1M / isDcaAlt / shouldDcaGrid / AIRejectFilter.entryGate sp=null nhu
 *  CrashDayRig.dcaPass) khi nap dieu kien thi truong = (a) market.bin CUA SIM (down,up,down15 moi phut) hoac (b) market.csv cua rig (Vision).
 *  args: market(csv ts,down,up,down15 | rig market.csv) mode(sim|rig) klines.csv.gz symbol firstEntry t0 tEnd p15.csv */
public final class Add24DcaProbe {
    public static void main(String[] a) throws Exception {
        String mode = a[1], sym = a[3];
        float first = Float.parseFloat(a[4]);
        long t0 = Long.parseLong(a[5]), tEnd = Long.parseLong(a[6]);
        TreeMap<Long, float[]> mk = new TreeMap<>();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(new FileInputStream(a[0])))) {
            String ln = br.readLine();
            while ((ln = br.readLine()) != null) {
                String[] p = ln.split(",", -1);
                if ("sim".equals(mode)) mk.put(Long.parseLong(p[0]), new float[]{Float.parseFloat(p[1]), Float.parseFloat(p[2]), Float.parseFloat(p[3])});
                else if (!p[3].isEmpty()) mk.put(Long.parseLong(p[0]), new float[]{Float.parseFloat(p[3]), Float.parseFloat(p[5]), Float.parseFloat(p[4])}); // b,p15,dip,down,down15,up
            }
        }
        TreeMap<Long, Float> cl = new TreeMap<>();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(new GZIPInputStream(new FileInputStream(a[2]))))) {
            String ln;
            while ((ln = br.readLine()) != null) {
                String[] p = ln.split(",");
                if (p[0].equals(sym)) cl.put(Long.parseLong(p[1]), Float.parseFloat(p[5]));
            }
        }
        TreeMap<Long, Float> p15 = new TreeMap<>();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(new FileInputStream(a[7])))) {
            String ln = br.readLine();
            while ((ln = br.readLine()) != null) {
                String[] p = ln.split(",");
                p15.put(Long.parseLong(p[0]), Float.parseFloat(p[1]));
            }
        }
        AIRejectFilter gate = new AIRejectFilter();
        int nPrice = 0, nMkt = 0, nBoth = 0;
        Long firstDue = null;
        StringBuilder sb = new StringBuilder();
        for (long t = t0 + 60_000L; t <= tEnd; t += 60_000L) {
            Float c = cl.get(t);
            float[] m = mk.get(t);
            if (c == null || m == null) continue;
            boolean price = DcaUtils.shouldDcaGrid(first, c, 1);
            MarketLevelChange lv = MarketBigChangeDetector.getMarketStatus1M(m[0], m[1], m[2]);
            boolean alt = MarketBigChangeDetector.isDcaAlt(m[2], m[0], m[1]);
            boolean mok = lv == MarketLevelChange.BIG_DOWN || alt;
            if (price) nPrice++;
            if (mok) nMkt++;
            if (price && mok) {
                Float p = p15.get(t);
                AIRejectFilter.FilterResult fr = gate.entryGate(new AiPredictionData(t, p == null ? 0f : p, 0f), null, false, false);
                boolean pass = fr.decision == AIRejectFilter.FilterDecision.PASS;
                nBoth++;
                if (sb.length() < 2000) sb.append(t).append(":").append(lv).append("/").append(alt).append("/gate=").append(pass).append(" ");
                if (pass && firstDue == null) firstDue = t;
            }
        }
        System.out.println("mode=" + mode + " sym=" + sym + " minutes_price_due=" + nPrice + " minutes_mkt_ok=" + nMkt + " both=" + nBoth
                + " FIRST_DCA=" + firstDue + " detail=" + sb);
    }
}
