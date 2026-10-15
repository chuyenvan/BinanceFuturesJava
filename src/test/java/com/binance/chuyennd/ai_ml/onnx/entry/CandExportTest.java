package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.CandExport;
import org.junit.After;
import org.junit.Test;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * QUEUE_1015 P4 / T9-FIX: SIM_EXPORT_CANDIDATES.
 *
 * <p>Khang dinh: (1) mac dinh TAT; (2) bat len KHONG doi quyet dinh gate (side-channel chi doc);
 * (3) dinh dang dong xuat dung schema. Parity day du (md5 printDone {@code ad26fd55}) do kernel
 * Kaggle chung minh, khong o day.
 */
public class CandExportTest {

    private static final float SP = 0.1f;
    private static final long MIN = 60_000L;
    private final List<String> tmp = new ArrayList<>();

    @After
    public void tearDown() {
        CandExport.close();
        for (String p : tmp) {
            new File(p).delete();
        }
    }

    private static AiPredictionData pred(long ts, float p15) {
        return new AiPredictionData(ts, p15, 0f);
    }

    /** Chay cung mot chuoi tick tren filter MOI, tra ve chuoi quyet dinh+ly do. */
    private static List<String> runSeq() {
        AIRejectFilter f = new AIRejectFilter();
        List<String> out = new ArrayList<>();
        for (int i = 0; i < 60; i++) {
            long ts = i * MIN;
            float p15 = 0.0020f + i * 0.0001f;
            AIRejectFilter.FilterResult r = f.entryGate(pred(ts, p15), SP, true, false);
            out.add(r.decision + "|" + r.reason);
        }
        return out;
    }

    @Test
    public void keyDefaultIsOff() {
        assertFalse("SIM_EXPORT_CANDIDATES phai mac dinh TAT (ON=false)", CandExport.ON);
    }

    @Test
    public void onDoesNotChangeGateDecision() {
        GateRollingRatio.configureForTest(0.9f, 90);
        List<String> off = runSeq();
        GateRollingRatio.configureForTest(0.9f, 90);
        Path p = Path.of(System.getProperty("java.io.tmpdir"), "cand_export_test_" + System.nanoTime() + ".csv");
        tmp.add(p.toString());
        assertTrue("init phai thanh cong voi path hop le", CandExport.init(p.toString()));
        assertTrue(CandExport.ON);
        List<String> on = runSeq();
        assertEquals("quyet dinh gate phai Y HET khi ON vs OFF", off, on);
        assertEquals("ly do gate phai Y HET khi ON vs OFF", off, on);
        // side-channel phai duoc dien khi ON (chi doc; khong goi lai threshold => khong nap buffer).
        assertFalse("LAST_QT phai duoc dien", Float.isNaN(CandExport.LAST_QT));
        assertFalse("LAST_P15 phai duoc dien", Float.isNaN(CandExport.LAST_P15));
    }

    @Test
    public void rowSchemaIsStable() throws Exception {
        Path p = Path.of(System.getProperty("java.io.tmpdir"), "cand_export_row_" + System.nanoTime() + ".csv");
        tmp.add(p.toString());
        assertTrue(CandExport.init(p.toString()));
        CandExport.LAST_P15 = 0.0123f;
        CandExport.LAST_THR_BASE = 0.008f;
        CandExport.LAST_QT = 0.0099f;
        CandExport.LAST_PASS = true;
        CandExport.LAST_REASON = "PASS";
        CandExport.begin(1791472800000L, "BTCUSDT", 0.01f, 0.2f, 3, true, true, "PASS", true);
        CandExport.finish(true);
        CandExport.begin(1791472860000L, "ETHUSDT", -0.02f, 0.3f, 9, true, false, "MOM15 reject", true);
        CandExport.finish(false);
        CandExport.direct(1791472920000L, "SOLUSDT", 0.4f, 12, "ALREADY_OPEN");
        CandExport.close();

        List<String> lines = Files.readAllLines(p);
        assertEquals("ts,symbol,bar_ret,p15,thr_base,q_t,gate_pass,gate_reason,s1,rank,topk,entered", lines.get(0));
        assertEquals(4, lines.size());
        String[] c1 = lines.get(1).split(",", -1);
        assertEquals(12, c1.length);
        assertEquals("BTCUSDT", c1[1]);
        assertEquals("1", c1[6]);
        assertEquals("PASS", c1[7]);
        assertEquals("1", c1[11]);
        String[] c3 = lines.get(3).split(",", -1);
        assertEquals("ALREADY_OPEN", c3[7]);
        assertEquals("0", c3[11]);
    }
}
