package com.binance.chuyennd.c3live.e2e.replay;

import com.binance.chuyennd.tradecore.selector.LiveDcaGridC3;
import com.binance.chuyennd.tradecore.selector.LiveGridSizing;
import com.google.gson.GsonBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * [E2E_V12] Driver 1 luot replay (prereg PREREG_E2E_REPLAY_V12 §1/§4). Chay bang {@code java -cp <JAR r4u3fin2>:target/test-classes}
 * (KHONG target/classes) qua tools/e2e/run_lane.sh — moi luot 1 JVM rieng (class production doc env 1 lan luc nap).
 * <ol>
 *   <li>Kiem jar: md5 file jar chua C3LiveEntry == E2E_JAR_MD5 (mac dinh 641803565297d4065d90245e04a00f11); 10 class then chot
 *       nap tu CHINH jar do (ClassLoader.getResource + CodeSource); classpath khong co target/classes. Sai => ghi refused.json, exit 3.</li>
 *   <li>Env: doc file danh sach trang 242 (E2E_ENV242, dong {@code export K=V}); ghi ten thieu / gia tri khac (tru override khai truoc).</li>
 *   <li>Nap som LiveGridSizing / LiveDcaGridC3 (banner INFO truoc khi LogCapture ha muc log); in dong [MINUTE-FIN] (harness) bang
 *       bieu thuc production {@code MinuteCompletenessGuard.enabled() && finEnabled()}.</li>
 * </ol>
 * Khong goi main() cua jar, khong REST/WS/Aerospike that.
 */
public final class ReplayMain {

    private static final Logger LOG = LoggerFactory.getLogger(ReplayMain.class);
    static final String DEFAULT_MD5 = "641803565297d4065d90245e04a00f11";
    static final String[] KEY_CLASSES = {
            "com.binance.chuyennd.c3live.entry.C3LiveEntry",
            "com.binance.chuyennd.c3live.runtime.C3LiveRuntime",
            "com.binance.chuyennd.tradecore.selector.LiveGridSizing",
            "com.binance.chuyennd.tradecore.selector.LiveDcaGridC3",
            "com.binance.chuyennd.tradecore.DcaUtils",
            "com.binance.chuyennd.tradecore.EntryGate",
            "com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter",
            "com.binance.chuyennd.trading.GatePreFilter",
            "com.binance.chuyennd.c3live.exit.TrailingStopManager",
            "com.binance.chuyennd.ai_ml.onnx.entry.LiveGateRollingRatio"};

    private ReplayMain() {
    }

    static String env(String k, String def) {
        String v = System.getenv(k);
        return v == null || v.trim().isEmpty() ? def : v.trim();
    }

    static long envL(String k, long def) {
        return Long.parseLong(env(k, Long.toString(def)));
    }

    static String md5(File f) throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
        try (InputStream in = new FileInputStream(f)) {
            byte[] buf = new byte[1 << 20];
            int n;
            while ((n = in.read(buf)) > 0) md.update(buf, 0, n);
        }
        StringBuilder sb = new StringBuilder();
        for (byte b : md.digest()) sb.append(String.format("%02x", b));
        return sb.toString();
    }

    /** Kiem jar + 10 class. Tra map ket qua; key "ok" = Boolean. */
    static Map<String, Object> jarCheck() throws Exception {
        Map<String, Object> m = new LinkedHashMap<>();
        String expect = env("E2E_JAR_MD5", DEFAULT_MD5);
        List<String> problems = new ArrayList<>();
        Class<?> c0 = Class.forName(KEY_CLASSES[0], false, ReplayMain.class.getClassLoader());
        File jar = new File(c0.getProtectionDomain().getCodeSource().getLocation().toURI());
        String md5 = jar.isFile() ? md5(jar) : "NOT_A_FILE";
        m.put("jar_path", jar.getAbsolutePath());
        m.put("jar_md5", md5);
        m.put("jar_md5_expected", expect);
        if (!expect.equals(md5)) problems.add("md5 jar " + md5 + " != " + expect);
        String cp = System.getProperty("java.class.path");
        m.put("java_class_path", cp);
        for (String e : cp.split(File.pathSeparator)) {
            if (e.replace('\\', '/').matches(".*/target/classes/?$")) problems.add("classpath co target/classes: " + e);
        }
        String jarUrl = "jar:" + jar.toURI().toURL().toString() + "!/";
        Map<String, String> res = new LinkedHashMap<>();
        for (String cn : KEY_CLASSES) {
            String path = cn.replace('.', '/') + ".class";
            URL u = ClassLoader.getSystemClassLoader().getResource(path);
            Class<?> c = Class.forName(cn, false, ReplayMain.class.getClassLoader());
            String src = String.valueOf(c.getProtectionDomain().getCodeSource().getLocation());
            res.put(cn, String.valueOf(u) + " | codeSource=" + src);
            if (u == null || !u.toString().startsWith(jarUrl)) problems.add(cn + " getResource ngoai jar: " + u);
            if (!new File(c.getProtectionDomain().getCodeSource().getLocation().toURI()).getAbsolutePath()
                    .equals(jar.getAbsolutePath())) problems.add(cn + " codeSource ngoai jar: " + src);
        }
        m.put("class_resources", res);
        m.put("classes_from_jar", res.size() - countPrefix(problems, "com.binance"));
        m.put("problems", problems);
        m.put("ok", problems.isEmpty());
        return m;
    }

    static int countPrefix(List<String> l, String p) {
        int n = 0;
        for (String s : l) if (s.startsWith(p)) n++;
        return n;
    }

    /** Doi chieu env tien trinh voi file danh sach trang 242 (gia tri cuoi cung thang, nhu bash source). */
    static Map<String, Object> envCheck() throws Exception {
        Map<String, Object> m = new LinkedHashMap<>();
        String f = env("E2E_ENV242", "");
        Map<String, String> w = new TreeMap<>();
        if (!f.isEmpty()) {
            for (String ln : Files.readAllLines(new File(f).toPath(), StandardCharsets.UTF_8)) {
                String s = ln.trim();
                if (s.startsWith("export ")) s = s.substring(7).trim();
                int i = s.indexOf('=');
                if (i <= 0) continue;
                w.put(s.substring(0, i), s.substring(i + 1));
            }
        }
        TreeSet<String> ov = new TreeSet<>(Arrays.asList(env("E2E_OVERRIDES", "").split(",")));
        ov.remove("");
        TreeSet<String> missing = new TreeSet<>();
        Map<String, String> differ = new TreeMap<>();
        for (Map.Entry<String, String> e : w.entrySet()) {
            String v = System.getenv(e.getKey());
            if (v == null) {
                if (!ov.contains(e.getKey())) missing.add(e.getKey());
            } else if (!v.equals(e.getValue()) && !ov.contains(e.getKey())) {
                differ.put(e.getKey(), "242=" + e.getValue() + " replay=" + v);
            }
        }
        Map<String, String> ovv = new TreeMap<>();
        for (String k : ov) ovv.put(k, System.getenv(k) == null ? "<unset>" : System.getenv(k));
        m.put("env242_file", f);
        m.put("env242_names", w.keySet());
        m.put("overrides_declared", ovv);
        m.put("missing_names_not_overridden", missing);
        m.put("differ_not_overridden", differ);
        return m;
    }

    /** [ERRATA1 E5] config.properties cua luot (tools/e2e/config_replay.properties): key -> "[NHAN] gia tri" (nhan = comment # [X]). */
    static Map<String, String> cfgProps(File f) throws Exception {
        Map<String, String> m = new LinkedHashMap<>();
        if (!f.isFile()) return m;
        String tag = "?";
        for (String ln : Files.readAllLines(f.toPath(), StandardCharsets.UTF_8)) {
            String s = ln.trim();
            if (s.startsWith("# [")) {
                int e = s.indexOf(']');
                if (e > 3) tag = s.substring(3, e);
                continue;
            }
            if (s.isEmpty() || s.startsWith("#")) continue;
            int i = s.indexOf('=');
            if (i > 0) m.put(s.substring(0, i).trim(), "[" + tag + "] " + s.substring(i + 1).trim());
        }
        return m;
    }

    /** md5 file (null neu duong dan rong; "KHONG_CO" neu khong ton tai). */
    static String fileMd5(String path) throws Exception {
        if (path == null || path.isEmpty()) return null;
        File f = new File(path);
        return f.isFile() ? md5(f) : "KHONG_CO";
    }

    /** [ERRATA3 E9] json nguon (E2E_LEGACY_META) + trang thai LegacySymbols cua jar (cung ham production blocksC3 doc). */
    static Map<String, Object> legacyInfo() throws Exception {
        Map<String, Object> m = new LinkedHashMap<>();
        String meta = env("E2E_LEGACY_META", "");
        m.put("meta_file", meta);
        if (!meta.isEmpty() && new File(meta).isFile()) {
            m.put("nguon", new com.google.gson.Gson().fromJson(new String(Files.readAllBytes(new File(meta).toPath()),
                    StandardCharsets.UTF_8), Map.class));
        }
        com.binance.chuyennd.tradecore.selector.LegacySymbols ls = com.binance.chuyennd.tradecore.selector.LegacySymbols.getInstance();
        m.put("jar_excludeLegacyHeld", com.binance.chuyennd.tradecore.selector.LegacySymbols.excludeLegacyHeld());
        m.put("jar_LiveProfileC3_on", com.binance.chuyennd.tradecore.selector.LiveProfileC3.on());
        m.put("jar_file", new File(ls.path()).getAbsolutePath());
        m.put("jar_file_md5", fileMd5(new File(ls.path()).getAbsolutePath()));
        m.put("jar_n", ls.size());
        m.put("jar_symbols", ls.all());
        return m;
    }

    public static void main(String[] args) throws Exception {
        String name = env("E2E_RUN", "R0");
        File fx = new File(env("E2E_FX_DIR", System.getProperty("user.home") + "/claude_master/e2e1105/fx"));
        File outRoot = new File(env("E2E_OUT", System.getProperty("user.home") + "/claude_master/e2e_v12/out"));
        File out = new File(outRoot, name);
        out.mkdirs();
        Map<String, Object> jc = jarCheck();
        Map<String, Object> ec = envCheck();
        if (!Boolean.TRUE.equals(jc.get("ok"))) {
            Map<String, Object> r = new LinkedHashMap<>();
            r.put("refused", true);
            r.put("jar_check", jc);
            r.put("env_check", ec);
            Files.write(new File(out, "refused.json").toPath(), new GsonBuilder().setPrettyPrinting().create().toJson(r)
                    .getBytes(StandardCharsets.UTF_8));
            System.err.println("[E2E_V12] TU CHOI CHAY: " + jc.get("problems"));
            System.exit(3);
        }
        // banner cau hinh (INFO) TRUOC khi LogCapture ha com.binance xuong WARN
        boolean sizing = LiveGridSizing.on();
        boolean grid = LiveDcaGridC3.active();
        boolean fin = com.binance.chuyennd.aerospike.MinuteCompletenessGuard.enabled()
                && com.binance.chuyennd.aerospike.MinuteCompletenessGuard.finEnabled();
        LOG.warn("[MINUTE-FIN] {} [harness: MinuteCompletenessGuard.enabled() && finEnabled() tu jar; banner production in o "
                + "DetectEntrySignal2TradeNormal.start, vong main khong chay]", fin ? "BAT" : "TAT");
        LOG.warn("[E2E_V12] run={} LiveGridSizing.on={} LiveDcaGridC3.active={} fin={}", name, sizing, grid, fin);
        if (!new File(fx, "mkt.csv.gz").isFile()) {
            System.err.println("[E2E_V12] TU CHOI CHAY: fixture thieu mkt.csv.gz (ERRATA1 N6: dieu kien thi truong DCA)");
            System.exit(3);
        }
        ReplayData d = new ReplayData(fx);
        d.flatExt = "1".equals(env("E2E_FLAT_EXT", "0"));
        CrashDayRig.Opts o = new CrashDayRig.Opts();
        o.name = name;
        o.venue = CrashDayRig.Venue.valueOf(env("E2E_VENUE", "FAKE"));
        o.end = envL("E2E_END", ReplayData.END);
        o.sDcaAt = envL("E2E_SDCA_AT", -1L);
        o.sDcaN = (int) envL("E2E_SDCA_N", 2L);
        o.finInjAt = envL("E2E_FIN_INJ_AT", -1L);
        // [ADD24 R-LIVE] tiem chan phut tu log live (csv decision_ts,symbol,level,kind; symbol/level "*" = moi)
        String lbf = env("E2E_LIVE_BLOCK_FILE", "");
        if (!lbf.isEmpty()) {
            for (String ln : Files.readAllLines(new File(lbf).toPath(), StandardCharsets.UTF_8)) {
                String[] x = ln.trim().split(",");
                if (x.length < 3 || !x[0].matches("\\d+")) continue;
                o.liveBlock.computeIfAbsent(Long.parseLong(x[0]), k -> new java.util.TreeSet<>()).add(x[1] + "|" + x[2]);
            }
            LOG.warn("[ADD24] E2E_LIVE_BLOCK_FILE={} phut={}", lbf, o.liveBlock.size());
        }
        o.fullFromLive = "1".equals(env("E2E_FULL_FROM_LIVE", "0"));   // [ADD24 ERRATA5 D1]
        // [ADD24 L0-FOLLOW-lite] csv cid,avg (gia khop that lenh MUA) - chi co nghia voi venue FAKE
        String fpf = env("E2E_FOLLOW_FILLS", "");
        if (!fpf.isEmpty()) {
            for (String ln : Files.readAllLines(new File(fpf).toPath(), StandardCharsets.UTF_8)) {
                String[] x = ln.trim().split(",");
                if (x.length < 2 || !x[0].startsWith("c3-")) continue;
                o.followPx.put(x[0], new java.math.BigDecimal(x[1]));
            }
            LOG.warn("[ADD24] E2E_FOLLOW_FILLS={} n={}", fpf, o.followPx.size());
        }
        CrashDayRig r = new CrashDayRig(o, d, outRoot);
        r.res.put("prereg", "PREREG_E2E_REPLAY_V12 (vz_e1_wt ea6c7a5b) + ERRATA1 (33633d41) + ERRATA2 (593e7f45) + ERRATA3 (409e1144)");
        // [ERRATA3 E11] md5 file gia tri env 242 da dung + md5 labels_1105.csv (khai truoc, commit truoc luot chinh thuc)
        r.res.put("env242_file_md5", fileMd5(env("E2E_ENV242", "")));
        r.res.put("labels_1105_file", env("E2E_LABELS_FILE", ""));
        r.res.put("labels_1105_md5", fileMd5(env("E2E_LABELS_FILE", "")));
        // [ERRATA3 E9] R-OLD: nguon danh sach LEGACY (legacy_src.py) + tap jar THAT SU nap (LegacySymbols, file run/legacy_symbols.csv)
        r.res.put("legacy_E9", legacyInfo());
        r.res.put("errata_mo_lai", env("E2E_ERRATA", ""));
        r.res.put("official_lock", env("E2E_OFFICIAL_LOCK", ""));
        r.res.put("config_properties_replay", cfgProps(new File("config.properties")));
        r.res.put("worktree_config_keys_KHONG_doc", env("E2E_WT_CFG_KEYS", ""));
        r.res.put("fixture_dir", fx.getAbsolutePath());
        r.res.put("fixture_START", ReplayData.START);
        r.res.put("fixture_END", ReplayData.END);
        r.res.put("jar_check", jc);
        r.res.put("env_check", ec);
        r.res.put("banners_harness", "LiveGridSizing.on=" + sizing + " LiveDcaGridC3.active=" + grid + " fin=" + fin);
        long t0 = System.currentTimeMillis();
        r.run();
        LOG.warn("[E2E_V12] run={} xong {} ms; ket qua {}", name, System.currentTimeMillis() - t0, out);
        System.exit(0);
    }
}
