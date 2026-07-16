package com.binance.chuyennd.ai_ml.validation.preflight;

import com.binance.chuyennd.ai_ml.validation.preflight.checks.A1PredCoverageValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.A2RangeConsistencyValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.A3GhostTickerValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.A4FoldCountValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.A5SurvivorshipValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.A6CountByCadenceValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.B1LabelOosValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.B2ShuffleTestValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.B3EmbargoValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.B4CrossSectionalLeakValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.C1NanInfValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.C2PriceSanityValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.C3DuplicateValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.C4ScaleValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.D1FundingTzValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.D2TimeGapValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.D3IntrabarLookaheadValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.E1ManifestValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.E2Md5Validator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.E3CutoffValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.F1RequiredEnvValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.F2ConfigVersionValidator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Composition-root: đăng ký đủ 22 {@link DataValidator} (A1-A6, B1-B4, C1-C4, D1-D3, E1-E3, F1-F2)
 * vào một {@link PreflightGate}. Tách khỏi {@link PreflightGate} để gate giữ generic (không phụ thuộc
 * danh sách check cụ thể). Dùng ở hook WFO: {@code PreflightValidators.buildDefault().assertReadyForWfo(...)}.
 */
public final class PreflightValidators {

    private static final Logger LOG = LoggerFactory.getLogger(PreflightValidators.class);

    private PreflightValidators() {
    }

    /**
     * @return gate đã đăng ký đủ 22 validator (thứ tự rẻ→đắt do {@link PreflightGate} tự sắp khi chạy).
     */
    public static PreflightGate buildDefault() {
        return new PreflightGate()
                .register(new A1PredCoverageValidator())
                .register(new A2RangeConsistencyValidator())
                .register(new A3GhostTickerValidator())
                .register(new A4FoldCountValidator())
                .register(new A5SurvivorshipValidator())
                .register(new A6CountByCadenceValidator())
                .register(new B1LabelOosValidator())
                .register(new B2ShuffleTestValidator())
                .register(new B3EmbargoValidator())
                .register(new B4CrossSectionalLeakValidator())
                .register(new C1NanInfValidator())
                .register(new C2PriceSanityValidator())
                .register(new C3DuplicateValidator())
                .register(new C4ScaleValidator())
                .register(new D1FundingTzValidator())
                .register(new D2TimeGapValidator())
                .register(new D3IntrabarLookaheadValidator())
                .register(new E1ManifestValidator())
                .register(new E2Md5Validator())
                .register(new E3CutoffValidator())
                .register(new F1RequiredEnvValidator())
                .register(new F2ConfigVersionValidator());
    }

    /**
     * Smoke wiring: dựng gate mặc định, in số validator đã đăng ký (không chạy — cần môi trường thật).
     *
     * @param args không dùng
     */
    public static void main(String[] args) {
        try {
            PreflightGate gate = buildDefault();
            LOG.info("✅ PreflightValidators.buildDefault() đăng ký {} validator.", gate.validatorCount());
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("PreflightValidators wiring FAIL", e);
            System.exit(1);
        }
    }
}
