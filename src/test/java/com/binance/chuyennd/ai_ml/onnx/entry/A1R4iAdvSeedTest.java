package com.binance.chuyennd.ai_ml.onnx.entry;

import org.junit.After;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;

import static org.junit.Assert.*;

/** [A1 R4i ADV] KHONG commit. Seed con trong env: restart > lag gio sau lan nap dau => fail-fast exit(2). */
public class A1R4iAdvSeedTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();
    static final long DAY = 86_400_000L, H = 3_600_000L;
    static final long NOW = 1_793_400_000_000L;

    @After
    public void tearDown() {
        LiveGateRollingRatio.resetForTest();
    }

    @Test
    public void restartAfterLagWithSameSeedEnvMustNotKillJvm() throws Exception {
        long from = NOW - 91 * DAY, to = NOW - 2 * H;
        int n = (int) ((to - from) / H) + 1;
        long[] ts = new long[n];
        float[] r = new float[n];
        for (int i = 0; i < n; i++) {
            ts[i] = from + i * H;
            r[i] = 0.001f * (i % 97);
        }
        File f = tmp.newFile();
        GateRatioPersist.writeFresh(f.getPath(), ts, r);
        String md5 = LiveGateRollingRatio.md5Hex(f);
        File persist = new File(tmp.getRoot(), "gate_ratio_live.bin");
        LiveGateRollingRatio.configureForTest(0.999950829f, 90);
        LiveGateRollingRatio.setPersistFileForTest(persist.getPath());
        assertNull("lan deploy dau", LiveGateRollingRatio.applySeedFile(f.getPath(), md5, 24, NOW));
        // 2 ngay sau: Reporter watchdog Utils.reset / systemd restart / reboot — env van con GATE_BUFFER_SEED
        LiveGateRollingRatio.configureForTest(0.999950829f, 90);
        LiveGateRollingRatio.setPersistFileForTest(persist.getPath());
        String p = LiveGateRollingRatio.applySeedFile(f.getPath(), md5, 24, NOW + 2 * DAY);
        assertNull("restart sau 48 h voi seed da nap => KHONG duoc fail-fast (exit 2 = mat process quan ly lenh that): " + p, p);
    }
}
