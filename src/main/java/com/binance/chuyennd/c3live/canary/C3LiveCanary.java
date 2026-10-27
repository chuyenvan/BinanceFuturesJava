package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.alert.C3LiveAlerts;
import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.client.C3LiveClient;
import com.binance.chuyennd.c3live.client.C3LiveClientConfig;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.rate.RateGuard;
import com.binance.chuyennd.c3live.runtime.C3LiveAccountLock;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.TimeZone;
import java.util.function.Function;

/**
 * [V12 3] Cong cu G-CANARY — JVM RIENG (KHONG phai JVM bot), thu muc {@code run/canary/}, chi chay theo lenh script owner
 * ({@code ops/c3live/canary/*.sh}):
 * <pre>
 *   java -cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.c3live.canary.C3LiveCanary &lt;lenh&gt; [K]
 *     keycheck | preflight | setup | step &lt;K1..K8|K6_OPEN|K6_RESTART|K6B_OPEN|K6B_RESTART|K7B&gt; | flatten | cleanup | status
 * </pre>
 * Dong cuoi stdout: {@code RESULT <lenh> DAT|TRUOT|TU_CHOI [| ly do]}. Ma thoat: 0 DAT, 3 TRUOT, 2 TU_CHOI, 4 loi.
 * Lay lock tai khoan con ({@link C3LiveAccountLock}) — runtime c3_live chinh (adapter live) dang giu => TU CHOI.
 * Bien moi truong: CANARY_DIR (run/canary), CANARY_EXPECT_TMB (so da nap, bat buoc cho preflight), CANARY_INJECT_TIMEOUT=1
 * (MO-5, mac dinh tat), LIVE_C3_* cua C3LiveClientConfig (key file root-only), LIVE_C3_WS_URLS, LIVE_C3_ACCOUNT_LOCK.
 * KHONG in key / secret / chu ky / listenKey.
 */
public final class C3LiveCanary {

    private static final Logger LOG = LoggerFactory.getLogger(C3LiveCanary.class);
    /** Dong ket qua cho script (logback-canary.xml: logger CANARY_OUT -> stdout, chi %msg). */
    private static final Logger OUT = LoggerFactory.getLogger("CANARY_OUT");

    /** Dong ket qua cuoi (cho test). */
    static volatile String lastLine;

    static void out(String s) {
        lastLine = s;
        OUT.info(s);
    }

    private C3LiveCanary() {
    }

    public static void main(String[] args) {
        int code;
        try {
            code = run(args, C3LiveCanary::env);
        } catch (Throwable t) {
            LOG.error("[CANARY] loi: {}", t.toString());
            out("RESULT " + (args.length > 0 ? args[0] : "?") + " LOI " + t.getClass().getSimpleName());
            code = 4;
        }
        sleepQuiet(2_000L);   // cho Telegram bat dong bo gui xong
        System.exit(code);
    }

    /**
     * [V12 3b] Bien env cam trong JVM canary. TrailingStopManager goi X14 (tradecore.selector): voi LIVE_PROFILE=c3_shadow|c3_live +
     * LIVE_TS_MKT_EXT=1, X14 doc kline tu Aerospike 242 (DataManagerAerospikeFloatSim, phu thuoc symbol_mapper); TRADING_PROFILE
     * nap profile bot qua Cfg (sai => System.exit). Canary chi kiem co che san => cam ca 3 (script chay JVM bang env -i).
     */
    static final String[] FORBIDDEN_ENV = {"LIVE_PROFILE", "TRADING_PROFILE", "LIVE_TS_MKT_EXT"};

    /**
     * null = env sach. X14 chi BAT khi Cfg(LIVE_TS_MKT_EXT)=1 VA LiveProfileC3.on() (LIVE_PROFILE) — Cfg doc env hoac profile
     * TRADING_PROFILE; cam ca 3 nguon => X14 tat chac chan (khong tham chieu lop X14 o day: test cau truc chi cho 3 file dung X14).
     */
    static String isolationProblem(Function<String, String> env) {
        for (String k : FORBIDDEN_ENV) {
            String v = env.apply(k);
            if (v != null && !v.trim().isEmpty()) return k + " dang dat";
        }
        return null;
    }

    /** [3c MIN-C3] File heartbeat trong CANARY_DIR: "pid=&lt;pid&gt; ms=&lt;epoch ms&gt; cmd=&lt;lenh&gt;". */
    static final String HEARTBEAT_FILE = "canary_jvm.hb";

    /**
     * [3c MIN-C3] Heartbeat cua LUONG CHINH (goi tu sleeper cua engine, toi da 1 lan / 5 s): script flatten chi kill JVM canary
     * (cwd = thu muc canary, giu lock > 10') khi heartbeat cu > 3' — JVM dang chay binh thuong (ke ca K0 65', K4 30') van ghi.
     */
    static final class Heartbeat {
        private final File dir;
        private final String cmd;
        private long last;

        Heartbeat(File dir, String cmd) {
            this.dir = dir;
            this.cmd = cmd;
        }

        synchronized void beat(boolean force) {
            long now = System.currentTimeMillis();
            if (!force && now - last < 5_000L) return;
            last = now;
            try {
                if (!dir.exists() && !dir.mkdirs()) return;
                File tmp = new File(dir, HEARTBEAT_FILE + ".tmp");
                Files.write(tmp.toPath(), ("pid=" + ProcessHandle.current().pid() + " ms=" + now + " cmd=" + cmd + "\n")
                        .getBytes(StandardCharsets.UTF_8));
                Files.move(tmp.toPath(), new File(dir, HEARTBEAT_FILE).toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING,
                        java.nio.file.StandardCopyOption.ATOMIC_MOVE);
            } catch (IOException | RuntimeException e) {
                LOG.warn("[CANARY] khong ghi duoc heartbeat: {}", e.toString());
            }
        }
    }

    /** [3d] {md5, mtimeMs} cua jar chua lop nay (jar canary dang chay); khong phai file .jar => {null, null}. */
    static String[] runningJarId() {
        try {
            File f = new File(C3LiveCanary.class.getProtectionDomain().getCodeSource().getLocation().toURI());
            if (!f.isFile() || !f.getName().endsWith(".jar")) return new String[]{null, null};
            java.security.MessageDigest md = java.security.MessageDigest.getInstance("MD5");
            try (java.io.InputStream in = Files.newInputStream(f.toPath())) {
                byte[] buf = new byte[1 << 16];
                for (int n; (n = in.read(buf)) > 0; ) md.update(buf, 0, n);
            }
            StringBuilder sb = new StringBuilder();
            for (byte b : md.digest()) sb.append(String.format(Locale.ROOT, "%02x", b));
            return new String[]{sb.toString(), String.valueOf(f.lastModified())};
        } catch (Exception e) {
            LOG.warn("[CANARY] khong doc duoc md5 jar: {}", e.toString());
            return new String[]{null, null};
        }
    }

    static String env(String k) {
        String v = System.getenv(k);
        return v != null ? v : System.getProperty(k);
    }

    static int run(String[] args, Function<String, String> env) throws IOException {
        if (args.length == 0) {
            out("RESULT ? TU_CHOI | thieu lenh");
            return 2;
        }
        String cmd = args[0].trim().toLowerCase(Locale.ROOT);
        String iso = isolationProblem(env);
        if (iso != null) {
            out("RESULT " + cmd + " TU_CHOI | env khong sach: " + iso
                    + " — JVM canary phai chay env sach (khong profile bot, khong X14 => khong doc Aerospike/symbol_mapper)");
            return 2;
        }
        File dir = new File(or(env.apply("CANARY_DIR"), "run/canary"));
        if ("status".equals(cmd)) {
            out(CanaryState.load(dir).toJson());
            out("RESULT status DAT");
            return 0;
        }
        File lockFile = new File(or(env.apply(C3LiveAccountLock.KEY_FILE), C3LiveAccountLock.DEFAULT_FILE));
        C3LiveAccountLock lock = C3LiveAccountLock.tryAcquire(lockFile, "c3live-canary " + cmd);
        if (lock == null) {
            out("RESULT " + cmd + " TU_CHOI | lock tai khoan con dang bi giu (" + C3LiveAccountLock.holderInfo(lockFile)
                    + ") — runtime c3_live chinh (adapter live) hoac canary khac dang chay");
            return 2;
        }
        try {
            return runLocked(cmd, args, env, dir);
        } finally {
            lock.release();   // K6/K6b _OPEN: halt() truoc khi toi day (OS nha lock khi JVM chet)
        }
    }

    private static int runLocked(String cmd, String[] args, Function<String, String> env, File dir) throws IOException {
        Heartbeat hb = new Heartbeat(dir, cmd);
        hb.beat(true);
        // [3i] chinh sach canary: nguong IP 1800 (env CANARY_IP_WEIGHT_CAP, kep <= 1920), rieng 600, doc cho <= 2 x 61 s, tranh burst
        String ipRaw = env.apply("CANARY_IP_WEIGHT_CAP");
        int ipCap = CanaryLimits.ipWeightCap(ipRaw);
        if (ipRaw != null && !ipRaw.trim().isEmpty() && !String.valueOf(ipCap).equals(ipRaw.trim())) {
            LOG.warn("[CANARY] CANARY_IP_WEIGHT_CAP='{}' khong hop le / vuot tran {} => dung {}", ipRaw.trim(),
                    CanaryLimits.IP_WEIGHT_ADMIT_MAX, ipCap);
        }
        RateGuard rg = new RateGuard(RateGuard.Limits.binanceDefault(), RateGuard.MAX_FRACTION, 2_000L, RateGuard.SYSTEM,
                new RateGuard.CanaryPolicy(ipCap, CanaryLimits.OWN_WEIGHT_1M_CAP, CanaryLimits.BURST_FROM_SEC, CanaryLimits.BURST_TO_SEC,
                        CanaryLimits.BURST_RESUME_SEC, CanaryLimits.READ_GUARD_MAX_WAITS, CanaryGateway.GUARD_RETRY_MAX_WAIT_MS));
        C3LiveClient client;
        try {
            client = C3LiveClient.create(C3LiveClientConfig.fromEnv(env), rg);
        } catch (Exception e) {
            out("RESULT " + cmd + " TU_CHOI | khong tao duoc client: " + e.getClass().getSimpleName() + ": " + e.getMessage());
            return 2;
        }
        if ("keycheck".equals(cmd)) return keycheck(client, dir);
        C3LiveAlerts tg = new C3LiveAlerts(Utils::sendSms2Telegram);
        CanaryEngine.Deps d = new CanaryEngine.Deps();
        d.raw = client;
        d.dir = dir;
        d.clock = System::currentTimeMillis;
        d.sleeper = ms -> {   // [3c MIN-C3] moi vong ngu cua engine (luong chinh) ghi heartbeat
            hb.beat(false);
            sleepQuiet(ms);
        };
        d.connector = UserStream.okHttp(60_000L);
        d.wsUrls = UserStream.parseUrls(or(env.apply("LIVE_C3_WS_URLS"), UserStream.DEFAULT_URLS));
        d.alert = tg::send;
        Set<String> legSet = legacySet(new File(or(env.apply("LIVE_LEGACY_FILE"), "run/legacy_symbols.csv")));
        d.legacy = legSet::contains;
        d.legacySize = legSet.size();   // [3g MIN-8] rong / thieu => K0 TU CHOI tren tai khoan chinh
        d.usedWeight1m = rg::lastServerWeight1m;
        d.rateGuard = rg;   // [3e] so lieu lan khan cap vao data buoc
        // [3f §ADD-4 J] key RIENG tai khoan chinh tu C3LiveClientConfig (keys.env) — KHONG dung PrivateConfig / key LEGACY
        d.journalName = "canary_" + ts() + "_" + cmd + (args.length > 1 ? "_" + args[1].replaceAll("[^A-Za-z0-9_]", "") : "") + ".jsonl";
        CanaryEngine.Config cfg = new CanaryEngine.Config();
        String et = env.apply("CANARY_EXPECT_TMB");
        if (et != null && !et.trim().isEmpty()) cfg.expectTmb = Double.parseDouble(et.trim());
        cfg.injectTimeout = "1".equals(or(env.apply("CANARY_INJECT_TIMEOUT"), "0").trim());
        cfg.reuseKeepAlive = "1".equals(or(env.apply("CANARY_K0_REUSE_KEEPALIVE"), "0").trim());   // [3d §ADD-3] engine tu kiem
        String pl = env.apply("CANARY_PRIOR_LOSS_USDT");   // [3g MIN-3] lo cong don cac phien truoc (script tinh)
        if (pl != null && !pl.trim().isEmpty()) cfg.priorLossUsdt = Double.parseDouble(pl.trim());
        d.jarId = C3LiveCanary::runningJarId;
        CanaryEngine e = new CanaryEngine(d, cfg);
        CanaryEngine.Result r;
        switch (cmd) {
            case "preflight": r = e.preflight(); break;
            case "setup": r = e.setup(); break;
            case "step":
                if (args.length < 2) {
                    out("RESULT step TU_CHOI | thieu ten buoc K");
                    return 2;
                }
                r = e.step(args[1]);
                break;
            case "flatten": r = e.flatten(); break;
            case "cleanup": r = e.cleanupCheck(); break;
            default:
                out("RESULT " + cmd + " TU_CHOI | lenh khong ho tro");
                return 2;
        }
        out("JOURNAL " + e.journal().file().getPath());
        out("DATA " + new com.google.gson.Gson().toJson(CanaryJournal.sanitize(r.data)));
        out(r.line());
        if ("step".equals(cmd) && args[1].toUpperCase(Locale.ROOT).endsWith("_OPEN") && r.ok()) {
            // K6/K6b: gia lap JVM chet dot ngot (khong shutdown hook, khong dong stream/so) — buoc _RESTART chay JVM moi
            sleepQuiet(2_000L);
            Runtime.getRuntime().halt(0);
        }
        e.close();
        return r.ok() ? 0 : (CanaryEngine.TU_CHOI.equals(r.verdict) ? 2 : 3);
    }

    /**
     * Doc thu key (chi doc): gio server, tmb, multiAssets, dual + [3d] so vi the != 0 / lenh mo / algo mo toan tai khoan
     * ({@code pos= orders= algos=}, de canary_early_all.sh kiem "tai khoan phang" ma KHONG ghi buoc vao state). Khong in key.
     */
    static int keycheck(C3LiveClient c, File dir) {
        try {
            long st = c.serverTime();
            AccountSnapshot a = c.account();
            boolean multi = c.multiAssetsMargin();
            boolean dual = c.dualSidePosition();
            // [3f §ADD-4 C] "phang" = PHAM VI CANARY (2 symbol trong state + cid canary o moi noi); LEGACY chi dem
            Set<String> scope = new HashSet<>();
            try {
                CanaryState s = CanaryState.load(dir);
                if (s.symbolsChosen() && !s.canaryQty.isEmpty()) {   // [3g MIN-5] phien truoc 3f (tai khoan cu): pham vi = cid canary
                    scope.add(s.symMain);
                    scope.add(s.symAux);
                }
            } catch (IOException | RuntimeException e) {
                LOG.warn("[CANARY] keycheck: khong doc duoc trang thai phien ({}) => pham vi = cid canary", e.getClass().getSimpleName());
            }
            int pos = 0, lpos = 0, ord = 0, lord = 0, alg = 0, lalg = 0;
            for (PositionInfo p : c.positions()) {
                if (p.getPositionAmt() == null || p.getPositionAmt().signum() == 0) continue;
                if (scope.contains(p.getSymbol())) pos++; else lpos++;
            }
            for (com.binance.chuyennd.c3live.api.OrderInfo o : c.openOrders(null)) {
                if (scope.contains(o.getSymbol()) || CanaryGateway.canaryAnyCid(o.getClientOrderId())) ord++; else lord++;
            }
            for (com.binance.chuyennd.c3live.api.OrderInfo o : c.openStops(null)) {
                if (scope.contains(o.getSymbol()) || CanaryGateway.canaryAnyCid(o.getClientOrderId())) alg++; else lalg++;
            }
            out("KEYCHECK serverTime=" + st + " tmb=" + a.getTotalMarginBalance() + " avail=" + a.getAvailableBalance()
                    + " multiAssets=" + multi + " dual=" + dual + " assets=" + CanaryEngine.assetMap(a)
                    + " scope=" + (scope.isEmpty() ? "cid_canary" : String.join(",", new java.util.TreeSet<>(scope)))
                    + " legacy=pos:" + lpos + ",orders:" + lord + ",algos:" + lalg + " pos=" + pos + " orders=" + ord + " algos=" + alg);
            out("RESULT keycheck DAT");
            return 0;
        } catch (RuntimeException e) {
            out("RESULT keycheck TRUOT | " + e.getClass().getSimpleName() + ": " + e.getMessage());
            return 3;
        }
    }

    /** Tap LEGACY tai khoan chinh (file run/legacy_symbols.csv: symbol dau moi dong). Thieu file => rong. */
    static Set<String> legacySet(File f) {
        Set<String> s = new HashSet<>();
        if (!f.exists()) return s;
        try {
            for (String line : Files.readAllLines(f.toPath(), StandardCharsets.UTF_8)) {
                String t = line.trim();
                if (t.isEmpty() || t.startsWith("#")) continue;
                String sym = t.split("[,;\\s]")[0].trim().toUpperCase(Locale.ROOT);
                if (!sym.isEmpty() && !"SYMBOL".equals(sym)) s.add(sym);
            }
        } catch (IOException e) {
            LOG.warn("[CANARY] khong doc duoc {}: {}", f.getPath(), e.toString());
        }
        return s;
    }

    static String ts() {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.ROOT);
        f.setTimeZone(TimeZone.getTimeZone("Asia/Ho_Chi_Minh"));
        return f.format(new Date());
    }

    static String or(String v, String def) {
        return v == null || v.trim().isEmpty() ? def : v.trim();
    }

    static void sleepQuiet(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        }
    }
}
