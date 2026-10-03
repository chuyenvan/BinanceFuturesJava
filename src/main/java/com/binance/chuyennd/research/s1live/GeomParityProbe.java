package com.binance.chuyennd.research.s1live;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import com.aerospike.client.AerospikeClient;
import com.binance.chuyennd.tradecore.selector.GeomFeatProvider;
import com.binance.chuyennd.tradecore.selector.GeomFeatureLive;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * [GEOM-LIVE] Probe parity offline<->live (docs/audit/GEOM_LIVE_IMPL_20261003.md). CHI DOC, khong ghi Aerospike.
 * <pre>
 *  geom &lt;host&gt; &lt;port&gt; &lt;ns&gt; &lt;fromTsH&gt; &lt;toTsH&gt; &lt;out.csv&gt;
 *       replay {@link GeomFeatProvider} (CHINH lop live) tren kline_1m_opt cua cum chi dinh, moi gio dong
 *       fromTsH..toTsH -> csv ts_h,sym,9 GEOM (doi chieu research/analysis/s1_geom_feat.py qua geom_live_model.py parity)
 *  onnx &lt;model.onnx&gt; &lt;in.csv&gt; &lt;out.csv&gt;
 *       chay ONNX bang onnxruntime JAVA (cung runtime S1RankerLive) tren mau 18 cot (cot 1 = p_json cua XGB) -> so |d|
 * </pre>
 */
public final class GeomParityProbe {

    private static final Logger LOG = LoggerFactory.getLogger(GeomParityProbe.class);

    private GeomParityProbe() {
    }

    public static void main(String[] a) throws Exception {
        if (a.length >= 7 && "geom".equals(a[0])) {
            geom(a[1], Integer.parseInt(a[2]), a[3], Long.parseLong(a[4]), Long.parseLong(a[5]), a[6]);
        } else if (a.length >= 4 && "onnx".equals(a[0])) {
            onnx(a[1], a[2], a[3]);
        } else {
            LOG.error("usage: geom host port ns fromTsH toTsH out.csv | onnx model in.csv out.csv");
            System.exit(2);
        }
    }

    static void geom(String host, int port, String ns, long from, long to, String out) throws IOException {
        long H = GeomFeatProvider.H;
        if (from % H != 0 || to % H != 0 || to < from) throw new IllegalArgumentException("ts_h phai tron gio");
        AerospikeClient cli = new AerospikeClient(host, port);
        long t0 = System.currentTimeMillis();
        int rows = 0, hours = 0;
        try (Writer w = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(out), StandardCharsets.UTF_8))) {
            w.write("ts_h,sym," + String.join(",", GeomFeatureLive.FEATURE_ORDER) + "\n");
            GeomFeatProvider p = new GeomFeatProvider(GeomFeatProvider.aerospike(cli, ns, "kline_1m_opt"));
            for (long t = from; t <= to; t += H) {
                if (!p.refresh(t, t + 10 * GeomFeatProvider.MIN)) throw new IOException("refresh loi tai " + t);
                Map<String, double[]> f = p.features(t);
                if (f == null) throw new IOException("chua san sang tai " + t);
                for (Map.Entry<String, double[]> e : f.entrySet()) {
                    StringBuilder sb = new StringBuilder().append(t).append(',').append(e.getKey());
                    for (double v : e.getValue()) sb.append(',').append(v);
                    w.write(sb.append('\n').toString());
                    rows++;
                }
                hours++;
            }
        } finally {
            cli.close();
        }
        LOG.info("GEOM_PROBE xong {} gio, {} dong -> {} trong {} ms", hours, rows, out, System.currentTimeMillis() - t0);
    }

    static void onnx(String model, String in, String out) throws Exception {
        List<float[]> xs = new ArrayList<>();
        List<Double> ref = new ArrayList<>();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(new FileInputStream(in), StandardCharsets.UTF_8))) {
            String hdr = r.readLine();
            int nf = hdr.split(",").length - 1;
            String line;
            while ((line = r.readLine()) != null) {
                String[] p = line.split(",", -1);
                ref.add(Double.parseDouble(p[0]));
                float[] x = new float[nf];
                for (int j = 0; j < nf; j++) x[j] = p[j + 1].isEmpty() ? Float.NaN : Float.parseFloat(p[j + 1]);
                xs.add(x);
            }
        }
        OrtEnvironment env = OrtEnvironment.getEnvironment();
        double maxd = 0d;
        try (OrtSession s = env.createSession(model, new OrtSession.SessionOptions());
             OnnxTensor t = OnnxTensor.createTensor(env, xs.toArray(new float[0][]));
             OrtSession.Result res = s.run(Collections.singletonMap(s.getInputNames().iterator().next(), t));
             Writer w = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(out), StandardCharsets.UTF_8))) {
            float[][] o = (float[][]) res.get(0).getValue();
            w.write("p_json,p_onnx_java\n");
            for (int i = 0; i < o.length; i++) {
                maxd = Math.max(maxd, Math.abs(o[i][0] - ref.get(i)));
                w.write(ref.get(i) + "," + o[i][0] + "\n");
            }
        }
        LOG.info("ONNX_JAVA_PROBE n={} max|p_onnx_java - p_json|={} {}", xs.size(), maxd, maxd <= 1e-6 ? "PASS" : "FAIL");
    }
}
