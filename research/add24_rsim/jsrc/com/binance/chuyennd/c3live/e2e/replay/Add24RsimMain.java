package com.binance.chuyennd.c3live.e2e.replay;

import com.binance.chuyennd.tradecore.selector.LiveDcaGridC3;
import com.binance.chuyennd.tradecore.selector.LiveGridSizing;
import com.google.gson.GsonBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.AbstractSet;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.zip.GZIPInputStream;

/**
 * ADD24 R-SIM (DEV-B, test-only, ngoai worktree DEV-A). Chay CrashDayRig (harness DEV-A, KHONG sua) "theo vet sim" HO5 s123:
 * (1) buffer gate warm-up = ung vien sim (top-24 khong giu, co nen) truoc START, r tinh bang ham jar (Add24BufWrite);
 * (2) sel moi phut = top-24 ung vien sim (gate cua jar nap r cho MOI ung vien nhu sim);
 * (3) "theo vet": o.legacy thay bang tap DONG = moi symbol KHONG phai lenh sim o phut quyet dinh (va khong dang giu) =>
 *     GatePreFilter/C3LiveEntry xu ly nhu LEGACY: van qua gate + nap r, KHONG vao lenh (SKIP_LEGACY_AFTER_GATE);
 * (4) co TS_EXT ngay UTC = SIM_LOSER_TS_EXT_DAYS cua sim, nap vao TsMktExt cua jar (LIVE_TS_MKT_EXT=1);
 * (5) o.a1=false (sim khong loc A1, K11). Moi quyet dinh gate / size / DCA / trailing / time-stop / X14 = code JAR stub.
 */
public final class Add24RsimMain {
    private static final Logger LOG = LoggerFactory.getLogger(Add24RsimMain.class);
    static final long MIN = 60_000L;

    private Add24RsimMain() {
    }

    static BufferedReader rd(File f) throws Exception {
        return new BufferedReader(new InputStreamReader(f.getName().endsWith(".gz")
                ? new GZIPInputStream(new FileInputStream(f)) : new FileInputStream(f), StandardCharsets.UTF_8));
    }

    /** tap dong: contains(s) = true (LEGACY, khong vao lenh) tru khi (s, b) la lenh sim hoac rig dang giu s. */
    static final class FollowSet extends AbstractSet<String> {
        final CrashDayRig r;
        final Set<String> starts;
        long nTrue, nFalse;

        FollowSet(CrashDayRig r, Set<String> starts) {
            this.r = r;
            this.starts = starts;
        }

        @Override
        public boolean contains(Object o) {
            if (r == null) return false;
            String s = String.valueOf(o);
            long b = (r.t() / MIN) * MIN - MIN;
            if (starts.contains(s + "@" + b) || r.heldPredicate(b).test(s)) {
                nFalse++;
                return false;
            }
            nTrue++;
            return true;
        }

        @Override
        public Iterator<String> iterator() {
            return Collections.<String>emptyIterator();
        }

        @Override
        public int size() {
            return 0;
        }
    }

    public static void main(String[] args) throws Exception {
        String name = ReplayMain.env("E2E_RUN", "RSIM");
        File fx = new File(ReplayMain.env("E2E_FX_DIR", ""));
        File outRoot = new File(ReplayMain.env("E2E_OUT", ""));
        File out = new File(outRoot, name);
        out.mkdirs();
        Map<String, Object> jc = ReplayMain.jarCheck();
        Map<String, Object> ec = ReplayMain.envCheck();
        if (!Boolean.TRUE.equals(jc.get("ok"))) {
            Map<String, Object> r = new LinkedHashMap<>();
            r.put("refused", true);
            r.put("jar_check", jc);
            Files.write(new File(out, "refused.json").toPath(), new GsonBuilder().setPrettyPrinting().create().toJson(r)
                    .getBytes(StandardCharsets.UTF_8));
            System.err.println("[ADD24-RSIM] TU CHOI CHAY: " + jc.get("problems"));
            System.exit(3);
        }
        boolean sizing = LiveGridSizing.on();
        boolean grid = LiveDcaGridC3.active();
        boolean fin = com.binance.chuyennd.aerospike.MinuteCompletenessGuard.enabled()
                && com.binance.chuyennd.aerospike.MinuteCompletenessGuard.finEnabled();
        LOG.warn("[ADD24-RSIM] run={} LiveGridSizing.on={} LiveDcaGridC3.active={} fin={} GATE_DYN_SCALE={} MIN_MOMENTUM_15M={}",
                name, sizing, grid, fin, com.binance.chuyennd.tradecore.EntryGate.GATE_DYN_SCALE,
                com.binance.chuyennd.tradecore.Configs.MIN_MOMENTUM_15M);
        // (1) buffer warm-up -> fx/gate_ratio_live.bin (ReplayData doc file nay)
        long nW = 0;
        java.util.ArrayList<long[]> tmpT = new java.util.ArrayList<>();
        long[] wt = new long[1 << 20];
        float[] wr = new float[1 << 20];
        try (BufferedReader br = rd(new File(ReplayMain.env("ADD24_WARM", "")))) {
            String ln = br.readLine();
            while ((ln = br.readLine()) != null) {
                String[] p = ln.split(",");
                if (nW == wt.length) {
                    wt = java.util.Arrays.copyOf(wt, wt.length * 2);
                    wr = java.util.Arrays.copyOf(wr, wr.length * 2);
                }
                wt[(int) nW] = Long.parseLong(p[0]);
                wr[(int) nW] = com.binance.chuyennd.ai_ml.onnx.entry.Add24BufWrite.ratio(Float.parseFloat(p[2]), Float.parseFloat(p[1]));
                nW++;
            }
        }
        wt = java.util.Arrays.copyOf(wt, (int) nW);
        wr = java.util.Arrays.copyOf(wr, (int) nW);
        com.binance.chuyennd.ai_ml.onnx.entry.Add24BufWrite.write(new File(fx, "gate_ratio_live.bin").getPath(), wt, wr);
        LOG.warn("[ADD24-RSIM] buffer warm-up {} ban ghi -> {}", nW, new File(fx, "gate_ratio_live.bin"));
        // (4) TS_EXT
        Set<Long> on = new HashSet<>();
        DateTimeFormatter f8 = DateTimeFormatter.ofPattern("yyyyMMdd");
        for (String rg : ReplayMain.env("ADD24_TSX_DAYS", "").split(",")) {
            if (rg.trim().isEmpty()) continue;
            String[] ab = rg.trim().split("-");
            for (LocalDate x = LocalDate.parse(ab[0], f8); !x.isAfter(LocalDate.parse(ab[1], f8)); x = x.plusDays(1)) on.add(x.toEpochDay());
        }
        ReplayData d = new ReplayData(fx);
        // (8) ERRATA2 2a/2b: duong gia trong nen cua rig. CrashDayRig.applyPrices: nen giam (c<o) -> moc O,s[1],s[2],C; nen tang -> O,s[2],s[1],C.
        //     Lane CHINH "sim" = O->L->H->C moi nen: doi cho chuoi s[1]/s[2] (H/L) cua nen GIAM. Lane DO NHAY "sens" = O->H->L->C: doi cho cua nen
        //     TANG. Chi doi mang chuoi s (chi applyPrices doc qua bd(i)); truong float h/l (kline() cho KillSwitch) giu nguyen.
        String lane = ReplayMain.env("ADD24_INTRABAR", "sim");
        long nSwap = 0;
        for (Map<Long, ReplayData.Bar> m : d.bars.values()) {
            for (ReplayData.Bar br : m.values()) {
                boolean down = br.c < br.o;
                if (("sim".equals(lane) && down) || ("sens".equals(lane) && !down)) {
                    String t = br.s[1];
                    br.s[1] = br.s[2];
                    br.s[2] = t;
                    nSwap++;
                }
            }
        }
        LOG.warn("[ADD24-RSIM] intrabar lane={} bars_swapped={}", lane, nSwap);
        Object[] bi = com.binance.chuyennd.ai_ml.onnx.entry.Add24BufWrite.initAndBulkAdd(wt, wr);
        LOG.warn("[ADD24-RSIM] LiveGateRollingRatio init + bulkAdd warm-up: on={} size={}", bi[0], bi[1]);
        long fromDay = Math.floorDiv(ReplayData.START, 86_400_000L) - 2, toDay = Math.floorDiv(ReplayData.END, 86_400_000L) + 40;
        int nf = com.binance.chuyennd.tradecore.selector.Add24TsxInject.install(on, fromDay, toDay, new File(out, "ts_ext_unused.csv"));
        // (2)(3)(5)
        Set<String> starts = new HashSet<>();
        Map<String, java.math.BigDecimal> entryPx = new java.util.HashMap<>();
        try (BufferedReader br = rd(new File(ReplayMain.env("ADD24_FOLLOW", "")))) {
            String ln = br.readLine();
            while ((ln = br.readLine()) != null) {
                String[] p = ln.split(",");
                starts.add(p[1] + "@" + p[0]);
                if (p.length >= 4 && !"0".equals(ReplayMain.env("ADD24_ENTRY_FOLLOW", "1"))) entryPx.put(p[2], new java.math.BigDecimal(p[3]));
            }
        }
        CrashDayRig.Opts o = new CrashDayRig.Opts();
        o.name = name;
        o.venue = CrashDayRig.Venue.FAKE;
        o.end = ReplayMain.envL("E2E_END", ReplayData.END);
        o.a1 = false;
        // (7) ERRATA1 EB11 buoc 1: FakeExchange khop leg 0 tai GIA VAO SIM (close nen sim) - co che L0-FOLLOW-lite cua DEV-A (cid -> gia)
        o.followPx.putAll(entryPx);
        CrashDayRig r = new CrashDayRig(o, d, outRoot);
        FollowSet fs = new FollowSet(r, starts);
        Field lf = CrashDayRig.Opts.class.getDeclaredField("legacy");
        lf.setAccessible(true);
        lf.set(o, fs);
        r.res.put("add24_buf_init", java.util.Arrays.toString(bi));
        r.res.put("add24", "R-SIM theo vet sim HO5 s123 (DEV-B); warm=" + nW + " follow=" + starts.size() + " tsx_on_days=" + on.size()
                + " tsx_flag_days=" + nf + " a1=false entry_follow=" + entryPx.size() + " intrabar=" + lane + " swapped=" + nSwap);
        r.res.put("jar_check", jc);
        r.res.put("env_check", ec);
        r.res.put("fixture_dir", fx.getAbsolutePath());
        r.res.put("fixture_START", ReplayData.START);
        r.res.put("fixture_END", ReplayData.END);
        r.res.put("banners_harness", "LiveGridSizing.on=" + sizing + " LiveDcaGridC3.active=" + grid + " fin=" + fin
                + " TsMktExt.enabled=" + com.binance.chuyennd.tradecore.selector.TsMktExt.enabled());
        // (6) X14: CrashDayRig (DEV-A) dung .defer((s,t0,n)->false) (E2E tat X14). R-SIM: thay bang TsMktExt::deferTimeStop
        //     CUA JAR (= mac dinh production TrailingStopManager khi b.defer == null) ngay khi mgr duoc tao (truoc moi time-stop).
        final boolean x14 = "1".equals(ReplayMain.env("ADD24_X14", "1"));
        final String[] x14Info = {"not_swapped"};
        if (x14) {
            Thread th = new Thread(() -> {
                try {
                    while (r.mgr == null) Thread.sleep(2L);
                    Field df = r.mgr.getClass().getDeclaredField("defer");
                    df.setAccessible(true);
                    Class<?> it = df.getType();
                    Object px = java.lang.reflect.Proxy.newProxyInstance(it.getClassLoader(), new Class<?>[]{it}, (pp, m, ar) -> {
                        if (m.getDeclaringClass() == Object.class) return m.getName().equals("toString") ? "add24-x14-proxy" : (m.getName().equals("hashCode") ? (Object) System.identityHashCode(pp) : (Object) Boolean.valueOf(pp == ar[0]));
                        return com.binance.chuyennd.tradecore.selector.TsMktExt.deferTimeStop((String) ar[0], (Long) ar[1], (Long) ar[2]);
                    });
                    df.set(r.mgr, px);
                    x14Info[0] = "swapped rig_t=" + r.t() + " type=" + it.getName();
                } catch (Throwable e) {
                    x14Info[0] = "SWAP_FAIL " + e;
                }
            }, "add24-x14-swap");
            th.setDaemon(true);
            th.start();
        }
        // (12) ERRATA4 1a: TIER LUOI cua sim -> chan DCA trong jar. CrashDayRig:922 truyen tier3=false (final, khong ke thua). C3LiveEntry
        //      (final) kiem in.tier3 NGAY SAU gridDue.due(...) va KHONG co tac dung phu giua hai buoc => boc 2 truong private final cua CHINH
        //      instance entry: reconAllows (Predicate<String>, goi ngay truoc trong decide) ghi symbol dang xet; gridDue (interface) = Proxy goi
        //      ham GOC, neu GOC tra true va tier luoi sim cua symbol tai phut b = T3 => tra false (=> outcome DCA_NOT_DUE, ghi sim_tier3_block.csv).
        //      Tier luoi: file ADD24_SIMTIER (moment,symbol,tier tu Add24SimTierCode = code a8690d46); b = floor(t/1')-1' (nhu L1).
        final String stf = ReplayMain.env("ADD24_SIMTIER", "");
        final String[] stInfo = {"off"};
        final java.util.TreeMap<Long, Set<String>> nonT3 = new java.util.TreeMap<>();
        final long[] stCnt = new long[4];   // gridDue goi, goc true, chan T3, khong co trang thai
        final java.io.PrintWriter stLog = stf.isEmpty() ? null : new java.io.PrintWriter(new java.io.FileWriter(new File(out, "sim_tier3_block.csv")), true);
        if (!stf.isEmpty()) {
            try (BufferedReader br = rd(new File(stf))) {
                String ln = br.readLine();
                while ((ln = br.readLine()) != null) {
                    String[] p = ln.split(",");
                    Set<String> st = nonT3.computeIfAbsent(Long.parseLong(p[0]), z -> new HashSet<>());
                    if (!"TIER_3_SHITCOIN".equals(p[3])) st.add(p[1]);
                }
            }
            stLog.println("b,symbol,moment,outcome");
            Thread th2 = new Thread(() -> {
                try {
                    while (r.entry == null) Thread.sleep(1L);
                    Object en = r.entry;
                    final String[] cur = {null};
                    Field rf = en.getClass().getDeclaredField("reconAllows");
                    rf.setAccessible(true);
                    @SuppressWarnings("unchecked") final java.util.function.Predicate<String> ro = (java.util.function.Predicate<String>) rf.get(en);
                    rf.set(en, (java.util.function.Predicate<String>) s -> { cur[0] = s; return ro.test(s); });
                    Field gf = en.getClass().getDeclaredField("gridDue");
                    gf.setAccessible(true);
                    final Object go = gf.get(en);
                    Class<?> gi = gf.getType();
                    Object gp = java.lang.reflect.Proxy.newProxyInstance(gi.getClassLoader(), new Class<?>[]{gi}, (pp, m, ar) -> {
                        if (m.getDeclaringClass() == Object.class) return m.getName().equals("toString") ? "add24-simtier-proxy" : (m.getName().equals("hashCode") ? (Object) System.identityHashCode(pp) : (Object) (pp == ar[0]));
                        Object v = m.invoke(go, ar);
                        stCnt[0]++;
                        if (!Boolean.TRUE.equals(v)) return v;
                        stCnt[1]++;
                        long b = Math.floorDiv(r.t(), 60_000L) * 60_000L - 60_000L;
                        Map.Entry<Long, Set<String>> e = nonT3.floorEntry(b);
                        if (e == null) { stCnt[3]++; stLog.println(b + "," + cur[0] + ",,NO_STATE_ALLOW"); return v; }
                        if (!e.getValue().contains(cur[0])) { stCnt[2]++; stLog.println(b + "," + cur[0] + "," + e.getKey() + ",SIM_TIER3_BLOCK"); return Boolean.FALSE; }
                        stLog.println(b + "," + cur[0] + "," + e.getKey() + ",ALLOW");
                        return v;
                    });
                    gf.set(en, gp);
                    stInfo[0] = "installed rig_t=" + r.t() + " moments=" + nonT3.keySet() + " gridDue_type=" + gi.getName();
                } catch (Throwable ex) {
                    stInfo[0] = "INSTALL_FAIL " + ex;
                }
            }, "add24-simtier");
            th2.setDaemon(true);
            th2.start();
        }
        long t0 = System.currentTimeMillis();
        r.run();
        LOG.warn("[ADD24-RSIM] run={} xong {} ms; follow legacy_true={} legacy_false={} x14={}", name, System.currentTimeMillis() - t0,
                fs.nTrue, fs.nFalse, x14Info[0]);
        Files.write(new File(out, "add24_meta.txt").toPath(), ("simtier=" + stInfo[0] + " calls=" + stCnt[0] + " due_true=" + stCnt[1] + " sim_t3_block=" + stCnt[2] + " no_state=" + stCnt[3] + "\nx14=" + x14Info[0] + "\nfollow_true=" + fs.nTrue + "\nfollow_false=" + fs.nFalse + "\n").getBytes(StandardCharsets.UTF_8));
        if (stLog != null) stLog.close();
        System.exit(0);
    }
}
