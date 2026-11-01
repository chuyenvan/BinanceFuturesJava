package com.binance.chuyennd.ai_ml.onnx.entry;

import org.junit.After;
import org.junit.Test;

import java.io.File;
import java.nio.file.Files;
import java.util.List;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/** [GATE_SEED_DUMP] docs/prereg/PREREG_PARITY_V12_DRY_ADDENDUM3.md: dump GRR1 dung moc + trace; key tat => khong ghi. */
public class GateSeedDumpTest {
    private static final long DAY = 86_400_000L;

    @After
    public void off() {
        GateRollingRatio.configureSeedForTest(null, Long.MAX_VALUE, null, Long.MAX_VALUE, Long.MIN_VALUE);
    }

    @Test
    public void dumpHasExactlyRecordsBeforeMarkWithinWindow() throws Exception {
        GateRollingRatio.configureForTest(0.5f, 30);
        File d = File.createTempFile("seed", ".bin"); d.delete();
        File t = File.createTempFile("trace", ".csv"); t.delete();
        long at = 40 * DAY;
        GateRollingRatio.configureSeedForTest(d.getPath(), at, t.getPath(), 39 * DAY, 41 * DAY);
        long[] ts = {0L, 5 * DAY, 10 * DAY + 1, 20 * DAY, 39 * DAY + 5, 40 * DAY - 1, 40 * DAY, 40 * DAY + 60_000L};
        for (int i = 0; i < ts.length; i++) {
            float r = 0.001f * (i + 1);
            GateRollingRatio.seedHook(ts[i], 0.2f, r, r);
            GateRollingRatio.addAndQuery(ts[i], r);
        }
        GateRollingRatio.closeTrace();
        assertTrue(d.exists());
        GateRatioPersist.Records rec = GateRatioPersist.load(d.getPath(), Long.MIN_VALUE);
        // cut = 40d - 30d = 10d => giu ts in [10d, 40d)
        assertArrayEquals(new long[]{10 * DAY + 1, 20 * DAY, 39 * DAY + 5, 40 * DAY - 1}, rec.ts);
        assertEquals(0.003f, rec.r[0], 0f);
        assertEquals(0.006f, rec.r[3], 0f);
        List<String> lines = Files.readAllLines(t.toPath());
        assertEquals(1 + 4, lines.size());   // header + 39d+5, 40d-1, 40d, 40d+1m
        assertEquals("ts,sp,p15,r", lines.get(0));
        d.delete(); t.delete();
    }

    @Test
    public void offWritesNothing() throws Exception {
        GateRollingRatio.configureForTest(0.5f, 30);
        GateRollingRatio.configureSeedForTest(null, Long.MAX_VALUE, null, Long.MAX_VALUE, Long.MIN_VALUE);
        File d = new File(System.getProperty("java.io.tmpdir"), "seed_off_never.bin"); d.delete();
        GateRollingRatio.addAndQuery(0L, 1f);
        assertFalse(d.exists());
    }

    @Test
    public void finalDumpWhenRunEndsBeforeMark() throws Exception {
        GateRollingRatio.configureForTest(0.5f, 30);
        File d = File.createTempFile("seedf", ".bin"); d.delete();
        GateRollingRatio.configureSeedForTest(d.getPath(), 100 * DAY, null, Long.MAX_VALUE, Long.MIN_VALUE);
        GateRollingRatio.addAndQuery(80 * DAY, 0.5f);
        GateRollingRatio.addAndQuery(99 * DAY, 0.7f);
        assertFalse(d.exists());
        GateRollingRatio.finalDump();
        GateRatioPersist.Records rec = GateRatioPersist.load(d.getPath(), Long.MIN_VALUE);
        assertArrayEquals(new long[]{80 * DAY, 99 * DAY}, rec.ts);
        GateRollingRatio.finalDump();   // idempotent
        d.delete();
    }
}
