package com.binance.chuyennd.tradecore;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.TreeMap;

/**
 * NIEM PHONG HOLDOUT 2026 (Uni chot 2026-09-02).
 *
 * <p>Du lieu du doan (pred/gate/funding) tu 2026-01-01 UTC da bi XOA khoi Oracle (manifest
 * /home/ubuntu/_SEALED_2026_MANIFEST.txt). Nhung kline tho 2026 van con — sim/export vo tinh chay
 * qua moc nay se sinh ket qua 2026 (BIG_DOWN khong can pred). Lop nay la chot CUNG trong code:
 * moi diem vao/ra du lieu deu clamp ve SEAL_MS, tru khi env HOLDOUT_UNSEAL dat DUNG chuoi mo khoa
 * (chi dung cho lan phan xu cuoi cung, ghi vao ledger).
 */
public final class HoldoutSeal {
    private static final Logger LOG = LoggerFactory.getLogger(HoldoutSeal.class);
    /** 2026-01-01 00:00:00 UTC */
    public static final long SEAL_MS = 1767225600000L;
    public static final String UNSEAL_PHRASE = "I_UNDERSTAND_THIS_BURNS_HOLDOUT_2026";

    private HoldoutSeal() {}

    public static boolean unsealed() {
        return UNSEAL_PHRASE.equals(System.getenv("HOLDOUT_UNSEAL"));
    }

    /** Clamp moc ket thuc. Tra ve moc da clamp; log ERROR neu phai clamp. */
    public static long clampEnd(long endMs, String what) {
        if (endMs <= SEAL_MS) return endMs;
        if (unsealed()) {
            LOG.error("!!!!!!!! HOLDOUT_UNSEAL DUNG — {} chay qua 2026-01-01 (toi {}). LAN NAY TINH VAO LEDGER HOLDOUT. !!!!!!!!", what, endMs);
            return endMs;
        }
        LOG.error("*** HOLDOUT SEAL *** {}: yeu cau toi {} > 2026-01-01 -> CLAMP ve 2025-12-31. "
                + "HOLDOUT 2026 da niem phong; muon mo phai dat env HOLDOUT_UNSEAL (xem HoldoutSeal.java).", what, endMs);
        return SEAL_MS;
    }

    /** Cat moi entry co ts >= SEAL_MS khoi TreeMap (dung cho market/pred/funding luc export). */
    public static <V> int trimMap(TreeMap<Long, V> m, String what) {
        if (m == null || m.isEmpty() || unsealed()) return 0;
        int before = m.size();
        m.tailMap(SEAL_MS, true).clear();
        int cut = before - m.size();
        if (cut > 0) LOG.error("*** HOLDOUT SEAL *** {}: cat {} ban ghi >= 2026-01-01 (con {}).", what, cut, m.size());
        return cut;
    }
}
