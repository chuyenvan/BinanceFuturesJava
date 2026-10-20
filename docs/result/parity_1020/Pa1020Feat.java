import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager;
import com.binance.chuyennd.utils.StorageSnappy;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;

/** AUDIT-ONLY: doc predictionSymbol/<ts>.features (Map symbol->FundingMarketFeatures, ghi boi live 242) va xuat
 *  dung mang float[45] = FundingOnnxInferenceManager.extractFeaturesToArray (cung class jar live). Khong ghi gi khac. */
public class Pa1020Feat {
    public static void main(String[] a) throws Exception {
        java.lang.reflect.Field uf = sun.misc.Unsafe.class.getDeclaredField("theUnsafe");
        uf.setAccessible(true);
        sun.misc.Unsafe u = (sun.misc.Unsafe) uf.get(null);
        FundingOnnxInferenceManager m = (FundingOnnxInferenceManager) u.allocateInstance(FundingOnnxInferenceManager.class);
        int nf = 0, nr = 0;
        try (PrintWriter w = new PrintWriter(new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(a[0]))))) {
            w.print("ts,symbol");
            for (int i = 0; i < 45; i++) w.print(",f" + i);
            w.println();
            for (int k = 1; k < a.length; k++) {
                String fn = a[k];
                long ts = Long.parseLong(new File(fn).getName().replace(".features", ""));
                Object o = StorageSnappy.readObjectFromFile(fn);
                if (!(o instanceof Map)) {
                    System.err.println("BAD " + fn + " " + (o == null ? "null" : o.getClass()));
                    continue;
                }
                Map<?, ?> mp = (Map<?, ?>) o;
                List<String> keys = new ArrayList<>();
                for (Object kk : mp.keySet()) keys.add((String) kk);
                Collections.sort(keys);
                for (String s : keys) {
                    float[] x = m.extractFeaturesToArray((FundingMarketFeatures) mp.get(s));
                    StringBuilder sb = new StringBuilder();
                    sb.append(ts).append(',').append(s);
                    for (float v : x) sb.append(',').append(Float.toString(v));
                    w.println(sb);
                    nr++;
                }
                nf++;
            }
        }
        System.out.println("files=" + nf + " rows=" + nr);
    }
}
