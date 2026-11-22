package com.binance.chuyennd.c3live.e2e.replay;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.DcaUtils;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import java.io.*;
import java.util.*;
import java.util.zip.GZIPInputStream;
/** ADD24 LUOT5 1c (DEV-B): voi MOI cum sim (cums.csv: cid,sym,first,t0,tEnd) va MOI phut t in (t0, tEnd) co ticker symbol:
 *  dieu kien thi truong DCA (getMarketStatus1M==BIG_DOWN [duong levelChange] hoac isDcaAlt), gate entryGate(sp=null) va gia cham bac
 *  shouldDcaGrid(first, close, lc) cho lc=1..4 (ham JAR stub). In: cid,t,mask(bit lc-1),bd(1/0),alt(1/0). Khong PnL.
 *  args: cums.csv market.csv(ts,down,up,down15) closes.csv.gz p15.csv(ts,p15) out.csv */
public final class Add24DcaAll {
    public static void main(String[] a) throws Exception {
        TreeMap<Long, float[]> mk = new TreeMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(a[1]))) {
            String ln = br.readLine();
            while ((ln = br.readLine()) != null) { String[] p = ln.split(","); mk.put(Long.parseLong(p[0]), new float[]{Float.parseFloat(p[1]), Float.parseFloat(p[2]), Float.parseFloat(p[3])}); }
        }
        HashMap<Long, Float> p15 = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(a[3]))) {
            String ln = br.readLine();
            while ((ln = br.readLine()) != null) { String[] p = ln.split(","); p15.put(Long.parseLong(p[0]), Float.parseFloat(p[1])); }
        }
        HashMap<String, TreeMap<Long, Float>> cl = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(new GZIPInputStream(new FileInputStream(a[2]))))) {
            String ln;
            while ((ln = br.readLine()) != null) { String[] p = ln.split(","); cl.computeIfAbsent(p[0], z -> new TreeMap<>()).put(Long.parseLong(p[1]), Float.parseFloat(p[3])); }
        }
        AIRejectFilter gate = new AIRejectFilter();
        HashMap<Long, Boolean> gp = new HashMap<>();
        int nc = 0, nout = 0, nmiss = 0;
        try (BufferedReader br = new BufferedReader(new FileReader(a[0])); PrintWriter pw = new PrintWriter(new FileWriter(a[4]))) {
            pw.println("cid,t,mask,bd,alt");
            String ln = br.readLine();
            while ((ln = br.readLine()) != null) {
                String[] p = ln.split(",");
                String cid = p[0], sym = p[1]; float first = Float.parseFloat(p[2]); long t0 = Long.parseLong(p[3]), te = Long.parseLong(p[4]);
                TreeMap<Long, Float> c = cl.get(sym); nc++;
                if (c == null) { nmiss++; continue; }
                for (long t = t0 + 60_000L; t < te; t += 60_000L) {
                    Float px = c.get(t); float[] m = mk.get(t);
                    if (px == null || m == null) continue;
                    boolean bd = MarketBigChangeDetector.getMarketStatus1M(m[0], m[1], m[2]) == MarketLevelChange.BIG_DOWN;
                    boolean alt = MarketBigChangeDetector.isDcaAlt(m[2], m[0], m[1]);
                    if (!bd && !alt) continue;
                    Boolean pass = gp.get(t);
                    if (pass == null) {
                        Float q = p15.get(t);
                        pass = gate.entryGate(new AiPredictionData(t, q == null ? 0f : q, 0f), null, false, false).decision == AIRejectFilter.FilterDecision.PASS;
                        gp.put(t, pass);
                    }
                    if (!pass) continue;
                    int mask = 0;
                    for (int lc = 1; lc <= 4; lc++) if (DcaUtils.shouldDcaGrid(first, px, lc)) mask |= 1 << (lc - 1);
                    if (mask == 0) continue;
                    pw.println(cid + "," + t + "," + mask + "," + (bd ? 1 : 0) + "," + (alt ? 1 : 0)); nout++;
                }
            }
        }
        System.out.println("ADD24DCAALL cums=" + nc + " no_closes=" + nmiss + " rows=" + nout);
    }
}
