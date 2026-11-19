package com.binance.chuyennd.c3live.client;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFileAttributes;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.EnumSet;
import java.util.Set;

/**
 * [V12 C2] Doc C3_LIVE_API_KEY / C3_LIVE_API_SECRET tu file root-only (mac dinh /root/.config/c3live/keys.env).
 * Dieu kien (sai bat ky -> {@link C3LiveKeyException}):
 * <ul>
 *   <li>ton tai, file thuong, KHONG phai symlink;</li>
 *   <li>quyen CHINH XAC 600 (rw-------), owner == expectedOwner (mac dinh root);</li>
 *   <li>thu muc cha khong ghi duoc boi group/other;</li>
 *   <li>co du 2 bien, gia tri ASCII in duoc khong khoang trang.</li>
 * </ul>
 * Doi tuong khong bao gio in gia tri (toString che).
 */
public final class C3LiveKeys {
    public static final String DEFAULT_PATH = "/root/.config/c3live/keys.env";
    public static final String DEFAULT_OWNER = "root";
    public static final String VAR_KEY = "C3_LIVE_API_KEY";
    public static final String VAR_SECRET = "C3_LIVE_API_SECRET";
    static final long MAX_FILE_BYTES = 64 * 1024;
    private static final Set<PosixFilePermission> REQUIRED = EnumSet.of(PosixFilePermission.OWNER_READ, PosixFilePermission.OWNER_WRITE);

    private final String apiKey;
    private final byte[] secret;

    private C3LiveKeys(String apiKey, byte[] secret) {
        this.apiKey = apiKey;
        this.secret = secret;
    }

    /** Chi cho test cung package (khong qua file). */
    static C3LiveKeys ofForTest(String apiKey, String secret) {
        return new C3LiveKeys(apiKey, secret.getBytes(StandardCharsets.US_ASCII));
    }

    String apiKey() { return apiKey; }

    byte[] secret() { return secret.clone(); }

    public static C3LiveKeys load(Path path, String expectedOwner) throws C3LiveKeyException {
        if (path == null) throw new C3LiveKeyException("LIVE_C3_KEYS_FILE rong");
        String owner = expectedOwner == null || expectedOwner.trim().isEmpty() ? DEFAULT_OWNER : expectedOwner.trim();
        if (Files.isSymbolicLink(path)) throw new C3LiveKeyException("key file la symlink - tu choi: " + path);
        if (!Files.exists(path, LinkOption.NOFOLLOW_LINKS)) throw new C3LiveKeyException("key file khong ton tai: " + path);
        if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) throw new C3LiveKeyException("key file khong phai file thuong: " + path);
        PosixFileAttributes attrs;
        try {
            attrs = Files.readAttributes(path, PosixFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        } catch (UnsupportedOperationException e) {
            throw new C3LiveKeyException("FS khong ho tro POSIX - khong kiem duoc quyen key file: " + path, e);
        } catch (IOException e) {
            throw new C3LiveKeyException("khong doc duoc thuoc tinh key file: " + path + " (" + e.getClass().getSimpleName() + ")", e);
        }
        Set<PosixFilePermission> perms = attrs.permissions();
        if (!perms.equals(REQUIRED)) {
            throw new C3LiveKeyException("quyen key file = " + PosixFilePermissions.toString(perms) + ", yeu cau rw------- (600): " + path);
        }
        String actualOwner = attrs.owner() == null ? "?" : attrs.owner().getName();
        if (!owner.equals(actualOwner)) {
            throw new C3LiveKeyException("owner key file = " + actualOwner + ", yeu cau " + owner + ": " + path);
        }
        Path parent = path.toAbsolutePath().getParent();
        if (parent != null) {
            try {
                Set<PosixFilePermission> pp = Files.readAttributes(parent, PosixFileAttributes.class).permissions();
                if (pp.contains(PosixFilePermission.GROUP_WRITE) || pp.contains(PosixFilePermission.OTHERS_WRITE)) {
                    throw new C3LiveKeyException("thu muc cha ghi duoc boi group/other (" + PosixFilePermissions.toString(pp) + "): " + parent);
                }
            } catch (IOException | UnsupportedOperationException e) {
                throw new C3LiveKeyException("khong doc duoc quyen thu muc cha: " + parent, e);
            }
        }
        if (attrs.size() > MAX_FILE_BYTES) throw new C3LiveKeyException("key file qua lon (" + attrs.size() + " B): " + path);
        String text;
        try {
            text = new String(Files.readAllBytes(path), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new C3LiveKeyException("khong doc duoc key file: " + path + " (" + e.getClass().getSimpleName() + ")", e);
        }
        return parse(text, path.toString());
    }

    static C3LiveKeys parse(String text, String where) throws C3LiveKeyException {
        String key = null;
        String secret = null;
        for (String raw : text.split("\r?\n")) {
            String line = raw.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;
            if (line.startsWith("export ")) line = line.substring(7).trim();
            int eq = line.indexOf('=');
            if (eq <= 0) continue;
            String name = line.substring(0, eq).trim();
            String val = unquote(line.substring(eq + 1).trim());
            if (VAR_KEY.equals(name)) key = val;
            else if (VAR_SECRET.equals(name)) secret = val;
        }
        if (key == null || key.isEmpty()) throw new C3LiveKeyException("thieu " + VAR_KEY + " trong " + where);
        if (secret == null || secret.isEmpty()) throw new C3LiveKeyException("thieu " + VAR_SECRET + " trong " + where);
        if (!printable(key)) throw new C3LiveKeyException(VAR_KEY + " co ky tu khong hop le (len=" + key.length() + ") trong " + where);
        if (!printable(secret)) throw new C3LiveKeyException(VAR_SECRET + " co ky tu khong hop le (len=" + secret.length() + ") trong " + where);
        return new C3LiveKeys(key, secret.getBytes(StandardCharsets.US_ASCII));
    }

    private static String unquote(String v) {
        if (v.length() >= 2 && ((v.startsWith("\"") && v.endsWith("\"")) || (v.startsWith("'") && v.endsWith("'")))) {
            return v.substring(1, v.length() - 1);
        }
        return v;
    }

    private static boolean printable(String s) {
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c < 0x21 || c > 0x7E) return false;
        }
        return true;
    }

    /**
     * [W3A muc 2] Dinh danh KHONG bi mat cua key: 8 ky tu hex dau cua sha256(API KEY) (API key khong phai secret;
     * secret KHONG bao gio duoc bam/in). Dung cho dong log khoi dong de doi chieu voi SUB_KEY_SHA8 cua ops.
     *
     * @return 8 ky tu hex thuong
     */
    public String apiKeySha8() {
        return sha8(apiKey);
    }

    /**
     * 8 ky tu hex dau cua sha256(UTF-8 cua s).
     *
     * @param s chuoi nguon (khong null)
     * @return 8 ky tu hex thuong
     */
    static String sha8(String s) {
        try {
            byte[] d = java.security.MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8));
            StringBuilder b = new StringBuilder(8);
            for (int i = 0; i < 4; i++) b.append(String.format("%02x", d[i] & 0xff));
            return b.toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            return "????????";
        }
    }

    @Override
    public String toString() { return "C3LiveKeys[key=***(" + apiKey.length() + "), secret=***]"; }
}
