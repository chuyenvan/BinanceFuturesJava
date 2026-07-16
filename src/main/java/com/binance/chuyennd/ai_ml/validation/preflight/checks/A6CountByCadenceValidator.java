package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.ExpectedRanges;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import com.binance.chuyennd.object.MarketDataObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.NavigableMap;

/**
 * A6 — Chặn "cadence-mismatch": một loại dữ liệu backtest bị THIẾU NGẦM số record so với mật độ kỳ
 * vọng theo cadence (vd funding-selector chỉ còn mốc 15m thay vì per-minute → 1/15 dữ liệu → tần suất
 * backtest sập). Bắt đúng {@code docs/reports/BUGHUNT_WFO_20260713.md} BUG 4 (funding.bin mất
 * forward-fill 15p→phút, coverage ~6.7%).
 *
 * <p><b>Ý tưởng (Uni chốt):</b> "counter số phút sẽ dùng ra dữ liệu cần lấy = số cần validate". Với mỗi
 * loại: cho range {@code [start,end]} + cadence kỳ vọng (per-minute cho market/gate/funding SAU fix) →
 * {@code expected = (end-start)/cadenceMs + 1}. Đếm {@code actual} = số record trong dataset (TreeMap
 * size) thuộc range. Tính {@code coverage = actual/expected}.</p>
 *
 * <ul>
 *   <li>coverage &lt; {@link #DEFAULT_BLOCK_BELOW} (mặc định 0.95) ⇒ <b>BLOCK</b> — thiếu ngầm nghiêm trọng.</li>
 *   <li>{@link #DEFAULT_BLOCK_BELOW} ≤ coverage &lt; {@link #DEFAULT_WARN_BELOW} (0.95–0.99) ⇒ <b>WARN</b>.</li>
 *   <li>coverage ≥ {@link #DEFAULT_WARN_BELOW} ⇒ <b>PASS</b>.</li>
 * </ul>
 *
 * <p><b>Range mỗi loại:</b> ưu tiên {@link ExpectedRanges#source(String)} (pre-register); nếu chưa khai báo
 * thì dùng CHÍNH span của loại đó {@code [firstKey, lastKey]}. Đo mật độ trong span RIÊNG của loại — nên
 * KHÔNG dính false-positive khi selector kết thúc sớm hơn market (GIỚI HẠN 3): với 15m-only, trong span
 * riêng mật độ vẫn chỉ 1/15 per-minute ⇒ vẫn BLOCK; với per-minute thật ⇒ coverage ~1.0.</p>
 *
 * <p><b>Vì sao chỉ market/gate/funding-selector là loại nguy cơ:</b> engine tra bằng {@code map.get(time)}
 * KHỚP CHÍNH XÁC phút ({@code SimulatorMarketLevelTicker1MStopLoss} dòng 182/185/202/245). Funding-FEE
 * dùng {@code floorEntry} (carry-forward, tolerant cadence 8h) nên KHÔNG nằm trong A6. Ticker 1m là lưới
 * chủ nhịp (drive vòng lặp, guard {@code size>=1440} + D2) nên cũng không thuộc A6. Xem
 * {@code docs/reports/DATA_FLOW_AUDIT_20260713.md}.</p>
 *
 * <p><b>Nguồn dữ liệu:</b> đọc offline-bin qua {@link WfoDataset#load(String)} tại {@code ctx.wfoDataDir()}
 * (WFO luôn set {@code WFO_DATA_DIR}). Nếu {@code wfoDataDir} rỗng ⇒ PASS-skip (KHÔNG phải run offline-bin;
 * đường Aerospike dùng set {@code *_1m_v2} vốn đã per-minute) — tránh biến run khác thành NEEDS_HUMAN.</p>
 */
public final class A6CountByCadenceValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(A6CountByCadenceValidator.class);

    /** Cadence per-minute (ms) — market/gate/funding-selector sau forward-fill. */
    static final long MINUTE_MS = 60_000L;

    /** Ngưỡng BLOCK: coverage < 0.95 (bug funding 15m ~0.067 chắc chắn dính). Env {@code WFO_COUNT_BLOCK_BELOW}. */
    static final double DEFAULT_BLOCK_BELOW = 0.95;
    /** Ngưỡng WARN: 0.95 ≤ coverage < 0.99. Env {@code WFO_COUNT_WARN_BELOW}. */
    static final double DEFAULT_WARN_BELOW = 0.99;

    private static final int MAX_LIST = 20;

    /** Số đo coverage của MỘT loại dữ liệu. */
    static final class TypeCoverage {
        final String type;
        final long cadenceMs;
        final long start;
        final long end;
        final long expected;
        final long actual;
        final double coverage;
        final boolean rangeFromDeclared;

        TypeCoverage(String type, long cadenceMs, long start, long end,
                     long expected, long actual, double coverage, boolean rangeFromDeclared) {
            this.type = type;
            this.cadenceMs = cadenceMs;
            this.start = start;
            this.end = end;
            this.expected = expected;
            this.actual = actual;
            this.coverage = coverage;
            this.rangeFromDeclared = rangeFromDeclared;
        }

        Map<String, Object> toMetricMap() {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("cadenceMs", cadenceMs);
            m.put("start", start);
            m.put("end", end);
            m.put("expected", expected);
            m.put("actual", actual);
            m.put("coverage", round4(coverage));
            m.put("rangeFromDeclared", rangeFromDeclared);
            return m;
        }
    }

    @Override
    public CheckId id() {
        return CheckId.A6;
    }

    /**
     * Nạp offline-bin (nếu có {@code wfoDataDir}) rồi đo coverage 3 loại per-minute (market/gate/funding).
     *
     * @param ctx cần {@code wfoDataDir()} (offline-bin). Rỗng ⇒ PASS-skip.
     * @return BLOCK nếu loại nào coverage &lt; blockBelow; WARN nếu &lt; warnBelow; PASS kèm metrics số.
     * @throws Exception khi lỗi hạ tầng đọc dataset (I/O, md5 lệch) → gate xử NEEDS_HUMAN.
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) throws Exception {
        String dir = ctx.wfoDataDir();
        if (dir == null || dir.trim().isEmpty()) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("skipped", "khong co WFO_DATA_DIR (khong phai run offline-bin) — A6 chi ap cho offline-bin");
            LOG.warn("A6: bo qua (wfoDataDir rong).");
            return ValidationResult.pass(id(), "A6 skip: khong phai run offline-bin.", m);
        }

        double blockBelow = parseDouble(ctx.env("WFO_COUNT_BLOCK_BELOW"), DEFAULT_BLOCK_BELOW);
        double warnBelow = parseDouble(ctx.env("WFO_COUNT_WARN_BELOW"), DEFAULT_WARN_BELOW);

        WfoDataset ds = WfoDataset.load(dir);
        return evaluate(ds.market, ds.pred, ds.funding, ctx.expected(), blockBelow, warnBelow);
    }

    /**
     * Lõi kiểm (tách khỏi I/O để unit-test thuần logic): đo coverage market/gate/funding rồi tổng hợp verdict.
     *
     * @param market   TreeMap ts→MarketDataObject (per-minute)
     * @param pred     TreeMap ts→AiPredictionData gate (per-minute)
     * @param funding  TreeMap ts→long[] selector (per-minute SAU forward-fill)
     * @param expected khai báo range pre-register (nullable field bên trong)
     * @param blockBelow ngưỡng BLOCK
     * @param warnBelow  ngưỡng WARN
     * @return verdict tổng hợp (loại xấu nhất quyết định severity) kèm metrics từng loại.
     */
    ValidationResult evaluate(NavigableMap<Long, MarketDataObject> market,
                              NavigableMap<Long, AiPredictionData> pred,
                              NavigableMap<Long, long[]> funding,
                              ExpectedRanges expected,
                              double blockBelow, double warnBelow) {
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("blockBelow", blockBelow);
        metrics.put("warnBelow", warnBelow);

        List<String> blockReasons = new ArrayList<>();
        List<String> warnReasons = new ArrayList<>();

        // 3 loai tra bang .get(time) KHOP CHINH XAC phut -> deu ky vong per-minute.
        evalType("market", market, MINUTE_MS, expected, metrics, blockBelow, warnBelow, blockReasons, warnReasons);
        evalType("gate", pred, MINUTE_MS, expected, metrics, blockBelow, warnBelow, blockReasons, warnReasons);
        evalType("funding", funding, MINUTE_MS, expected, metrics, blockBelow, warnBelow, blockReasons, warnReasons);

        if (!blockReasons.isEmpty()) {
            return ValidationResult.fail(id(),
                    "Cadence-mismatch (thieu ngam): " + blockReasons, metrics);
        }
        if (!warnReasons.isEmpty()) {
            return ValidationResult.warn(id(),
                    "Coverage duoi nguong WARN (nhung >= BLOCK): " + warnReasons, metrics);
        }
        return ValidationResult.pass(id(),
                "Moi loai (market/gate/funding) coverage >= " + warnBelow + " theo cadence per-minute.", metrics);
    }

    /** Đo 1 loại + ghi metrics + phân loại BLOCK/WARN theo ngưỡng. */
    private void evalType(String type, NavigableMap<Long, ?> data, long cadenceMs, ExpectedRanges expected,
                          Map<String, Object> metrics, double blockBelow, double warnBelow,
                          List<String> blockReasons, List<String> warnReasons) {
        TypeCoverage tc = coverageOf(type, data, cadenceMs, expected);
        metrics.put(type, tc.toMetricMap());
        if (tc.coverage < blockBelow) {
            if (blockReasons.size() < MAX_LIST) {
                blockReasons.add(type + " coverage=" + round4(tc.coverage)
                        + " (actual=" + tc.actual + "/expected=" + tc.expected + ") < " + blockBelow);
            }
        } else if (tc.coverage < warnBelow) {
            if (warnReasons.size() < MAX_LIST) {
                warnReasons.add(type + " coverage=" + round4(tc.coverage)
                        + " (actual=" + tc.actual + "/expected=" + tc.expected + ") < " + warnBelow);
            }
        }
    }

    /**
     * Tính coverage của 1 loại: {@code expected=(end-start)/cadenceMs+1}, {@code actual=size trong [start,end]}.
     * Range = {@link ExpectedRanges#source(String)} nếu khai báo, else span riêng {@code [firstKey,lastKey]}.
     *
     * @param type     nhãn loại (dùng tra ExpectedRanges + log)
     * @param data     map ts→giá trị (chỉ đọc key)
     * @param cadenceMs khoảng cách kỳ vọng giữa 2 mốc liền kề
     * @param expected khai báo pre-register (nullable an toàn)
     * @return số đo coverage; map rỗng và không có range khai báo ⇒ expected=0, coverage=0 (⇒ BLOCK).
     */
    static TypeCoverage coverageOf(String type, NavigableMap<Long, ?> data, long cadenceMs, ExpectedRanges expected) {
        ExpectedRanges.SourceRange sr = (expected == null) ? null : expected.source(type);
        boolean declared = (sr != null);

        long start, end;
        if (declared) {
            start = sr.expectedStartMs;
            end = sr.expectedEndMs;
        } else if (data == null || data.isEmpty()) {
            // Khong co du lieu VA khong co range khai bao -> khong suy dien duoc; coi la thieu (coverage=0).
            LOG.warn("A6: loai {} map rong va khong co range khai bao -> coverage=0 (BLOCK).", type);
            return new TypeCoverage(type, cadenceMs, 0, 0, 0, 0, 0.0, false);
        } else {
            start = data.firstKey();
            end = data.lastKey();
        }

        long expectedCount = end > start ? (end - start) / cadenceMs + 1 : 1;
        long actual = (data == null || data.isEmpty()) ? 0 : countInRange(data, start, end);
        double coverage = expectedCount <= 0 ? 0.0 : (double) actual / (double) expectedCount;

        TypeCoverage tc = new TypeCoverage(type, cadenceMs, start, end, expectedCount, actual, coverage, declared);
        LOG.info("A6 {}: expected={} actual={} coverage={} range=[{}..{}] cadenceMs={} declared={}",
                type, expectedCount, actual, round4(coverage), start, end, cadenceMs, declared);
        return tc;
    }

    /** Số record có key trong [start,end] (inclusive). */
    private static long countInRange(NavigableMap<Long, ?> data, long start, long end) {
        if (end < start) return 0;
        return data.subMap(start, true, end, true).size();
    }

    private static double parseDouble(String v, double def) {
        if (v == null || v.trim().isEmpty()) return def;
        try {
            return Double.parseDouble(v.trim());
        } catch (NumberFormatException e) {
            LOG.warn("A6: khong parse duoc '{}' -> dung mac dinh {}", v, def);
            return def;
        }
    }

    private static double round4(double d) {
        return Math.round(d * 10_000.0) / 10_000.0;
    }
}
