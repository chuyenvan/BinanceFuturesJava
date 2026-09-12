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
 * <p>⚠️ Ke toan GIAY: PnL o day tinh tu gia {@code price_realtime}, khong co phi/slippage/funding
 * va khong lam tron tick-size. Khong duoc so {@code mean(margin)}/equity voi sim
 * ({@code docs/L1_SHADOW_C3.md} muc 7.2).
 */
public final class ShadowBookC3 {

    private static final Logger LOG = LoggerFactory.getLogger(ShadowBookC3.class);
    private static volatile ShadowBookC3 INSTANCE;

    /** Cot ledger: giu ten {@code sym/ts_entry/symbol_pred/entry/ts_exit} de
     * {@code tools/shadow_vs_sim.py pair} doc truc tiep duoc. */
    private static final String HEADER =
            "sym,ts_entry,entry,qty,rank,symbol_pred,ts_exit,exit_price,reason,pnl";

    public static final String REASON_TRAILING = "TRAILING_STOP";
    public static final String REASON_TIME_STOP = "TIME_STOP_168H";

    /** Mot vi the giay. */
    public static final class Pos {
        public final String symbol;
        public final long tsOpen;
        public final float entry;
        public final float qty;
        public final int rank;
        public final Float symbolPred;
        /** null = CHUA arm trailing (dieu kien cua time-stop, giong {@code priceSL == null} o sim). */
        public Float priceSL;
        /** dinh lai (ty le so voi entry) da dat duoc — ratchet bam theo dinh nhu sim. */
        public float peakRate;

        Pos(String symbol, long tsOpen, float entry, float qty, int rank, Float symbolPred) {
            this.symbol = symbol;
            this.tsOpen = tsOpen;
            this.entry = entry;
            this.qty = qty;
            this.rank = rank;
            this.symbolPred = symbolPred;
            this.peakRate = 0f;
        }

        /** Margin dang chiem = notional / don bay (cung cach {@code PositionHelper.callMargin}). */
        float margin() {
            int lev = Configs.LEVERAGE_ORDER > 0 ? Configs.LEVERAGE_ORDER : 1;
            return entry * qty / lev;
        }
    }

    private final Map<String, Pos> open = new ConcurrentHashMap<>();
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
     */
    private void loadState() {
        File f = new File(statePath);
        if (!f.exists()) return;
        try {
            for (String ln : java.nio.file.Files.readAllLines(f.toPath())) {
                // dong "#realized,<so>,,,,,," CUNG co 8 truong nen phai bat TRUOC guard do dai,
                // neu khong no roi vao nhanh parse Pos -> nem -> mat TOAN BO state (bug 2026-09-06).
                if (ln.startsWith("#realized,")) {
                    realized = Double.parseDouble(ln.split(",", -1)[1]);
                    continue;
                }
                String[] p = ln.split(",", -1);
                if (p.length < 8 || "sym".equals(p[0])) continue;
                Pos q = new Pos(p[0], Long.parseLong(p[1]), Float.parseFloat(p[2]), Float.parseFloat(p[3]),
                        Integer.parseInt(p[4]), p[5].isEmpty() ? null : Float.parseFloat(p[5]));
                q.priceSL = p[6].isEmpty() ? null : Float.parseFloat(p[6]);
                q.peakRate = Float.parseFloat(p[7]);
                open.put(q.symbol, q);
            }
        } catch (Exception e) {
            LOG.error("[SHADOW] khong nap duoc state {}: {}", statePath, e.getMessage());
        }
    }

    private synchronized void saveState() {
        try (PrintWriter w = new PrintWriter(new FileWriter(statePath, false))) {
            w.println("sym,ts_open,entry,qty,rank,symbol_pred,price_sl,peak_rate");
            w.printf("#realized,%.10f,,,,,,%n", realized);
            for (Pos p : open.values()) {
                w.printf("%s,%d,%s,%s,%d,%s,%s,%s%n", p.symbol, p.tsOpen, Float.toString(p.entry),
                        Float.toString(p.qty), p.rank,
                        p.symbolPred == null ? "" : Float.toString(p.symbolPred),
                        p.priceSL == null ? "" : Float.toString(p.priceSL),
                        Float.toString(p.peakRate));
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

    public String ledgerPath() {
        return ledgerPath;
    }

    /** Mo mot vi the giay. Bo qua neu dang giu coin do (giong guard {@code symbol2Pos}). */
    public void openPos(String symbol, long ts, float entry, float qty, int rank, Float symbolPred) {
        if (symbol == null || entry <= 0f || qty <= 0f) return;
        Pos p = new Pos(symbol, ts, entry, qty, rank, symbolPred);
        if (open.putIfAbsent(symbol, p) == null) {
            nOpen++;
            saveState();
            LOG.info("[SHADOW] open {} entry={} qty={} rank={} symbolPred={} margin={} open={}",
                    symbol, entry, qty, rank, symbolPred, p.margin(), open.size());
        }
    }

    /** Tong margin giay dang chiem — thay {@code BudgetManager.marginRunning} khi profile bat. */
    public float marginRunning() {
        float s = 0f;
        for (Pos p : open.values()) s += p.margin();
        return s;
    }

    /**
     * (d) Equity GIAY = {@code PAPER_EQUITY} + PnL da chot + PnL mark-to-market cua vi the mo.
     * Day la thu {@code docs/L1_SHADOW_C3.md} muc 3(e) noi la con thieu.
     */
    public float equityNow(Map<String, Float> price) {
        double eq = LiveProfileC3.paperEquity() + realized;
        if (price != null) {
            for (Pos p : open.values()) {
                Float px = price.get(p.symbol);
                if (px != null && px > 0f) eq += (px - p.entry) * (double) p.qty;
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
     * Tra so lenh vua dong.
     */
    public int tick(Map<String, Float> price, long now) {
        if (price == null || open.isEmpty()) return 0;
        List<Pos> closing = new ArrayList<>();
        boolean dirty = false;
        for (Pos p : open.values()) {
            Float pxObj = price.get(p.symbol);
            if (pxObj == null || pxObj <= 0f) continue;
            float px = pxObj;
            float rate = (px - p.entry) / p.entry;
            if (rate > p.peakRate) p.peakRate = rate;

            if (p.priceSL == null) {
                // (a) ARM: chi arm khi lai vuot nguong C3 0.07
                if (rate > LiveProfileC3.ARM_RATE) {
                    p.priceSL = p.entry * (1f + trailRate(p.peakRate, p.symbolPred, p.symbol));
                    dirty = true;
                    LOG.info("[SHADOW] arm {} peak={} SL={}", p.symbol, p.peakRate, p.priceSL);
                } else if (now - p.tsOpen > LiveProfileC3.TIME_STOP_HOURS * 3600_000L) {
                    // (b) TIME-STOP 168h cho cum CHUA arm — port tu sim, live khong co
                    LOG.info("[SHADOW] would-CLOSE time-stop {} entry={} px={} gio_giu={}",
                            p.symbol, p.entry, px, (now - p.tsOpen) / 3600_000L);
                    p.priceSL = null;
                    closing.add(p);
                    closeAt(p, px, REASON_TIME_STOP, now);
                    continue;
                }
            }
            if (p.priceSL != null) {
                // (c) RATCHET LIEN TUC — khong co dead-zone x5.21847 cua live
                float nsl = p.entry * (1f + trailRate(p.peakRate, p.symbolPred, p.symbol));
                if (nsl > p.priceSL) {
                    p.priceSL = nsl;
                    dirty = true;
                }
                if (px <= p.priceSL) {
                    LOG.info("[SHADOW] would-CLOSE trailing {} entry={} SL={} px={} peak={}",
                            p.symbol, p.entry, p.priceSL, px, p.peakRate);
                    closing.add(p);
                    closeAt(p, p.priceSL, REASON_TRAILING, now);
                }
            }
        }
        if (dirty && !open.isEmpty()) saveState();
        return closing.size();
    }

    private void closeAt(Pos p, float exitPx, String reason, long now) {
        open.remove(p.symbol);
        double pnl = (exitPx - p.entry) * (double) p.qty;
        realized += pnl;
        nClose++;
        try (PrintWriter w = new PrintWriter(new FileWriter(ledgerPath, true))) {
            w.printf("%s,%d,%s,%s,%d,%s,%d,%s,%s,%.6f%n",
                    p.symbol, p.tsOpen, Float.toString(p.entry), Float.toString(p.qty), p.rank,
                    p.symbolPred == null ? "" : Float.toString(p.symbolPred),
                    now, Float.toString(exitPx), reason, pnl);
        } catch (IOException e) {
            LOG.error("[SHADOW] khong ghi duoc ledger {}: {}", ledgerPath, e.getMessage());
        }
        saveState();
        LOG.info("[SHADOW] closed {} reason={} pnl={} realized={} open={}",
                p.symbol, reason, pnl, realized, open.size());
    }

    /** Dong tom tat cho log dinh ky / health. */
    public String summary(Map<String, Float> price) {
        return String.format("open=%d nOpen=%d nClose=%d realized=%.2f equity=%.2f margin=%.2f",
                open.size(), nOpen, nClose, realized, equityNow(price), marginRunning());
    }
}
