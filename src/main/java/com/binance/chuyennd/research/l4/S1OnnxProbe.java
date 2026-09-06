package com.binance.chuyennd.research.l4;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.Collections;

/** Chay ONNX S1 (cung file + cung runtime ma {@code S1RankerLive} dung) tren ma tran 9 feature. */
final class S1OnnxProbe {

    private static final Logger LOG = LoggerFactory.getLogger(S1OnnxProbe.class);

    private S1OnnxProbe() {
    }

    static float[] scoreAll(float[][] x9) {
        String p = Cfg.getOr("S1_MODEL_ONNX", "/home/ubuntu/s1_model/s1a2x1_cut20251001.onnx");
        try {
            OrtEnvironment env = OrtEnvironment.getEnvironment();
            OrtSession s = env.createSession(p, new OrtSession.SessionOptions());
            String in = s.getInputNames().iterator().next();
            float[] out = new float[x9.length];
            int bs = 20000;
            for (int i = 0; i < x9.length; i += bs) {
                int hi = Math.min(x9.length, i + bs);
                float[][] sub = Arrays.copyOfRange(x9, i, hi);
                try (OnnxTensor t = OnnxTensor.createTensor(env, sub);
                     OrtSession.Result r = s.run(Collections.singletonMap(in, t))) {
                    Object v = r.get(0).getValue();
                    if (v instanceof float[][]) {
                        float[][] m = (float[][]) v;
                        for (int k = 0; k < m.length; k++) out[i + k] = -m[k][0];   // score thap = tot
                    } else {
                        float[] m = (float[]) v;
                        for (int k = 0; k < m.length; k++) out[i + k] = -m[k];
                    }
                }
                LOG.info("[L4] S1 {}/{}", hi, x9.length);
            }
            s.close();
            return out;
        } catch (Throwable t) {
            LOG.error("[L4] S1 ONNX loi: {}", t.toString());
            return null;
        }
    }
}
