package com.binance.chuyennd.ai_ml.features.export.entry;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.nio.file.Files;

import static org.junit.Assert.*;

/** [V12 R4j A1 MIN-5] tran TONG dung luong thu muc feat/sel dump. */
public class LiveFeatureDumpCapR4jTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void totalCap() throws Exception {
        assertEquals(2048L, LiveFeatureDump.parseTotalMb("x"));
        assertEquals(2048L, LiveFeatureDump.parseTotalMb("-5"));
        assertEquals(0L, LiveFeatureDump.parseTotalMb("0"));
        assertFalse("0 = khong tran", LiveFeatureDump.overTotalCap(Long.MAX_VALUE, 0L));
        assertTrue(LiveFeatureDump.overTotalCap(100L, 100L));
        assertFalse(LiveFeatureDump.overTotalCap(99L, 100L));
        File d = tmp.newFolder("feat_dump");
        Files.write(new File(d, "a.csv.gz").toPath(), new byte[1000]);
        Files.write(new File(d, "b.csv.gz").toPath(), new byte[500]);
        assertEquals(1500L, LiveFeatureDump.dirBytes(d));
        assertEquals(0L, LiveFeatureDump.dirBytes(new File(d, "khong_co")));
        assertEquals("mac dinh 2 GB", 2048L * 1024L * 1024L, LiveFeatureDump.MAX_TOTAL_BYTES);
    }
}
