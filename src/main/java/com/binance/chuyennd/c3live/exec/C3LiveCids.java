package com.binance.chuyennd.c3live.exec;

import com.binance.chuyennd.c3live.api.ClientOrderIds;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * [V12 C3] clientOrderId xac dinh cho c3_live (idempotency).
 * <ul>
 *   <li>leg MUA: {@code c3-<symbolToken>-<barMin>-<leg>} — barMin = startTime nen quyet dinh / 60 000 (phut epoch),
 *       leg = bac grid (0 = mo cum).</li>
 *   <li>lenh DONG: {@code c3x-<symbolToken>-<min>-<n>} — min = phut bat dau dong, n = lan gui (1, 2, ...).</li>
 * </ul>
 * symbolToken = {@link ClientOrderIds#symbolToken} (non-ASCII => x+hash). Neu chuoi > 36 ky tu => token thay bang
 * {@code x<10 hex sha256(symbol)>} (on dinh, khong va cham thuc te). Moi cid tra ra deu {@link ClientOrderIds#isValid}.
 */
public final class C3LiveCids {

    public static final String ENTRY_PREFIX = "c3-";
    public static final String CLOSE_PREFIX = "c3x-";

    private C3LiveCids() {
    }

    public static String entry(String symbol, long barMin, int leg) {
        return build(ENTRY_PREFIX, symbol, barMin, Integer.toString(leg));
    }

    public static String close(String symbol, long minute, int attempt) {
        return build(CLOSE_PREFIX, symbol, minute, Integer.toString(attempt));
    }

    static String build(String prefix, String symbol, long minute, String tail) {
        String tok = ClientOrderIds.symbolToken(symbol);
        String id = prefix + tok + "-" + minute + "-" + tail;
        if (id.length() > ClientOrderIds.MAX_LEN) {
            id = prefix + hashToken(symbol) + "-" + minute + "-" + tail;
        }
        if (!ClientOrderIds.isValid(id)) {
            throw new IllegalArgumentException("cid khong hop le: len=" + id.length());
        }
        return id;
    }

    static String hashToken(String symbol) {
        try {
            byte[] h = MessageDigest.getInstance("SHA-256").digest(String.valueOf(symbol).getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder("x");
            for (int i = 0; i < 5; i++) sb.append(String.format("%02x", h[i] & 0xff));
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 khong co", e);
        }
    }

    /** Phut epoch cua nen quyet dinh (startTime ms). */
    public static long barMin(long startTimeMs) {
        return Math.floorDiv(startTimeMs, 60_000L);
    }
}
