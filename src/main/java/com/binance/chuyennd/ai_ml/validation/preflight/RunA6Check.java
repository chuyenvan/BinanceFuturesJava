package com.binance.chuyennd.ai_ml.validation.preflight;

import com.binance.chuyennd.ai_ml.validation.preflight.checks.A6CountByCadenceValidator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * A6-ONLY fail-fast runner (offline-bin, KHONG can Aerospike) - dung cho WFO worker TRUOC khi cay:
 * doc dataset WFO_DATA_DIR (market/pred/funding.bin + manifest, md5-verified) roi do coverage
 * per-minute theo cadence. BLOCK (coverage duoi 0.95) thi exit 3 (worker Kaggle/Oracle dung ngay,
 * khong cay vo ich tren dataset thieu ngam). PASS/WARN thi exit 0.
 *
 * <p>Vi sao tach khoi RunPreflightFull: full gate chay 22 validator, nhieu cai can Aerospike
 * source-set (A1, A5, B nhom, ...) - tren Kaggle KHONG co cac set do nen se FAIL nham. A6 chi doc
 * file bin cuc bo nen chay duoc o MOI node (Oracle/226/Kaggle) khong phu thuoc Aerospike.
 *
 * <p>Env: WFO_DATA_DIR (bat buoc), WFO_COUNT_BLOCK_BELOW (mac dinh 0.95),
 * WFO_COUNT_WARN_BELOW (mac dinh 0.99). Exit: 0=PASS/WARN, 3=BLOCK, 2=thieu WFO_DATA_DIR,
 * 1=loi ha tang (I/O, md5 lech).
 */
public final class RunA6Check {

    private static final Logger LOG = LoggerFactory.getLogger(RunA6Check.class);

    private RunA6Check() {
    }

    public static void main(String[] args) {
        String dir = System.getenv("WFO_DATA_DIR");
        try {
            if (dir == null || dir.trim().isEmpty()) {
                LOG.error("A6 fail-fast: thieu WFO_DATA_DIR - khong biet dataset nao de do coverage.");
                System.exit(2);
            }
            PreflightContext ctx = new PreflightContext.Builder()
                    .wfoDataDir(dir)
                    .env(System.getenv())
                    .expected(new ExpectedRanges())
                    .build();

            ValidationResult r = new A6CountByCadenceValidator().validate(ctx);
            LOG.info("A6 fail-fast result: {}", r);
            if (r.isBlockingFailure()) {
                LOG.error("A6 BLOCK: dataset {} coverage duoi nguong - DUNG, khong cay. metrics={}", dir, r.metrics());
                System.exit(3);
            }
            LOG.info("A6 OK ({}): dataset {} du coverage - cho phep chay worker.",
                    r.passed() ? "PASS" : "WARN", dir);
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("RunA6Check FAIL (ha tang)", e);
            System.exit(1);
        }
    }
}
