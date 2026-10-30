package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

import static org.junit.Assert.*;

/**
 * [V12 R4j A1 MAJ-2] seed: KHONG BAO GIO System.exit. Lan dau ap seed + file danh dau; restart / watchdog (Utils.reset re-exec
 * cung env) / reboot => persist THANG (bo qua seed, WARN). Seed hong lan dau => chan vao lenh moi, KHAN, van chay.
 */
public class GateSeedR4jTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();
    static final long DAY = 86_400_000L, H = 3_600_000L;
    static final long NOW = 1_793_400_000_000L;
    Consumer<String> origAlert;
    final List<String> alerts = new ArrayList<>();

    @Before
    public void setUp() {
        origAlert = LiveGateRollingRatio.seedAlert;
        LiveGateRollingRatio.seedAlert = alerts::add;
    }

    @After
    public void tearDown() {
        LiveGateRollingRatio.seedAlert = origAlert;
        LiveGateRollingRatio.resetForTest();
    }

    private File seed(long from, long to) throws Exception {
        int n = (int) ((to - from) / H) + 1;
        long[] ts = new long[n];
        float[] r = new float[n];
        for (int i = 0; i < n; i++) {
            ts[i] = from + i * H;
            r[i] = 0.001f * (i % 97);
        }
        File f = tmp.newFile();
        GateRatioPersist.writeFresh(f.getPath(), ts, r);
        return f;
    }

    private void start(File persist) {
        LiveGateRollingRatio.configureForTest(0.999950829f, 90);
        LiveGateRollingRatio.setPersistFileForTest(persist.getPath());
    }

    @Test
    public void firstStartApplies_thenRestartWatchdogReboot_persistWins_neverFail() throws Exception {
        File f = seed(NOW - 91 * DAY, NOW - 2 * H);
        String md5 = LiveGateRollingRatio.md5Hex(f);
        File persist = new File(tmp.getRoot(), "gate_ratio_live.bin");
        start(persist);
        assertFalse(LiveGateRollingRatio.initSeedBranch(f.getPath(), md5, 24, NOW));
        assertTrue("file danh dau", LiveGateRollingRatio.seedMarker().isFile());
        int n0 = LiveGateRollingRatio.bufferSizeForTest();
        // r live tich luy sau deploy
        GateRatioPersist.append(persist.getPath(), new long[]{NOW + 10 * 60_000L, NOW + 20 * 60_000L}, new float[]{0.5f, 0.6f});
        // watchdog Reporter (Utils.reset re-exec CUNG env) ngay lap tuc
        start(persist);
        assertFalse(LiveGateRollingRatio.initSeedBranch(f.getPath(), md5, 24, NOW));
        assertEquals("persist thang: seed + 2 r live", n0 + 2, LiveGateRollingRatio.bufferSizeForTest());
        // restart 48 h sau (seed > lag)
        start(persist);
        assertFalse(LiveGateRollingRatio.initSeedBranch(f.getPath(), md5, 24, NOW + 2 * DAY));
        assertFalse(LiveGateRollingRatio.isSeedBlocked());
        // reboot, env seed doi md5 (hoac file seed mat) => van persist thang, khong chan
        start(persist);
        assertFalse(LiveGateRollingRatio.initSeedBranch(new File(tmp.getRoot(), "mat.bin").getPath(), "ffffffffffffffffffffffffffffffff",
                24, NOW + 3 * DAY));
        assertTrue(LiveGateRollingRatio.bufferSizeForTest() > 0);
        assertTrue("khong KHAN khi persist thang", alerts.isEmpty());
    }

    @Test
    public void firstStartBadMd5_blocksNewEntries_noExit_alert() throws Exception {
        File f = seed(NOW - 91 * DAY, NOW - 2 * H);
        File persist = new File(tmp.getRoot(), "gate_ratio_live.bin");
        start(persist);
        assertTrue(LiveGateRollingRatio.initSeedBranch(f.getPath(), "ffffffffffffffffffffffffffffffff", 24, NOW));
        assertTrue(LiveGateRollingRatio.isSeedBlocked());
        assertFalse("chua ap => khong danh dau", LiveGateRollingRatio.seedMarker().isFile());
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0), alerts.get(0).contains("KHAN") && alerts.get(0).contains("CHAN VAO LENH MOI"));
        AIRejectFilter.FilterResult r = new AIRejectFilter().entryGate(new AiPredictionData(NOW, 0.5f, 0f), 0.2f, true, false);
        assertEquals(AIRejectFilter.FilterDecision.REJECT, r.decision);
        AIRejectFilter.FilterResult r2 = new AIRejectFilter().entryGate(new AiPredictionData(NOW, 0.5f, 0f), null, false, false);
        assertEquals("ca leg BIG_DOWN/DCA cung bi chan", AIRejectFilter.FilterDecision.REJECT, r2.decision);
    }

    @Test
    public void firstStartStaleSeed_blocks_noExit() throws Exception {
        File f = seed(NOW - 91 * DAY, NOW - 2 * H);
        File persist = new File(tmp.getRoot(), "gate_ratio_live.bin");
        start(persist);
        assertTrue(LiveGateRollingRatio.initSeedBranch(f.getPath(), LiveGateRollingRatio.md5Hex(f), 24, NOW + 30 * H));
        assertTrue(LiveGateRollingRatio.isSeedBlocked());
    }

    @Test
    public void noSeedEnv_unchanged() {
        File persist = new File(tmp.getRoot(), "gate_ratio_live.bin");
        start(persist);
        assertFalse(LiveGateRollingRatio.initSeedBranch(null, null, 24, NOW));
        assertFalse(LiveGateRollingRatio.isSeedBlocked());
    }
}
