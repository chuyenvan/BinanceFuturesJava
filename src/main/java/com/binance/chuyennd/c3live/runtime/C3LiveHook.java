package com.binance.chuyennd.c3live.runtime;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.c3live.adapter.GatewayFactory;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import com.binance.chuyennd.tradecore.selector.LiveDcaGridC3;
import com.binance.chuyennd.tradecore.selector.LiveProfileC3;
import com.binance.chuyennd.trading.DetectEntrySignal2TradeNormal;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Predicate;

/**
 * [V12 c3_live] Diem noi DUY NHAT tu {@code DetectEntrySignal2TradeNormal} vao duong lenh that. {@link #enabled()} =
 * {@code LIVE_PROFILE=c3_live} && {@code LIVE_ADAPTER} in {dry, live} (doc 1 lan luc nap lop) — tat => moi ham la
 * no-op / null / rong => c3_shadow & sim KHONG doi. Khong bao gio nem ra ngoai.
 *
 * <p>[2b MASTER 10-25] {@link #excludeTradFiFeatures()} = enabled && {@code LIVE_C3_EXCLUDE_TRADFI_FEATURES} != 0
 * (mac dinh 1 o c3_live; ngoai c3_live luon 0): loai symbol TradFi khoi moi phep tinh cat ngang/thi truong cua feature
 * gate (snapshot LiveFeaturePipeline => MarketDataInline + HistoryManager/CoinRank + funding cross-sectional + pool rank
 * selector). Ly do: DEV/model chua tung thay TradFi. Input model DOI chi o c3_live — kiem bang dry-run parity sau.
 */
public final class C3LiveHook {

    private static final Logger LOG = LoggerFactory.getLogger(C3LiveHook.class);
    public static final String KEY_EXCLUDE_TRADFI_FEATURES = "LIVE_C3_EXCLUDE_TRADFI_FEATURES";
    private static final boolean ENABLED = decide(LiveProfileC3.isLive(), Cfg.get(GatewayFactory.KEY_ADAPTER));
    private static final boolean EXCL_TRADFI_FEAT = decideExcludeTradFi(ENABLED, Cfg.get(KEY_EXCLUDE_TRADFI_FEATURES));
    private static volatile long lastIdxWarnMs = Long.MIN_VALUE / 2;
    private static volatile long lastFeatWarnMs = Long.MIN_VALUE / 2;

    private C3LiveHook() {
    }

    static boolean decide(boolean profileLive, String adapter) {
        return profileLive && GatewayFactory.Mode.parse(adapter) != GatewayFactory.Mode.OFF;
    }

    /** Thuan: chi bat khi hook bat (c3_live + adapter); gia tri "0"/"false" => tat; mac dinh bat. */
    static boolean decideExcludeTradFi(boolean hookEnabled, String raw) {
        if (!hookEnabled) return false;
        if (raw == null) return true;
        String v = raw.trim();
        return !("0".equals(v) || "false".equalsIgnoreCase(v));
    }

    public static boolean enabled() {
        return ENABLED;
    }

    /** [V12 R4h] hook bat VA LIVE_ADAPTER=live (lenh that) — chon nguon "dang giu" truoc gate. */
    private static final boolean LIVE_ADAPTER = ENABLED
            && GatewayFactory.Mode.parse(Cfg.get(GatewayFactory.KEY_ADAPTER)) == GatewayFactory.Mode.LIVE;

    public static boolean liveAdapter() {
        return LIVE_ADAPTER;
    }

    /** [2b] loai TradFi khoi feature cat ngang/thi truong (chi c3_live). */
    public static boolean excludeTradFiFeatures() {
        return EXCL_TRADFI_FEAT;
    }

    /** [V12 R4d] UNIVERSE_A1 dang bat (loi init => false: start() da nem truoc do; hook khong bao gio nem). */
    static boolean a1Active() {
        try {
            return com.binance.chuyennd.tradecore.selector.UniverseA1Filter.isActive();
        } catch (RuntimeException e) {
            return false;
        }
    }

    /**
     * 1 leg da qua cong quyet dinh (gate PASS, cau dao mat do) => duong that. ref = close nen 1m quyet dinh (C2);
     * gia size = price_realtime tuoi (nhu so giay TASK-027 #7) else close. [2b] symbolPred/rank cua leg (nhu so giay) =>
     * metadata cum that (trailing dung symbolPred).
     */
    public static void onLeg(String symbol, KlineObjectSimple ticker, MarketLevelChange level) {
        if (!ENABLED || symbol == null || ticker == null) return;
        try {
            C3LiveRuntime rt = C3LiveRuntime.get();
            if (rt == null || rt.entry() == null) return;   // [2c MIN-7] manage-only: khong mo moi
            double ref = ticker.priceClose;
            double sizing = ref;
            Float rtPx = DataManagerAerospikeFloatSim.getPriceRealtime(symbol);
            Long rtTs = DataManagerAerospikeFloatSim.getPriceRealtimeTs(symbol);
            if (rtPx != null && rtPx > 0 && rtTs != null
                    && System.currentTimeMillis() - rtTs <= Configs.PRICE_REALTIME_MAX_AGE_MS) {
                sizing = rtPx.doubleValue();
            }
            CoinRankManager crm = CoinRankManager.getInstance();
            float tierMul = crm.getBudgetMultiplier(symbol);
            // peek: KHONG goi checkAndUpdate (khong doi thu tu cap nhat tier ma so giay thay)
            boolean tier3 = crm.peekCoinTier(symbol) == CoinRankManager.CoinTier.TIER_3_SHITCOIN;
            Integer rk = DetectEntrySignal2TradeNormal.LATEST_SEL_RANK.get(symbol);
            Float pred = DetectEntrySignal2TradeNormal.paperSymbolPred(symbol);
            rt.entry().onLeg(new C3LiveEntry.LegInput(symbol, String.valueOf(level),
                    level == MarketLevelChange.DCA_LEVEL1, ticker.startTime.longValue(), ref, sizing, tierMul, tier3,
                    pred, rk == null ? -1 : rk), System.currentTimeMillis());
        } catch (Throwable t) {
            LOG.error("[C3-LIVE] hook onLeg loi {}: {}", symbol, t.toString());
        }
    }

    /** Symbol vi the THAT den bac DCA grid (gia = close nen cuoi) — de goi leg "chi live" khi so giay khong den bac. */
    public static List<String> dcaDue(Map<String, KlineObjectSimple> lastTickers) {
        if (!ENABLED || lastTickers == null || !LiveDcaGridC3.active()) return Collections.emptyList();
        try {
            C3LiveRuntime rt = C3LiveRuntime.get();
            if (rt == null) return Collections.emptyList();
            List<String> out = new ArrayList<>();
            for (LiveDcaGridC3.GridState g : rt.book().gridStates()) {
                KlineObjectSimple t = lastTickers.get(g.symbol);
                if (t == null || !(t.priceClose > 0f)) continue;
                if (DcaUtils.shouldDcaGrid(g.firstEntryPrice, t.priceClose, g.legCount)) out.add(g.symbol);
            }
            return out;
        } catch (Throwable t) {
            LOG.error("[C3-LIVE] hook dcaDue loi: {}", t.toString());
            return Collections.emptyList();
        }
    }

    /**
     * Thanh vien chi so thi truong (market level / ALT_EW) cua c3_live = {@code SymbolUniverseLive.marketIndexMembers()}
     * (da loai TradFi). null = KHONG loc (hook tat, hoac chua co snapshot universe — WARN 10').
     */
    public static Set<String> marketIndexOrNull() {
        if (!ENABLED) return null;
        if (a1Active()) return null;   // [V12 R4d] UNIVERSE_A1=1: market level tren universe A1 (= backtest), khong hep them
        try {
            C3LiveRuntime rt = C3LiveRuntime.get();
            Set<String> m = rt == null ? null : rt.marketIndexOrNull();
            if (m == null) {
                long now = System.currentTimeMillis();
                if (now - lastIdxWarnMs > 600_000L) {
                    lastIdxWarnMs = now;
                    LOG.warn("[C3-LIVE] chua co universe snapshot => market level KHONG loc TradFi o tick nay");
                }
            }
            return m;
        } catch (Throwable t) {
            return null;
        }
    }

    /**
     * [2b] Predicate "symbol TradFi" de loai khoi feature; null = KHONG loc (co tat / c3_shadow / sim / chua co universe).
     */
    public static Predicate<String> tradFiFeatureFilterOrNull() {
        if (!EXCL_TRADFI_FEAT) return null;
        if (a1Active()) return null;   // [V12 R4d] UNIVERSE_A1=1: TF/INDEX da loai point-in-time o diem loc A1
        try {
            C3LiveRuntime rt = C3LiveRuntime.get();
            Predicate<String> p = rt == null ? null : rt.tradFiOrNull();
            if (p == null) {
                long now = System.currentTimeMillis();
                if (now - lastFeatWarnMs > 600_000L) {
                    lastFeatWarnMs = now;
                    LOG.warn("[C3-LIVE] {}=1 nhung chua co universe snapshot => feature KHONG loc TradFi o lan nay",
                            KEY_EXCLUDE_TRADFI_FEATURES);
                }
            }
            return p;
        } catch (Throwable t) {
            return null;
        }
    }

    /**
     * [2b] Ban sao map KHONG co symbol TradFi (khi {@link #excludeTradFiFeatures()} + co universe); nguoc lai tra CHINH
     * map dau vao (cung object => duong c3_shadow/sim khong doi). Khong sua map goc.
     */
    public static <V> Map<String, V> dropTradFi(Map<String, V> m) {
        if (m == null || !EXCL_TRADFI_FEAT) return m;
        Predicate<String> tf = tradFiFeatureFilterOrNull();
        return filter(m, tf);
    }

    /** Thuan: loc map theo predicate TradFi (null => tra nguyen map). Giu thu tu lap neu map co thu tu. */
    static <V> Map<String, V> filter(Map<String, V> m, Predicate<String> tf) {
        if (m == null || tf == null) return m;
        boolean any = false;
        for (String k : m.keySet()) {
            if (k != null && tf.test(k)) {
                any = true;
                break;
            }
        }
        if (!any) return m;
        Map<String, V> out = m instanceof LinkedHashMap || m instanceof java.util.SortedMap
                ? new LinkedHashMap<>() : new HashMap<>();
        for (Map.Entry<String, V> e : m.entrySet()) {
            if (e.getKey() != null && tf.test(e.getKey())) continue;
            out.put(e.getKey(), e.getValue());
        }
        return out;
    }

    /** Symbol c3_live dang so huu (so that) — cho LegacySymbols. Tat => rong. */
    public static Set<String> ownedSymbols() {
        if (!ENABLED) return Collections.emptySet();
        try {
            C3LiveRuntime rt = C3LiveRuntime.get();
            return rt == null ? Collections.<String>emptySet() : rt.book().ownedSymbols();
        } catch (Throwable t) {
            return Collections.emptySet();
        }
    }
}
