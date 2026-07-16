package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.validation.preflight.ExpectedRanges;
import com.binance.chuyennd.ai_ml.validation.preflight.Severity;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.object.MarketDataObject;
import org.junit.Test;

import java.util.TreeMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * Unit-test A6 (count-by-cadence) — thuần logic, KHÔNG cần Aerospike/file. Bám khung
 * {@code PreflightFrameworkTest} (JUnit4, org.junit.Test/Assert).
 *
 * <p>Bắt đúng bug funding 15m ({@code BUGHUNT_WFO_20260713.md} BUG 4): dataset chỉ có mốc 15m thay vì
 * per-minute ⇒ coverage ~6.7% ⇒ A6 BLOCK.</p>
 */
public class A6CountByCadenceValidatorTest {

    private static final long DAY_MS = 24L * 60L * 60L * 1000L;
    private static final long MIN = 60_000L;
    private static final long START = 1_600_000_000_000L; // moc bat ky

    /** Dataset đủ mốc mỗi phút trong [START, START+spanMinutes*60000]. */
    private TreeMap<Long, MarketDataObject> perMinuteMarket(long spanMinutes) {
        TreeMap<Long, MarketDataObject> m = new TreeMap<>();
        for (long i = 0; i <= spanMinutes; i++) {
            m.put(START + i * MIN, new MarketDataObject(0f, 0f, 0f));
        }
        return m;
    }

    private TreeMap<Long, AiPredictionData> perMinutePred(long spanMinutes) {
        TreeMap<Long, AiPredictionData> m = new TreeMap<>();
        for (long i = 0; i <= spanMinutes; i++) {
            long ts = START + i * MIN;
            m.put(ts, new AiPredictionData(ts, 0f, 0f));
        }
        return m;
    }

    /** Selector chỉ có mốc 15m (bug thiếu forward-fill). */
    private TreeMap<Long, long[]> only15mFunding(long spanMinutes) {
        TreeMap<Long, long[]> m = new TreeMap<>();
        for (long i = 0; i <= spanMinutes; i += 15) {
            m.put(START + i * MIN, new long[]{0L});
        }
        return m;
    }

    /** Selector per-minute (SAU forward-fill) — đúng thiết kế. */
    private TreeMap<Long, long[]> perMinuteFunding(long spanMinutes) {
        TreeMap<Long, long[]> m = new TreeMap<>();
        for (long i = 0; i <= spanMinutes; i++) {
            m.put(START + i * MIN, new long[]{0L});
        }
        return m;
    }

    private A6CountByCadenceValidator validator() {
        return new A6CountByCadenceValidator();
    }

    // (a) Dataset đủ phút mọi loại -> PASS
    @Test
    public void datasetDuPhutThiPass() {
        long span = 1440; // 1 ngay du phut
        ValidationResult r = validator().evaluate(
                perMinuteMarket(span), perMinutePred(span), perMinuteFunding(span),
                new ExpectedRanges(),
                A6CountByCadenceValidator.DEFAULT_BLOCK_BELOW,
                A6CountByCadenceValidator.DEFAULT_WARN_BELOW);
        assertTrue("Du phut moi loai -> PASS. metrics=" + r.metrics(), r.passed());
    }

    // (b) Funding chỉ 15m -> coverage ~6.7% -> BLOCK (bắt đúng bug forward-fill)
    @Test
    public void fundingChi15mThiBlock() {
        long span = 1440;
        ValidationResult r = validator().evaluate(
                perMinuteMarket(span), perMinutePred(span), only15mFunding(span),
                new ExpectedRanges(),
                A6CountByCadenceValidator.DEFAULT_BLOCK_BELOW,
                A6CountByCadenceValidator.DEFAULT_WARN_BELOW);
        assertFalse("Funding 15m -> khong PASS", r.passed());
        assertTrue("Funding 15m -> BLOCK (severity)", r.isBlockingFailure());
        assertEquals(Severity.BLOCK, r.severity());

        // Xac nhan coverage funding rot ve ~1/15 (~0.0674) trong metrics.
        @SuppressWarnings("unchecked")
        java.util.Map<String, Object> fund = (java.util.Map<String, Object>) r.metrics().get("funding");
        double cov = ((Number) fund.get("coverage")).doubleValue();
        assertTrue("coverage funding ~1/15, do duoc=" + cov, cov < 0.10);
    }

    // (c) Thiếu 1 phần: coverage rơi vào dải WARN (0.95-0.99) -> WARN (khong BLOCK)
    @Test
    public void thieuMotPhanNhoThiWarn() {
        long span = 1440;
        // bo ~2% moc funding (giu ~98%) -> coverage ~0.98 -> WARN
        TreeMap<Long, long[]> funding = perMinuteFunding(span);
        int drop = (int) Math.round(funding.size() * 0.02); // bo 2%
        java.util.Iterator<Long> it = funding.keySet().iterator();
        int dropped = 0;
        java.util.List<Long> toRemove = new java.util.ArrayList<>();
        // bo rai deu de KHONG doi firstKey/lastKey (giu nguyen span)
        long first = funding.firstKey(), last = funding.lastKey();
        while (it.hasNext() && dropped < drop) {
            long k = it.next();
            if (k != first && k != last) {
                toRemove.add(k);
                dropped++;
            }
        }
        for (Long k : toRemove) funding.remove(k);

        ValidationResult r = validator().evaluate(
                perMinuteMarket(span), perMinutePred(span), funding,
                new ExpectedRanges(),
                A6CountByCadenceValidator.DEFAULT_BLOCK_BELOW,
                A6CountByCadenceValidator.DEFAULT_WARN_BELOW);
        assertFalse("Thieu ~2% -> khong PASS", r.passed());
        assertFalse("Thieu ~2% -> KHONG BLOCK (chi WARN)", r.isBlockingFailure());
        assertEquals(Severity.WARN, r.severity());
    }

    // (d) coverageOf: kiểm số học expected/actual/coverage trực tiếp
    @Test
    public void coverageOfTinhDungSoHoc() {
        long span = 150; // 151 moc/phut
        TreeMap<Long, long[]> fund15 = only15mFunding(span); // 0,15,...,150 -> 11 moc
        A6CountByCadenceValidator.TypeCoverage tc =
                A6CountByCadenceValidator.coverageOf("funding", fund15, MIN, new ExpectedRanges());
        assertEquals(151L, tc.expected); // (150*60000)/60000 + 1
        assertEquals(11L, tc.actual);    // 0..150 buoc 15 => 11 moc
        assertTrue("coverage ~11/151=0.073", tc.coverage < 0.10);
    }

    // (e) Range khai báo (ExpectedRanges) dài hơn span thực -> vẫn phát hiện thiếu (BLOCK)
    @Test
    public void rangeKhaiBaoDaiHonThiBatThieu() {
        long spanReal = 100;
        TreeMap<Long, long[]> fund = perMinuteFunding(spanReal); // 101 moc thuc
        ExpectedRanges er = new ExpectedRanges();
        // khai bao span 1 ngay (1440 phut) trong khi data chi 100 phut -> coverage ~7%
        er.putSource(new ExpectedRanges.SourceRange("funding", START, START + DAY_MS, 0));
        A6CountByCadenceValidator.TypeCoverage tc =
                A6CountByCadenceValidator.coverageOf("funding", fund, MIN, er);
        assertTrue("range khai bao dung", tc.rangeFromDeclared);
        assertEquals(1441L, tc.expected);
        assertEquals(101L, tc.actual);
        assertTrue("coverage thap -> se BLOCK", tc.coverage < 0.95);
    }
}
