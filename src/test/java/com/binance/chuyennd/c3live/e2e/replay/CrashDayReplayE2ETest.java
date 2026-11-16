package com.binance.chuyennd.c3live.e2e.replay;

import com.binance.chuyennd.ai_ml.onnx.entry.E2eGateSupport;
import com.google.gson.GsonBuilder;
import org.junit.After;
import org.junit.Assume;
import org.junit.BeforeClass;
import org.junit.FixMethodOrder;
import org.junit.Test;
import org.junit.runners.MethodSorters;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;

import static org.junit.Assert.assertTrue;

/**
 * [E2E_REPLAY] Lượt chạy theo docs/c3live/E2E_REPLAY.md §4 (ngày sập 10-30, dữ liệu fixture tools/e2e/prep_fixture.py).
 * Không có fixture (CI) ⇒ bỏ qua. Mỗi lượt ghi {@code <E2E_OUT>/<run>/result.json}; assert = tiêu chí §5.
 * Chạy: {@code LIVE_IS_SHADOW_HOST=true E2E_FX_DIR=... E2E_OUT=... mvn -o test -Dtest=CrashDayReplayE2ETest}.
 */
@FixMethodOrder(MethodSorters.NAME_ASCENDING)
public class CrashDayReplayE2ETest {

    private static final Logger LOG = LoggerFactory.getLogger(CrashDayReplayE2ETest.class);
    static final long T_0330 = 1_793_305_800_000L, T_0340 = 1_793_306_400_000L, T_0346 = 1_793_306_760_000L,
            T_0352 = 1_793_307_120_000L, T_0430 = 1_793_309_400_000L, T_1000 = 1_793_329_200_000L,
            T_1100 = 1_793_332_800_000L, T_1200 = 1_793_336_400_000L, T_1205 = 1_793_336_700_000L;
    static ReplayData D;
    static File OUT;
    static CrashDayRig R0;
    static final Map<String, Object> SUMMARY = new LinkedHashMap<>();

    @BeforeClass
    public static void load() throws Exception {
        String fx = System.getenv("E2E_FX_DIR");
        File dir = new File(fx != null ? fx : System.getProperty("user.home") + "/claude_master/e2e1105/fx");
        Assume.assumeTrue("khong co fixture E2E => bo qua", new File(dir, "manifest.json").isFile());
        String o = System.getenv("E2E_OUT");
        OUT = new File(o != null ? o : System.getProperty("user.home") + "/claude_master/e2e1105/out");
        OUT.mkdirs();
        D = new ReplayData(dir);
        LOG.warn("[E2E] fixture {}", ReplayData.info(D));
    }

    @After
    public void tearDown() throws Exception {
        E2eGateSupport.reset();
        Files.write(new File(OUT, "summary.json").toPath(), new GsonBuilder().setPrettyPrinting().create().toJson(SUMMARY)
                .getBytes(StandardCharsets.UTF_8));
    }

    static CrashDayRig run(CrashDayRig.Opts o) throws Exception {
        CrashDayRig r = new CrashDayRig(o, D, OUT);
        long t0 = System.currentTimeMillis();
        r.run();
        r.res.put("wall_ms", System.currentTimeMillis() - t0);
        Files.write(new File(r.out, "result.json").toPath(), new GsonBuilder().setPrettyPrinting()
                .serializeSpecialFloatingPointValues().create().toJson(r.res).getBytes(StandardCharsets.UTF_8));
        SUMMARY.put(o.name, r.crit);
        LOG.warn("[E2E] {} tieu chi {}", o.name, r.crit);
        return r;
    }

    static void assertAll(CrashDayRig r) {
        List<String> fail = new ArrayList<>();
        for (Map.Entry<String, Boolean> e : r.crit.entrySet()) if (!e.getValue()) fail.add(e.getKey());
        assertTrue(r.o.name + " TRUOT " + fail + " vi pham " + r.viol.keySet(), fail.isEmpty());
    }

    static CrashDayRig.Opts opts(String name) {
        CrashDayRig.Opts o = new CrashDayRig.Opts();
        o.name = name;
        return o;
    }

    static List<String[]> latchEvents(CrashDayRig r) {
        List<String[]> l = new ArrayList<>();
        for (String e : r.eventRows) {
            String[] a = e.split(",", -1);
            if ("KS_LATCH".equals(a[2])) l.add(a);
        }
        return l;
    }

    static int submittedAfter(CrashDayRig r, long t) {
        int n = 0;
        for (String row : r.outcomeRows) {
            String[] a = row.split(",", -1);
            if ("SUBMITTED".equals(a[5]) && Long.parseLong(a[2]) >= t) n++;
        }
        return n;
    }

    // ------------------------------------------------------------------ tang quyet dinh
    @Test
    public void a_e2a_bufferParityLiveV11() throws Exception {
        CrashDayRig.Opts o = opts("E2a");
        o.held = CrashDayRig.HeldMode.NONE_V11;
        o.a1 = false;
        o.exec = false;
        assertAll(run(o));
    }

    @Test
    public void b_e2b_anchorR4h() throws Exception {
        CrashDayRig.Opts o = opts("E2b");
        o.held = CrashDayRig.HeldMode.SHADOW_R4H;
        o.a1 = false;
        o.exec = false;
        o.end = T_1100 + 60_000L;
        assertAll(run(o));
    }

    // ------------------------------------------------------------------ lop thuc thi
    @Test
    public void c_r0_fake() throws Exception {
        R0 = run(opts("R0"));
        assertAll(R0);
    }

    @Test
    public void d_r0_dry() throws Exception {
        CrashDayRig.Opts o = opts("R0-DRY");
        o.venue = CrashDayRig.Venue.DRY;
        assertAll(run(o));
    }

    @Test
    public void e_f1_wsDrop() throws Exception {
        CrashDayRig.Opts o = opts("F1");
        o.wsDownFrom = T_0340;
        o.wsDownTo = T_0352;
        CrashDayRig r = run(o);
        long maxLat = 0;
        int inGap = 0;
        for (Map.Entry<String, Long> e : r.submitTime.entrySet()) {
            if (e.getValue() < T_0340 || e.getValue() >= T_0352) continue;
            inGap++;
            Long c = r.confirmAt.get(e.getKey());
            maxLat = Math.max(maxLat, c == null ? Long.MAX_VALUE : c - e.getValue());
        }
        boolean fb = r.alerts.stream().anyMatch(a -> a.contains("mat user stream"));
        r.res.put("F1", "legs_trong_khoang_rot=" + inGap + " max_xac_nhan_ms=" + maxLat + " fallback_alert=" + fb);
        r.crit.put("F1", maxLat <= 60_000L && fb);
        rewrite(r);
        assertAll(r);
    }

    @Test
    public void f_f2_rest429() throws Exception {
        CrashDayRig.Opts o = opts("F2");
        o.rlAt = T_0346;
        o.rlOrders = 3;
        o.rlStops = 2;
        CrashDayRig r = run(o);
        boolean c3 = false;
        for (String[] e : latchEvents(r)) if (e[5].contains("C3")) c3 = true;
        r.res.put("F2", "latch_C3=" + c3);
        r.crit.put("F2", !c3);
        rewrite(r);
        assertAll(r);
    }

    @Test
    public void g_f2b_rest429x6() throws Exception {
        CrashDayRig.Opts o = opts("F2b");
        o.rlAt = T_0346;
        o.rlOrders = 6;
        CrashDayRig r = run(o);
        long on = -1, off = -1;
        for (String[] e : latchEvents(r)) {
            boolean has = e[5].contains("C3");
            if (has && on < 0) on = Long.parseLong(e[0]);
            if (!has && on >= 0 && off < 0) off = Long.parseLong(e[0]);
        }
        r.res.put("F2b", "C3_latch=" + (on < 0 ? "-" : CrashDayRig.fmt(on)) + " go=" + (off < 0 ? "-" : CrashDayRig.fmt(off)));
        r.crit.put("F2b", on >= 0 && off >= 0 && off - on >= 30 * 60_000L);
        rewrite(r);
        assertAll(r);
    }

    @Test
    public void h_f3_noAvgPrice() throws Exception {
        CrashDayRig.Opts o = opts("F3");
        o.ackNoAvg = true;
        CrashDayRig r = run(o);
        boolean c2 = false;
        for (String[] e : latchEvents(r)) if (e[5].contains("C2")) c2 = true;
        r.crit.put("F3", !c2);
        rewrite(r);
        assertAll(r);
    }

    @Test
    public void i_f4_expire4ms() throws Exception {
        CrashDayRig.Opts o = opts("F4");
        o.expireDelayMs = 4L;
        // ADDENDUM (sau lan chay 1): moi lan thoat R0 deu do stop kich => khong co dong MARKET khi stop con mo => F4 rong.
        // Ghep FLATTEN (DD gia nhu F6a) de co dong MARKET khi stop closePosition con mo tren san.
        o.ddAt = T_1000;
        o.ddUsd = 4_500d;
        CrashDayRig r = run(o);
        long bad = r.alerts.stream().filter(a -> a.contains("UNKNOWN") || a.contains("vi the la") || a.contains("LOST")).count();
        r.res.put("F4", "expired_by_exchange=" + r.fake.expiredCount + " alert_la=" + bad);
        r.crit.put("F4", bad == 0 && r.fake.expiredCount > 0);
        rewrite(r);
        assertAll(r);
    }

    @Test
    public void j_f5_legacyMerged() throws Exception {
        if (R0 == null) R0 = run(opts("R0"));
        List<String> wave1 = new ArrayList<>();
        Map<String, Long> at = new LinkedHashMap<>();
        for (String row : R0.outcomeRows) {
            String[] a = row.split(",", -1);
            if (!"SUBMITTED".equals(a[5]) || Long.parseLong(a[0]) < T_0330 || !"PREDICT_SYMBOL_TRADE".equals(a[4])) continue;
            if (!wave1.contains(a[3])) {
                wave1.add(a[3]);
                at.put(a[3], Long.parseLong(a[2]));
            }
        }
        Assume.assumeTrue("R0 can >= 3 lenh dot 1", wave1.size() >= 3);
        CrashDayRig.Opts o = opts("F5");
        o.legacy.add(wave1.get(0));
        o.legacy.add(wave1.get(1));
        o.mergeSymbol = wave1.get(2);
        o.mergeAt = at.get(wave1.get(2)) + 10 * 60_000L;
        CrashDayRig r = run(o);
        int c3OnLegacy = 0;
        for (String l : r.fake.callLog()) {
            String[] t = l.split(":", 3);
            if (t.length == 3 && o.legacy.contains(t[1]) && com.binance.chuyennd.c3live.scope.C3Scope.isC3Cid(t[2])) c3OnLegacy++;
        }
        int legacyOutcome = 0, legacySubmitted = 0;
        for (String row : r.outcomeRows) {
            String[] a = row.split(",", -1);
            if (!o.legacy.contains(a[3])) continue;
            if ("SKIP_LEGACY_AFTER_GATE".equals(a[5]) || "LEGACY".equals(a[5])) legacyOutcome++;
            if ("SUBMITTED".equals(a[5])) legacySubmitted++;
        }
        int legacyGatedRows = 0;
        for (String row : r.traceRows) {
            String[] a = row.split(",", -1);
            if (o.legacy.contains(a[1]) && "1".equals(a[8])) legacyGatedRows++;
        }
        boolean mergedSeen = r.alerts.stream().anyMatch(a -> a.contains("MERGED")) || r.scope.isMerged(o.mergeSymbol);
        java.math.BigDecimal endPos = java.math.BigDecimal.ZERO;
        for (com.binance.chuyennd.c3live.api.PositionInfo p : r.fake.positions()) if (p.getSymbol().equals(o.mergeSymbol)) endPos = p.getPositionAmt();
        java.math.BigDecimal lq = r.legacyQty.get(o.mergeSymbol);
        boolean c3Exited = !r.book.isHolding(o.mergeSymbol);
        Map<String, Object> f5 = new LinkedHashMap<>();
        f5.put("legacy", o.legacy);
        f5.put("merge", o.mergeSymbol + " @" + CrashDayRig.fmt(o.mergeAt));
        f5.put("c3_calls_on_legacy", c3OnLegacy);
        f5.put("legacy_outcomes", legacyOutcome);
        f5.put("legacy_submitted", legacySubmitted);
        f5.put("legacy_gated_rows(r nap)", legacyGatedRows);
        f5.put("merged_seen", mergedSeen);
        f5.put("merge_pos_end", endPos.toPlainString() + " legacy_qty=" + lq + " c3_da_thoat=" + c3Exited);
        r.res.put("F5", f5);
        boolean posOk = !c3Exited || (lq != null && endPos.compareTo(lq) == 0);
        r.crit.put("F5", c3OnLegacy == 0 && legacySubmitted == 0 && legacyGatedRows > 0 && mergedSeen && posOk);
        rewrite(r);
        assertAll(r);
    }

    @Test
    public void k_f6a_drawdown() throws Exception {
        CrashDayRig.Opts o = opts("F6a");
        o.ddAt = T_1000;
        o.ddUsd = 4_500d;
        CrashDayRig r = run(o);
        long latch = r.latchFlattenAt;
        int stopsEnd = 0;
        for (com.binance.chuyennd.c3live.api.OrderInfo s : r.raw.openStops(null)) if (s.getClientOrderId().startsWith("c3s-")) stopsEnd++;
        int subAfter = latch < 0 ? -1 : submittedAfter(r, latch);
        Map<String, Object> f6 = new LinkedHashMap<>();
        f6.put("latch_flatten", latch < 0 ? "-" : CrashDayRig.fmt(latch));
        f6.put("latch_codes_final", new TreeSet<>(r.ks.latchCodes()));
        f6.put("flat_done", r.flatDoneAt < 0 ? "-" : CrashDayRig.fmt(r.flatDoneAt));
        f6.put("c3_stops_end", stopsEnd);
        f6.put("submitted_after_latch", subAfter);
        r.res.put("F6a", f6);
        r.crit.put("F6a", latch >= 0 && latch - T_1000 <= 11 * 60_000L && r.flatDoneAt >= 0 && r.flatDoneAt - latch <= 2 * 60_000L
                && stopsEnd == 0 && subAfter == 0);
        rewrite(r);
        assertAll(r);
    }

    @Test
    public void l_f6b_c1Stall() throws Exception {
        CrashDayRig.Opts o = opts("F6b");
        o.c1From = T_1200;
        o.c1To = T_1205;
        CrashDayRig r = run(o);
        long on = -1, off = -1;
        for (String[] e : latchEvents(r)) {
            boolean has = e[5].contains("C1");
            if (has && on < 0) on = Long.parseLong(e[0]);
            if (!has && on >= 0 && off < 0) off = Long.parseLong(e[0]);
        }
        int blocked = 0, subDuring = 0;
        for (String row : r.outcomeRows) {
            String[] a = row.split(",", -1);
            long ts = Long.parseLong(a[2]);
            if (on >= 0 && ts >= on && (off < 0 || ts < off)) {
                if ("KS_BLOCKED".equals(a[5])) blocked++;
                if ("SUBMITTED".equals(a[5])) subDuring++;
            }
        }
        r.res.put("F6b", "C1_latch=" + (on < 0 ? "-" : CrashDayRig.fmt(on)) + " go=" + (off < 0 ? "-" : CrashDayRig.fmt(off))
                + " KS_BLOCKED_trong_latch=" + blocked + " SUBMITTED_trong_latch=" + subDuring);
        r.crit.put("F6b", on >= 0 && on - T_1200 <= 5 * 60_000L + 60_000L && off >= 0 && off - T_1205 >= 30 * 60_000L - 60_000L
                && subDuring == 0);
        rewrite(r);
        assertAll(r);
    }

    @Test
    public void m_sDca() throws Exception {
        CrashDayRig.Opts o = opts("S-DCA");
        o.sDcaAt = T_0430;
        o.end = T_1200;
        CrashDayRig r = run(o);
        r.crit.put("X10_SDCA", r.nDcaSubmitted >= 1);
        rewrite(r);
        assertAll(r);
    }

    static void rewrite(CrashDayRig r) throws Exception {
        r.res.put("criteria", r.crit);
        Files.write(new File(r.out, "result.json").toPath(), new GsonBuilder().setPrettyPrinting()
                .serializeSpecialFloatingPointValues().create().toJson(r.res).getBytes(StandardCharsets.UTF_8));
        SUMMARY.put(r.o.name, r.crit);
    }
}
