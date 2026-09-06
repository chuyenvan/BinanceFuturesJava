package com.binance.chuyennd.tradecore.selector;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;

/**
 * THANG GIA TRI cua C3 tren duong LIVE — {@code net015} fold cutoff {@code 20251001}.
 *
 * <p>Dung DUNG mot bo 45 feature ma {@code Funding_Classifier_Final.onnx} live dang an
 * ({@code FundingOnnxInferenceManager.extractFeaturesToArray}); lop nay chi doi PHIEN ONNX.
 * KHONG tinh lai feature => khong them mot phep tinh feature nao vao vong nong.
 *
 * <p>Output ONNX: {@code TreeEnsembleClassifier} -> {@code probabilities [N,2]}.
 * <b>{@code P(win) = probabilities[:,1]}</b> (lop 1 = {@code retEnd_4h > 0.015}).
 * Bins {@code predict_wf_*.bin} luu dung gia tri nay o {@code p0}; Java dao dau khi dung
 * ({@code symbolPred = 1 - P(win)}, xem {@link LiveBuildMap}).
 *
 * <p>CHI nap khi {@link LiveProfileC3#on()}. Hong model -> {@link #isReady()} false, caller
 * PHAI giu duong cu (KHONG doan gia tri).
 */
public final class Net015ValueLive {

    private static final Logger LOG = LoggerFactory.getLogger(Net015ValueLive.class);
    private static volatile Net015ValueLive INSTANCE;

    public static final int N_FEATURE = 45;

    private OrtEnvironment env;
    private OrtSession session;
    private String inputName;
    private int probIdx = -1;
    private boolean broken = false;

    private Net015ValueLive() {
        String path = Cfg.get("NET015_MODEL_ONNX");
        if (path == null || path.trim().isEmpty()) {
            path = "/home/ubuntu/g3x26/g015x26_f15_cut20251001.onnx";
        }
        try {
            env = OrtEnvironment.getEnvironment();
            session = env.createSession(path.trim(), new OrtSession.SessionOptions());
            inputName = session.getInputNames().iterator().next();
            int i = 0;
            for (String o : session.getOutputNames()) {
                if (o.toLowerCase().contains("prob")) probIdx = i;
                i++;
            }
            if (probIdx < 0) probIdx = session.getOutputNames().size() - 1;
            LOG.info("[MAP] nap model GIA TRI net015 {} input={} out={} probIdx={} nFeature={}",
                    path, inputName, session.getOutputNames(), probIdx, N_FEATURE);
        } catch (Throwable t) {
            broken = true;
            LOG.error("[MAP] KHONG nap duoc net015 ONNX {}: {} -> KHONG co thang gia tri C3",
                    path, t.toString());
        }
    }

    public static Net015ValueLive getInstance() {
        if (INSTANCE == null) {
            synchronized (Net015ValueLive.class) {
                if (INSTANCE == null) INSTANCE = new Net015ValueLive();
            }
        }
        return INSTANCE;
    }

    public boolean isReady() {
        return !broken;
    }

    /**
     * @param x ma tran {@code [N][45]} theo DUNG thu tu cua
     *          {@code FundingOnnxInferenceManager.extractFeaturesToArray}
     * @return {@code P(win)} cho tung dong, hoac null khi loi.
     */
    public synchronized float[] pwin(float[][] x) {
        if (broken || x == null || x.length == 0) return null;
        if (x[0].length != N_FEATURE) {
            LOG.error("[MAP] so feature = {} != {} -> bo qua", x[0].length, N_FEATURE);
            return null;
        }
        try (OnnxTensor t = OnnxTensor.createTensor(env, x);
             OrtSession.Result r = session.run(Collections.singletonMap(inputName, t))) {
            Object v = r.get(probIdx).getValue();
            if (v instanceof float[][]) {
                float[][] m = (float[][]) v;
                float[] o = new float[m.length];
                for (int i = 0; i < m.length; i++) o[i] = m[i][m[i].length - 1];   // lop 1 = win
                return o;
            }
            if (v instanceof java.util.List) {
                // ZipMap: List<Map<Long,Float>>
                java.util.List<?> l = (java.util.List<?>) v;
                float[] o = new float[l.size()];
                for (int i = 0; i < l.size(); i++) {
                    java.util.Map<?, ?> mp = (java.util.Map<?, ?>) l.get(i);
                    Object p1 = mp.get(1L);
                    if (p1 == null) p1 = mp.get(1);
                    o[i] = p1 == null ? Float.NaN : ((Number) p1).floatValue();
                }
                return o;
            }
            LOG.error("[MAP] kieu output ONNX la {} — chua ho tro", v.getClass());
            return null;
        } catch (Throwable e) {
            LOG.error("[MAP] ONNX run loi: {}", e.toString());
            return null;
        }
    }
}
