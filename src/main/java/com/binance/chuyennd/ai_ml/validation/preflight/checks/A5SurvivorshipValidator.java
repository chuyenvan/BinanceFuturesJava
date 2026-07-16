package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.tradecore.Configs;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicLong;

/**
 * A5 — Chặn SURVIVORSHIP BIAS: coin delist/dead phải CÓ mặt trong universe lịch sử.
 *
 * <p>Cơ chế (cheap, full-scan set {@code symbol_lifecycle}): đếm coin DEAD + kiểm lifespan hợp lệ
 * (first &lt; delist). Nếu số DEAD &lt; {@code ExpectedRanges.expectedMinDeadCoins()} → nghi universe đã bị
 * lọc chỉ còn survivor (backtest sẽ tâng bốc vì không thấy coin đã chết). Bài học: task 001
 * survivorship-bac0, task 005/132.</p>
 *
 * <p>Đây là tầng RẺ (membership). Phần cross-check sâu "coin DEAD có feature/pred trong [first, delist]"
 * là sample-based, thuộc nhóm B/task riêng — KHÔNG gộp vào đây để giữ check rẻ chạy inline.</p>
 */
public final class A5SurvivorshipValidator implements DataValidator {

    private static final String SET_LIFECYCLE = "symbol_lifecycle";

    @Override
    public CheckId id() {
        return CheckId.A5;
    }

    /**
     * Quét {@code symbol_lifecycle}, đếm DEAD/LIVE + lifespan lỗi, so ngưỡng pre-register.
     *
     * @param ctx ngữ cảnh (cần {@link PreflightContext#client()} != null)
     * @return FAIL nếu số DEAD &lt; ngưỡng (nghi survivorship) hoặc có lifespan lỗi; PASS kèm metrics
     * @throws IllegalStateException nếu thiếu Aerospike client (lỗi hạ tầng → gate xử NEEDS_HUMAN)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        AerospikeClient client = ctx.client();
        if (client == null) {
            throw new IllegalStateException("A5: thiếu Aerospike client trong PreflightContext (226/Oracle).");
        }
        AtomicLong total = new AtomicLong();
        AtomicLong dead = new AtomicLong();
        AtomicLong live = new AtomicLong();
        List<String> invalidLifespan = new CopyOnWriteArrayList<>();

        ScanPolicy sp = new ScanPolicy();
        sp.concurrentNodes = true;
        client.scanAll(sp, Configs.AEROSPIKE_NAMESPACE, SET_LIFECYCLE, (key, rec) -> {
            total.incrementAndGet();
            String status = rec.getString("status");
            long first = rec.getLong("first");
            long delist = rec.getLong("delist");
            if ("DEAD".equals(status)) {
                dead.incrementAndGet();
                if (delist <= 0 || first <= 0 || first >= delist) {
                    if (invalidLifespan.size() < 50) {
                        invalidLifespan.add(rec.getString("sym") + "(first=" + first + ",delist=" + delist + ")");
                    }
                }
            } else if ("LIVE".equals(status)) {
                live.incrementAndGet();
            }
        }, "sym", "status", "first", "delist");

        int expectedMinDead = ctx.expected().expectedMinDeadCoins();
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("total", total.get());
        metrics.put("live", live.get());
        metrics.put("dead", dead.get());
        metrics.put("expectedMinDead", expectedMinDead);
        metrics.put("invalidLifespan", invalidLifespan.size());

        if (dead.get() < expectedMinDead) {
            return ValidationResult.fail(id(),
                    "Số coin DEAD (" + dead.get() + ") < ngưỡng (" + expectedMinDead
                            + ") — NGHI survivorship: universe thiếu coin đã chết.", metrics);
        }
        if (!invalidLifespan.isEmpty()) {
            return ValidationResult.fail(id(),
                    "Có " + invalidLifespan.size() + " coin DEAD lifespan lỗi (first>=delist): "
                            + Collections.unmodifiableList(invalidLifespan), metrics);
        }
        return ValidationResult.pass(id(),
                "Universe giữ " + dead.get() + " coin DEAD (>= " + expectedMinDead + "), lifespan hợp lệ.", metrics);
    }
}
