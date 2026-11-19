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

    /** Server gia: tra header roi NHO GIOT body 1 byte / 100 ms (moi lan read < read timeout). */
    private static Thread dripServer(ServerSocket ss, java.util.concurrent.atomic.AtomicBoolean stop) {
        Thread t = new Thread(() -> {
            while (!stop.get()) {
                try {
                    java.net.Socket s = ss.accept();
                    Thread h = new Thread(() -> {
                        try (java.net.Socket c = s) {
                            java.io.InputStream in = c.getInputStream();
                            int st = 0;
                            while (st < 4) {
                                int b = in.read();
                                if (b < 0) return;
                                st = (b == '\r' || b == '\n') ? st + 1 : 0;
                            }
                            java.io.OutputStream out = c.getOutputStream();
                            out.write("HTTP/1.1 200 OK\r\nContent-Length: 100000\r\n\r\n".getBytes(StandardCharsets.US_ASCII));
                            out.flush();
                            while (!stop.get()) {
                                out.write('x');
                                out.flush();
                                Thread.sleep(100L);
                            }
                        } catch (Exception ignore) {
                            // client dong
                        }
                    });
                    h.setDaemon(true);
                    h.start();
                } catch (Exception e) {
                    return;
                }
            }
        });
        t.setDaemon(true);
        t.start();
        return t;
    }

    /** [W3B muc 3c] server nho giot: han TONG moi lan thu (timeout + read) => 5 lan x ~600 ms, khong treo vo han. */
    @Test(timeout = 60_000L)
    public void serverNhoGiot_hanTong() throws Exception {
        java.util.concurrent.atomic.AtomicBoolean stop = new java.util.concurrent.atomic.AtomicBoolean();
        try (ServerSocket ss = new ServerSocket(0, 50, InetAddress.getLoopbackAddress())) {
            dripServer(ss, stop);
            String url = "http://127.0.0.1:" + ss.getLocalPort() + "/w3b_drip";
            long t0 = System.nanoTime();
            String r = HttpRequest.getContentFromUrl0(url, new HashMap<>(), 300, true, true);
            long ms = (System.nanoTime() - t0) / 1_000_000L;
            assertNull("het lan thu => null", r);
            assertTrue("5 x (300+300) ms + du phong < 8 s, do " + ms, ms < 8_000L);
            assertTrue("van phai doi it nhat ~5 x 600 ms, do " + ms, ms >= 2_500L);
        } finally {
            stop.set(true);
        }
    }

    /** [W3B muc 3c] doi chung: tat han tong (= W3A) => server nho giot giu > 6 s (read timeout la moi lan read). */
    @Test(timeout = 60_000L)
    public void serverNhoGiot_doiChung_khongHanTong_treo() throws Exception {
        java.util.concurrent.atomic.AtomicBoolean stop = new java.util.concurrent.atomic.AtomicBoolean();
        try (ServerSocket ss = new ServerSocket(0, 50, InetAddress.getLoopbackAddress())) {
            dripServer(ss, stop);
            String url = "http://127.0.0.1:" + ss.getLocalPort() + "/w3b_drip0";
            java.util.concurrent.atomic.AtomicBoolean done = new java.util.concurrent.atomic.AtomicBoolean();
            Thread c = new Thread(() -> {
                HttpRequest.getContentFromUrl0(url, new HashMap<>(), 300, true, false);
                done.set(true);
            });
            c.setDaemon(true);
            c.start();
            c.join(6_000L);
            assertFalse("khong han tong => van dang doc sau 6 s", done.get());
        } finally {
            stop.set(true);
        }
    }

    /** [W3B muc 3d] CONNECT treo (backlog day): timeout ap vao giai doan connect; doi chung ban cu (fix=false) > 3 s. */
    @Test(timeout = 60_000L)
    public void connectTreo_timeoutApThat_vaDoiChung() throws Exception {
        try (ServerSocket ss = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) {
            int port = ss.getLocalPort();
            java.util.List<java.net.Socket> fill = new java.util.ArrayList<>();
            boolean hang = false;
            try {
                for (int i = 0; i < 20 && !hang; i++) {
                    java.net.Socket s = new java.net.Socket();
                    try {
                        s.connect(new java.net.InetSocketAddress("127.0.0.1", port), 500);
                        fill.add(s);
                    } catch (java.net.SocketTimeoutException e) {
                        hang = true;
                        s.close();
                    }
                }
                org.junit.Assume.assumeTrue("kernel nay khong tai hien connect treo", hang);
                String url = "http://127.0.0.1:" + port + "/w3b_conn";
                long t0 = System.nanoTime();
                assertNull(HttpRequest.getContentFromUrl0(url, new HashMap<>(), 300, true, true));
                long ms = (System.nanoTime() - t0) / 1_000_000L;
                assertTrue("5 x 300 ms connect < 10 s, do " + ms, ms < 10_000L);
                java.util.concurrent.atomic.AtomicBoolean done = new java.util.concurrent.atomic.AtomicBoolean();
                Thread c = new Thread(() -> {
                    HttpRequest.getContentFromUrl0(url, new HashMap<>(), 300, false, false);
                    done.set(true);
                });
                c.setDaemon(true);
                c.start();
                c.join(3_000L);
                assertFalse("ban cu: connect 30 s/lan => chua xong sau 3 s", done.get());
            } finally {
                for (java.net.Socket s : fill) s.close();
            }
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
