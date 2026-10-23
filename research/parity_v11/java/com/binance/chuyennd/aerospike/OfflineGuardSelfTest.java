package com.binance.chuyennd.aerospike;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.net.InetAddress;
import java.net.Socket;
import java.util.*;

/**
 * PARITY_V11_WINDOW §6 R0 — test chan mang/Aerospike cua HARNESS_OFFLINE. Moi ca chay trong JVM CON, kiem exit code.
 * Driver: `java ... OfflineGuardSelfTest driver <cpOffline> <cpNoStub> <dirOfflineCfg> <dirRealCfg>`.
 * Ca con: `java ... OfflineGuardSelfTest case <ten>`.
 */
public class OfflineGuardSelfTest {
    private static final Logger LOG = LoggerFactory.getLogger(OfflineGuardSelfTest.class);

    public static void main(String[] a) throws Exception {
        if ("case".equals(a[0])) {
            runCase(a[1]);
            return;
        }
        String cpOff = a[1], cpNoStub = a[2];
        File dirOff = new File(a[3]), dirReal = new File(a[4]);
        // ten ca, classpath, thu muc (config), exit ky vong
        Object[][] cases = {
                {"ok", cpOff, dirOff, 0},
                {"client242", cpOff, dirOff, 97},
                {"clientOracle", cpOff, dirOff, 97},
                {"readClient", cpOff, dirOff, 97},
                {"mapperLoad", cpOff, dirOff, 97},     // loadSymbolMapper co catch(Exception) — halt khong bi nuot
                {"fundingScan", cpOff, dirOff, 97},    // getAllFundingMap co catch(Exception)
                {"tickerRead", cpOff, dirOff, 97},     // readDataFromAerospikeCustom (duong kline harness cu)
                {"socket242", cpOff, dirOff, 98},
                {"dnsVision", cpOff, dirOff, 98},
                {"ok", cpNoStub, dirOff, 96},          // thieu stub => tien kiem chan
                {"ok", cpOff, dirReal, 96},            // config that (cluster 242) => tien kiem chan
        };
        int fail = 0;
        for (Object[] c : cases) {
            List<String> cmd = new ArrayList<>(Arrays.asList(System.getProperty("java.home") + "/bin/java", "-Xmx512m", "-cp",
                    (String) c[1], OfflineGuardSelfTest.class.getName(), "case", (String) c[0]));
            ProcessBuilder pb = new ProcessBuilder(cmd).directory((File) c[2]).redirectErrorStream(true)
                    .redirectOutput(new File((File) c[2], "selftest_" + c[0] + "_" + c[3] + ".log"));
            pb.environment().put("HARNESS_OFFLINE", "1");
            int rc = pb.start().waitFor();
            boolean ok = rc == (Integer) c[3];
            if (!ok) fail++;
            LOG.info("[R0] case={} cp={} cfg={} exit={} ky_vong={} => {}", c[0], ((String) c[1]).contains("stub") ? "stub+jar" : "jar",
                    ((File) c[2]).getName(), rc, c[3], ok ? "DAT" : "TRUOT");
        }
        LOG.info("[R0] tong: {} ca, {} truot", cases.length, fail);
        System.exit(fail == 0 ? 0 : 1);
    }

    static void runCase(String name) throws Exception {
        OfflineGuard.install();
        LOG.info("case {} bat dau", name);
        switch (name) {
            case "ok":
                break;
            case "client242":
                DataManagerAerospikeFloatSim.getClient242();
                break;
            case "clientOracle":
                DataManagerAerospikeFloatSim.getClientOracle();
                break;
            case "readClient":
                DataManagerAerospikeFloatSim.getReadClient();
                break;
            case "mapperLoad":
                LOG.info("mapper {}", DataManagerAerospikeFloatSim.loadSymbolMapper().size());
                break;
            case "fundingScan":
                LOG.info("funding {}", DataManagerAerospikeFloatSim.getAllFundingMap().size());
                break;
            case "tickerRead":
                LOG.info("ticker {}", DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(1792540800000L, 2).size());
                break;
            case "socket242":
                try (Socket s = new Socket("103.157.218.242", 3222)) {
                    LOG.error("KET NOI DUOC ?! {}", s);
                }
                break;
            case "dnsVision":
                LOG.error("resolve ?! {}", InetAddress.getByName("data.binance.vision"));
                break;
            default:
                throw new IllegalArgumentException(name);
        }
        LOG.info("case {} ket thuc binh thuong", name);
        System.exit(0);
    }
}
