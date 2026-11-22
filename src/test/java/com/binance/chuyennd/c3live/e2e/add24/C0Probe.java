package com.binance.chuyennd.c3live.e2e.add24;

import java.io.File;
import java.io.InputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URL;
import java.security.MessageDigest;

/**
 * ADD24 C0 (d)(e): 12 class quyet dinh + C3MainEquity + KillSwitchEngine phai nap tu jar STUB (ClassLoader.getResource + CodeSource),
 * md5 byte class nap duoc; thu ket noi ra ngoai (phai THAT BAI trong bwrap --unshare-net). Khong goi main() cua jar.
 * In 1 dong JSON-lines moi muc. Chay: java -cp <stub>:target/test-classes ...C0Probe <stub_path>
 */
public class C0Probe {
    static final String[] CLASSES = {
            "com.binance.chuyennd.c3live.entry.C3LiveEntry",
            "com.binance.chuyennd.c3live.runtime.C3LiveRuntime",
            "com.binance.chuyennd.tradecore.selector.LiveGridSizing",
            "com.binance.chuyennd.tradecore.selector.LiveDcaGridC3",
            "com.binance.chuyennd.tradecore.DcaUtils",
            "com.binance.chuyennd.tradecore.EntryGate",
            "com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter",
            "com.binance.chuyennd.trading.GatePreFilter",
            "com.binance.chuyennd.c3live.exit.TrailingStopManager",
            "com.binance.chuyennd.ai_ml.onnx.entry.LiveGateRollingRatio",
            "com.binance.chuyennd.c3live.risk.C3MainEquity",
            "com.binance.chuyennd.ops.KillSwitchEngine"};

    static String hex(byte[] b) {
        StringBuilder s = new StringBuilder();
        for (byte x : b) s.append(String.format("%02x", x));
        return s.toString();
    }

    public static void main(String[] a) throws Exception {
        String stub = new File(a[0]).getAbsolutePath();
        String jarUrl = "jar:" + new File(stub).toURI().toURL() + "!/";
        int ok = 0;
        System.out.println("{\"shadow_host\":\"" + System.getenv("LIVE_IS_SHADOW_HOST") + "\",\"adapter\":\"" + System.getenv("LIVE_ADAPTER") + "\"}");
        for (String cn : CLASSES) {
            String path = cn.replace('.', '/') + ".class";
            URL u = ClassLoader.getSystemClassLoader().getResource(path);
            Class<?> c = Class.forName(cn, false, C0Probe.class.getClassLoader());
            String cs = new File(c.getProtectionDomain().getCodeSource().getLocation().toURI()).getAbsolutePath();
            MessageDigest md = MessageDigest.getInstance("MD5");
            try (InputStream in = ClassLoader.getSystemClassLoader().getResourceAsStream(path)) {
                byte[] buf = new byte[8192];
                int n;
                while ((n = in.read(buf)) > 0) md.update(buf, 0, n);
            }
            boolean good = u != null && u.toString().startsWith(jarUrl) && cs.equals(stub);
            if (good) ok++;
            System.out.println("{\"class\":\"" + cn + "\",\"resource\":\"" + u + "\",\"codeSource\":\"" + cs + "\",\"md5\":\""
                    + hex(md.digest()) + "\",\"from_stub\":" + good + "}");
        }
        String net;
        try (Socket s = new Socket()) {
            s.connect(new InetSocketAddress("1.1.1.1", 443), 2000);
            net = "CONNECTED";
        } catch (Exception e) {
            net = "FAIL:" + e.getClass().getSimpleName() + ":" + e.getMessage();
        }
        System.out.println("{\"net_probe\":\"" + net.replace('"', '\'') + "\",\"from_stub_n\":" + ok + ",\"n\":" + CLASSES.length + "}");
    }
}
