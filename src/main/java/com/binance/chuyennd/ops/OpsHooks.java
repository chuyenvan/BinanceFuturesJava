package com.binance.chuyennd.ops;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.selector.ShadowBookC3;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

/**
 * [V11D OPS 2026-10-21] Diem noi DUY NHAT tu code giao dich sang heartbeat + kill-switch. Moi ham:
 * (1) co tat => return ngay (khong I/O, khong tinh toan); (2) KHONG BAO GIO nem (bat Throwable); (3) chi DOC doi so,
 * khong sua map/so giay. Call site:
 * <ul>
 *   <li>{@link #start()} — {@code BinanceOrderTradingManager.start()}: 1 dong log cau hinh + thread kill-switch (khi bat).</li>
 *   <li>{@link #onTickStart()} — dau {@code DetectEntrySignal2TradeNormal.checkMarketLevelChange2Trade}.</li>
 *   <li>{@link #onMarketData(Map)} — ngay sau khi ghi {@code LAST_TIME_CHECK_MARKET} trong cung ham.</li>
 *   <li>{@link #onApiResult(String, boolean)} — sau {@code getAllPositionInfos} trong {@code updatePositionInfo}.</li>
 *   <li>{@link #onPaperBook(ShadowBookC3)} / {@link #onPaperTick(ShadowBookC3, Map)} — {@code shadowTickC3}.</li>
 * </ul>
 *
 * <p>[V12 SAFE 2026-10-25] API cho vong 2 (c3_live) — CHUA co call site nao trong v1.2/safe:
 * <ul>
 *   <li>{@link #allowNewEntry(String)} — goi o {@code createOrderBuyRequest} TRUOC push VA o cua gui lenh (entry + DCA).</li>
 *   <li>{@link #requiredAction()} — vong quan ly vi the: FLATTEN => dong het reduce-only chia lo.</li>
 *   <li>{@link #onFill(String, boolean, Double, Double)} — moi fill that (C2), ref = close nen 1m quyet dinh.</li>
 *   <li>{@link #attachEquitySource(EquitySource)} — totalMarginBalance tai khoan con (A40).</li>
 *   <li>{@link #setAlert(Consumer)} — Telegram.</li>
 *   <li>{@link #onBook(int, float, float)} — so lenh that (C4/C6); {@link #onApiResult} — moi call REST tai khoan con (C3).</li>
 * </ul>
 * Mode khac ACT (c3_shadow, sim): allowNewEntry = true, requiredAction = NONE (khong doi quyet dinh).
 */
public final class OpsHooks {

    private static final Logger LOG = LoggerFactory.getLogger(OpsHooks.class);
    private static final long ERR_LOG_EVERY_MS = 600_000L;
    private static final long KS_PERIOD_MS = 15_000L;

    private static final String RAW_MODE = Cfg.get(OpsConfig.KEY_KILLSW_MODE);
    private static final String PROFILE = Cfg.get("LIVE_PROFILE");
    /** [V12 Q1b] c3_live: so GIAY KHONG duoc lam nguon C4/C6 (chi onBook tu so THAT). */
    private static final boolean C3LIVE = OpsConfig.isC3Live(PROFILE);
    private static final KillSwitchEngine.Resolved KS_MODE = KillSwitchEngine.resolve(RAW_MODE, PROFILE);
    private static final boolean HB = OpsHeartbeat.on();
    private static final KillSwitchEngine KS = KS_MODE.effective == KillSwitchEngine.Mode.OFF ? null : newEngine();
    private static volatile boolean started = false;
    private static volatile long lastErrMs = Long.MIN_VALUE / 2;

    private OpsHooks() {
    }

    private static KillSwitchEngine newEngine() {
        String label = KS_MODE.effective.name().toLowerCase(java.util.Locale.ROOT)
                + (KS_MODE.requested == KillSwitchEngine.Mode.ACT && KS_MODE.effective != KillSwitchEngine.Mode.ACT
                ? "(act_tu_choi)" : "");
        KillSwitchEngine.Sink sink = new KillSwitchEngine.Sink() {
            public void info(String m) {
                LOG.info("{}", m);
            }

            public void warn(String m) {
                LOG.warn("{}", m);
            }
        };
        File peak = new File(Cfg.getOr(OpsConfig.KEY_KILLSW_STATE_FILE, OpsConfig.DEFAULT_KILLSW_STATE_FILE));
        KillSwitchEngine.Params prm = OpsConfig.killSwitchParams(KS_MODE.effective == KillSwitchEngine.Mode.ACT);
        return build(KS_MODE.effective, label, sink, C3LIVE, peak, C3LIVE ? OpsConfig.c3LivePeakFile() : null,
                com.binance.chuyennd.tradecore.selector.LiveProfileC3::paperEquity,
                () -> com.binance.chuyennd.tradecore.Configs.U_MAX,
                System.currentTimeMillis(), prm);
    }

    /**
     * [V12 2c CRIT-1] Dung engine theo profile (tach ra de test duong that). c3_live: C6 tren tmb that so voi dinh RIENG
     * ({@code c3livePeakFile}), KHONG san PAPER_EQUITY, KHONG dung {@code shadowPeakFile}. Profile khac: y nhu v1.1
     * (dinh so giay {@code shadowPeakFile}, san PAPER_EQUITY).
     */
    static KillSwitchEngine build(KillSwitchEngine.Mode mode, String label, KillSwitchEngine.Sink sink, boolean c3live,
                                  File shadowPeakFile, File c3livePeakFile,
                                  java.util.function.DoubleSupplier paperEquity,
                                  java.util.function.Supplier<Float> uMax, long nowMs, KillSwitchEngine.Params prm) {
        if (c3live) {
            KillSwitchEngine.Params p = prm == null ? new KillSwitchEngine.Params() : prm;
            p.c6OwnPeak = true;
            // [2d MIN-19] dinh dry != dinh live; [V12 R4 R4] C6/A40 do tren EQUITY C3 => dinh rieng (dinh tmb cu bi bo qua)
            if (p.peakTag == null) {
                // [W3B muc 7 A-02] gan dinh C6/A40 voi C3_CAPITAL (token cap= rieng, nhan adapter= GIU nhu jar cu)
                applyC3PeakTag(p, Cfg.get("LIVE_ADAPTER"), Cfg.get("C3_CAPITAL"), Cfg.get("LIVE_C3_PILOT_CAPITAL"),
                        Cfg.get(KEY_PEAK_TAG_CAP), new File(Cfg.getOr(
                                com.binance.chuyennd.c3live.runtime.C3LiveRuntime.KEY_EQUITY_FILE,
                                com.binance.chuyennd.c3live.runtime.C3LiveRuntime.DEFAULT_EQUITY_FILE)));
            }
            return new KillSwitchEngine(mode, label, sink, c3livePeakFile, null, uMax, nowMs, p);
        }
        return new KillSwitchEngine(mode, label, sink, shadowPeakFile, paperEquity, uMax, nowMs, prm);
    }

    /** [W3A muc 7] env tat XET von khi doc dinh ("0"|"false" => hanh vi doc jar cu; [W3B v2] van GHI cap=). */
    static final String KEY_PEAK_TAG_CAP = "C3_PEAK_TAG_CAPITAL";

    /**
     * [W3B muc 7 A-02] Dat nhan + von cho dinh kill-switch c3_live. Nhan = "&lt;adapter&gt;_c3eq" (y nhu jar cu => rollback jar
     * van nap dinh); von hien tai -&gt; {@link KillSwitchEngine.Params#peakCap}; von JVM truoc (file trang thai equity c3
     * cung adapter) -&gt; {@link KillSwitchEngine.Params#peakCapPrev} (chi dung khi file dinh thieu von).
     *
     * @param p          tham so engine (ghi de peakTag/peakCap/peakCapPrev)
     * @param adapterRaw env LIVE_ADAPTER
     * @param capRaw     env C3_CAPITAL
     * @param pilotRaw   env LIVE_C3_PILOT_CAPITAL
     * @param flag       env C3_PEAK_TAG_CAPITAL ("false" => khong gan von)
     * @param eqState    file trang thai equity c3 (LIVE_C3_EQUITY_FILE)
     */
    static void applyC3PeakTag(KillSwitchEngine.Params p, String adapterRaw, String capRaw, String pilotRaw, String flag,
                               File eqState) {
        String ad = adapterTag(adapterRaw);
        p.peakTag = ad + C3EQ_TAG_SUFFIX;
        p.peakCap = capValue(capRaw, pilotRaw, flag);
        p.peakCapWrite = capValue(capRaw, pilotRaw, null);   // [W3B v2] ghi von ca khi co tat
        p.peakCapPrev = p.peakCap == null ? null : prevCapital(eqState, ad);
        LOG.info("[KILLSW] dinh c3_live nhan={} von={} von_JVM_truoc={} ({})", p.peakTag, p.peakCap == null ? "(khong gan, "
                + KEY_PEAK_TAG_CAP + "=false)" : p.peakCap, p.peakCapPrev == null ? "-" : p.peakCapPrev,
                eqState == null ? "-" : eqState.getPath());
    }

    /**
     * [W3B muc 7 A-02] Von c3 hien tai dang chuan (vd "1000", "1000.5"): C3_CAPITAL, thieu/sai =&gt; LIVE_C3_PILOT_CAPITAL,
     * thieu/sai =&gt; 10 000 (cung thu tu C3LiveRuntime).
     *
     * @param capRaw   env C3_CAPITAL
     * @param pilotRaw env LIVE_C3_PILOT_CAPITAL
     * @param flag     env C3_PEAK_TAG_CAPITAL ("false" =&gt; null = khong gan)
     * @return von hoac null
     */
    static String capValue(String capRaw, String pilotRaw, String flag) {
        if (flag != null && ("false".equalsIgnoreCase(flag.trim()) || "0".equals(flag.trim()))) return null;   // [W3B v2] 0|false
        double pilot = posOr(pilotRaw, com.binance.chuyennd.c3live.risk.C3LiveEquity.DEFAULT_PILOT_CAPITAL);
        double cap = posOr(capRaw, pilot);
        return java.math.BigDecimal.valueOf(cap).stripTrailingZeros().toPlainString();
    }

    /**
     * [W3B muc 7] Von c3 cua JVM truoc: truong "capital" file trang thai equity c3 (C3MainEquity, jar cu va moi deu ghi)
     * neu "adapter" cua file = adapter hien tai. Doc truoc khi runtime tao C3MainEquity (KS dung o class-init OpsHooks).
     *
     * @param f       file trang thai equity c3
     * @param adapter nhan adapter (vd "live")
     * @return von &gt; 0 hoac null (khong co / hong / adapter khac)
     */
    static Double prevCapital(File f, String adapter) {
        if (f == null || !f.isFile() || adapter == null) return null;
        try {
            com.google.gson.JsonObject o = com.google.gson.JsonParser.parseString(new String(java.nio.file.Files.readAllBytes(
                    f.toPath()), java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
            String t = o.has("adapter") && !o.get("adapter").isJsonNull() ? o.get("adapter").getAsString() : null;
            if (!adapter.equals(t) || !o.has("capital")) return null;
            double c = o.get("capital").getAsDouble();
            return Double.isFinite(c) && c > 0d ? c : null;
        } catch (Exception e) {
            LOG.warn("[KILLSW] khong doc duoc von JVM truoc tu {}: {} => khong co moc von", f.getPath(), e.toString());
            return null;
        }
    }

    private static double posOr(String raw, double def) {
        try {
            if (raw == null || raw.trim().isEmpty()) return def;
            double v = Double.parseDouble(raw.trim());
            return Double.isFinite(v) && v > 0d ? v : def;
        } catch (NumberFormatException e) {
            return def;
        }
    }

    /** [V12 R4 R4] hau to nhan dinh kill-switch c3_live: dinh do tren equity c3 (khong phai tmb tai khoan chinh). */
    static final String C3EQ_TAG_SUFFIX = "_c3eq";

    /** [2d MIN-19] nhan adapter cho dinh kill-switch c3_live: dry|live|... (thuong, khong khoang trang); rong => off. */
    static String adapterTag(String raw) {
        if (raw == null || raw.trim().isEmpty()) return "off";
        return raw.trim().toLowerCase(java.util.Locale.ROOT).replaceAll("[^a-z0-9_]", "_");
    }

    /** Goi 1 lan khi khoi dong (idempotent). */
    public static synchronized void start() {
        if (started) return;
        started = true;
        try {
            LOG.info("[OPS] v11d {}={}h (0=tat reset dinh ky; Reporter >15' giu nguyen) {}={} file={} {}={} => hieu luc={} profile={}",
                    OpsConfig.KEY_RESET_HOURS, OpsConfig.periodicResetHours(),
                    OpsConfig.KEY_HEARTBEAT, HB ? 1 : 0, OpsHeartbeat.file().getPath(),
                    OpsConfig.KEY_KILLSW_MODE, RAW_MODE == null ? "-" : RAW_MODE.trim(),
                    KS_MODE.effective.name().toLowerCase(java.util.Locale.ROOT), PROFILE == null ? "-" : PROFILE.trim());
            if (KS_MODE.warn != null) LOG.warn("{}", KS_MODE.warn);
            if (OpsConfig.isC3Live(PROFILE) && KS_MODE.effective != KillSwitchEngine.Mode.ACT) {
                LOG.warn("[KILLSW] LIVE_PROFILE=c3_live nhung kill-switch KHONG o mode act (hieu luc={}) => KHONG co bao ve tu"
                        + " dong; vong 2 phai tu choi push khi killSwitchArmed()=false", KS_MODE.effective);
            }
            if (KS == null) return;
            if (KS.mode() == KillSwitchEngine.Mode.ACT) {
                LOG.warn("[KILLSW] BAT mode=act (c3_live): C1/C2/C3/C5 => latch NO_NEW_ENTRY (C1/C3/C5 tu go); C4 = cong suat "
                                + "(chan mo cum moi, DCA van chay, tu go); C6/A40 => latch FLATTEN; latch file={} "
                                + "reset file={} (chi ops/killsw_reset.sh); C2 signed={}",
                        OpsConfig.latchFile().getPath(), OpsConfig.resetFile().getPath(), OpsConfig.c2SignedRaw());
            } else {
                LOG.info("[KILLSW] BAT mode={} CHI LOG (khong doi quyet dinh). Nguong: C1 lag>{}s|miss>{}%|no_data>{}s; "
                                + "C2 slip>{} (so giay: N/A, khong co fill that); C3 >={} loi API lien tiep (dong bo vi the REST); "
                                + "C4 open>{} hoac U>=U_MAX; C5 khong tick>{}s; C6 DD<={} (so giay MTM). LEGACY khong tinh C4/C6.",
                        KS.mode().name().toLowerCase(java.util.Locale.ROOT), KillSwitchEngine.C1_LAG_SEC, KillSwitchEngine.C1_MISSING_PCT,
                        KillSwitchEngine.C1_NODATA_SEC, KillSwitchEngine.C2_SLIP, KillSwitchEngine.C3_CONSEC,
                        KillSwitchEngine.C4_MAX_POS, KillSwitchEngine.C5_NOTICK_SEC, KillSwitchEngine.C6_DD);
            }
            Thread t = new Thread(() -> {
                while (true) {
                    try {
                        Thread.sleep(KS_PERIOD_MS);
                        KS.periodic(System.currentTimeMillis());
                    } catch (InterruptedException ie) {
                        return;
                    } catch (Throwable e) {
                        err("periodic", e);
                    }
                }
            }, "OpsKillSwitch");
            t.setDaemon(true);
            t.start();
        } catch (Throwable e) {
            err("start", e);
        }
    }

    public static void onTickStart() {
        if (!HB && KS == null) return;
        try {
            long now = System.currentTimeMillis();
            if (HB) OpsHeartbeat.beat(now);
            if (KS != null) KS.onTickStart(now);
        } catch (Throwable e) {
            err("onTickStart", e);
        }
    }

    public static void onMarketData(Map<String, List<KlineObjectSimple>> window) {
        if (KS == null) return;
        try {
            KS.onMarketData(System.currentTimeMillis(), window);
        } catch (Throwable e) {
            err("onMarketData", e);
        }
    }

    public static void onApiResult(String api, boolean ok) {
        if (KS == null) return;
        try {
            KS.onApiResult(System.currentTimeMillis(), api, ok);
        } catch (Throwable e) {
            err("onApiResult", e);
        }
    }

    /** [V12 R4p Bug3] ket qua DAT LENH => bo dem 429 rieng cua C3. */
    public static void onOrderResult(String api, boolean ok, boolean rateLimited) {
        if (KS == null) return;
        try {
            KS.onOrderResult(System.currentTimeMillis(), api, ok, rateLimited);
        } catch (Throwable e) {
            err("onOrderResult", e);
        }
    }

    /** Dau shadowTickC3: so trong (0 cum) => C4/C6 tren equity = PAPER_EQUITY + realized (khong can gia). */
    public static void onPaperBook(ShadowBookC3 book) {
        if (KS == null || book == null || C3LIVE) return;
        try {
            if (book.openCount() != 0) return;   // co cum mo => onPaperTick (co gia) se xu ly
            KS.onPaper(System.currentTimeMillis(), 0, book.marginRunning(),
                    book.equityNow(Collections.<String, Float>emptyMap()));
        } catch (Throwable e) {
            err("onPaperBook", e);
        }
    }

    /** Sau {@code book.tick(px, now)} trong shadowTickC3 — CUNG map gia vua dung cho nhip exit (chi doc). */
    public static void onPaperTick(ShadowBookC3 book, Map<String, Float> px) {
        if (KS == null || book == null || C3LIVE) return;
        try {
            KS.onPaper(System.currentTimeMillis(), book.openCount(), book.marginRunning(), book.equityNow(px));
        } catch (Throwable e) {
            err("onPaperTick", e);
        }
    }

    // ------------------------------------------------------------------ [V12] API vong 2 (c3_live)

    /**
     * [V12] So LIVE (vong 2: so lenh that c3_live) — C4 (so vi the, U = margin/equity) + C6. [2c CRIT-1] c3_live: C6 =
     * DD cua totalMarginBalance that so voi dinh RIENG ({@code LIVE_C3_KILLSW_PEAK_FILE}, mac dinh
     * run/c3live_killsw_peak; KHONG san PAPER_EQUITY, KHONG dung run/killsw_peak cua c3_shadow). Goi sau moi nhip danh
     * gia vi the. KHONG goi dong thoi voi onPaperTick tren CUNG profile (c3_live: onPaper* bi bo qua).
     */
    public static void onBook(int openPos, float margin, float equity) {
        if (KS == null) return;
        try {
            KS.onPaper(System.currentTimeMillis(), openPos, margin, equity);
        } catch (Throwable e) {
            err("onBook", e);
        }
    }

    /** [V12] true iff kill-switch dang o mode ACT (c3_live). Vong 2 nen tu choi push that khi false. */
    public static boolean killSwitchArmed() {
        return KS != null && KS.mode() == KillSwitchEngine.Mode.ACT;
    }

    /**
     * [V12] Cong mo lenh MOI. KS tat / mode LOG => true (khong doi quyet dinh). Mode ACT: theo latch; loi noi bo =>
     * FAIL-CLOSED false.
     */
    public static boolean allowNewEntry(String symbol) {
        if (KS == null) return true;
        try {
            return KS.allowNewEntry(symbol);
        } catch (Throwable e) {
            err("allowNewEntry", e);
            return KS.mode() != KillSwitchEngine.Mode.ACT;
        }
    }

    /** [V12 2b] Cong DCA cua cum dang co (C4 cong suat KHONG chan DCA). KS tat / LOG => true; loi noi bo o ACT => false. */
    public static boolean allowDca(String symbol) {
        if (KS == null) return true;
        try {
            return KS.allowDca(symbol);
        } catch (Throwable e) {
            err("allowDca", e);
            return KS.mode() != KillSwitchEngine.Mode.ACT;
        }
    }

    /** [V12] NONE / NO_NEW_ENTRY / FLATTEN (chi khac NONE o mode ACT). Loi noi bo o ACT => NO_NEW_ENTRY. */
    public static KillSwitchEngine.Action requiredAction() {
        if (KS == null) return KillSwitchEngine.Action.NONE;
        try {
            return KS.requiredAction();
        } catch (Throwable e) {
            err("requiredAction", e);
            return KS.mode() == KillSwitchEngine.Mode.ACT ? KillSwitchEngine.Action.NO_NEW_ENTRY : KillSwitchEngine.Action.NONE;
        }
    }

    /** [V12] fill that (C2). ref = close nen 1m quyet dinh; isBuy = chieu lenh. */
    public static void onFill(String symbol, boolean isBuy, Double fillPx, Double refPx) {
        if (KS == null) return;
        try {
            KS.onFill(System.currentTimeMillis(), symbol, isBuy, fillPx, refPx);
        } catch (Throwable e) {
            err("onFill", e);
        }
    }

    /** [V12] gan nguon totalMarginBalance tai khoan con (A40). */
    public static void attachEquitySource(EquitySource src) {
        if (KS == null) return;
        try {
            KS.attachEquitySource(src);
        } catch (Throwable e) {
            err("attachEquitySource", e);
        }
    }

    /** [V12] noi Telegram cho latch/reset/C2_WARN. */
    public static void setAlert(Consumer<String> alert) {
        if (KS == null) return;
        try {
            KS.setAlert(alert);
        } catch (Throwable e) {
            err("setAlert", e);
        }
    }

    private static void err(String where, Throwable e) {
        long now = System.currentTimeMillis();
        if (now - lastErrMs < ERR_LOG_EVERY_MS) return;
        lastErrMs = now;
        LOG.warn("[OPS] loi hook {} (bo qua, khong anh huong giao dich): {}", where, e.toString());
    }
}
