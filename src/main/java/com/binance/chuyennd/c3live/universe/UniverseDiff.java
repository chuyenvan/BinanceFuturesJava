package com.binance.chuyennd.c3live.universe;

import java.util.Collections;
import java.util.Set;
import java.util.TreeSet;

/** [V12 P0-U1] Bao cao 1 lan refresh universe (so voi lan truoc). Tap da sap xep, bat bien. */
public final class UniverseDiff {
    private final long atMs;
    private final int nListed;
    private final int nAlive;
    private final int nTradable;
    private final int nBuyable;
    private final Set<String> added;
    private final Set<String> removed;
    private final Set<String> tradfiExcluded;
    private final Set<String> newlyTradFi;
    private final Set<String> excludeStillTrading;
    private final Set<String> nonAsciiTradable;
    private final Set<String> deliverySoon;
    private final Set<String> unverified;

    UniverseDiff(long atMs, int nListed, int nAlive, int nTradable, int nBuyable, Set<String> added, Set<String> removed,
                 Set<String> tradfiExcluded, Set<String> newlyTradFi, Set<String> excludeStillTrading,
                 Set<String> nonAsciiTradable, Set<String> deliverySoon, Set<String> unverified) {
        this.atMs = atMs;
        this.nListed = nListed;
        this.nAlive = nAlive;
        this.nTradable = nTradable;
        this.nBuyable = nBuyable;
        this.added = s(added);
        this.removed = s(removed);
        this.tradfiExcluded = s(tradfiExcluded);
        this.newlyTradFi = s(newlyTradFi);
        this.excludeStillTrading = s(excludeStillTrading);
        this.nonAsciiTradable = s(nonAsciiTradable);
        this.deliverySoon = s(deliverySoon);
        this.unverified = s(unverified);
    }

    private static Set<String> s(Set<String> x) { return Collections.unmodifiableSet(new TreeSet<>(x)); }

    public long getAtMs() { return atMs; }
    /** So symbol trong exchangeInfo. */
    public int getListed() { return nListed; }
    /** status == TRADING (moi loai hop dong). */
    public int getAlive() { return nAlive; }
    /** Trong universe U: TRADING, PERPETUAL, USDT, khong EXCLUDE, khong TradFi. */
    public int getTradable() { return nTradable; }
    /** Mua duoc tai atMs (them non-ASCII theo co, deliveryDate &gt;= now + 7 ngay). */
    public int getBuyable() { return nBuyable; }
    /** Vao universe U so voi lan truoc. */
    public Set<String> getAdded() { return added; }
    /** Ra khoi universe U so voi lan truoc. */
    public Set<String> getRemoved() { return removed; }
    /** TradFi dang TRADING bi loai (toan bo). */
    public Set<String> getTradfiExcluded() { return tradfiExcluded; }
    /** TradFi moi xuat hien so voi lan truoc. */
    public Set<String> getNewlyTradFi() { return newlyTradFi; }
    /** Trong UNIVERSE_EXCLUDE (khong co co intentional) ma van TRADING -> CANH BAO (vd POWR, MDT). */
    public Set<String> getExcludeStillTrading() { return excludeStillTrading; }
    /** Ten non-ASCII trong U (mac dinh khong mua: LIVE_C3_ALLOW_NONASCII=0). */
    public Set<String> getNonAsciiTradable() { return nonAsciiTradable; }
    /** Trong U nhung deliveryDate &lt; now + 7 ngay (khong mua). */
    public Set<String> getDeliverySoon() { return deliverySoon; }
    /** Phan loai TradFi chua xac minh (thieu underlyingType). */
    public Set<String> getUnverified() { return unverified; }

    public String summary() {
        return "[UNIVERSE] listed=" + nListed + " alive=" + nAlive + " tradable=" + nTradable + " buyable=" + nBuyable
                + " +" + added.size() + " -" + removed.size() + " tradfi_excl=" + tradfiExcluded.size() + " new_tradfi=" + newlyTradFi
                + " exclude_still_trading=" + excludeStillTrading + " nonascii=" + nonAsciiTradable.size()
                + " delivery_soon=" + deliverySoon + " unverified=" + unverified.size();
    }

    @Override
    public String toString() { return summary(); }
}
