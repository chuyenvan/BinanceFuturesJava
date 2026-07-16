package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * B2 — SHUFFLE-TEST (chẩn đoán feature dùng dữ liệu tương lai): xáo nhãn (permutation) → nếu model
 * vẫn còn "edge" thì edge đó là ARTIFACT của leakage, không phải tín hiệu thật. So precision/AUC
 * train vs OOS trên nhãn thật vs nhãn xáo (spec §2 nhóm B — mức WARN, cần người nhìn kết luận).
 *
 * <p><b>Vì sao WARN + khung:</b> shuffle-test ĐÚNG NGHĨA phải RETRAIN model với nhãn đã xáo rồi so
 * metric — việc này thuộc pipeline Python ({@code ml/training/}), KHÔNG làm inline trong preflight
 * Java (CORE: Python chỉ dùng để validate/compare). Do đó validator này KHÔNG tự chạy shuffle mà
 * KIỂM SỰ HIỆN DIỆN + đọc KẾT QUẢ của một lần shuffle-test đã chạy ngoài (artifact report). Thiếu
 * artifact → WARN "chưa chạy" (không chặn, nhưng ghi cờ để người theo dõi).</p>
 *
 * <p><b>TODO (Python compare — GAP):</b>
 * <ol>
 *   <li>Viết script {@code ml/training/shuffle_test_selector.py}: với mỗi fold, permute nhãn y trong
 *       tập train, retrain XGB (cùng params {@code gen_funding_wf_predictions.py}), dự đoán OOS, đo
 *       AUC/precision. Ghi report (JSON/CSV) gồm: {@code auc_real}, {@code auc_shuffled},
 *       {@code precision_real}, {@code precision_shuffled} mỗi fold + horizon.</li>
 *   <li>Đặt report tại {@code WFO_SHUFFLE_TEST_REPORT} (env) hoặc {@code <predDir>/shuffle_test_report.json}.</li>
 *   <li>Ở đây parse report: PASS nếu {@code auc_shuffled ≈ 0.5} (edge biến mất) trên mọi fold;
 *       WARN/FAIL nếu {@code auc_shuffled} còn cao (leak). Format report CHƯA chốt → TODO khi Python xong.</li>
 * </ol>
 * KHÔNG bịa số: khi chưa có report, chỉ báo trạng thái, không tự tuyên PASS.</p>
 */
public final class B2ShuffleTestValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(B2ShuffleTestValidator.class);

    /** Tên file report mặc định trong thư mục pred (nếu env không trỏ nơi khác). */
    private static final String DEFAULT_REPORT_NAME = "shuffle_test_report.json";

    /** Env trỏ tới report shuffle-test đã chạy ngoài (Python). */
    private static final String ENV_REPORT = "WFO_SHUFFLE_TEST_REPORT";

    @Override
    public CheckId id() {
        return CheckId.B2;
    }

    @Override
    public boolean expensive() {
        return true;
    }

    /**
     * Kiểm sự hiện diện của report shuffle-test; nếu chưa có → WARN (cần chạy Python ngoài).
     *
     * @param ctx ngữ cảnh (đọc env {@link #ENV_REPORT}; fallback {@code fundingPredDir/shuffle_test_report.json})
     * @return WARN nếu chưa có report; WARN kèm TODO nếu có report (parse chưa cài — format chờ chốt)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        Map<String, Object> metrics = new LinkedHashMap<>();
        String reportPath = ctx.env(ENV_REPORT);
        File report = null;
        if (reportPath != null && !reportPath.trim().isEmpty()) {
            report = new File(reportPath.trim());
        } else if (ctx.fundingPredDir() != null && !ctx.fundingPredDir().trim().isEmpty()) {
            report = new File(ctx.fundingPredDir(), DEFAULT_REPORT_NAME);
        }
        boolean found = report != null && report.isFile();
        metrics.put("reportPath", report == null ? "(none)" : report.getAbsolutePath());
        metrics.put("reportFound", found);

        if (!found) {
            LOG.warn("B2: chưa có report shuffle-test ({}). Cần chạy ml/training/shuffle_test_selector.py (GAP).",
                    metrics.get("reportPath"));
            return ValidationResult.warn(id(),
                    "Shuffle-test CHƯA chạy (thiếu report). Chẩn đoán leak feature cần retrain nhãn-xáo "
                            + "bằng Python — xem TODO trong Javadoc. Không chặn gate nhưng cần người chạy.", metrics);
        }
        // TODO: parse report (auc_real vs auc_shuffled mỗi fold) khi format Python chốt.
        metrics.put("parsed", false);
        metrics.put("todo", "parse auc_real/auc_shuffled — format report chờ chốt (Python GAP)");
        LOG.warn("B2: tìm thấy report {} nhưng parser CHƯA cài (format chờ chốt).", metrics.get("reportPath"));
        return ValidationResult.warn(id(),
                "Tìm thấy report shuffle-test nhưng parser chưa cài (format chờ chốt) — cần người xác nhận "
                        + "edge biến mất khi xáo nhãn.", metrics);
    }
}
