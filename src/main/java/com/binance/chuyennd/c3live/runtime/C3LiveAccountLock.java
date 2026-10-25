package com.binance.chuyennd.c3live.runtime;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.charset.StandardCharsets;

/**
 * [V12 3] Lock DOC QUYEN tai khoan con c3_live giua cac JVM tren cung may (FileChannel.tryLock, OS tu nha khi JVM chet).
 * Giu boi: runtime c3_live chinh khi {@code LIVE_ADAPTER=live} (lenh that) va cong cu canary ({@code c3live.canary}).
 * Ai lay truoc thi giu suot doi JVM; ben con lai TU CHOI chay. Runtime dry KHONG lay lock (khong cham san) => canary
 * duoc chay song song voi dry (MASTER MO-1).
 */
public final class C3LiveAccountLock {

    private static final Logger LOG = LoggerFactory.getLogger(C3LiveAccountLock.class);
    public static final String KEY_FILE = "LIVE_C3_ACCOUNT_LOCK";
    public static final String DEFAULT_FILE = "run/c3live_account.lock";

    private final File file;
    private final RandomAccessFile raf;
    private final FileLock lock;

    private C3LiveAccountLock(File file, RandomAccessFile raf, FileLock lock) {
        this.file = file;
        this.raf = raf;
        this.lock = lock;
    }

    /**
     * Thu lay lock (khong cho). null = dang bi JVM khac (hoac chinh JVM nay) giu, hoac khong mo duoc file (=> coi nhu bi
     * giu: an toan). {@code owner} ghi vao file de owner biet ai giu (khong chua bi mat).
     */
    public static C3LiveAccountLock tryAcquire(File file, String owner) {
        RandomAccessFile raf = null;
        try {
            File parent = file.getAbsoluteFile().getParentFile();
            if (parent != null && !parent.exists() && !parent.mkdirs()) return null;
            raf = new RandomAccessFile(file, "rw");
            FileChannel ch = raf.getChannel();
            FileLock l;
            try {
                l = ch.tryLock();
            } catch (OverlappingFileLockException e) {
                l = null;
            }
            if (l == null) {
                raf.close();
                return null;
            }
            String info = (owner == null ? "?" : owner) + " pid=" + ProcessHandle.current().pid() + " since="
                    + System.currentTimeMillis() + "\n";
            raf.setLength(0);
            raf.write(info.getBytes(StandardCharsets.UTF_8));
            raf.getFD().sync();
            return new C3LiveAccountLock(file, raf, l);
        } catch (IOException | RuntimeException e) {
            LOG.warn("[C3-LIVE-LOCK] khong lay duoc lock {}: {}", file.getPath(), e.toString());
            if (raf != null) {
                try {
                    raf.close();
                } catch (IOException ignore) {
                    // da dong
                }
            }
            return null;
        }
    }

    /** Noi dung file lock (ai dang giu) — chi de in thong bao. */
    public static String holderInfo(File file) {
        try {
            return new String(java.nio.file.Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8).trim();
        } catch (IOException | RuntimeException e) {
            return "?";
        }
    }

    public File file() {
        return file;
    }

    public boolean isValid() {
        return lock.isValid();
    }

    /** Nha lock (test / ket thuc lenh canary). */
    public void release() {
        try {
            lock.release();
        } catch (IOException ignore) {
            // JVM ket thuc cung nha
        }
        try {
            raf.close();
        } catch (IOException ignore) {
            // da dong
        }
    }
}
