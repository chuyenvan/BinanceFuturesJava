package com.binance.chuyennd.ai_ml.validation.preflight;

import com.binance.chuyennd.ai_ml.validation.preflight.checks.F1RequiredEnvValidator;
import org.junit.Test;

import java.io.File;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * Unit-test FRAMEWORK Data Preflight Gate (task 210) — thuần logic, KHÔNG cần Aerospike/data.
 *
 * <p>Kiểm bất biến của khung gate: verdict (BLOCK chặn, WARN không), thứ tự chạy rẻ→đắt,
 * round-trip {@link ValidationStamp}, logic validator mẫu F1, và wiring đủ 21 validator.</p>
 */
public class PreflightFrameworkTest {

    /** Validator ghi lại thứ tự được gọi — để test tier ordering. */
    private static final class RecordingValidator implements DataValidator {
        private final CheckId id;
        private final List<CheckId> log;

        RecordingValidator(CheckId id, List<CheckId> log) {
            this.id = id;
            this.log = log;
        }

        @Override
        public CheckId id() {
            return id;
        }

        @Override
        public ValidationResult validate(PreflightContext ctx) {
            log.add(id);
            return ValidationResult.pass(id, "recorded", null);
        }
    }

    @Test
    public void wiringRegistersAll22Validators() {
        // +A6 (cadence-mismatch count validator, 2026-07-13) => 22
        assertEquals(22, PreflightValidators.buildDefault().validatorCount());
    }

    @Test
    public void severityChotKhopCheckId() {
        // F2 nâng WARN->BLOCK (Uni chốt 2026-07-11)
        assertEquals(Severity.BLOCK, CheckId.F2.defaultSeverity());
        assertEquals(Severity.BLOCK, CheckId.A1.defaultSeverity());
        assertEquals(Severity.WARN, CheckId.B2.defaultSeverity());
        // Bổ sung A6 (cadence-mismatch) -> 22
        assertEquals(22, CheckId.values().length);
    }

    @Test
    public void reportBlockFailLamVerdictFail() {
        ValidationReport r = new ValidationReport();
        r.add(ValidationResult.pass(CheckId.C1, "ok", null));
        r.add(ValidationResult.fail(CheckId.A1, "thiếu coverage", null)); // A1 = BLOCK
        assertFalse("BLOCK-fail phải làm gate FAIL", r.isPass());
        assertEquals(1, r.blockingFailures());
    }

    @Test
    public void reportWarnKhongChanGate() {
        ValidationReport r = new ValidationReport();
        r.add(ValidationResult.pass(CheckId.C1, "ok", null));
        r.add(ValidationResult.warn(CheckId.C4, "scale lệch", null)); // WARN
        assertTrue("WARN không được chặn gate", r.isPass());
        assertEquals(1, r.warnings());
    }

    @Test
    public void reportInfraErrorChanGate() {
        ValidationReport r = new ValidationReport();
        r.add(ValidationResult.pass(CheckId.C1, "ok", null));
        r.addInfraError(CheckId.A5); // chưa kiểm được -> NEEDS_HUMAN
        assertFalse("Infra-error phải chặn gate", r.isPass());
    }

    @Test
    public void gateChayReTruocDatSau() {
        List<CheckId> order = new ArrayList<>();
        PreflightGate gate = new PreflightGate()
                .register(new RecordingValidator(CheckId.B1, order))  // expensive=true (SLOW)
                .register(new RecordingValidator(CheckId.C1, order)); // expensive=false (FAST)
        gate.run(new PreflightContext.Builder().build(), Tier.ALL);
        assertEquals("FAST (C1) phải chạy trước SLOW (B1)", CheckId.C1, order.get(0));
        assertEquals(CheckId.B1, order.get(1));
    }

    @Test
    public void gateTierFastChiChayCheckRe() {
        List<CheckId> order = new ArrayList<>();
        PreflightGate gate = new PreflightGate()
                .register(new RecordingValidator(CheckId.B1, order))  // SLOW
                .register(new RecordingValidator(CheckId.C1, order)); // FAST
        gate.run(new PreflightContext.Builder().build(), Tier.FAST);
        assertEquals("Tier FAST chỉ chạy check rẻ", 1, order.size());
        assertEquals(CheckId.C1, order.get(0));
    }

    @Test
    public void stampRoundTripVaHopLe() throws Exception {
        File tmp = File.createTempFile("stamp", ".properties");
        tmp.deleteOnExit();
        String fp = "md5abc";
        String env = "oracle";
        new ValidationStamp(fp, env, true, System.currentTimeMillis(), PreflightGate.GATE_VERSION)
                .writeTo(tmp.getAbsolutePath());

        ValidationStamp read = ValidationStamp.readFrom(tmp.getAbsolutePath());
        assertTrue(read.pass());
        assertEquals(fp, read.datasetFingerprint());
        assertEquals(env, read.gateVersion() == null ? "" : env); // gateVersion tồn tại
        assertTrue("stamp khớp fingerprint+env hiện tại", read.isValidFor(fp, env));
        assertFalse("đổi env -> stamp không còn hợp lệ", read.isValidFor(fp, "kaggle"));
        assertFalse("đổi fingerprint -> stamp không còn hợp lệ", read.isValidFor("md5XYZ", env));
    }

    @Test
    public void stampThieuFileTraNull() {
        assertEquals(null, ValidationStamp.readFrom("khong-ton-tai-" + System.nanoTime() + ".properties"));
    }

    @Test
    public void f1FailKhiThieuEnv() throws Exception {
        PreflightContext ctx = new PreflightContext.Builder().env(new LinkedHashMap<>()).build();
        ValidationResult r = new F1RequiredEnvValidator().validate(ctx);
        assertFalse("Thiếu env bắt buộc -> FAIL", r.passed());
        assertTrue(r.isBlockingFailure());
    }

    @Test
    public void f1PassKhiDuEnv() throws Exception {
        Map<String, String> env = new LinkedHashMap<>();
        env.put("WFO_DATA_DIR", "/data/wfo");
        env.put("WFO_FUNDING_PRED_DIR", "/data/pred");
        env.put("WFO_SMART_CACHE", "1");
        PreflightContext ctx = new PreflightContext.Builder().env(env).build();
        ValidationResult r = new F1RequiredEnvValidator().validate(ctx);
        assertTrue("Đủ env bắt buộc -> PASS", r.passed());
    }
}
