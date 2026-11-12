"""R4u3 C3-EXCL-FORCE: adapter=live + C3_EXCLUDE_LEGACY_HELD=false + key KHONG phai keys_sub.env => ep true."""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
P = "src/main/java/com/binance/chuyennd/tradecore/selector/LegacySymbols.java"
s = open(P, "rb").read().decode("utf-8")
old = """        Boolean c = excludeCached;
        if (c == null) {
            c = parseExclude(Cfg.get(KEY_EXCLUDE));
            excludeCached = c;
        }
        return c;
    }
"""
new = """        Boolean c = excludeCached;
        if (c == null) {
            synchronized (LegacySymbols.class) {
                c = excludeCached;
                if (c == null) {
                    boolean env = parseExclude(Cfg.get(KEY_EXCLUDE));
                    boolean live = com.binance.chuyennd.c3live.adapter.GatewayFactory.Mode.parse(
                            Cfg.get(com.binance.chuyennd.c3live.adapter.GatewayFactory.KEY_ADAPTER))
                            == com.binance.chuyennd.c3live.adapter.GatewayFactory.Mode.LIVE;
                    String kf = System.getenv(KEY_KEYS_FILE);   // cung nguon C3LiveClientConfig.fromEnv
                    if (kf == null) kf = System.getProperty(KEY_KEYS_FILE);
                    String why = forceReason(env, live, kf, LegacySymbols::canonical);
                    if (why != null) {
                        LOG.warn("[C3-EXCL-FORCE] C3_EXCLUDE_LEGACY_HELD=false bi EP ve true: {}", why);
                    }
                    c = env || why != null;
                    excludeCached = c;
                }
            }
        }
        return c;
    }

    // ===================== [V12 R4u3 C3-EXCL-FORCE 2026-11-10] =====================
    /** Env file key c3 (= C3LiveClientConfig.fromEnv). Vang => jar dung C3LiveKeys.DEFAULT_PATH = keys.env tk CHINH. */
    public static final String KEY_KEYS_FILE = "LIVE_C3_KEYS_FILE";
    /** Ten file key tk CON (ADD4). Chi file chinh tac co DUNG ten nay moi duoc coi la SUB. */
    public static final String SUB_KEYS_NAME = "keys_sub.env";

    /** Duong dan chinh tac (realpath, theo symlink); file chua co => tuyet doi + normalize. KHONG doc noi dung. */
    static String canonical(String p) {
        try {
            return java.nio.file.Paths.get(p).toRealPath().toString();
        } catch (Exception e) {
            try {
                return java.nio.file.Paths.get(p).toAbsolutePath().normalize().toString();
            } catch (Exception e2) {
                return p;
            }
        }
    }

    /**
     * Thuan: ly do EP {@code true} hoac null. Chi ep khi env=false VA adapter=live VA key KHONG phai tk con:
     * LIVE_C3_KEYS_FILE vang/rong, hoac ten file chinh tac != keys_sub.env (vd keys.env, symlink sang keys.env).
     * adapter khac live (dry/off) => giu dung env.
     */
    static String forceReason(boolean envExclude, boolean liveAdapter, String keysFileRaw,
                              java.util.function.Function<String, String> canon) {
        if (envExclude || !liveAdapter) return null;
        String f = keysFileRaw == null ? null : keysFileRaw.trim();
        if (f == null || f.isEmpty()) {
            return "adapter=live va LIVE_C3_KEYS_FILE vang => jar dung key mac dinh keys.env (tk CHINH)";
        }
        String c = canon == null ? f : canon.apply(f);
        java.nio.file.Path fn = c == null ? null : java.nio.file.Paths.get(c).getFileName();
        String name = fn == null ? null : fn.toString();
        if (!SUB_KEYS_NAME.equals(name)) {
            return "adapter=live va LIVE_C3_KEYS_FILE=" + f + " (chinh tac " + c + ") khong phai " + SUB_KEYS_NAME
                    + " => coi la tk CHINH";
        }
        return null;
    }

    /** Thuan: gia tri hieu luc cua C3_EXCLUDE_LEGACY_HELD. */
    static boolean effectiveExclude(String envRaw, boolean liveAdapter, String keysFileRaw,
                                    java.util.function.Function<String, String> canon) {
        boolean env = parseExclude(envRaw);
        return env || forceReason(env, liveAdapter, keysFileRaw, canon) != null;
    }
"""
assert s.count(old) == 1
s = s.replace(old, new)
open(P, "wb").write(s.encode("utf-8"))
logging.info("PATCH4_OK")
