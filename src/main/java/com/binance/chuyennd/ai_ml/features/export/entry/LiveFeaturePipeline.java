package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.ai_ml.features.export.MarketDataInlineGenerator;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.CoinRankManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.TreeMap;

/**
 * [V11 2026-10-20] docs/plan/V11_COLLECTOR_SETTLE.md — duong INPUT feature gate cua live = backtest
 * ({@code ExportGateDataset.replayToCsv}): moi phut M (theo thu tu, ke ca phut lo tick) nuoi
 * {@code HistoryManager}/{@code CoinRankManager} bang snapshot DAY DU record phut M (khong loc diedSymbol /
 * isTickerAvailable, khong last-ticker), phut quyet dinh goi {@code extractAllFeatures(M, snap, md)}.
 * MarketDataObject cua feature lay tu {@link MarketDataInlineGenerator} nuoi cung snapshot.
 *
 * <p>Cong: {@code LIVE_FEAT_INPUT=snapshot} (mac dinh {@code legacy} = khong tao lop nay => byte-identical).
 * Thuan logic qua {@link Sink}/{@link MdGen}/{@link MinuteSource} de unit test khong can Aerospike.
 */
public final class LiveFeaturePipeline {

    private static final Logger LOG = LoggerFactory.getLogger(LiveFeaturePipeline.class);
    static final long MIN = 60_000L;
    /** Cua so LiveTickerWindow (1000') — khong co snapshot cu hon. */
    static final int MAX_CATCHUP_MIN = 999;

    public static final String K_INPUT = "LIVE_FEAT_INPUT";
    public static final String K_FEAT_MD = "LIVE_FEAT_MD";
    public static final String K_MD_SOURCE = "LIVE_MD_SOURCE";
    public static final String K_TOL = "LIVE_FEAT_SETTLE_TOL";
    public static final String K_TIMEOUT = "LIVE_FEAT_SETTLE_TIMEOUT_MS";
    public static final String K_POLL = "LIVE_FEAT_SETTLE_POLL_MS";
    /** [V11 §6] tap died cho MarketDataObject = cua NGUON sim/train (store/market.bin sinh voi DIED_SYMBOLS=BTCDOM,USDC). */
    public static final String K_MD_DIED = "LIVE_MD_DIED_SYMBOLS";
    public static final String MD_DIED_DEFAULT = "BTCDOM,USDC";
    /**
     * [V12 SAFE C11 2026-10-25] {@code LIVE_SEED_EXCLUDE_DECISION_MIN=1}: seed GIU LAI phut cuoi cua map seed (khong nuoi
     * ngay); tick dau: phut giu lai &lt; phut quyet dinh => nuoi (= hanh vi cu), &gt;= => bo (phut quyet dinh tinh tu
     * snapshot cua so nhu moi tick) => het race "seed nuoi toi phut quyet dinh dau => minute &lt;= lastFed => mat tick"
     * (10-21 07:54:10). Mac dinh 0 = hanh vi cu y nguyen; c3_live dat 1.
     */
    public static final String K_SEED_EXCL = "LIVE_SEED_EXCLUDE_DECISION_MIN";
    public static final int TOL_DEFAULT = 3;
    public static final long TIMEOUT_DEFAULT = 3000L;
    public static final long POLL_DEFAULT = 250L;

    /** Nuoi lich su (updateHistory + getTopCoin) va trich feature — prod: {@link #extractorSink}. */
    public interface Sink {
        void feed(long minute, Map<String, KlineObjectSimple> snap);

        MarketFeatures extract(long minute, Map<String, KlineObjectSimple> snap, MarketDataObject md);
    }

    /** Bo sinh MarketDataObject tuan tu theo phut — prod: {@link MarketDataInlineGenerator#update}. */
    public interface MdGen {
        MarketDataObject update(Map<String, KlineObjectSimple> snap);

        /** [V12 R4d UNIVERSE-A1] ban point-in-time (prod: loc tai dung phut); mac dinh bo qua ts (fake/test cu khong doi). */
        default MarketDataObject update(Map<String, KlineObjectSimple> snap, long tsMs) {
            return update(snap);
        }
    }

    /** Nguon phut — prod: LiveTickerWindow (snapshot tu cache + cho du symbol). */
    public interface MinuteSource {
        Map<String, KlineObjectSimple> snapshot(long minute);

        SettleInfo await(long minute, int expected);
    }

    /** Ket qua cho settle phut quyet dinh. */
    public static final class SettleInfo {
        public final int have;
        public final int expected;
        public final long waitedMs;
        public final int polls;

        public SettleInfo(int have, int expected, long waitedMs, int polls) {
            this.have = have;
            this.expected = expected;
            this.waitedMs = waitedMs;
            this.polls = polls;
        }

        public boolean partial() {
            return expected > 0 && have < expected;
        }
    }

    /** Ket qua 1 tick. {@code features == null} => khong co snapshot phut quyet dinh (caller bo tick). */
    public static final class Result {
        public final long minute;
        public final MarketFeatures features;
        public final MarketDataObject featRate;
        public final MarketDataObject inlineRate;
        public final int nSym;
        public final boolean partial;
        /** [V11 §6] snapshot DAY DU phut quyet dinh (cho funding-45 + EntrySignalFilter). */
        public final Map<String, KlineObjectSimple> snapshot;

        Result(long minute, MarketFeatures features, MarketDataObject featRate, MarketDataObject inlineRate,
               int nSym, boolean partial, Map<String, KlineObjectSimple> snapshot) {
            this.snapshot = snapshot;
            this.minute = minute;
            this.features = features;
            this.featRate = featRate;
            this.inlineRate = inlineRate;
            this.nSym = nSym;
            this.partial = partial;
        }
    }

    private final Sink sink;
    private final MdGen md;
    private final boolean featMdInline;
    private final int tol;
    private long lastFed = Long.MIN_VALUE;
    private long lastMinute = Long.MIN_VALUE;
    private Result last;
    private int prevCount = -1;
    // [V12 SAFE C11] phut seed giu lai (chi khi seedExclLast)
    private boolean seedExclLast = false;
    private long pendingMinute = Long.MIN_VALUE;
    private Map<String, KlineObjectSimple> pendingSnap = null;
    long nSeedHeldFed = 0, nSeedHeldDropped = 0;
    /** [V12 2b c3_live] loc snapshot TRUOC khi nuoi md/history/feature (loai TradFi). null = khong loc (mac dinh). */
    private java.util.function.UnaryOperator<Map<String, KlineObjectSimple>> snapFilter = null;
    long nTicks = 0, nPartial = 0, nMdNull = 0, nGapMinutes = 0, nCatchup = 0, nNoSnap = 0;

    public LiveFeaturePipeline(Sink sink, MdGen md, boolean featMdInline, int tol) {
        this.sink = sink;
        this.md = md;
        this.featMdInline = featMdInline;
        this.tol = Math.max(0, tol);
    }

    // ------------------------------ cau hinh ------------------------------

    public static boolean snapshotMode() {
        return "snapshot".equalsIgnoreCase(Cfg.getOr(K_INPUT, "legacy").trim());
    }

    /** Rate dung cho QUYET DINH market-level (levelChange/predictAllCandidates). Mac dinh legacy. */
    public static boolean decisionMdInline() {
        return "inline".equalsIgnoreCase(Cfg.getOr(K_MD_SOURCE, "legacy").trim());
    }

    /** [V12 SAFE C11] doc co LIVE_SEED_EXCLUDE_DECISION_MIN ("1"/"true" => bat; mac dinh 0). */
    static boolean seedExcludeCfg() {
        String v = Cfg.getOr(K_SEED_EXCL, "0").trim();
        return "1".equals(v) || "true".equalsIgnoreCase(v);
    }

    /**
     * [V12 2b] dat bo loc snapshot (goi TRUOC {@link #seed}); c3_live: bo symbol TradFi khoi MarketDataInline, HistoryManager/
     * CoinRank, feature va snapshot funding/EntrySignalFilter. null = khong loc (c3_shadow/sim y nguyen).
     */
    public synchronized void setSnapshotFilter(java.util.function.UnaryOperator<Map<String, KlineObjectSimple>> f) {
        this.snapFilter = f;
    }

    private Map<String, KlineObjectSimple> filt(Map<String, KlineObjectSimple> snap, long minute) {
        // [V12 R4d UNIVERSE-A1] universe A1 tai dung phut (co tat => cung map), roi bo loc c3_live (neu co)
        snap = com.binance.chuyennd.tradecore.selector.UniverseA1Filter.filter(snap, minute);
        java.util.function.UnaryOperator<Map<String, KlineObjectSimple>> f = snapFilter;
        return f == null || snap == null ? snap : f.apply(snap);
    }

    /** [V12 SAFE C11] bat/tat giu lai phut seed cuoi (goi TRUOC {@link #seed}). */
    public synchronized void setSeedExcludeDecisionMin(boolean on) {
        this.seedExclLast = on;
    }

    static boolean featMdInlineCfg() {
        return !"legacy".equalsIgnoreCase(Cfg.getOr(K_FEAT_MD, "inline").trim());
    }

    static long cfgLong(String k, long def) {
        try {
            return Long.parseLong(Cfg.getOr(k, String.valueOf(def)).trim());
        } catch (NumberFormatException e) {
            LOG.error("[FEAT-PIPE] {} khong phai so -> {}", k, def);
            return def;
        }
    }

    public static long timeoutMs() {
        return Math.max(0L, cfgLong(K_TIMEOUT, TIMEOUT_DEFAULT));
    }

    public static long pollMs() {
        return Math.max(10L, cfgLong(K_POLL, POLL_DEFAULT));
    }

    /** Sink prod: CUNG trinh tu replayToCsv (updateHistory qua extractor de chat ms startTime, roi getTopCoin). */
    public static Sink extractorSink(final ComprehensiveMarketFeatureExtractor ex) {
        return new Sink() {
            @Override
            public void feed(long minute, Map<String, KlineObjectSimple> snap) {
                ex.updateMarketHistory(snap);
                CoinRankManager.getInstance().getTopCoin(minute);
            }

            @Override
            public MarketFeatures extract(long minute, Map<String, KlineObjectSimple> snap, MarketDataObject m) {
                return ex.extractAllFeatures(minute, snap, m);
            }
        };
    }

    public static LiveFeaturePipeline forProd(ComprehensiveMarketFeatureExtractor ex) {
        java.util.Set<String> died = parseDied(Cfg.getOr(K_MD_DIED, MD_DIED_DEFAULT));
        final MarketDataInlineGenerator g = new MarketDataInlineGenerator(died);
        MdGen gen = new MdGen() {   // [V12 R4d] co tat: update(snap, ts) == update(snap)
            @Override
            public MarketDataObject update(Map<String, KlineObjectSimple> snap) {
                return g.update(snap);
            }

            @Override
            public MarketDataObject update(Map<String, KlineObjectSimple> snap, long tsMs) {
                return g.update(snap, tsMs);
            }
        };
        LiveFeaturePipeline p = new LiveFeaturePipeline(extractorSink(ex), gen, featMdInlineCfg(),
                (int) cfgLong(K_TOL, TOL_DEFAULT));
        LOG.warn("*** [FEAT-PIPE] LIVE_FEAT_INPUT=snapshot: feature gate tinh tren snapshot DAY DU phut M (= replayToCsv); "
                        + "feat_md={} decision_md={} settle tol={} timeout={}ms poll={}ms md_died={}",
                p.featMdInline ? "inline" : "legacy", decisionMdInline() ? "inline" : "legacy", p.tol, timeoutMs(), pollMs(),
                new java.util.TreeSet<>(died));
        p.seedExclLast = seedExcludeCfg();
        if (p.seedExclLast) {
            LOG.warn("*** [FEAT-PIPE] {}=1: seed giu lai phut cuoi, tick dau tinh phut quyet dinh tu snapshot cua so (C11)",
                    K_SEED_EXCL);
        } else if ("c3_live".equalsIgnoreCase(Cfg.getOr("LIVE_PROFILE", "").trim())) {
            LOG.warn("[FEAT-PIPE] LIVE_PROFILE=c3_live nhung {}=0 => race seed/tick dau sau restart (C11) VAN CON", K_SEED_EXCL);
        }
        return p;
    }

    /** Cung quy uoc Constants.diedSymbol: tach dau phay, them USDT neu thieu. */
    static java.util.Set<String> parseDied(String v) {
        java.util.Set<String> out = new java.util.HashSet<>();
        if (v == null) return out;
        for (String x : v.split(",")) {
            String t = x.trim();
            if (t.isEmpty()) continue;
            out.add(t.contains("USDT") ? t : t + "USDT");
        }
        return out;
    }

    static long align(long t) {
        return t - Math.floorMod(t, MIN);
    }

    // ------------------------------ logic ------------------------------

    /**
     * Seed luc khoi dong: replay TUNG phut tang dan (md + updateHistory + getTopCoin) — hang CoinRank gio dau sau
     * restart = backtest. Key co the lech ms (readDataFromAerospikeCustom(now-2000')) => can ve dau phut.
     */
    public synchronized void seed(TreeMap<Long, Map<String, KlineObjectSimple>> minutes) {
        if (seedExclLast) {
            seedHoldLast(minutes);
            return;
        }
        int n = 0;
        if (minutes != null) {
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : minutes.entrySet()) {
                long m = align(e.getKey());
                Map<String, KlineObjectSimple> snap = filt(e.getValue(), m);
                if (m <= lastFed || snap == null || snap.isEmpty()) continue;
                for (KlineObjectSimple k : snap.values()) {
                    if (k != null && k.startTime != null) k.startTime = align(k.startTime);
                }
                md.update(snap, m);
                sink.feed(m, snap);
                lastFed = m;
                prevCount = snap.size();
                n++;
            }
        }
        LOG.info("[FEAT-PIPE] seed replay {} phut, phut cuoi {} ({} symbol)", n, lastFed, prevCount);
    }

    /** [V12 SAFE C11] nhu {@link #seed} nhung phut hop le CUOI cung duoc giu lai (pending) cho tick dau quyet dinh. */
    private void seedHoldLast(TreeMap<Long, Map<String, KlineObjectSimple>> minutes) {
        int n = 0;
        long heldMin = Long.MIN_VALUE;
        Map<String, KlineObjectSimple> held = null;
        if (minutes != null) {
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : minutes.entrySet()) {
                long m = align(e.getKey());
                Map<String, KlineObjectSimple> snap = filt(e.getValue(), m);
                if (m <= lastFed || m <= heldMin || snap == null || snap.isEmpty()) continue;
                for (KlineObjectSimple k : snap.values()) {
                    if (k != null && k.startTime != null) k.startTime = align(k.startTime);
                }
                if (held != null) {
                    md.update(held, heldMin);
                    sink.feed(heldMin, held);
                    lastFed = heldMin;
                    prevCount = held.size();
                    n++;
                }
                held = snap;
                heldMin = m;
            }
        }
        pendingSnap = held;
        pendingMinute = heldMin;
        LOG.info("[FEAT-PIPE] seed replay {} phut, phut cuoi {} ({} symbol); GIU LAI phut {} cho tick dau ({})",
                n, lastFed, prevCount, held == null ? "-" : String.valueOf(heldMin), K_SEED_EXCL);
    }

    /**
     * Tick quyet dinh phut {@code minute}: (1) cho du symbol (F-settle); (2) nuoi cac phut con thieu
     * (lastFed, minute); (3) phut quyet dinh: md + extract. Goi lai cung phut => tra ket qua cu (khong nuoi trung).
     */
    public synchronized Result onTick(MinuteSource src, long minute, MarketDataObject legacyRate) {
        if (minute == lastMinute && last != null) return last;
        if (pendingSnap != null) {   // [V12 SAFE C11] chi khi co LIVE_SEED_EXCLUDE_DECISION_MIN=1
            if (pendingMinute < minute) {
                md.update(pendingSnap, pendingMinute);
                sink.feed(pendingMinute, pendingSnap);
                lastFed = pendingMinute;
                prevCount = pendingSnap.size();
                nSeedHeldFed++;
                LOG.info("[FEAT-PIPE] tick dau phut {}: nuoi phut seed giu lai {} (< phut quyet dinh)", minute, pendingMinute);
            } else {
                nSeedHeldDropped++;
                LOG.warn("[FEAT-PIPE] tick dau phut {}: BO phut seed giu lai {} (>= phut quyet dinh) -> tinh tu snapshot cua so"
                        + " (race seed/tick dau da tranh, C11)", minute, pendingMinute);
            }
            pendingSnap = null;
            pendingMinute = Long.MIN_VALUE;
        }
        if (lastFed != Long.MIN_VALUE && minute <= lastFed) {
            LOG.warn("[FEAT-PIPE] phut {} <= phut da nuoi {} (clock lui?) -> giu ket qua cu", minute, lastFed);
            return last;
        }
        int expected = prevCount > 0 ? Math.max(1, prevCount - tol) : 0;
        SettleInfo si = expected > 0 ? src.await(minute, expected) : new SettleInfo(-1, 0, 0L, 0);
        boolean partial = si.partial();
        if (partial) {
            nPartial++;
            LOG.warn("[FEAT-SETTLE] partial=true minute={} have={} expected={} waited={}ms polls={} (tinh tren du lieu dang co)",
                    minute, si.have, si.expected, si.waitedMs, si.polls);
        }
        long from = lastFed == Long.MIN_VALUE ? minute : lastFed + MIN;
        from = Math.max(from, minute - (long) MAX_CATCHUP_MIN * MIN);
        for (long m = from; m < minute; m += MIN) {
            Map<String, KlineObjectSimple> snap = filt(src.snapshot(m), m);
            if (snap == null || snap.isEmpty()) {
                nGapMinutes++;
                continue;
            }
            md.update(snap, m);
            sink.feed(m, snap);
            lastFed = m;
            nCatchup++;
        }
        Map<String, KlineObjectSimple> snap = filt(src.snapshot(minute), minute);
        if (snap == null || snap.isEmpty()) {
            nNoSnap++;
            LOG.error("[FEAT-PIPE] khong co snapshot phut {} trong cache -> bo tick", minute);
            return new Result(minute, null, legacyRate, null, 0, true, null);
        }
        MarketDataObject inl = md.update(snap, minute);
        MarketDataObject fr = legacyRate;
        if (featMdInline) {
            if (inl != null) {
                fr = inl;
            } else {
                nMdNull++;
                LOG.warn("[FEAT-PIPE] MarketDataInlineGenerator tra null phut {} (guard) -> feature dung rate legacy", minute);
            }
        }
        MarketFeatures f = sink.extract(minute, snap, fr);
        lastFed = minute;
        lastMinute = minute;
        prevCount = snap.size();
        nTicks++;
        if (nTicks % 60 == 0) {
            LOG.info("[FEAT-PIPE] ticks={} partial={} md_null={} gap_minutes={} catchup={} no_snap={} nsym={}",
                    nTicks, nPartial, nMdNull, nGapMinutes, nCatchup, nNoSnap, snap.size());
        }
        last = new Result(minute, f, fr, inl, snap.size(), partial, snap);
        return last;
    }

    public synchronized long lastFed() {
        return lastFed;
    }
}
