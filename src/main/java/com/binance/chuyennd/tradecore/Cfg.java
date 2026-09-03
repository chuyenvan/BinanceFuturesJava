package com.binance.chuyennd.tradecore;

import java.io.BufferedReader;
import java.io.FileReader;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * CONG DUY NHAT de doc cau hinh runtime (2026-09-03).
 *
 * <p>Ly do ton tai: truoc day tham so nam rai rac o 3 tang (hardcode Java / config.properties / env SIM_*)
 * va duoc doc o 25+ file => khong ai nhin duoc gia tri hieu dung. Hai ket luan sai (clamp AI_DYNAMIC_MAX
 * bien gate thanh hang so; "nguong 0.008" khong phai nguong that) deu tu do ma ra.
 *
 * <p>Cach dung:
 * <pre>
 *   TRADING_PROFILE=/duong/dan/profile.properties java -cp ... &lt;MainClass&gt;
 * </pre>
 * Khi TRADING_PROFILE duoc dat: profile la NGUON SU THAT DUY NHAT.
 * <ul>
 *   <li>{@link #get(String)} tra ve gia tri trong profile (null neu khong khai bao) — KHONG doc env nua.</li>
 *   <li>Neu con bien env "tham so giao dich" ({@link #TRADING_PREFIXES} / {@link #TRADING_KEYS}) => DUNG NGAY
 *       (fail-fast), tranh canh hai nguon cung ton tai.</li>
 *   <li>Bien ha tang ({@link #INFRA_KEYS}: duong dan du lieu, dataset, kill-switch...) van doc tu env nhu cu.</li>
 *   <li>{@link #auditProfile()} bao key khai bao trong profile ma KHONG AI DOC (bat loi go sai ten key —
 *       truoc day mot key go sai chi am tham roi ve default, khong ai biet).</li>
 * </ul>
 * Khi KHONG dat TRADING_PROFILE: hanh vi y het truoc day (doc env) => tuong thich nguoc, parity byte-identical.
 *
 * <p>QUY TAC BAT BUOC: moi tham so GIAO DICH phai doc qua {@code Cfg.get}/{@code Cfg.getOr}, KHONG duoc
 * goi {@code System.getenv} truc tiep — neu khong, profile khong kiem soat duoc no va ta lai co cau hinh "an".
 * Script {@code tools/check_cfg_gateway.sh} kiem dieu nay va fail build khi bi vi pham.
 */
public final class Cfg {

    /** Bien env thuoc nhom "ha tang"/kill-switch — khong phai tham so giao dich, van cho phep dat qua env. */
    private static final List<String> INFRA_KEYS = Arrays.asList(
            "WFO_DATA_DIR", "WFO_SMART_CACHE", "WFO_CODE_SHA", "WFO_SET_PRED",
            "WFO_SEL_HORIZON_IDX", "WFO_STATIC_RANK", "WFO_COINTIER_FILE", "WFO_STATE_HOST", "WFO_LEAKFREE_FROM",
            "WFO_MAX_OOS_DATE", "WFO_MAX_WINDOWS", "WFO_N_SAMPLES", "WFO_LOG_ENTRIES", "WFO_HARNESS_FIX",
            "WFO_DISABLE_DCA", "WFO_FROZEN_GENOME", "EXCHANGE_INFO_PATH", "HOLDOUT_UNSEAL", "TRADING_PROFILE",
            "SIM_END_DATE", "HOME", "APP_PID_DIR", "APP_MAIN_CLASS", "GEN_THREADS", "NO_VALIDATE",
            "CONFIG_STRICT", "SHADOW_NO_PUSH", "OI_STALE_HALT", "OI_STALE_HALT_MS");

    /** Tien to cua bien env DUOC COI LA THAM SO GIAO DICH — cam dat khi da co profile. */
    private static final List<String> TRADING_PREFIXES = Arrays.asList(
            "SIM_", "DCA_", "TS_", "SELECTOR_", "TIER_", "CONF_SIZE_", "TRAIL_", "GATE_", "LIVE_",
            "SIZE_MULT", "MAX_CONCURRENT", "TIME_STOP_HOURS", "ENABLE_SHORT", "ABLATION_MODE", "SHORT_");

    /** Tham so giao dich co ten KHONG khop tien to nao o tren — phai liet ke dich danh. */
    private static final List<String> TRADING_KEYS = Arrays.asList(
            "NUMBER_ORDER_BUDGET", "HARD_STOP_LOSS_RATE", "DISABLE_PREDICT_SYMBOL", "CAPITAL_START",
            "SEL_BACKTEST_SET", "SEL_BACKTEST_HORIZON_IDX",
            // 2026-09-03: WFO_FUNDING_PRED_DIR ROI khoi INFRA_KEYS sang day. Ly do: no la BIEN
            // QUYET DINH cua selector S1 (+7.35pp CAGR / maxDD -13.12 vs -20.82 so voi G015 o
            // cung thang exit C2b), khong phai duong dan ha tang. Truoc day no o INFRA_KEYS nen
            // dat tuy y qua env, khong duoc pin trong profile, va CONFIG_HASH/PROFILE_HASH khong
            // he doi khi doi selector => khong truy nguyen duoc. Xem docs/AUDIT_APPLIED.md 3.3(a).
            "WFO_FUNDING_PRED_DIR");

    private static final Map<String, String> PROFILE;   // null neu khong dung profile
    private static final String PROFILE_PATH;
    private static final String PROFILE_HASH;
    /** Cac key da tung duoc code hoi — dung de bat key khai bao nhung khong ai doc. */
    private static final Set<String> ASKED = Collections.synchronizedSet(new TreeSet<String>());

    static {
        String p = System.getenv("TRADING_PROFILE");
        PROFILE_PATH = (p == null || p.trim().isEmpty()) ? null : p.trim();
        Map<String, String> m = null;
        String hash = "-";
        if (PROFILE_PATH != null) {
            m = new LinkedHashMap<>();
            try (BufferedReader br = new BufferedReader(new FileReader(PROFILE_PATH))) {
                String line;
                int no = 0;
                while ((line = br.readLine()) != null) {
                    no++;
                    String s = line.trim();
                    if (s.isEmpty() || s.startsWith("#")) continue;
                    int i = s.indexOf('=');
                    if (i <= 0) throw new IllegalStateException("profile dong " + no + " sai dinh dang: " + s);
                    String k = s.substring(0, i).trim();
                    String v = s.substring(i + 1).trim();
                    if (m.put(k, v) != null) throw new IllegalStateException("profile khai bao TRUNG key: " + k);
                }
            } catch (Exception e) {
                System.err.println("[CFG] KHONG doc duoc TRADING_PROFILE=" + PROFILE_PATH + ": " + e);
                System.exit(2);
            }
            // fail-fast: con env tham so giao dich => hai nguon su that
            List<String> conflicts = new ArrayList<>();
            for (String k : System.getenv().keySet()) {
                if (INFRA_KEYS.contains(k)) continue;
                if (TRADING_KEYS.contains(k)) { conflicts.add(k); continue; }
                for (String pre : TRADING_PREFIXES) {
                    if (k.startsWith(pre)) { conflicts.add(k); break; }
                }
            }
            Collections.sort(conflicts);
            if (!conflicts.isEmpty()) {
                System.err.println("[CFG] DUNG: da dung TRADING_PROFILE nhung van con env tham so giao dich: " + conflicts);
                System.err.println("[CFG] Moi tham so phai khai bao trong profile. Bo cac env tren roi chay lai.");
                System.exit(2);
            }
            hash = sha8(new TreeMap<>(m).toString());
            System.out.println("[CFG] profile=" + PROFILE_PATH + " keys=" + m.size() + " PROFILE_HASH=" + hash);
        }
        PROFILE = m;
        PROFILE_HASH = hash;
    }

    private Cfg() { }

    /** Doc 1 tham so. Co profile -> chi lay tu profile (null neu khong khai bao). Khong co -> doc env (hanh vi cu). */
    public static String get(String key) {
        ASKED.add(key);
        if (PROFILE != null) {
            if (INFRA_KEYS.contains(key)) return System.getenv(key);
            return PROFILE.get(key);
        }
        return System.getenv(key);
    }

    /** Nhu {@link #get(String)} nhung tra {@code def} khi khong khai bao (thay System.getenv().getOrDefault). */
    public static String getOr(String key, String def) {
        String v = get(key);
        return (v == null || v.isEmpty()) ? def : v;
    }

    public static boolean usingProfile() { return PROFILE != null; }

    public static String profilePath() { return PROFILE_PATH; }

    public static String profileHash() { return PROFILE_HASH; }

    /** Cac key co trong profile. */
    public static Map<String, String> all() {
        return PROFILE == null ? Collections.emptyMap() : Collections.unmodifiableMap(PROFILE);
    }

    /** Cac key ma code da tung hoi (sau khi Configs da nap xong = toan bo key he doc). */
    public static Set<String> asked() {
        return Collections.unmodifiableSet(new TreeSet<>(ASKED));
    }

    /**
     * Bao key khai bao trong profile ma KHONG AI DOC — gan nhu chac chan la GO SAI TEN KEY
     * (truoc day loi nay am tham: key sai ten -> code roi ve default -> run "thanh cong" voi cau hinh khac y).
     * Tra ve so key mo. CONFIG_STRICT=1 -> exit 2.
     */
    public static int auditProfile() {
        if (PROFILE == null) return 0;
        List<String> unread = new ArrayList<>();
        for (String k : PROFILE.keySet()) if (!ASKED.contains(k)) unread.add(k);
        Collections.sort(unread);
        if (!unread.isEmpty()) {
            System.err.println("[CFG] CANH BAO: profile khai bao " + unread.size()
                    + " key KHONG AI DOC (go sai ten?): " + unread);
            if ("1".equals(System.getenv("CONFIG_STRICT"))) {
                System.err.println("[CFG] CONFIG_STRICT=1 -> DUNG.");
                System.exit(2);
            }
        } else {
            System.out.println("[CFG] audit profile: OK, ca " + PROFILE.size() + " key deu duoc doc.");
        }
        return unread.size();
    }

    private static String sha8(String s) {
        try {
            byte[] h = MessageDigest.getInstance("SHA-256").digest(s.getBytes("UTF-8"));
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 8; i++) sb.append(String.format("%02x", h[i]));
            return sb.toString();
        } catch (Exception e) {
            return "?";
        }
    }
}
