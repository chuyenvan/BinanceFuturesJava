package com.binance.chuyennd.c3live.api;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * [V12 C3 ho tro] Kiem clientOrderId theo luat san: ^[.A-Z:/a-z0-9_-]{1,36}$ (khong dung regex, chi so ky tu ASCII).
 * Symbol non-ASCII (vd ten tieng Trung) KHONG duoc dua nguyen vao clientOrderId -> {@link #symbolToken(String)}.
 */
public final class ClientOrderIds {
    public static final int MAX_LEN = 36;

    private ClientOrderIds() { }

    public static boolean isValid(String id) {
        if (id == null || id.isEmpty() || id.length() > MAX_LEN) return false;
        for (int i = 0; i < id.length(); i++) {
            if (!allowed(id.charAt(i))) return false;
        }
        return true;
    }

    private static boolean allowed(char c) {
        return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')
                || c == '.' || c == ':' || c == '/' || c == '_' || c == '-';
    }

    /**
     * Symbol chi gom [A-Za-z0-9] -> giu nguyen; nguoc lai -> "x" + 10 hex dau cua SHA-256(UTF-8 symbol) (on dinh, ASCII).
     */
    public static String symbolToken(String symbol) {
        if (symbol == null) return "null";
        boolean plain = !symbol.isEmpty();
        for (int i = 0; i < symbol.length() && plain; i++) {
            char c = symbol.charAt(i);
            plain = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9');
        }
        if (plain) return symbol;
        try {
            byte[] h = MessageDigest.getInstance("SHA-256").digest(symbol.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder("x");
            for (int i = 0; i < 5; i++) sb.append(String.format("%02x", h[i] & 0xff));
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 khong co", e);
        }
    }
}
