package com.binance.chuyennd.websocket;

import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.IntSupplier;
import java.util.function.LongSupplier;
import java.util.function.ToDoubleFunction;

/**
 * [INGEST-QF2 2026-10-31] Hai pass REST kline của mode ws_settle, tách khỏi TickerIngestor2AerospikeNew để test đối kháng chạy
 * đúng mã production (KlineIngestCore + SettlePlanner + ngân sách). Prereg ADD1/ADD-1b.
 * <ul>
 *   <li>{@link #early} (+4 s): symbol thiếu WS final ⇒ đánh dấu suspect; REST sớm CHỈ khi số thiếu ≤ {@code earlyMax} và chỉ
 *       lấy phần vừa {@code klineRoom} (không xếp hàng chờ); phút đóng TRƯỚC khi JVM start ⇒ chỉ đánh dấu.</li>
 *   <li>{@link #settle} (+30 s): gỡ ô đã có WS final, kiểm lại suspects (vừa room), rồi đối soát mẫu (vừa room còn lại);
 *       trả số đếm cho dòng [KLINE-COVER].</li>
 * </ul>
 */
final class KlinePassController {
    private static final Logger LOG = LoggerFactory.getLogger(KlinePassController.class);
    static final long MIN = 60_000L;

    final KlineIngestCore core;
    final SettlePlanner planner;
    private final IntSupplier klineRoom;
    private final LongSupplier clock;
    private final int earlyMax, settleLimit;
    private final long startMinute, settleMinAgeMs;

    final AtomicLong cReconFetched = new AtomicLong(), cReconDiffWs = new AtomicLong(), cReconFilled = new AtomicLong();
    final AtomicLong cSuspectFetched = new AtomicLong(), cEarlySkippedBig = new AtomicLong();

    KlinePassController(KlineIngestCore core, SettlePlanner planner, IntSupplier klineRoom, LongSupplier clock,
                        int earlyMax, int settleLimit, long startMinute, long settleMinAgeMs) {
        this(core, planner, klineRoom, clock, earlyMax, settleLimit, startMinute, settleMinAgeMs, 600);
    }

    KlinePassController(KlineIngestCore core, SettlePlanner planner, IntSupplier klineRoom, LongSupplier clock,
                        int earlyMax, int settleLimit, long startMinute, long settleMinAgeMs, int gapGlobalN) {
        this.gapGlobalN = gapGlobalN;
        this.settleMinAgeMs = settleMinAgeMs;
        this.core = core;
        this.planner = planner;
        this.klineRoom = klineRoom;
        this.clock = clock;
        this.earlyMax = earlyMax;
        this.settleLimit = settleLimit;
        this.startMinute = startMinute;
    }

    static final class EarlyOut {
        /** need = thiếu WS final TRỪ symbol đã REST ở pass +2 s (cơ sở luật ≤ earlyMax); missingWs = thiếu WS final (log thieu_ws). */
        int need, missingWs, requested, closed, failed;
        boolean restSkipped;
        Map<String, KlineObjectOptimized> open = Collections.emptyMap();
        List<String> needSample = Collections.emptyList();
        /** [QF4] symbol không WS final và không REST ngay sau pass +4 s = ô live đọc bản nặn ở +6 s. */
        int thieuLucChot;
        List<String> thieuEx = Collections.emptyList();
    }

    // ===================== [QF4, ADDENDUM 3] REST bù mất WS ở giây +2 =====================

    static final class GapOut {
        int missing, lost, byDown, requested, closed, failed;
        boolean global, restSkipped;
        long doneAtMs;
        Map<String, KlineObjectOptimized> open = Collections.emptyMap();
        List<String> lostSample = Collections.emptyList();
    }

    /** Thống kê lúc chốt của 1 phút (cho [KLINE-COVER] +30 s). */
    static final class ChotStat {
        final long minute;
        final int wsMat, restWsMat, thieuLucChot;

        ChotStat(long minute, int wsMat, int restWsMat, int thieuLucChot) {
            this.minute = minute;
            this.wsMat = wsMat;
            this.restWsMat = restWsMat;
            this.thieuLucChot = thieuLucChot;
        }
    }

    final AtomicLong cWsMat = new AtomicLong(), cRestWsMat = new AtomicLong(), cThieuLucChot = new AtomicLong();
    private final int gapGlobalN;
    /** Symbol (ngắn) đã có bản REST cho phút {@link #restMinute} (pass +2 s và +4 s). */
    private long restMinute = Long.MIN_VALUE;
    private final Set<String> restClosed = new HashSet<>();
    private int gapLostM, gapRestM;
    private final java.util.concurrent.ConcurrentHashMap<Long, ChotStat> chot = new java.util.concurrent.ConcurrentHashMap<>();

    private synchronized Set<String> restClosedFor(long m) {
        if (m != restMinute) {
            restMinute = m;
            restClosed.clear();
            gapLostM = 0;
            gapRestM = 0;
        }
        return restClosed;
    }

    ChotStat chotOf(long m) {
        return chot.get(m);
    }

    /**
     * Tập "mất WS" (thuần, test được; ADDENDUM 3 + ADD-3b): thiếu WS final ∩ {@code gapSyms} (symbol của kết nối hở — luật a — hoặc
     * im lặng ≥ 1,5 s — luật b, do KlineWsClient tính); luật c: tổng thiếu &gt; globalN ⇒ mọi symbol thiếu.
     * {@code stat} = {so_theo_ket_noi, toan_cuc}.
     */
    static Set<String> lostSet(List<String> missing, Set<String> gapSyms, int globalN, int[] stat) {
        Set<String> lost = new java.util.LinkedHashSet<>();
        for (String s : missing) if (gapSyms.contains(s)) lost.add(s);
        stat[0] = lost.size();
        if (missing.size() > globalN) {
            lost.addAll(missing);
            stat[1] = 1;
        }
        return lost;
    }

    /**
     * Pass +2 s cho phút M vừa đóng: chỉ REST tập "mất WS" (lane KLINE, vừa room, không chờ, ưu tiên {@code prio} giảm dần).
     * Không có mất WS ⇒ không gọi gì (phút bình thường để pass +4 s như cũ).
     */
    GapOut gap(long m, List<String> universe, Set<String> gapSyms, ToDoubleFunction<String> prio, boolean restAllowed) {
        GapOut o = new GapOut();
        Set<String> done = restClosedFor(m);
        List<String> missing = core.missingFinals(m, universe);
        o.missing = missing.size();
        int[] st = new int[2];
        Set<String> lost = lostSet(missing, gapSyms, gapGlobalN, st);
        o.byDown = st[0];
        o.global = st[1] == 1;
        o.lost = lost.size();
        if (lost.isEmpty()) return o;
        List<String> l = new ArrayList<>(lost);
        o.lostSample = l.subList(0, Math.min(10, l.size()));
        planner.markSuspects(l, m);
        synchronized (this) { gapLostM = l.size(); }
        cWsMat.addAndGet(l.size());
        if (!restAllowed || m < startMinute) {
            o.restSkipped = true;
            return o;
        }
        if (prio != null) {
            final java.util.Map<String, Double> pv = new java.util.HashMap<>();
            for (String s : l) pv.put(s, prio.applyAsDouble(s));
            l.sort((a, b) -> {
                int c = Double.compare(pv.get(b), pv.get(a));
                return c != 0 ? c : a.compareTo(b);
            });
        }
        int room = Math.max(0, klineRoom.getAsInt());
        List<String> req = new ArrayList<>(l.subList(0, Math.min(room, l.size())));
        o.requested = req.size();
        if (!req.isEmpty()) {
            KlineIngestCore.EarlyResult r = core.earlyRest(m, req);
            o.closed = r.closed.size();
            o.failed = r.failed.size();
            o.open = r.open;
            synchronized (this) {
                done.addAll(r.closed.keySet());
                gapRestM = r.closed.size();
            }
            cRestWsMat.addAndGet(r.closed.size());
        }
        o.doneAtMs = clock.getAsLong();
        return o;
    }

    /** Cửa sổ live đọc lại nến (KFIX-B, LiveTickerWindow, mặc định 3′). */
    static final long LIVE_REREAD_MS = 3 * MIN;
    final AtomicLong cLateHeal = new AtomicLong();

    static final class SettleOut {
        int lateHeal;
        List<String> lateEx = new java.util.ArrayList<>();
        int wsCovered, suspects, suspectsRequested, suspectLimit, sampleRequested, calls;
        int pendingM, pendingPrev;
        long dropped;
        KlineIngestCore.SettleResult sus, smp;
    }

    /** Pass +4 s cho phút M vừa đóng. {@code restAllowed}=false khi đang ban. */
    EarlyOut early(long m, List<String> universe, boolean restAllowed) {
        EarlyOut o = new EarlyOut();
        Set<String> done = restClosedFor(m);
        List<String> missing = core.missingFinals(m, universe);
        planner.markSuspects(missing, m);
        List<String> need = new ArrayList<>();
        synchronized (this) {
            for (String s : missing) if (!done.contains(KlineIngestCore.shortSym(s))) need.add(s);   // [QF4] da REST o +2 s => bo
        }
        o.missingWs = missing.size();
        o.need = need.size();
        o.needSample = need.subList(0, Math.min(10, need.size()));
        if (!need.isEmpty() && restAllowed) {
            if (m < startMinute || need.size() > earlyMax) {     // lo lon / phut truoc khi start: de pass +30 s (nen da settle)
                o.restSkipped = true;
                if (need.size() > earlyMax) cEarlySkippedBig.incrementAndGet();
            } else {
                List<String> req = SettlePlanner.take(need, klineRoom.getAsInt(), m / MIN);
                o.requested = req.size();
                if (!req.isEmpty()) {
                    KlineIngestCore.EarlyResult r = core.earlyRest(m, req);
                    o.closed = r.closed.size();
                    o.failed = r.failed.size();
                    o.open = r.open;
                    synchronized (this) { done.addAll(r.closed.keySet()); }
                }
            }
        }
        recordChot(m, universe, o);
        return o;
    }

    /** [QF4] Sau pass +4 s: symbol không WS final và không REST = thiếu lúc chốt (live đọc bản nặn ở +6 s). */
    private void recordChot(long m, List<String> universe, EarlyOut o) {
        List<String> still = core.missingFinals(m, universe);
        List<String> thieu = new ArrayList<>();
        int lostM, restM;
        synchronized (this) {
            for (String s : still) if (!restClosed.contains(KlineIngestCore.shortSym(s))) thieu.add(s);
            lostM = gapLostM;
            restM = gapRestM;
        }
        o.thieuLucChot = thieu.size();
        o.thieuEx = thieu.subList(0, Math.min(10, thieu.size()));
        cThieuLucChot.addAndGet(thieu.size());
        chot.put(m, new ChotStat(m, lostM, restM, thieu.size()));
        chot.keySet().removeIf(k -> k < m - 10 * MIN);
    }

    /** Pass +30 s: phút đang mở {@code curMin}, M = curMin-1 (kiểm lại suspects + đối soát mẫu). */
    SettleOut settle(long curMin, List<String> universe) {
        return settle(curMin, universe, true);
    }

    /**
     * Pass bù (chỉ suspects, không mẫu): cửa sổ 60 s giải phóng DẦN nên pass cố định mỗi phút chỉ thấy một phần room; pass bù
     * chạy liên tục (mỗi ≥2 s, từ giây 8 của phút — sau REST sớm +4 s) khi còn suspect và room ≥ 10 ⇒ lỗ lớn lành ở tốc độ
     * ~KLINE_QUOTA/phút (prereg ADD-1b). Bình thường không có suspect ⇒ không gọi gì.
     */
    SettleOut catchUp(long curMin, List<String> universe) {
        return settle(curMin, universe, false);
    }

    private long lastCatchUpMs = 0;

    /** Gọi mỗi nhịp Finalizer; trả null nếu chưa tới lúc. */
    SettleOut maybeCatchUp(long curMin, long inMin, List<String> universe) {
        long now = clock.getAsLong();
        if (inMin < 8_000L || now - lastCatchUpMs < 2_000L || planner.suspectCount() == 0 || klineRoom.getAsInt() < 10) return null;
        lastCatchUpMs = now;
        return catchUp(curMin, universe);
    }

    SettleOut settle(long curMin, List<String> universe, boolean withSample) {
        SettleOut o = new SettleOut();
        long m = curMin - MIN;
        o.wsCovered = planner.dropCovered((s, mm) -> core.hasWsFinal(mm, s));
        long nowMs = clock.getAsLong();
        long mature = nowMs - settleMinAgeMs - MIN;   // nen openTime <= mature da dong >= settleMinAge: REST final, settle ghi
        SettlePlanner.Plan plan = planner.plan(curMin, universe, mature);
        o.suspects = plan.suspects.size();
        List<String> sus = SettlePlanner.take(plan.suspects, klineRoom.getAsInt(), 0);   // plan da xep o cu nhat truoc
        o.suspectsRequested = sus.size();
        if (!sus.isEmpty()) {
            o.suspectLimit = planner.limitFor(sus, curMin);
            o.sus = core.settle(nowMs, sus, o.suspectLimit);
            // [QF3, A1_QF2 MIN-A] ô lành SAU cửa sổ đọc lại của live (KFIX-B, mặc định 3′) ⇒ live giữ bản nặn cho phút đó: đếm + ví dụ
            java.util.Set<String> bad = new java.util.HashSet<>(o.sus.failedSymbols);
            for (String s : sus) {
                if (bad.contains(s)) continue;
                for (long mm : planner.pendingOf(s)) {
                    if (mm > mature) continue;
                    if (nowMs - (mm + MIN) > LIVE_REREAD_MS) {
                        o.lateHeal++;
                        if (o.lateEx.size() < 5) o.lateEx.add(KlineIngestCore.shortSym(s) + "@" + mm);
                    }
                }
            }
            cLateHeal.addAndGet(o.lateHeal);
            planner.onSuspectsSettled(sus, o.sus.failedSymbols, curMin, o.suspectLimit, mature);
            cSuspectFetched.addAndGet(o.sus.fetched);
            o.calls += o.sus.fetched + o.sus.failed;
        }
        List<String> smp = withSample ? SettlePlanner.take(plan.sample, klineRoom.getAsInt(), 0) : Collections.<String>emptyList();
        o.sampleRequested = smp.size();
        if (!smp.isEmpty()) {
            o.smp = core.settle(clock.getAsLong(), smp, settleLimit);
            cReconFetched.addAndGet(o.smp.fetched);
            cReconDiffWs.addAndGet(o.smp.rewrittenDiff);
            cReconFilled.addAndGet(o.smp.filledMissing);
            o.calls += o.smp.fetched + o.smp.failed;
        }
        o.pendingM = planner.pendingAt(m);
        o.pendingPrev = planner.pendingAt(m - 2 * MIN);
        o.dropped = planner.droppedCells();
        return o;
    }

    /** Ô thiếu trong {@code minutes} phút gần nhất (đọc store) ⇒ suspects. Trả số ô. */
    int seedFromStore(long curMin, int minutes, List<String> universe, KlineIngestCore.MinuteStore store) {
        int cells = 0;
        for (int i = minutes; i >= 1; i--) {
            long mm = curMin - i * MIN;
            Map<String, KlineObjectOptimized> rec = null;
            try {
                rec = store.read(mm);
            } catch (Exception e) {
                LOG.warn("[KLINE-INGEST] startup: doc phut {} loi: {}", mm, e.toString());
            }
            List<String> miss = new ArrayList<>();
            for (String s : universe) if (rec == null || !rec.containsKey(KlineIngestCore.shortSym(s))) miss.add(s);
            planner.markSuspects(miss, mm);
            cells += miss.size();
        }
        return cells;
    }
}
