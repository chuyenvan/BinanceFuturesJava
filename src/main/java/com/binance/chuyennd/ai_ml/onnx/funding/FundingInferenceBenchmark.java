package com.binance.chuyennd.ai_ml.onnx.funding;

import ai.onnxruntime.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.FloatBuffer;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/**
 * BENCHMARK CHI TIẾT bước INFERENCE của funding model (nút thắt ~68% thời gian gen).
 * KHÔNG đoán — đo thật rows/sec theo từng cấu hình để chọn đòn tối ưu (mục tiêu 10x):
 *   (1) số CPU core thật của máy (trần song song).
 *   (2) batch size: 64..8192 (model lớn 263M — batch lớn thường ăn throughput nhờ vectorize/cache).
 *   (3) intraOpNumThreads: 1..N_CORES (1 run dùng mấy thread).
 *   (4) CHẠY SONG SONG nhiều run() đồng thời (session ONNX thread-safe) — nếu 1 run không bão hòa core.
 *   (5) graph optimization level ALL vs default.
 *
 * In: rows/sec + ms/batch từng cấu hình + so với BASELINE hiện tại (batch256, intraOp4) => speedup.
 * Feature 21 chiều random (seed cố định) — chỉ đo TỐC ĐỘ, không phải độ chính xác.
 *
 * Chạy: java -cp ...jar com.binance.chuyennd.ai_ml.onnx.funding.FundingInferenceBenchmark
 */
public class FundingInferenceBenchmark {

    private static final Logger LOG = LoggerFactory.getLogger(FundingInferenceBenchmark.class);

    private static final String MODEL_PATH = "models_funding/Funding_Classifier_Final.onnx";
    private static final int FEAT = 21;
    private static final long BENCH_MS = 3000;       // mỗi cấu hình đo ~3s
    private static final int WARMUP_RUNS = 3;
    private static final int N_CORES = Runtime.getRuntime().availableProcessors();

    private static final OrtEnvironment ENV = OrtEnvironment.getEnvironment();
    private static String INPUT_NAME = "X";

    public static void main(String[] args) {
        try { new FundingInferenceBenchmark().run(); }
        catch (Exception e) { LOG.error("Benchmark error", e); }
        System.exit(0);
    }

    public void run() throws Exception {
        File f = new File(MODEL_PATH);
        LOG.info("================ FUNDING INFERENCE BENCHMARK ================");
        LOG.info("CPU cores (Runtime.availableProcessors) = {}", N_CORES);
        LOG.info("Model: {} | size = {} MB | exists={}", f.getAbsolutePath(),
                f.exists() ? f.length() / (1024 * 1024) : -1, f.exists());
        if (!f.exists()) { LOG.error("⛔ Không thấy model."); return; }

        // ===== Thông tin I/O model =====
        try (OrtSession.SessionOptions o = new OrtSession.SessionOptions();
             OrtSession s = ENV.createSession(MODEL_PATH, o)) {
            Map<String, NodeInfo> in = s.getInputInfo();
            if (!in.isEmpty()) INPUT_NAME = in.keySet().iterator().next();
            LOG.info("Input: {} | Outputs: {}", in.keySet(), s.getOutputInfo().keySet());
        }

        // ===== BASELINE hiện tại: batch=256, intraOp=4, opt mặc định =====
        double baseline;
        try (OrtSession s = build(Math.min(4, N_CORES), 1, false)) {
            baseline = benchSeq(s, 256);
            LOG.info("\n🔹 BASELINE (batch=256, intraOp={}, opt=default) = {} rows/s", Math.min(4, N_CORES), fmt(baseline));
        }

        // ===== (A) intraOp × batch (1 luồng phát run tuần tự) =====
        LOG.info("\n================ (A) intraOp × batch — rows/s (1 luong) ================");
        int[] intraOps = uniq(new int[]{1, 2, 4, N_CORES});
        int[] batches = {256, 512, 1024, 2048, 4096, 8192};
        LOG.info(String.format("%-10s", "intraOp\\batch") + header(batches));
        double best = baseline; String bestCfg = "baseline";
        for (int io : intraOps) {
            StringBuilder row = new StringBuilder(String.format("%-10d", io));
            try (OrtSession s = build(io, 1, false)) {
                for (int b : batches) {
                    double rps = benchSeq(s, b);
                    row.append(String.format("%12s", fmt(rps)));
                    if (rps > best) { best = rps; bestCfg = "seq intraOp=" + io + " batch=" + b; }
                }
            }
            LOG.info(row.toString());
        }

        // ===== (B) CHẠY SONG SONG nhiều run() đồng thời =====
        LOG.info("\n================ (B) song song T run() — rows/s (session intraOp thap) ================");
        int[] intraForConc = uniq(new int[]{1, 2});
        int[] threadsArr = uniq(new int[]{1, 2, 4, N_CORES, 2 * N_CORES});
        for (int io : intraForConc) {
            try (OrtSession s = build(io, N_CORES, false)) {
                StringBuilder row = new StringBuilder(String.format("intraOp=%-2d | T:", io));
                for (int t : threadsArr) {
                    double rps = benchConcurrent(s, 512, t);
                    row.append(String.format("  T%d=%s", t, fmt(rps)));
                    if (rps > best) { best = rps; bestCfg = "concurrent intraOp=" + io + " threads=" + t + " batch=512"; }
                }
                LOG.info(row.toString());
            }
        }

        // ===== (C) optimization level ALL =====
        LOG.info("\n================ (C) graph opt ALL (batch=2048, intraOp={}) ================", Math.min(4, N_CORES));
        try (OrtSession s = build(Math.min(4, N_CORES), 1, true)) {
            double rps = benchSeq(s, 2048);
            LOG.info("opt=ALL_OPT batch=2048 = {} rows/s", fmt(rps));
            if (rps > best) { best = rps; bestCfg = "opt=ALL intraOp=" + Math.min(4, N_CORES) + " batch=2048"; }
        }

        // ===== KẾT =====
        double rowsPerDay = 500.0 * 1440;   // ~500 symbol × 1440 phút
        LOG.info("\n📌 KẾT QUẢ:");
        LOG.info("   BASELINE = {} rows/s  (~{}s infer/ngay cho {} rows)", fmt(baseline),
                f1(rowsPerDay / Math.max(baseline, 1)), (long) rowsPerDay);
        LOG.info("   TỐT NHẤT = {} rows/s  [{}]  (~{}s infer/ngay)", fmt(best), bestCfg,
                f1(rowsPerDay / Math.max(best, 1)));
        LOG.info("   => SPEEDUP = {}x. {}", f1(best / Math.max(baseline, 1)),
                (best / Math.max(baseline, 1) >= 10) ? "ĐẠT >=10x ✅" :
                        "CHƯA tới 10x bằng riêng infer — cần thêm: async write (~21%) + extract (~10%), và/hoặc model nhẹ hơn.");
        LOG.info("   (Áp config tốt nhất vào FundingOnnxInferenceManager + GenerateFundingPredictionsTool.)");
    }

    private static OrtSession build(int intraOp, int interOp, boolean optAll) throws OrtException {
        OrtSession.SessionOptions o = new OrtSession.SessionOptions();
        o.addConfigEntry("session.disable_cpu_mem_arena", "1");
        o.setIntraOpNumThreads(intraOp);
        o.setInterOpNumThreads(interOp);
        if (optAll) o.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
        return ENV.createSession(MODEL_PATH, o);
    }

    /** rows/sec khi 1 luồng phát run() tuần tự, batch=b, đo trong ~BENCH_MS. */
    private double benchSeq(OrtSession s, int b) throws OrtException {
        float[] data = randomData(b);
        for (int i = 0; i < WARMUP_RUNS; i++) runOnce(s, data, b);
        long rows = 0, t0 = System.nanoTime(), deadline = t0 + BENCH_MS * 1_000_000L;
        while (System.nanoTime() < deadline) { runOnce(s, data, b); rows += b; }
        double sec = (System.nanoTime() - t0) / 1e9;
        return rows / sec;
    }

    /** rows/sec tổng khi T luồng cùng gọi run() đồng thời (session ONNX thread-safe), batch=b. */
    private double benchConcurrent(OrtSession s, int b, int threads) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        AtomicLong rows = new AtomicLong();
        long deadline = System.nanoTime() + BENCH_MS * 1_000_000L;
        List<Future<?>> fs = new ArrayList<>();
        long t0 = System.nanoTime();
        for (int i = 0; i < threads; i++) {
            fs.add(pool.submit(() -> {
                try {
                    float[] data = randomData(b);
                    runOnce(s, data, b);   // warmup riêng luồng
                    while (System.nanoTime() < deadline) { runOnce(s, data, b); rows.addAndGet(b); }
                } catch (Exception e) { LOG.error("conc run err: {}", e.getMessage()); }
            }));
        }
        for (Future<?> fut : fs) fut.get();
        pool.shutdown();
        double sec = (System.nanoTime() - t0) / 1e9;
        return rows.get() / sec;
    }

    private void runOnce(OrtSession s, float[] data, int b) throws OrtException {
        FloatBuffer buf = FloatBuffer.wrap(data);
        try (OnnxTensor t = OnnxTensor.createTensor(ENV, buf, new long[]{b, FEAT});
             OrtSession.Result r = s.run(Collections.singletonMap(INPUT_NAME, t))) {
            // chạm output để không bị tối ưu bỏ qua
            r.iterator().hasNext();
        }
    }

    private static float[] randomData(int b) {
        Random rnd = new Random(42L + b);   // cố định theo batch để tái lập
        float[] d = new float[b * FEAT];
        for (int i = 0; i < d.length; i++) d[i] = (float) (rnd.nextGaussian() * 0.1);  // feature ~ nhỏ
        return d;
    }

    private static int[] uniq(int[] a) {
        TreeSet<Integer> set = new TreeSet<>();
        for (int x : a) if (x >= 1) set.add(x);
        int[] out = new int[set.size()];
        int i = 0; for (int x : set) out[i++] = x;
        return out;
    }

    private static String header(int[] batches) {
        StringBuilder sb = new StringBuilder();
        for (int b : batches) sb.append(String.format("%12s", "b" + b));
        return sb.toString();
    }

    private static String fmt(double v) {
        if (v >= 1_000_000) return String.format(Locale.US, "%.2fM", v / 1e6);
        if (v >= 1000) return String.format(Locale.US, "%.1fk", v / 1e3);
        return String.format(Locale.US, "%.0f", v);
    }

    private static String f1(double v) { return String.format(Locale.US, "%.1f", v); }
}
