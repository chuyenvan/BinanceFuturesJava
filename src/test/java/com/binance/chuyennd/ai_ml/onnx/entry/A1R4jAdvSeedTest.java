package com.binance.chuyennd.ai_ml.onnx.entry;

import org.junit.After;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

import static org.junit.Assert.*;

/** [A1 R4j ADV] KHONG commit. File danh dau .seeded: mat / seed moi. */
public class A1R4jAdvSeedTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();
    static final long DAY = 86_400_000L, H = 3_600_000L;
    static final long NOW = 1_793_400_000_000L;

    @After
    public void tearDown() {
        LiveGateRollingRatio.resetForTest();
    }

    File seed(long from, long to, float base) throws Exception {
        int n = (int) ((to - from) / H) + 1;
        long[] ts = new long[n];
        float[] r = new float[n];
        for (int i = 0; i < n; i++) {
            ts[i] = from + i * H;
            r[i] = base + 0.001f * (i % 97);
        }
        File f = tmp.newFile();
        GateRatioPersist.writeFresh(f.getPath(), ts, r);
        return f;
    }

    void start(File persist) {
        LiveGateRollingRatio.configureForTest(0.999950829f, 90);
        LiveGateRollingRatio.setPersistFileForTest(persist.getPath());
    }

    /** Marker mat (vd don thu muc run/) + restart 48 h sau: KHONG exit, CHAN vao lenh + KHAN (fail-closed). */
    @Test
    public void markerLostAfterLag_blocksNotExit() throws Exception {
        File s = seed(NOW - 91 * DAY, NOW - 2 * H, 0f);
        String md5 = LiveGateRollingRatio.md5Hex(s);
        File persist = new File(tmp.getRoot(), "gate_ratio_live.bin");
        start(persist);
        assertFalse(LiveGateRollingRatio.initSeedBranch(s.getPath(), md5, 24, NOW));
        assertTrue(LiveGateRollingRatio.seedMarker().delete());
        List<String> al = new ArrayList<>();
        Consumer<String> o = LiveGateRollingRatio.seedAlert;
        LiveGateRollingRatio.seedAlert = al::add;
        try {
            start(persist);
            assertTrue(LiveGateRollingRatio.initSeedBranch(s.getPath(), md5, 24, NOW + 2 * DAY));
            assertTrue(LiveGateRollingRatio.isSeedBlocked());
            assertEquals(1, al.size());
            assertTrue("buffer van nap persist", LiveGateRollingRatio.bufferSizeForTest() > 0);
        } finally {
            LiveGateRollingRatio.seedAlert = o;
        }
    }

    /** Owner dat SEED MOI (md5 khac) de seed lai: marker cu => seed moi bi bo qua IM (chi WARN log), khong chan, khong KHAN. */
    @Test
    public void newSeedWithOldMarkerMustNotBeSilentlyIgnored() throws Exception {
        File s1 = seed(NOW - 91 * DAY, NOW - 2 * H, 0f);
        File persist = new File(tmp.getRoot(), "gate_ratio_live.bin");
        start(persist);
        assertFalse(LiveGateRollingRatio.initSeedBranch(s1.getPath(), LiveGateRollingRatio.md5Hex(s1), 24, NOW));
        File s2 = seed(NOW - 91 * DAY + DAY, NOW + DAY - H, 5f);   // seed moi, gia tri khac
        String md52 = LiveGateRollingRatio.md5Hex(s2);
        List<String> al = new ArrayList<>();
        Consumer<String> o = LiveGateRollingRatio.seedAlert;
        LiveGateRollingRatio.seedAlert = al::add;
        try {
            start(persist);
            boolean blocked = LiveGateRollingRatio.initSeedBranch(s2.getPath(), md52, 24, NOW + DAY);
            assertTrue("seed moi md5 khac marker: phai ap seed moi HOAC chan+KHAN, khong duoc bo qua im", blocked || !al.isEmpty());
        } finally {
            LiveGateRollingRatio.seedAlert = o;
        }
    }
}
