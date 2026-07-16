package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoJob;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoJobStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;

/**
 * A4 — Chặn "fold WFO thiếu" (selector/candidate chỉ có 16 fold, thiếu 2026Q1 → 16 vs 17;
 * {@code DATA_VALIDATION_FRAMEWORK §5.10}).
 *
 * <p><b>Cơ chế:</b> đếm số fold/cửa sổ WFO thật sinh ra (job type {@code strategy_window} trong
 * {@code wfo_jobs}) và so với {@code ctx.expected().expectedFolds()} (mặc định 17). Lệch ⇒ FAIL (A4 = BLOCK).</p>
 *
 * <p><b>WRAP {@code WfoJobStore}:</b> đọc job qua {@link WfoJobStore#listAll()} (API chính tắc: đọc record chỉ
 * mục {@code __job_index__} + batch-get, KHÔNG scanAll — server 8 tắt legacy scan). Đếm fold PHÂN BIỆT theo
 * {@code job.id} (mỗi cửa sổ = 1 id {@code strat-wNN}) trong các job type {@code strategy_window}.</p>
 *
 * <p><b>Lưu ý client:</b> {@code WfoJobStore} tự quản client theo thiết kế của nó (state-store riêng qua env
 * {@code WFO_STATE_HOST}, hoặc 226 dùng chung) — đây là store TRẠNG THÁI job, KHÁC nguồn data 242/226 của
 * {@code ctx.client()}; vì vậy A4 dùng store thay vì {@code ctx.client()} (đúng ý "WRAP WfoJobStore").</p>
 *
 * <p><b>TODO-verify-trên-data-thật:</b> (1) xác nhận type job WFO strategy là {@code "strategy_window"}
 * (khớp {@code StrategyWfoTask.TYPE}); nếu chạy probe khác thì loại trừ — hiện lọc đúng type này; (2) "fold" =
 * 1 job cửa sổ ({@code strat-wNN}); nếu định nghĩa fold khác (vd fold model gate 14) thì thêm nguồn đếm; (3)
 * store rỗng (chưa init job) trả 0 fold ⇒ FAIL đúng-ngữ-nghĩa (WFO chưa dựng job) — KHÔNG coi là NEEDS_HUMAN.</p>
 */
public final class A4FoldCountValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(A4FoldCountValidator.class);

    private static final String STRATEGY_TYPE = "strategy_window";
    private static final String STRATEGY_ID_PREFIX = "strat-w";

    @Override
    public CheckId id() {
        return CheckId.A4;
    }

    /**
     * Đếm fold strategy_window trong wfo_jobs, so expectedFolds.
     *
     * @param ctx đọc {@code expected().expectedFolds()}
     * @return FAIL (BLOCK) nếu số fold != expectedFolds; PASS kèm metrics
     * @throws RuntimeException nếu store không đọc được (lỗi hạ tầng → NEEDS_HUMAN)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        int expectedFolds = ctx.expected().expectedFolds();

        WfoJobStore store = new WfoJobStore();
        List<WfoJob> all = store.listAll();

        TreeSet<String> folds = new TreeSet<>();
        int strategyJobs = 0;
        for (WfoJob j : all) {
            if (j == null) continue;
            boolean isStrategy = STRATEGY_TYPE.equals(j.type)
                    || (j.id != null && j.id.startsWith(STRATEGY_ID_PREFIX));
            if (isStrategy) {
                strategyJobs++;
                folds.add(j.id != null ? j.id : ("null-" + strategyJobs));
            }
        }
        int distinctFolds = folds.size();

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("totalJobs", all.size());
        metrics.put("strategyJobs", strategyJobs);
        metrics.put("distinctFolds", distinctFolds);
        metrics.put("expectedFolds", expectedFolds);
        metrics.put("folds", new ArrayList<>(folds.size() <= 40 ? folds : Collections.<String>emptyList()));

        if (distinctFolds != expectedFolds) {
            return ValidationResult.fail(id(),
                    "So fold WFO (" + distinctFolds + ") != expectedFolds (" + expectedFolds + ") — "
                            + (distinctFolds < expectedFolds ? "THIEU fold" : "THUA fold") + ".", metrics);
        }
        return ValidationResult.pass(id(),
                "Du " + distinctFolds + " fold WFO (= expectedFolds).", metrics);
    }
}
