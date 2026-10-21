package com.binance.chuyennd.ops;

import org.junit.Assume;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.io.FileWriter;

import static org.junit.Assert.*;

/** [V11D OPS] heartbeat: chi cham mtime file rong; tat => khong I/O. */
public class OpsHeartbeatTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void touchCreatesEmptyFileAndSetsMtime() throws Exception {
        File f = new File(tmp.getRoot(), "run/sub/heartbeat");   // thu muc cha chua co
        long t0 = 1_792_000_000_000L;
        assertTrue(OpsHeartbeat.touch(f, t0));
        assertTrue(f.exists());
        assertEquals(0L, f.length());
        assertTrue(Math.abs(f.lastModified() - t0) < 1000L);
        long t1 = t0 + 60_000L;
        assertTrue(OpsHeartbeat.touch(f, t1));
        assertEquals("van rong sau lan 2", 0L, f.length());
        assertTrue(Math.abs(f.lastModified() - t1) < 1000L);
    }

    @Test
    public void touchDoesNotTruncateOrWriteExistingContent() throws Exception {
        File f = tmp.newFile("hb");
        try (FileWriter w = new FileWriter(f)) {
            w.write("x");
        }
        assertTrue(OpsHeartbeat.touch(f, 1_792_000_060_000L));
        assertEquals(1L, f.length());
    }

    @Test
    public void touchFailsQuietly() throws Exception {
        File notDir = tmp.newFile("plainfile");
        File f = new File(notDir, "heartbeat");   // cha la file thuong => khong tao duoc
        assertFalse(OpsHeartbeat.touch(f, 1_792_000_000_000L));
    }

    /** Env khong dat => tat; beat() khong tao file mac dinh. */
    @Test
    public void offByDefaultNoIo() {
        Assume.assumeTrue(System.getenv(OpsConfig.KEY_HEARTBEAT) == null);
        assertFalse(OpsHeartbeat.on());
        File def = OpsHeartbeat.file();
        boolean existed = def.exists();
        long m0 = existed ? def.lastModified() : -1L;
        OpsHeartbeat.beat(System.currentTimeMillis());
        assertEquals(existed, def.exists());
        if (existed) assertEquals(m0, def.lastModified());
    }
}
