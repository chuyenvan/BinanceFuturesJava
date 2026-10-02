package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * [FIX_NO_WRITE_242 2026-10-03] Cong DUY NHAT quyet dinh co duoc GHI vao Aerospike 242 (tien that) hay khong.
 *
 * <p>VI SAO CAN: shadow_c3 tren Oracle chay CUNG jar/CUNG {@code LIVE_PROFILE=c3_shadow}/CUNG
 * {@code SHADOW_NO_PUSH=true} voi 242 (env 242 co ca 2 key nay) ⇒ khong the dua vao 2 key do de biet
 * "minh co phai 242 khong". Truoc fix, shadow ghi {@code ai_pred_1m} vao 242 moi phut (last-writer-wins,
 * docs/audit/DEPLOY_SHADOW_2A_20261002.md §4) ⇒ p15 tren 242 tron 2 nguon.
 *
 * <p>QUY TAC (opt-in TUONG MINH, KHONG doan hostname):
 * <ul>
 *   <li>{@code LIVE_IS_SHADOW_HOST=true} ⇒ CHAN moi ghi 242 di qua cong nay.</li>
 *   <li>{@code LIVE_WRITE_242_ENABLED=false} ⇒ CHAN (kill-switch chung, vd box tool/test).</li>
 *   <li>Thieu/rong/gia tri khac ⇒ CHO GHI = hanh vi cu. 242 khong dat 2 key ⇒ byte-identical.</li>
 * </ul>
 * Doc ⇒ KHONG di qua cong nay (doc 242 cua shadow giu nguyen). Khi chan: log INFO 1 lan / loai ghi.
 * 2 key nam trong {@code Cfg.INFRA_KEYS} (ha tang, doc tu env ke ca khi co TRADING_PROFILE).
 */
public final class Live242WriteGuard {

    private static final Logger LOG = LoggerFactory.getLogger(Live242WriteGuard.class);

    public static final String KEY_ENABLED = "LIVE_WRITE_242_ENABLED";
    public static final String KEY_SHADOW_HOST = "LIVE_IS_SHADOW_HOST";

    /** null = chua quyet (lazy, doc env 1 lan). */
    private static volatile Boolean decided;
    private static final Set<String> LOGGED = ConcurrentHashMap.newKeySet();

    private Live242WriteGuard() { }

    /** Quyet dinh THUAN (khong I/O) — de unit test ma tran env. */
    static boolean decide(String enabledVal, String shadowHostVal) {
        if (shadowHostVal != null && "true".equalsIgnoreCase(shadowHostVal.trim())) return false;
        if (enabledVal != null && "false".equalsIgnoreCase(enabledVal.trim())) return false;
        return true;
    }

    /** true = duoc ghi 242 (mac dinh). Doc env qua Cfg dung 1 lan. */
    public static boolean writesEnabled() {
        Boolean d = decided;
        if (d == null) {
            synchronized (Live242WriteGuard.class) {
                d = decided;
                if (d == null) {
                    String en = Cfg.get(KEY_ENABLED);
                    String sh = Cfg.get(KEY_SHADOW_HOST);
                    d = decide(en, sh);
                    decided = d;
                    if (!d) {
                        LOG.info("[NO-WRITE-242] GHI Aerospike 242 BI TAT ({}={} {}={}) — doc 242 giu nguyen.",
                                KEY_SHADOW_HOST, sh, KEY_ENABLED, en);
                    }
                }
            }
        }
        return d;
    }

    /**
     * Goi o DAU moi ham ghi 242. true = ghi tiep (hanh vi cu); false = bo qua (log INFO 1 lan cho {@code what}).
     *
     * @param what ten loai ghi (vd "ai_pred_1m") — chi de log.
     */
    public static boolean allowed(String what) {
        if (writesEnabled()) return true;
        if (LOGGED.add(what)) {
            LOG.info("[NO-WRITE-242] bo qua ghi '{}' vao Aerospike 242 (shadow host). Log 1 lan.", what);
        }
        return false;
    }

    /** CHI cho test: ep trang thai (null = doc lai env lan sau). */
    static void resetForTest(Boolean forced) {
        decided = forced;
        LOGGED.clear();
    }
}
