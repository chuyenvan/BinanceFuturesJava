#!/usr/bin/env python3
"""Ap patch R3-G3 MTF-OR vao worktree r3_wt (prereg b901016e). Key mac dinh TAT => duong cu nguyen ven."""
import logging, re
logging.basicConfig(level=logging.INFO)
W = "/home/ubuntu/claude_master/r3_wt/src/main/java/com/binance/chuyennd/"
def sub(path, old, new, cnt=1):
    s = open(W + path, encoding="utf-8").read()
    assert s.count(old) == cnt, (path, old[:60], s.count(old))
    open(W + path, "w", encoding="utf-8").write(s.replace(old, new))
    logging.info("patched %s", path)

G = "ai_ml/onnx/entry/GateRollingRatio.java"
sub(G, "    private static final GateRatioBuffer buffer = new GateRatioBuffer();\n",
"""    private static final GateRatioBuffer buffer = new GateRatioBuffer();

    // [R3-G3 MTF-OR 2026-11-10] docs/prereg/PREREG_R3_GATE_FAMILY.md (b901016e) §2 G3: khung 1' (p15 diem) + khung W'
    //   (mean causal p15 tren [t-(W-1)', t], can >= MINCOV phut), MOI khung 1 buffer r rieng, pct_w = float32(1 - c*(1 - pct)).
    //   PASS <=> qua khung 1 HOAC qua khung W. Key SIM_GATE_MTF_W vang => TAT => duong cu nguyen ven (byte-identical).
    private static boolean mtfOn = false;
    private static int mtfW = 15;
    private static int mtfMinCov = 12;
    private static float mtfC = 0.5f;
    private static float mtfPct = 0f;
    private static final GateRatioBuffer bufferW = new GateRatioBuffer();
    private static java.util.NavigableMap<Long, com.binance.chuyennd.ai_ml.onnx.AiPredictionData> p15Src = null;
    private static long mtfPass1 = 0, mtfPassW = 0, mtfPassBoth = 0, mtfNoCov = 0;
""")
sub(G, """        LOG.warn("*** [GATE-RATIO] BAT: mode=ratio pct={} window={}d | warm-up 7d | quantile tren TY SO r ***",
                String.format("%.8f", pct), days);
""", """        LOG.warn("*** [GATE-RATIO] BAT: mode=ratio pct={} window={}d | warm-up 7d | quantile tren TY SO r ***",
                String.format("%.8f", pct), days);
        initMtf();
""")
sub(G, """    /** [NUP3-SLEEVE] q2 sleeve san sang""", """    /** [R3-G3] doc key MTF (chi khi gate ratio BAT). Sai cau hinh => fail-fast. */
    private static void initMtf() {
        String w = Cfg.get("SIM_GATE_MTF_W");
        if (w == null || w.trim().isEmpty()) {
            mtfOn = false;
            return;
        }
        mtfW = Integer.parseInt(w.trim());
        String c = Cfg.get("SIM_GATE_MTF_C");
        String mc = Cfg.get("SIM_GATE_MTF_MINCOV");
        if (c == null || c.trim().isEmpty() || mc == null || mc.trim().isEmpty()) {
            throw new IllegalStateException("[R3-G3] SIM_GATE_MTF_W dat nhung thieu SIM_GATE_MTF_C / SIM_GATE_MTF_MINCOV");
        }
        mtfC = Float.parseFloat(c.trim());
        mtfMinCov = Integer.parseInt(mc.trim());
        if (mtfW < 2 || mtfMinCov < 1 || mtfMinCov > mtfW || !(mtfC > 0f && mtfC <= 1f)) {
            throw new IllegalStateException("[R3-G3] tham so MTF sai W=" + mtfW + " minCov=" + mtfMinCov + " c=" + mtfC);
        }
        if (tier2On || Configs.SLEEVE_ENABLED) {
            throw new IllegalStateException("[R3-G3] MTF khong duoc bat cung TIER2/SLEEVE");
        }
        mtfPct = (float) (1.0 - (double) mtfC * (1.0 - (double) pct));
        mtfOn = true;
        LOG.warn("*** [R3-G3 MTF-OR] BAT: khung 1' + {}' (minCov {}), c={} => pct_w={} (gate pct {}) | buffer rieng moi khung ***",
                mtfW, mtfMinCov, mtfC, String.format("%.10f", mtfPct), String.format("%.10f", pct));
    }

    /** [R3-G3] MTF bat (gate ratio BAT + SIM_GATE_MTF_W). */
    public static boolean mtfOn() {
        return on && mtfOn;
    }

    /** [R3-G3] nguon p15 THEO PHUT cua sim (predictionMap) — bat buoc khi MTF bat. */
    public static void setP15Source(java.util.NavigableMap<Long, com.binance.chuyennd.ai_ml.onnx.AiPredictionData> src) {
        p15Src = src;
    }

    /** [R3-G3] mean causal p15 tren [ts-(W-1)', ts] (gom ts, theo thoi gian that); < minCov gia tri huu han => NaN. */
    static float smoothedP15(long ts) {
        if (p15Src == null) throw new IllegalStateException("[R3-G3] chua setP15Source");
        double s = 0.0;
        int n = 0;
        for (com.binance.chuyennd.ai_ml.onnx.AiPredictionData d
                : p15Src.subMap(ts - (long) (mtfW - 1) * 60_000L, true, ts, true).values()) {
            if (d == null || !Float.isFinite(d.predReturn15M)) continue;
            s += (double) d.predReturn15M;
            n++;
        }
        return n >= mtfMinCov ? (float) (s / n) : Float.NaN;
    }

    /**
     * [R3-G3] quyet dinh MTF-OR cho 1 ung vien PREDICT: nap r1 (p15 diem) vao buffer khung 1 va rW (p15 mean) vao buffer khung W
     * (chi khi du phu), moi buffer q rieng voi pct_w, causal theo gio nhu {@link GateRatioBuffer#addAndQuery}.
     * PASS <=> !(p15 < q1*fac*gs) || !(pW < qW*fac*gs).
     */
    public static synchronized boolean mtfPass(long ts, float p15, float sp) {
        float factor = Math.max(EntryGate.DYN_MIN, (sp / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
        float gs = EntryGate.GATE_REGIME_ADAPTIVE ? EntryGate.CURRENT_REGIME_SCALE : EntryGate.GATE_DYN_SCALE;
        if (!Float.isFinite(p15)) return false;
        float r1 = p15 / (factor * gs);
        float q1 = buffer.addAndQuery(ts, r1, mtfPct, days, Configs.MIN_MOMENTUM_15M);
        boolean pass1 = !(p15 < EntryGate.threshold(q1, sp));
        boolean passW = false;
        float pw = smoothedP15(ts);
        if (Float.isNaN(pw)) {
            mtfNoCov++;
        } else {
            float rw = pw / (factor * gs);
            float qw = bufferW.addAndQuery(ts, rw, mtfPct, days, Configs.MIN_MOMENTUM_15M);
            passW = !(pw < EntryGate.threshold(qw, sp));
        }
        if (pass1) mtfPass1++;
        if (passW) mtfPassW++;
        if (pass1 && passW) mtfPassBoth++;
        return pass1 || passW;
    }

    /** Chi dung cho unit test: bat MTF voi tham so cu the + reset buffer khung W va bo dem. */
    static void configureMtfForTest(int w, int minCov, float c) {
        mtfW = w;
        mtfMinCov = minCov;
        mtfC = c;
        mtfPct = (float) (1.0 - (double) c * (1.0 - (double) pct));
        mtfOn = true;
        bufferW.reset();
        mtfPass1 = mtfPassW = mtfPassBoth = mtfNoCov = 0;
    }

    static void disableMtfForTest() {
        mtfOn = false;
        p15Src = null;
    }

    static float mtfPctForTest() {
        return mtfPct;
    }

    /** [NUP3-SLEEVE] q2 sleeve san sang""")
sub(G, """        if (Configs.GATE_QUOTA_SKIP_WHEN_FULL) sb.append(" | skipFull=").append(predictSkipFull);
        return sb.toString();""", """        if (Configs.GATE_QUOTA_SKIP_WHEN_FULL) sb.append(" | skipFull=").append(predictSkipFull);
        if (mtfOn) {
            sb.append(String.format(" | MTF W=%d minCov=%d c=%.4f pct_w=%.10f pass1=%d passW=%d both=%d noCov=%d bufW=%d",
                    mtfW, mtfMinCov, mtfC, mtfPct, mtfPass1, mtfPassW, mtfPassBoth, mtfNoCov, bufferW.size()));
        }
        return sb.toString();""")

A = "ai_ml/onnx/entry/AIRejectFilter.java"
sub(A, """        float thrBase;
        if (LiveGateRollingRatio.isOn() && sp != null) {""", """        // [R3-G3 MTF-OR 2026-11-10] PREREG_R3_GATE_FAMILY b901016e: chi SIM (LIVE tat), chi nhanh PREDICT. Key TAT => bo qua.
        if (sp != null && !LiveGateRollingRatio.isOn() && GateRollingRatio.mtfOn()) {
            boolean ok = GateRollingRatio.mtfPass(prediction.timestamp, prediction.predReturn15M, sp);
            if (!ok) {
                mom15RejectCount.incrementAndGet();
                return new FilterResult(FilterDecision.REJECT,
                        String.format("BAD MOMENTUM: MTF-OR khong qua khung nao (p15 %.2f%%)", prediction.predReturn15M * 100));
            }
            if (predictSymbolTrade) GateRollingRatio.notePass(prediction.timestamp);
            return new FilterResult(FilterDecision.PASS,
                    String.format("PERFECT: MTF-OR 15M(%.2f%%)", prediction.predReturn15M * 100));
        }
        float thrBase;
        if (LiveGateRollingRatio.isOn() && sp != null) {""")

S = "research/SimulatorMarketLevelTicker1MStopLoss.java"
sub(S, """        com.binance.chuyennd.ai_ml.onnx.entry.GateRollingRatio.init();
        preprocessFundingData(time2SymbolPred);""", """        com.binance.chuyennd.ai_ml.onnx.entry.GateRollingRatio.init();
        // [R3-G3 MTF-OR] nguon p15 theo phut cho khung mean (chi khi key MTF bat; TAT => khong goi).
        if (com.binance.chuyennd.ai_ml.onnx.entry.GateRollingRatio.mtfOn()) {
            if (predictionMap == null) throw new IllegalStateException("[R3-G3] MTF bat nhung predictionMap null");
            com.binance.chuyennd.ai_ml.onnx.entry.GateRollingRatio.setP15Source(predictionMap);
        }
        preprocessFundingData(time2SymbolPred);""")
