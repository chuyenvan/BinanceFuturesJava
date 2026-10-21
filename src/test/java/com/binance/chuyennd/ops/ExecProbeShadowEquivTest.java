package com.binance.chuyennd.ops;

import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.selector.ShadowBookC3;
import org.junit.After;
import org.junit.Test;

import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

/**
 * LEGACY-EQUIVALENCE muc so giay: cung kich ban (mo cum, DCA, arm, ratchet, trailing, time-stop) chay 2 lan tren
 * {@link ShadowBookC3} — probe TAT va probe BAT (nguon so gia, khong mang). Moi quyet dinh (so cum dong moi nhip,
 * summary, dong ledger moi, state) phai TRUNG KHOP; probe BAT chi them dong {@code [EXEC-PROBE]}.
 */
public class ExecProbeShadowEquivTest {

    @After
    public void tearDown() {
        ExecProbe.installForTest(null);
        ShadowBookC3.resetForTest();
    }

    private static File stateFile() {
        return new File(System.getProperty("user.dir"), "open_positions.csv");
    }

    private static File ledgerFile() {
        return new File(System.getProperty("user.dir"), "ledger.csv");
    }

    private static Map<String, Float> px(Object... kv) {
        Map<String, Float> m = new HashMap<>();
        for (int i = 0; i < kv.length; i += 2) m.put((String) kv[i], ((Number) kv[i + 1]).floatValue());
        return m;
    }

    /** Chay kich ban, tra dau vet quyet dinh: so dong moi nhip + summary + ledger moi + state cuoi. */
    private List<String> scenario() throws Exception {
        ShadowBookC3.resetForTest();
        stateFile().delete();
        Configs.properties.putIfAbsent("CAPITAL_START", "35000");
        long before = ledgerFile().exists() ? Files.readAllLines(ledgerFile().toPath()).size() : 0;
        ShadowBookC3 b = ShadowBookC3.getInstance();
        long h = 3600_000L;
        List<String> trace = new ArrayList<>();
        b.openPos("AAAUSDT", 0L, 100f, 2f, 1, 0.10f, "BIG_DOWN");
        b.openPos("BBBUSDT", 0L, 10f, 30f, 2, 0.50f, "PREDICT_SYMBOL_TRADE");
        b.openPos("CCCUSDT", 0L, 1f, 500f, 3, 0.10f, "BIG_DOWN");
        b.openPos("AAAUSDT", 60_000L, 50f, 4f, -1, null, "DCA_LEVEL1");   // DCA -> VWAP 66.67
        float[][] path = {{66f, 10f, 0.99f}, {75f, 10.9f, 0.98f}, {80f, 11.5f, 0.97f}, {72f, 10.6f, 0.97f},
                {70f, 10.0f, 0.96f}};
        for (int i = 0; i < path.length; i++) {
            int closed = b.tick(px("AAAUSDT", path[i][0], "BBBUSDT", path[i][1], "CCCUSDT", path[i][2]), (i + 1) * h);
            trace.add("t" + i + " closed=" + closed + " " + b.summary(px("AAAUSDT", path[i][0], "BBBUSDT", path[i][1],
                    "CCCUSDT", path[i][2])));
        }
        int closed = b.tick(px("CCCUSDT", 0.95f), 200 * h);   // time-stop 168h cum chua arm
        trace.add("ts closed=" + closed + " open=" + b.openCount());
        List<String> led = Files.readAllLines(ledgerFile().toPath());
        trace.addAll(led.subList((int) before, led.size()));
        trace.addAll(Files.readAllLines(stateFile().toPath()));
        return trace;
    }

    @Test
    public void decisionsIdenticalWithProbeOnAndOff() throws Exception {
        ExecProbe.installForTest(null);
        assertFalse(ExecProbe.on());
        List<String> off = scenario();

        List<String> lines = new ArrayList<>();
        ExecProbe.Engine e = new ExecProbe.Engine(
                ExecProbe.Settings.parse("mock", null, "5", "20", "1000", "0", "30"), null, lines::add);
        ExecProbe.installForTest(e);
        assertTrue(ExecProbe.on());
        List<String> on = scenario();
        while (e.runOnce(1L) > 0) {
            // xa hang doi
        }

        assertEquals(off, on);
        // so giay dong 3 cum (AAA trailing, BBB trailing, CCC time-stop) => 3 dong EXIT (+ header)
        long exits = lines.stream().filter(s -> s.contains(",EXIT,")).count();
        assertTrue("exit lines=" + exits + " " + off, exits >= 2);
        for (String s : lines) {
            if (s.contains("#hdr")) continue;
            assertTrue(s, s.endsWith(",ok,mock") || s.endsWith(",short,mock"));
        }
    }
}
