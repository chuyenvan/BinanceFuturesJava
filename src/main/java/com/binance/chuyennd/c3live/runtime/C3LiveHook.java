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
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * [V12 c3_live] Diem noi DUY NHAT tu {@code DetectEntrySignal2TradeNormal} vao duong lenh that. {@link #enabled()} =
 * {@code LIVE_PROFILE=c3_live} && {@code LIVE_ADAPTER} in {dry, live} (doc 1 lan luc nap lop) — tat => moi ham la
 * no-op / null / rong => c3_shadow & sim KHONG doi. Khong bao gio nem ra ngoai.
 */
public final class C3LiveHook {

    private static final Logger LOG = LoggerFactory.getLogger(C3LiveHook.class);
    private static final boolean ENABLED = decide(LiveProfileC3.isLive(), Cfg.get(GatewayFactory.KEY_ADAPTER));
    private static volatile long lastIdxWarnMs = Long.MIN_VALUE / 2;

    private C3LiveHook() {
    }

    static boolean decide(boolean profileLive, String adapter) {
        return profileLive && GatewayFactory.Mode.parse(adapter) != GatewayFactory.Mode.OFF;
    }

    public static boolean enabled() {
        return ENABLED;
    }

    /**
     * 1 leg da qua cong quyet dinh (gate PASS, cau dao mat do) => duong that. ref = close nen 1m quyet dinh (C2);
     * gia size = price_realtime tuoi (nhu so giay TASK-027 #7) else close.
     */
    public static void onLeg(String symbol, KlineObjectSimple ticker, MarketLevelChange level) {
        if (!ENABLED || symbol == null || ticker == null) return;
        try {
            C3LiveRuntime rt = C3LiveRuntime.get();
            if (rt == null) return;
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
            rt.entry().onLeg(new C3LiveEntry.LegInput(symbol, String.valueOf(level),
                    level == MarketLevelChange.DCA_LEVEL1, ticker.startTime.longValue(), ref, sizing, tierMul, tier3),
                    System.currentTimeMillis());
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
