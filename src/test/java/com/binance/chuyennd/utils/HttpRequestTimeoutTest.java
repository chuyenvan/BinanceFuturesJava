package com.binance.chuyennd.utils;

import org.junit.Test;

import java.io.File;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.HashMap;

import static org.junit.Assert.*;

/**
 * [W3A muc 4] getContentFromUrl(url, timeout): timeout ap THAT (connect + read, dat truoc connect). Server gia nhan TCP
 * (backlog) nhung khong bao gio tra loi => ban cu treo 30 s x 5 lan thu = 150 s; ban sua ~ 5 x timeout.
 */
public class HttpRequestTimeoutTest {

    @Test(timeout = 30_000L)
    public void serverKhongTraLoi_timeoutApThat() throws Exception {
        try (ServerSocket ss = new ServerSocket(0, 50, InetAddress.getLoopbackAddress())) {
            String url = "http://127.0.0.1:" + ss.getLocalPort() + "/w3a_" + ProcessHandle.current().pid();
            long t0 = System.nanoTime();
            String r = HttpRequest.getContentFromUrl0(url, new HashMap<>(), 300, true);
            long ms = (System.nanoTime() - t0) / 1_000_000L;
            assertNull("het lan thu => null nhu cu", r);
            assertTrue("5 lan thu x 300 ms phai < 10 s, do duoc " + ms + " ms", ms < 10_000L);
        }
    }

    @Test
    public void macDinh_giuNguyen30s_vaFixBat() {
        assertTrue("mac dinh HTTP_TIMEOUT_FIX bat (env khong dat tren may test)", HttpRequest.TIMEOUT_FIX
                || "false".equalsIgnoreCase(System.getenv("HTTP_TIMEOUT_FIX")));
        assertEquals(30_000, HttpRequest.envMs("W3A_KHONG_CO_ENV_NAY", 30_000));
        if (System.getenv("HTTP_CONNECT_TIMEOUT_MS") == null) assertEquals(30_000, HttpRequest.connect_time_out);
        if (System.getenv("HTTP_READ_TIMEOUT_MS") == null) assertEquals(30_000, HttpRequest.read_time_out);
        if (System.getenv("HTTP_TIMEOUT_READ_MS") == null) assertEquals(5_000, HttpRequest.readTimeoutFor(5_000));
    }

    /** Duong khong timeout (LEGACY) giu nguyen; duong timeout khong con setConnectTimeout sau connect khi fix bat. */
    @Test
    public void nguon_duongCuGiuNguyen() throws Exception {
        String s = new String(Files.readAllBytes(new File("src/main/java/com/binance/chuyennd/utils/HttpRequest.java").toPath()),
                StandardCharsets.UTF_8);
        assertTrue(s.contains("return connect(url_, extendedHeader, proxy, connect_time_out, read_time_out);"));
        assertTrue(s.contains("if (!fix) hc.setConnectTimeout(timeout);"));
    }
}
