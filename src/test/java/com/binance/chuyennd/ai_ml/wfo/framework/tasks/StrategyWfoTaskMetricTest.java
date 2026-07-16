package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.utils.Utils;
import org.json.JSONObject;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * BUG-FIX 2026-07-13 (tang metric/hygiene WFO):
 * <ul>
 *   <li>BUG 1 — WFE median CHI tinh tren window SUCCESS ({@link StrategyWfoTask#collectSuccessWfe}).</li>
 *   <li>GIOI HAN 3 — cap ngay OOS cuoi qua env WFO_MAX_OOS_DATE ({@link StrategyWfoTask#parseMaxOosDateMs}).</li>
 * </ul>
 * Test HAM THUAN (khong dung Aerospike/backtest I/O).
 */
public class StrategyWfoTaskMetricTest {

    private static JSONObject row(double wfe, String oosNote) {
        JSONObject r = new JSONObject();
        r.put("wfe", wfe);
        if (oosNote != null) r.put("oosNote", oosNote);   // null = mo phong result cu (chua co field)
        return r;
    }

    /** BUG 1: sentinel/disqualify KHONG duoc vao median; chi SUCCESS. */
    @Test
    public void collectSuccessWfeLocSuccessOnly() {
        List<JSONObject> rows = new ArrayList<>();
        rows.add(row(0.711, "SUCCESS"));
        rows.add(row(0.933, "SUCCESS"));
        rows.add(row(0.000, "ZERO_TRADES"));
        rows.add(row(0.010, "TOO_FEW_TRADES"));
        rows.add(row(1.790, "TOO_MUCH_CAPITAL_LOCK"));
        rows.add(row(-173.0, "BURN_ACCOUNT"));

        List<Double> wfes = StrategyWfoTask.collectSuccessWfe(rows);
        assertEquals("chi 2 window SUCCESS vao median", 2, wfes.size());
        assertTrue(wfes.contains(0.711));
        assertTrue(wfes.contains(0.933));
        // median 2 phan tu SUCCESS = (0.711+0.933)/2 = 0.822 (>= PASS_WFE 0.5), KHONG con ket ~0.010
        double median = StrategyWfoTask.median(wfes);
        assertEquals(0.822, median, 1e-9);
        assertTrue("median SUCCESS-only phai vuot nguong WFE", median >= StrategyWfoTask.PASS_WFE);
    }

    /** BUG 1: result cu khong co oosNote -> optString default SUCCESS -> van tinh (tuong thich nguoc). */
    @Test
    public void collectSuccessWfeTuongThichResultCu() {
        List<JSONObject> rows = new ArrayList<>();
        rows.add(row(0.40, null));   // khong co field oosNote
        rows.add(row(0.60, "SUCCESS"));
        List<Double> wfes = StrategyWfoTask.collectSuccessWfe(rows);
        assertEquals(2, wfes.size());
    }

    /** BUG 1: khong co window SUCCESS nao -> danh sach rong -> median=0 -> giu verdict FAIL an toan. */
    @Test
    public void collectSuccessWfeKhongCoSuccessThiRong() {
        List<JSONObject> rows = new ArrayList<>();
        rows.add(row(0.010, "TOO_FEW_TRADES"));
        rows.add(row(0.000, "ZERO_TRADES"));
        List<Double> wfes = StrategyWfoTask.collectSuccessWfe(rows);
        assertTrue(wfes.isEmpty());
        assertEquals(0.0, StrategyWfoTask.median(wfes), 1e-12);
    }

    /** GIOI HAN 3: env rong/null -> Long.MAX_VALUE (giu nguyen hanh vi, khong cap). */
    @Test
    public void parseMaxOosDateRongThiKhongCap() {
        assertEquals(Long.MAX_VALUE, StrategyWfoTask.parseMaxOosDateMs(null));
        assertEquals(Long.MAX_VALUE, StrategyWfoTask.parseMaxOosDateMs(""));
        assertEquals(Long.MAX_VALUE, StrategyWfoTask.parseMaxOosDateMs("  "));
    }

    /**
     * GIOI HAN 3: env KHONG parse duoc -> Long.MAX_VALUE (an toan, khong cap).
     * Luu y: Utils.sdfFile la SimpleDateFormat lenient => chuoi kieu "2025-12-01" van parse (khong throw),
     * nen chi test chuoi that su khong phai so (parse throw ParseException).
     */
    @Test
    public void parseMaxOosDateSaiDinhDangThiKhongCap() {
        assertEquals(Long.MAX_VALUE, StrategyWfoTask.parseMaxOosDateMs("linhtinh"));
        assertEquals(Long.MAX_VALUE, StrategyWfoTask.parseMaxOosDateMs("abcd-ef-gh"));
    }

    /** GIOI HAN 3: env yyyyMMdd hop le -> khop millis parse + 7h; window vuot mac bi loai. */
    @Test
    public void parseMaxOosDateHopLeVaLogicCap() throws Exception {
        long cap = StrategyWfoTask.parseMaxOosDateMs("20251201");
        long expected = Utils.sdfFile.parse("20251201").getTime() + 7 * Utils.TIME_HOUR;
        assertEquals(expected, cap);

        // window co oosEnd 2026-03-31 (vuot cap 2025-12) -> phai bi loai (oosEnd > cap)
        long oosEnd2026 = Utils.sdfFile.parse("20260331").getTime() + 7 * Utils.TIME_HOUR;
        assertTrue("oosEnd 2026 > cap 2025-12 -> loai", oosEnd2026 > cap);
        // window oosEnd 2025-09-01 (truoc cap) -> giu
        long oosEnd2025 = Utils.sdfFile.parse("20250901").getTime() + 7 * Utils.TIME_HOUR;
        assertTrue("oosEnd 2025-09 <= cap -> giu", oosEnd2025 <= cap);
    }
}
