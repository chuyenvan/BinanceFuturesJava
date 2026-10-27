package com.binance.chuyennd.c3live.canary;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.TreeSet;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.Assert.*;

/**
 * [V12 3b] Bang chung CHAY (khong chi grep): toan bo kich ban canary (CanaryEngineTest K0..K8/K6b/K7b + CanaryGuardTest, gom ca
 * duong C3LiveCanary.run) chay trong JVM CON voi {@code -Xlog:class+load}; khong duoc nap BAT KY lop Aerospike / Redis / symbol_mapper
 * nao (symbol_mapper 242 dang co id trung {1: BTCUSDT, XUSDT}). Env con bo LIVE_PROFILE / TRADING_PROFILE / LIVE_TS_MKT_EXT (nhu script).
 */
public class CanaryIsolationTest {

    static final Pattern LOAD = Pattern.compile("\\[class,load\\] (\\S+)");
    static final Pattern FORBIDDEN = Pattern.compile(
            "^(com\\.aerospike\\.|redis\\.clients\\.|io\\.lettuce\\.|org\\.redisson\\.|com\\.binance\\.chuyennd\\.aerospike\\."
                    // [3c MIN-C6] client/key cua tai khoan CHINH: khong duoc nap trong JVM canary
                    + "|com\\.binance\\.client\\.|com\\.binance\\.chuyennd\\.config\\.)"
                    + "|PrivateConfig|ClientSingleton|(?i)symbol_?mapper");

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @Test(timeout = 300_000L)
    public void canaryLoadsNoAerospikeRedisOrSymbolMapperClasses() throws Exception {
        String cp = System.getProperty("surefire.test.class.path");
        if (cp == null || cp.trim().isEmpty()) cp = System.getProperty("java.class.path");
        String java = Paths.get(System.getProperty("java.home"), "bin", "java").toString();
        File classLog = new File(tmp.getRoot(), "classload.log");
        File out = new File(tmp.getRoot(), "child.out");
        List<String> cmd = new ArrayList<>(Arrays.asList(java, "-Xmx512m", "-Xlog:class+load=info:file=" + classLog.getPath(),
                "-cp", cp, "org.junit.runner.JUnitCore", CanaryEngineTest.class.getName(), CanaryGuardTest.class.getName()));
        ProcessBuilder pb = new ProcessBuilder(cmd);
        for (String k : C3LiveCanary.FORBIDDEN_ENV) pb.environment().remove(k);
        pb.redirectErrorStream(true);
        pb.redirectOutput(out);
        pb.directory(tmp.getRoot());
        Process p = pb.start();
        assertTrue("JVM con qua 240 s", p.waitFor(240, TimeUnit.SECONDS));
        String o = new String(Files.readAllBytes(out.toPath()), StandardCharsets.UTF_8);
        assertEquals("JVM con loi:\n" + tail(o), 0, p.exitValue());
        assertTrue(tail(o), o.contains("OK ("));

        TreeSet<String> loaded = new TreeSet<>();
        for (String line : Files.readAllLines(classLog.toPath(), StandardCharsets.UTF_8)) {
            Matcher m = LOAD.matcher(line);
            if (m.find()) loaded.add(m.group(1));
        }
        // doi chung duong: lop canary + lop c3_live that su da chay trong JVM con
        for (String must : new String[]{CanaryEngine.class.getName(), CanaryGateway.class.getName(), C3LiveCanary.class.getName(),
                "com.binance.chuyennd.c3live.exit.TrailingStopManager", "com.binance.chuyennd.c3live.recon.Reconciler",
                "com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor", "com.binance.chuyennd.c3live.risk.C3LiveFlattener"}) {
            assertTrue("khong thay lop " + must + " trong class-load log (" + loaded.size() + " lop)", loaded.contains(must));
        }
        List<String> bad = new ArrayList<>();
        for (String c : loaded) if (FORBIDDEN.matcher(c).find()) bad.add(c);
        assertTrue("canary nap lop Aerospike/Redis/symbol_mapper: " + bad, bad.isEmpty());
    }

    private static String tail(String s) {
        return s.length() <= 4000 ? s : s.substring(s.length() - 4000);
    }
}
