package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * SO VI THE SHADOW cua profile {@code LIVE_PROFILE=c3_shadow} — CHI chay khi
 * {@link LiveProfileC3#on()}.
 *
 * <p>VI SAO CAN: duong live chan lenh that o {@code SHADOW_NO_PUSH} => KHONG co
 * {@code PositionRisk} nao sinh ra => {@code marginRunning} mai bang 0 (throttle = 1, cung mot
 * coin duoc "would-BUY" lai moi tick) va toan bo duong exit live ({@code initSLFirst} /
 * {@code processDynamicTP_SL}) khong bao gio chay. Lop nay giu vi the GIAY de:
 * <ul>
 *   <li>chan mo trung coin dang giu (giong {@code symbol2Pos} that),</li>
 *   <li>cap {@code marginRunning} + {@code equity} cho sizing compound (d),</li>
 *   <li>chay exit C3: arm 0.07 (a), ratchet LIEN TUC voi {@code giveback = min(peak*0.5, cap)}
 *       va cap 0.08/0.03 ban le 0.29 tren {@code symbolPred} (c), time-stop 168h (b),</li>
 *   <li>ghi {@code ledger.csv} de {@code tools/shadow_vs_sim.py} ghep cap voi sim.</li>
 * </ul>
 *
 * <p>KHONG dat lenh, KHONG goi Binance, KHONG ghi Aerospike/Redis. "Dong lenh" = mot dong log
 * {@code [SHADOW] would-CLOSE ...} + mot dong ledger.
 *
 * <p>[BOOKFIX 2026-09-13] DCA/BIG_DOWN cung coin: truoc day {@code open} la {@code Map<String,Pos>}
 * + {@code putIfAbsent} => leg2+ bi VUT im lang (khong VWAP/legCount/margin) => thieu 22.6% pnl
 * (docs/RESULT_BOOKFIX.md). Nay {@code open} la {@code Map<String,Cluster>}: openPos CONG leg vao
 * cum + tinh lai VWAP giong {@code SimulatorMarketLevelTicker1MStopLoss.mergeOrder}.
 *
 * <p>&#9888; Ke toan GIAY: PnL o day tinh tu gia {@code price_realtime}, khong co phi/slippage/funding
 * va khong lam tron tick-size. Khong duoc so {@code mean(margin)}/equity voi sim
 * ({@code docs/L1_SHADOW_C3.md} muc 7.2).
 */
public final class ShadowBookC3 {

    private static final Logger LOG = LoggerFactory.getLogger(ShadowBookC3.class);
    private static volatile ShadowBookC3 INSTANCE;

    /** Cot ledger: giu ten {@code sym/ts_entry/symbol_pred/entry} de
     * {@code tools/shadow_vs_sim.py pair} doc truc tiep duoc. */
    private static final String HEADER =
            "sym,ts_entry,entry,qty,rank,symbol_pred,ts_exit,exit_price,reason,pnl";

    public static final String REASON_TRAILING = "TRAILING_STOP";
    public static final String REASON_TIME_STOP = "TIME_STOP_168H";

    /**
     * Mot CUM vi the giay cua 1 coin: gop tat ca leg (leg mo + DCA_LEVEL1 + BIG_DOWN) giong
     * {@code OrderTargetInfoTest} cum cua sim sau {@code mergeOrder}. Giu VWAP entry, tong qty,
     * so leg, gia entry leg dau (bat bien) va moc leg dau (neo time-stop).
     */
    public static final class Cluster {
        public final String symbol;
        /** Moc leg DAU cua cum — neo time-stop 168h (giong {@code clusterFirstLegTime} cua sim). */
        public long tsFirstLeg;
        /** Moc leg CUOI (chi de luu tru/chan doan). */
        public long tsLastLeg;
        /** &Sigma;(entry_i * qty_i) — notional cum; VWAP = sumEntryQty / qty. */
        public double sumEntryQty;
        /** Tong qty cua ca cum. */
        public float qty;
        /** So leg da khop (1 = chua nhoi). Giong {@code OrderTargetInfoTest.legCount}. */
        public int legCount;
        /** Gia entry leg DAU — bat bien qua DCA (giong {@code firstEntryPrice} cua sim). */
        public float firstEntryPrice;
        /** Rank cua leg KHONG-null (>=0) DAU TIEN — giong {@code clusterSelRank}. -1 = chua co. */
        public int rank;
        /** symbolPred cua leg KHONG-null DAU TIEN — giong {@code clusterSymbolPred}. */
        public Float symbolPred;
        /** null = CHUA arm trailing (dieu kien time-stop, giong {@code priceSL == null} o sim). */
        public Float priceSL;
        /** dinh lai (ty le so voi VWAP entry) da dat — ratchet bam theo dinh nhu sim. */
        public float peakRate;

        Cluster(String symbol, long ts, float entry, float qty, int rank, Float symbolPred) {
            this.symbol = symbol;
            this.tsFirstLeg = ts;
            this.tsLastLeg = ts;
            this.sumEntryQty = (double) entry * qty;
            this.qty = qty;
            this.legCount = 1;
            this.firstEntryPrice = entry;
            this.rank = rank;
            this.symbolPred = symbolPred;
            this.priceSL = null;
            this.peakRate = 0f;
        }

        /** VWAP entry = &Sigma;(entry_i*qty_i)/&Sigma;qty_i — CUNG cong thuc {@code mergeOrder} cua sim. */
        public float avgEntry() {
            return (float) (sumEntryQty / qty);
        }

        /**
         * Cong 1 leg (DCA/BIG_DOWN cung coin) vao cum: cap nhat VWAP/qty/legCount; giu rank/pred
         * cua leg KHONG-null dau tien; RE-ARM (priceSL=null, peakRate=0) vi sim {@code mergeOrder}
         * tao ra mot cum {@code REQUEST} moi voi {@code minPrice=priceClose} (dinh trailing reset).
         * KHONG dung tsFirstLeg/firstEntryPrice (bat bien qua DCA nhu sim).
         */
        void addLeg(long ts, float entry, float q, int legRank, Float legPred) {
            this.sumEntryQty += (double) entry * q;
            this.qty += q;
            this.legCount++;
            if (ts > this.tsLastLeg) this.tsLastLeg = ts;
            if (this.rank < 0 && legRank >= 0) this.rank = legRank;
            if (this.symbolPred == null && legPred != null) this.symbolPred = legPred;
            this.priceSL = null;
            this.peakRate = 0f;
        }

        /** Margin dang chiem = notional / don bay (cung cach {@code PositionHelper.callMargin}). */
        float margin() {
            int lev = Configs.LEVERAGE_ORDER > 0 ? Configs.LEVERAGE_ORDER : 1;
            return (float) (sumEntryQty / lev);
        }
    }

    private final Map<String, Cluster> open = new ConcurrentHashMap<>();
    private final String ledgerPath;
    /** Vi the DANG MO + PnL da chot, ghi ra dia sau MOI thay doi. */
    private final String statePath;
    private double realized = 0d;
    private long nOpen = 0, nClose = 0;

    private ShadowBookC3() {
        String dir = Cfg.get("SHADOW_C3_DIR");
        if (dir == null || dir.trim().isEmpty()) dir = ".";
        File f = new File(dir, "ledger.csv");
        ledgerPath = f.getAbsolutePath();
        try {
            File parent = f.getParentFile();
            if (parent != null && !parent.exists() && !parent.mkdirs()) {
                LOG.warn("[SHADOW] khong tao duoc thu muc ledger {}", parent);
            }
            if (!f.exists()) {
                try (PrintWriter w = new PrintWriter(new FileWriter(f, true))) {
                    w.println(HEADER);
                }
            }
        } catch (IOException e) {
            LOG.error("[SHADOW] khong mo duoc ledger {}: {}", ledgerPath, e.getMessage());
        }
        statePath = new File(dir, "open_positions.csv").getAbsolutePath();
        loadState();
        LOG.info("[SHADOW] so vi the giay khoi tao, ledger={} state={} open={} realized={} paperEquity={}",
                ledgerPath, statePath, open.size(), realized, LiveProfileC3.paperEquity());
    }

    /**
     * Nap lai vi the dang mo sau restart. BAT BUOC: {@code ThreadAutoRestartProgram} restart JVM
     * moi 4 gio — neu so chi nam trong RAM thi (i) time-stop 168h KHONG BAO GIO toi duoc,
     * (ii) cung mot coin bi mo lai moi lan restart => ledger sai he thong.
     *
     * <p>Tuong thich nguoc: dong 8-truong cu (1 leg) van doc duoc — legCount=1,
     * firstEntryPrice=entry, tsLastLeg=tsFirstLeg. Dong 11-truong moi mang them leg_count,
     * first_entry, ts_last de tai lap cum DCA.
     */
    private void loadState() {
        File f = new File(statePath);
        if (!f.exists()) return;
        try {
            for (String ln : java.nio.file.Files.readAllLines(f.toPath())) {
                // dong "#realized,<so>,,,,,," CUNG co 8 truong nen phai bat TRUOC guard do dai,
                // neu khong no roi vao nhanh parse Cluster -> nem -> mat TOAN BO state (bug 2026-09-06).
                if (ln.startsWith("#realized,")) {
                    realized = Double.parseDouble(ln.split(",", -1)[1]);
                    continue;
                }
                String[] p = ln.split(",", -1);
                if (p.length < 8 || "sym".equals(p[0])) continue;
                Cluster c = new Cluster(p[0], Long.parseLong(p[1]), Float.parseFloat(p[2]),
                        Float.parseFloat(p[3]), Integer.parseInt(p[4]),
                        p[5].isEmpty() ? null : Float.parseFloat(p[5]));
                c.priceSL = p[6].isEmpty() ? null : Float.parseFloat(p[6]);
                c.peakRate = Float.parseFloat(p[7]);
                if (p.length >= 11) {
                    c.legCount = Integer.parseInt(p[8]);
                    c.firstEntryPrice = Float.parseFloat(p[9]);
                    c.tsLastLeg = Long.parseLong(p[10]);
                }
                open.put(c.symbol, c);
            }
        } catch (Exception e) {
            LOG.error("[SHADOW] khong nap duoc state {}: {}", statePath, e.getMessage());
        }
    }

    private synchronized void saveState() {
        try (PrintWriter w = new PrintWriter(new FileWriter(statePath, false))) {
            w.println("sym,ts_first,avg_entry,qty,rank,symbol_pred,price_sl,peak_rate,leg_count,first_entry,ts_last");
            w.printf("#realized,%.10f,,,,,,,,,%n", realized);
            for (Cluster c : open.values()) {
                w.printf("%s,%d,%s,%s,%d,%s,%s,%s,%d,%s,%d%n", c.symbol, c.tsFirstLeg,
                        Float.toString(c.avgEntry()), Float.toString(c.qty), c.rank,
                        c.symbolPred == null ? "" : Float.toString(c.symbolPred),
                        c.priceSL == null ? "" : Float.toString(c.priceSL),
                        Float.toString(c.peakRate),
                        c.legCount, Float.toString(c.firstEntryPrice), c.tsLastLeg);
            }
        } catch (IOException e) {
            LOG.error("[SHADOW] khong ghi duoc state {}: {}", statePath, e.getMessage());
        }
    }

    public static ShadowBookC3 getInstance() {
        if (INSTANCE == null) {
            synchronized (ShadowBookC3.class) {
                if (INSTANCE == null) INSTANCE = new ShadowBookC3();
            }
        }
        return INSTANCE;
    }

    /** CHI cho unit test — dung trong duong chay that. */
    public static void resetForTest() {
        synchronized (ShadowBookC3.class) {
            INSTANCE = null;
        }
    }

    public boolean isHolding(String symbol) {
        return open.containsKey(symbol);
    }

    public int openCount() {
        return open.size();
    }

    /** Tap symbol dang giu (giay) — de lay gia tuoi mot lan cho ca nhip exit. */
    public java.util.Set<String> openSymbols() {
        return new java.util.HashSet<>(open.keySet());
    }

    /** CHI cho unit test (cung package): doc cum de kiem tra VWAP/legCount. */
    Cluster cluster(String symbol) {
        return open.get(symbol);
    }

    public String ledgerPath() {
        return ledgerPath;
    }

    /**
     * Mo/nhoi mot leg giay. Neu CHUA giu coin => tao cum moi. Neu DANG giu => CONG leg vao cum
     * (VWAP + legCount + qty), giong sim {@code mergeOrder}. [BOOKFIX] Truoc day leg2+ bi
     * {@code putIfAbsent} vut im lang => thieu pnl DCA/BIG_DOWN.
     */
    public void openPos(String symbol, long ts, float entry, float qty, int rank, Float symbolPred) {
        if (symbol == null || entry <= 0f || qty <= 0f) return;
        Cluster c = open.get(symbol);
        if (c == null) {
            c = new Cluster(symbol, ts, entry, qty, rank, symbolPred);
            open.put(symbol, c);
            nOpen++;
            saveState();
            LOG.info("[SHADOW] open {} entry={} qty={} rank={} symbolPred={} margin={} open={}",
                    symbol, entry, qty, rank, symbolPred, c.margin(), open.size());
        } else {
            c.addLeg(ts, entry, qty, rank, symbolPred);
            saveState();
            LOG.info("[SHADOW] add-leg {} leg={} entry={} qty={} avgEntry={} totQty={} margin={} open={}",
                    symbol, c.legCount, entry, qty, c.avgEntry(), c.qty, c.margin(), open.size());
        }
    }

    /** Tong margin giay dang chiem — thay {@code BudgetManager.marginRunning} khi profile bat. */
    public float marginRunning() {
        float s = 0f;
        for (Cluster c : open.values()) s += c.margin();
        return s;
    }

    /**
     * (d) Equity GIAY = {@code PAPER_EQUITY} + PnL da chot + PnL mark-to-market cua cum mo
     * (tinh tren VWAP entry va tong qty). Day la thu {@code docs/L1_SHADOW_C3.md} muc 3(e).
     */
    public float equityNow(Map<String, Float> price) {
        double eq = LiveProfileC3.paperEquity() + realized;
        if (price != null) {
            for (Cluster c : open.values()) {
                Float px = price.get(c.symbol);
                if (px != null && px > 0f) eq += (px - c.avgEntry()) * (double) c.qty;
            }
        }
        return (float) eq;
    }

    /**
     * (c) Gap trailing C3: {@code rate = peak - min(peak * TS_GIVEBACK_RATIO, maxGap)} voi
     * {@code maxGap = TS_MAX_GAP_WEAK (0.03)} khi {@code symbolPred > TS_PNOPUMP_WEAK_THR (0.29)},
     * nguoc lai {@code TS_MAX_GAP (0.08)} — CUNG HAM voi sim ({@code OrderTargetInfoTest.trailRate}).
     */
    static float trailRate(float peakRate, Float symbolPred) {
        return trailRate(peakRate, symbolPred, null);
    }

    /**
     * [LIVE_EQ_SIM] TRAIL_HINGE_NET015 (default OFF): khi BAT, ban le trailing STRONG/WEAK cua vi
     * the SHADOW/PAPER dung net015-mapped cua symbol ({@code LATEST_SEL_MAPPRED}, DUNG gia tri
     * gate + sim) thay cho {@code symbolPred} luc mo. Vi the LEGACY THAT di qua
     * {@code BinanceOrderTradingManager.tsGap} -> {@code LATEST_SEL_PNOPUMP} (Funding), KHONG qua
     * day => VAN dung Funding pNoPump. Flag TAT => dung {@code symbolPred} => byte-identical HEAD.
     */
    static float trailRate(float peakRate, Float symbolPred, String symbol) {
        Float pnp = symbolPred;
        if (symbol != null
                && com.binance.chuyennd.tradecore.selector.TrailHingeSource.net015()) {
            Float n = com.binance.chuyennd.trading.DetectEntrySignal2TradeNormal
                    .LATEST_SEL_MAPPRED.get(symbol);
            if (n != null) pnp = n;   // net015-mapped per-coin, dong bo voi gate + sim
        }
        float p = pnp != null ? pnp : 1f;   // chua co selector -> coi nhu YEU
        return TradeUtils.calRateLossDynamicBuyPNoPump(peakRate, p, Configs.tsPnoPumpWeakThr());
    }

    /**
     * Mot nhip exit. {@code price} = gia hien tai theo symbol; {@code now} = moc thoi gian.
     * Tra so cum vua dong. Ratchet/arm/time-stop chay tren VWAP entry cua cum.
     */
    public int tick(Map<String, Float> price, long now) {
        if (price == null || open.isEmpty()) return 0;
        List<Cluster> closing = new ArrayList<>();
        boolean dirty = false;
        for (Cluster c : open.values()) {
            Float pxObj = price.get(c.symbol);
            if (pxObj == null || pxObj <= 0f) continue;
            float px = pxObj;
            float entry = c.avgEntry();
            float rate = (px - entry) / entry;
            if (rate > c.peakRate) c.peakRate = rate;

            if (c.priceSL == null) {
                // (a) ARM: chi arm khi lai vuot nguong C3 0.07
                if (rate > LiveProfileC3.ARM_RATE) {
                    c.priceSL = entry * (1f + trailRate(c.peakRate, c.symbolPred, c.symbol));
                    dirty = true;
                    LOG.info("[SHADOW] arm {} peak={} SL={}", c.symbol, c.peakRate, c.priceSL);
                } else if (now - c.tsFirstLeg > LiveProfileC3.TIME_STOP_HOURS * 3600_000L) {
                    // (b) TIME-STOP 168h cho cum CHUA arm — port tu sim, live khong co
                    LOG.info("[SHADOW] would-CLOSE time-stop {} entry={} px={} gio_giu={}",
                            c.symbol, entry, px, (now - c.tsFirstLeg) / 3600_000L);
                    c.priceSL = null;
                    closing.add(c);
                    closeAt(c, px, REASON_TIME_STOP, now);
                    continue;
                }
            }
            if (c.priceSL != null) {
                // (c) RATCHET LIEN TUC — khong co dead-zone x5.21847 cua live
                float nsl = entry * (1f + trailRate(c.peakRate, c.symbolPred, c.symbol));
                if (nsl > c.priceSL) {
                    c.priceSL = nsl;
                    dirty = true;
                }
                if (px <= c.priceSL) {
                    LOG.info("[SHADOW] would-CLOSE trailing {} entry={} SL={} px={} peak={}",
                            c.symbol, entry, c.priceSL, px, c.peakRate);
                    closing.add(c);
                    closeAt(c, c.priceSL, REASON_TRAILING, now);
                }
            }
        }
        if (dirty && !open.isEmpty()) saveState();
        return closing.size();
    }

    private void closeAt(Cluster c, float exitPx, String reason, long now) {
        open.remove(c.symbol);
        float entry = c.avgEntry();
        double pnl = (exitPx - entry) * (double) c.qty;
        realized += pnl;
        nClose++;
        try (PrintWriter w = new PrintWriter(new FileWriter(ledgerPath, true))) {
            w.printf("%s,%d,%s,%s,%d,%s,%d,%s,%s,%.6f%n",
                    c.symbol, c.tsFirstLeg, Float.toString(entry), Float.toString(c.qty), c.rank,
                    c.symbolPred == null ? "" : Float.toString(c.symbolPred),
                    now, Float.toString(exitPx), reason, pnl);
        } catch (IOException e) {
            LOG.error("[SHADOW] khong ghi duoc ledger {}: {}", ledgerPath, e.getMessage());
        }
        saveState();
        LOG.info("[SHADOW] closed {} reason={} pnl={} legs={} realized={} open={}",
                c.symbol, reason, pnl, c.legCount, realized, open.size());
    }

    /** Dong tom tat cho log dinh ky / health. */
    public String summary(Map<String, Float> price) {
        return String.format("open=%d nOpen=%d nClose=%d realized=%.2f equity=%.2f margin=%.2f",
                open.size(), nOpen, nClose, realized, equityNow(price), marginRunning());
    }
}
