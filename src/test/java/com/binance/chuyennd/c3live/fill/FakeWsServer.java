package com.binance.chuyennd.c3live.fill;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.List;

/**
 * [V12 C7 test] Server websocket TOI THIEU (JDK ServerSocket, RFC 6455: bat tay + frame text khong mask tu server) de
 * test {@link UserStream} khong can mang/thu vien ngoai. Moi lan chi giu 1 ket noi; {@link #drop()} dong dot ngot.
 */
final class FakeWsServer implements AutoCloseable {

    private static final String GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
    private final ServerSocket ss;
    private final Thread acceptor;
    private volatile Socket cur;
    private volatile OutputStream out;
    final List<String> paths = Collections.synchronizedList(new ArrayList<>());
    volatile int accepted;
    /** true => tu choi ket noi moi (dong ngay, khong bat tay) — gia lap san/mang chet lau. */
    volatile boolean refuse;

    FakeWsServer() throws IOException {
        ss = new ServerSocket(0, 5, InetAddress.getLoopbackAddress());
        acceptor = new Thread(this::acceptLoop, "fake-ws");
        acceptor.setDaemon(true);
        acceptor.start();
    }

    int port() {
        return ss.getLocalPort();
    }

    private void acceptLoop() {
        while (!ss.isClosed()) {
            try {
                Socket s = ss.accept();
                if (refuse) {
                    s.close();
                    continue;
                }
                handshake(s);
            } catch (IOException e) {
                // dong server
            }
        }
    }

    private void handshake(Socket s) throws IOException {
        InputStream in = s.getInputStream();
        ByteArrayOutputStream hdr = new ByteArrayOutputStream();
        int b, n = 0;
        while ((b = in.read()) >= 0) {
            hdr.write(b);
            n = (b == '\r' || b == '\n') ? n + 1 : 0;
            if (n == 4) break;
        }
        String h = new String(hdr.toByteArray(), StandardCharsets.ISO_8859_1);
        String key = null;
        String[] lines = h.split("\r\n");
        if (lines.length > 0) {
            String[] p = lines[0].split(" ");
            if (p.length > 1) paths.add(p[1]);
        }
        for (String l : lines) {
            int i = l.indexOf(':');
            if (i > 0 && l.substring(0, i).trim().equalsIgnoreCase("Sec-WebSocket-Key")) key = l.substring(i + 1).trim();
        }
        String accept;
        try {
            byte[] d = MessageDigest.getInstance("SHA-1").digest((key + GUID).getBytes(StandardCharsets.ISO_8859_1));
            accept = Base64.getEncoder().encodeToString(d);
        } catch (Exception e) {
            throw new IOException(e);
        }
        OutputStream o = s.getOutputStream();
        o.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "
                + accept + "\r\n\r\n").getBytes(StandardCharsets.ISO_8859_1));
        o.flush();
        synchronized (this) {
            cur = s;
            out = o;
            accepted++;
        }
        Thread r = new Thread(() -> drain(s), "fake-ws-read");
        r.setDaemon(true);
        r.start();
    }

    /** Doc bo frame tu client (ping/close) de socket khong day buffer. */
    private void drain(Socket s) {
        try {
            InputStream in = s.getInputStream();
            byte[] buf = new byte[4096];
            while (in.read(buf) >= 0) {
                // bo qua
            }
        } catch (IOException ignore) {
            // dong
        }
    }

    synchronized boolean send(String text) {
        if (out == null) return false;
        try {
            byte[] p = text.getBytes(StandardCharsets.UTF_8);
            ByteArrayOutputStream f = new ByteArrayOutputStream();
            f.write(0x81);
            if (p.length <= 125) {
                f.write(p.length);
            } else if (p.length <= 65535) {
                f.write(126);
                f.write((p.length >> 8) & 0xff);
                f.write(p.length & 0xff);
            } else {
                f.write(127);
                for (int i = 7; i >= 0; i--) f.write((int) (((long) p.length >> (8 * i)) & 0xff));
            }
            f.write(p);
            out.write(f.toByteArray());
            out.flush();
            return true;
        } catch (IOException e) {
            return false;
        }
    }

    /** Dong ket noi hien tai dot ngot (mat stream). */
    synchronized void drop() {
        try {
            if (cur != null) cur.close();
        } catch (IOException ignore) {
            // da dong
        }
        cur = null;
        out = null;
    }

    synchronized boolean connected() {
        return out != null;
    }

    @Override
    public void close() throws IOException {
        drop();
        ss.close();
    }
}
