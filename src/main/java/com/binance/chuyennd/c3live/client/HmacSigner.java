package com.binance.chuyennd.c3live.client;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;

/** [V12 C2] HMAC-SHA256 hex thuong (chu ky Binance SIGNED). Khong log gi. */
public final class HmacSigner {
    private static final char[] HEX = "0123456789abcdef".toCharArray();
    private final SecretKeySpec key;

    public HmacSigner(byte[] secret) {
        if (secret == null || secret.length == 0) throw new IllegalArgumentException("secret rong");
        this.key = new SecretKeySpec(secret.clone(), "HmacSHA256");
    }

    /** Ky payload (query string DA percent-encode, dung y chuoi gui di). */
    public String sign(String payload) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(key);
            return hex(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("HmacSHA256 khong kha dung", e);
        }
    }

    public static String hmacSha256Hex(byte[] secret, String payload) {
        return new HmacSigner(secret).sign(payload);
    }

    static String hex(byte[] b) {
        char[] out = new char[b.length * 2];
        for (int i = 0; i < b.length; i++) {
            out[2 * i] = HEX[(b[i] >> 4) & 0xF];
            out[2 * i + 1] = HEX[b[i] & 0xF];
        }
        return new String(out);
    }

    @Override
    public String toString() { return "HmacSigner[***]"; }
}
