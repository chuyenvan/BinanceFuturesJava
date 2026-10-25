package com.binance.chuyennd.ops;

import org.junit.Assume;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

import static org.junit.Assert.*;

/** [V12 SAFE C8] ops/killsw_reset.sh (DRY mac dinh, phai go YES, ghi log) + engine ap dung yeu cau (khong restart). */
public class KillSwitchResetScriptTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    private static final File SCRIPT = new File("ops/killsw_reset.sh");

    private String run(File runDir, String dry, String input) throws Exception {
        ProcessBuilder pb = new ProcessBuilder("bash", SCRIPT.getAbsolutePath());
        pb.environment().put("RUN_DIR", runDir.getPath());
        pb.environment().put("DRY", dry);
        pb.environment().put("WAIT_S", "0");
        pb.environment().remove("LIVE_KILLSW_LATCH_FILE");
        pb.environment().remove("LIVE_KILLSW_RESET_FILE");
        pb.redirectErrorStream(true);
        Process p = pb.start();
        try (OutputStream o = p.getOutputStream()) {
            o.write(input.getBytes(StandardCharsets.UTF_8));
        }
        String out = new String(readAll(p), StandardCharsets.UTF_8);
        assertTrue(p.waitFor(30, TimeUnit.SECONDS));
        return p.exitValue() + "|" + out;
    }

    private static byte[] readAll(Process p) throws Exception {
        java.io.ByteArrayOutputStream b = new java.io.ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = p.getInputStream().read(buf)) > 0) b.write(buf, 0, n);
        return b.toByteArray();
    }

    @Test
    public void dryNoYesAndYesThenEngineApplies() throws Exception {
        Assume.assumeTrue(SCRIPT.isFile() && new File("/bin/bash").canExecute());
        File runDir = tmp.newFolder("run");
        KillSwitchEngine.Params prm = new KillSwitchEngine.Params();
        prm.latchFile = new File(runDir, "killsw_latch.json");
        prm.resetFile = new File(runDir, "killsw_reset.req");
        List<String> lines = new ArrayList<>();
        KillSwitchEngine.Sink sink = new KillSwitchEngine.Sink() {
            public void info(String m) {
                lines.add(m);
            }

            public void warn(String m) {
                lines.add(m);
            }
        };
        long t0 = System.currentTimeMillis();
        KillSwitchEngine e = new KillSwitchEngine(KillSwitchEngine.Mode.ACT, "act", sink, null, () -> 1d, () -> 0.6f, t0, prm);
        for (int i = 0; i < 5; i++) e.onApiResult(t0 + i, "order", false);
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, e.requiredAction());

        String dry = run(runDir, "1", "");
        assertTrue(dry, dry.startsWith("0|"));
        assertTrue(dry, dry.contains("latch=NO_NEW_ENTRY"));
        assertFalse(prm.resetFile.exists());

        String no = run(runDir, "0", "yes\n");
        assertTrue(no, no.startsWith("3|"));
        assertFalse(prm.resetFile.exists());
        assertFalse(new File(runDir, "killsw_reset.log").exists());

        String yes = run(runDir, "0", "YES\n");
        assertTrue(yes, yes.startsWith("0|"));
        assertTrue(prm.resetFile.exists());
        String log = new String(Files.readAllBytes(new File(runDir, "killsw_reset.log").toPath()), StandardCharsets.UTF_8);
        assertTrue(log, log.contains("reset_peak=0") && log.contains("latch_truoc=NO_NEW_ENTRY"));

        e.periodic(t0 + 15_000L);   // thread periodic cua bot dang chay — khong restart
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        assertTrue(e.allowNewEntry("XUSDT"));
        assertFalse(prm.resetFile.exists());
        assertTrue(lines.stream().anyMatch(l -> l.contains("RESET boi owner")));
    }
}
