package com.binance.chuyennd.ai_ml.validation.preflight;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

/**
 * MASTER GATE — điều phối 19 {@link DataValidator}, chạy TRƯỚC mọi HPO/WFO.
 *
 * <p>Đây là "class tổng": các validator con đăng ký vào đây; gate chạy FULL-SCAN rẻ trước
 * ({@link CheckId#expensive()} == false), rồi RANDOM-SAMPLE đắt sau (§3), gom
 * {@link ValidationReport}. {@link #assertPassOrThrow} ném khi có BLOCK-fail để chặn WFO/HPO.</p>
 *
 * <p><b>Điểm gắn (DATA_VALIDATION_FRAMEWORK §3):</b> gọi {@link #assertPassOrThrow} ở đầu
 * {@code WfoCoordinator.init()/reset()} (trước {@code task.buildJobs()}) và đầu mỗi HPO run.
 * Fail → log SLF4J + throw → caller System.exit(1). KHÔNG cho chạy tiếp trên data hỏng.</p>
 *
 * <p>Validator con implement ở các task fan-out WS1; ở đây mới là khung + thứ tự chạy.
 * Đăng ký thật qua {@link #register} (hoặc một registry sau này) — skeleton chưa cắm sẵn class con
 * nào để tránh phụ thuộc code chưa tồn tại.</p>
 */
public final class PreflightGate {

    private static final Logger LOG = LoggerFactory.getLogger(PreflightGate.class);

    /** Bump khi đổi tập validator / ngưỡng → stamp cũ coi như hết hạn. */
    public static final String GATE_VERSION = "v1-20260711";

    private final List<DataValidator> validators = new ArrayList<>();

    /**
     * Đăng ký một validator.
     *
     * @param v validator con
     * @return this (chain được)
     */
    public PreflightGate register(DataValidator v) {
        validators.add(v);
        return this;
    }

    /** @return số validator đã đăng ký. */
    public int validatorCount() {
        return validators.size();
    }

    /**
     * Chạy toàn bộ check (cả FAST + SLOW).
     *
     * @param ctx ngữ cảnh chạy
     * @return report tổng hợp
     */
    public ValidationReport run(PreflightContext ctx) {
        return run(ctx, Tier.ALL);
    }

    /**
     * Chạy check theo tầng: rẻ trước, đắt sau. Không dừng giữa chừng khi 1 check fail —
     * gom hết để report đầy đủ; verdict do {@link ValidationReport#isPass()} quyết.
     *
     * @param ctx  ngữ cảnh chạy
     * @param tier {@link Tier#FAST} (chỉ check rẻ, gắn inline WFO) / {@link Tier#SLOW} (chỉ check đắt,
     *             chạy ngoài theo trigger) / {@link Tier#ALL}
     * @return report tổng hợp cho tầng đã chọn
     */
    public ValidationReport run(PreflightContext ctx, Tier tier) {
        ValidationReport report = new ValidationReport();
        List<DataValidator> ordered = new ArrayList<>();
        for (DataValidator v : validators) {
            if (!v.expensive() && tier != Tier.SLOW) {
                ordered.add(v);
            }
        }
        for (DataValidator v : validators) {
            if (v.expensive() && tier != Tier.FAST) {
                ordered.add(v);
            }
        }
        LOG.info("🔎 PREFLIGHT [{}]: chạy {} validator (rẻ trước, đắt sau)...", tier, ordered.size());
        for (DataValidator v : ordered) {
            try {
                ValidationResult r = v.validate(ctx);
                report.add(r);
                if (r.passed()) {
                    LOG.info("  ✅ {} PASS — {}", r.checkId(), r.message());
                } else if (r.isBlockingFailure()) {
                    LOG.error("  ⛔ {} BLOCK-FAIL — {} {}", r.checkId(), r.message(), r.metrics());
                } else {
                    LOG.warn("  ⚠️ {} WARN — {} {}", r.checkId(), r.message(), r.metrics());
                }
            } catch (Exception e) {
                report.addInfraError(v.id());
                LOG.error("  ❗ {} lỗi hạ tầng (chưa kiểm được) — NEEDS_HUMAN", v.id(), e);
            }
        }
        return report;
    }

    /**
     * Chạy gate và NÉM nếu không PASS — dùng làm cổng chặn HPO/WFO.
     *
     * @param ctx     ngữ cảnh
     * @param outPath nơi ghi report markdown
     * @throws IllegalStateException nếu có BLOCK-fail hoặc lỗi hạ tầng
     */
    public void assertPassOrThrow(PreflightContext ctx, String outPath) {
        ValidationReport report = run(ctx);
        report.writeTo(outPath);
        if (!report.isPass()) {
            throw new IllegalStateException("DATA PREFLIGHT FAIL: " + report.blockingFailures()
                    + " BLOCK-fail. Xem report: " + outPath + ". KHÔNG chạy HPO/WFO trên data hỏng.");
        }
        LOG.info("✅ DATA PREFLIGHT PASS ({} WARN) — cho phép HPO/WFO khởi động.", report.warnings());
    }

    /**
     * CỔNG WFO/HPO (Uni chốt 2026-07-11): luôn chạy tầng FAST inline; tầng SLOW chỉ đòi có
     * {@link ValidationStamp} hợp lệ cho dataset+env hiện tại. Dùng ở đầu {@code WfoCoordinator.init()/reset()}.
     *
     * <ul>
     *   <li>FAST BLOCK-fail → THROW (chặn tại chỗ).</li>
     *   <li>Stamp khớp fingerprint + env → OK (SLOW đã validate rồi, khỏi chạy lại đắt).</li>
     *   <li>Không stamp / md5 đổi / đổi env / đổi {@link #GATE_VERSION} → THROW, yêu cầu chạy full ngoài.</li>
     * </ul>
     *
     * @param ctx         ngữ cảnh
     * @param fingerprint md5 dataset hiện tại (từ manifest.txt WFO)
     * @param env         môi trường hiện tại ("oracle"/"kaggle"/...)
     * @param stampPath   nơi đọc stamp
     * @param reportPath  nơi ghi report tầng FAST
     * @throws IllegalStateException nếu FAST fail hoặc chưa có stamp SLOW hợp lệ
     */
    public void assertReadyForWfo(PreflightContext ctx, String fingerprint, String env,
                                  String stampPath, String reportPath) {
        ValidationReport fast = run(ctx, Tier.FAST);
        fast.writeTo(reportPath);
        if (!fast.isPass()) {
            throw new IllegalStateException("PREFLIGHT FAST FAIL: " + fast.blockingFailures()
                    + " BLOCK-fail. Xem " + reportPath + ". KHÔNG chạy WFO/HPO.");
        }
        ValidationStamp stamp = ValidationStamp.readFrom(stampPath);
        boolean stampOk = stamp != null
                && stamp.isValidFor(fingerprint, env)
                && GATE_VERSION.equals(stamp.gateVersion());
        if (!stampOk) {
            throw new IllegalStateException("Dataset CHƯA validate tầng SLOW cho (fingerprint=" + fingerprint
                    + ", env=" + env + ", gate=" + GATE_VERSION + "). Nguyên nhân: chưa từng validate / data đổi"
                    + " / đổi môi trường / đổi gate. → Chạy PreflightGate FULL ngoài trước (runFullAndStamp).");
        }
        LOG.info("✅ WFO READY: FAST PASS + stamp SLOW hợp lệ (env={}, fingerprint={}).", env, fingerprint);
    }

    /**
     * Chạy validate FULL (FAST+SLOW) ngoài WFO theo TRIGGER (run đầu / data mới / đổi môi trường / gen mới),
     * PASS thì đóng {@link ValidationStamp}. Đây là "chạy ngoài" cho check lâu.
     *
     * @param ctx         ngữ cảnh
     * @param fingerprint md5 dataset
     * @param env         môi trường
     * @param stampPath   nơi ghi stamp khi PASS
     * @param reportPath  nơi ghi report full
     * @return true nếu PASS (đã ghi stamp)
     */
    public boolean runFullAndStamp(PreflightContext ctx, String fingerprint, String env,
                                   String stampPath, String reportPath) {
        ValidationReport report = run(ctx, Tier.ALL);
        report.writeTo(reportPath);
        boolean pass = report.isPass();
        if (pass) {
            new ValidationStamp(fingerprint, env, true, System.currentTimeMillis(), GATE_VERSION)
                    .writeTo(stampPath);
            LOG.info("✅ VALIDATE FULL PASS — đã đóng stamp cho env={} ({} WARN).", env, report.warnings());
        } else {
            LOG.error("⛔ VALIDATE FULL FAIL: {} BLOCK-fail — KHÔNG đóng stamp. Xem {}.",
                    report.blockingFailures(), reportPath);
        }
        return pass;
    }

    /**
     * Chạy độc lập (chẩn đoán). CHƯA cắm validator con nào (skeleton) → in cảnh báo.
     *
     * @param args [reportPath]
     */
    public static void main(String[] args) {
        try {
            String outPath = args.length > 0 ? args[0] : "docs/reports/preflight.md";
            PreflightGate gate = new PreflightGate();
            // TODO WS1: gate.register(new A1PredCoverageValidator()) ... 19 validator.
            if (gate.validators.isEmpty()) {
                LOG.warn("PreflightGate skeleton: chưa đăng ký validator con nào (WS1 fan-out sẽ cắm). "
                        + "Chạy rỗng để verify khung.");
            }
            PreflightContext ctx = new PreflightContext.Builder().build();
            ValidationReport report = gate.run(ctx);
            report.writeTo(outPath);
            LOG.info("Preflight verdict: {}", report.isPass() ? "PASS" : "FAIL");
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("PreflightGate FAIL", e);
            System.exit(1);
        }
    }
}
