package com.binance.chuyennd.ai_ml.wfo.framework;

import com.binance.chuyennd.ai_ml.wfo.framework.tasks.StrategyWfoTask;

import java.util.HashMap;
import java.util.Map;

/**
 * WFO FRAMEWORK — REGISTRY map type → WfoTask. Worker/coordinator tra task theo {@code WfoJob.type}.
 * Thêm loại WFO mới = đăng ký 1 dòng ở đây (KHÔNG sửa worker/coordinator).
 */
public final class WfoTaskRegistry {

    private static final Map<String, WfoTask> TASKS = new HashMap<>();

    static {
        register(new StrategyWfoTask());
        // register(new ModelWfoTask());  // sẽ thêm khi chuẩn hóa WFOGateRunner thành task
    }

    public static void register(WfoTask t) { TASKS.put(t.type(), t); }

    public static WfoTask get(String type) {
        WfoTask t = TASKS.get(type);
        if (t == null) throw new IllegalArgumentException("Khong co WfoTask cho type=" + type
                + " (da dang ky: " + TASKS.keySet() + ")");
        return t;
    }

    public static java.util.Set<String> types() { return TASKS.keySet(); }

    private WfoTaskRegistry() {}
}
