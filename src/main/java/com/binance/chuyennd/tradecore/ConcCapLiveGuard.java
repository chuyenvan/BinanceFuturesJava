package com.binance.chuyennd.tradecore;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * [CONC-CAP LIVE 2026-09-15] TRANG THAI + QUYET DINH cua 2 guard safety-net tren duong LIVE.
 * Xem docs/PREREG_CONCENTRATION_SAFETYCAP.md (spec goc) va
 * docs/RESULT_CONCENTRATION_SAFETYCAP_LIVE_PORT.md (ban port live).
 *
 * <p><b>Vi sao tach ra khoi {@code DetectEntrySignal2TradeNormal}</b>: lop do phu thuoc Redis +
 * Binance client nen KHONG unit-test duoc. Toan bo trang thai va phep quyet dinh cua guard la ham
 * THUAN, khong I/O, nen dat o day de co test that ({@code ConcCapLiveGuardTest}) — cung khuon voi
 * {@code ShadowBookC3}. {@code DetectEntrySignal2TradeNormal} chi con goi 4 ham cua lop nay.
 *
 * <p><b>Khac ban SIM o cho nao</b> (duong sim: {@code SimulatorMarketLevelTicker1MStopLoss}):
 * <ol>
 *   <li>SIM doc thang {@code symbol2OrdersEntry[sym]} (danh sach TUNG leg) — LIVE khong co cau
 *       truc do (vi the da GOP o san giao dich), nen phai TU TRACK margin tung leg DCA o day.</li>
 *   <li>SIM reset rolling window trong {@code initData()/initDataReady()} — LIVE chay 24/7, khong
 *       co "dau run", nen cua so 60 phut TU TROI theo {@code System.currentTimeMillis()}.</li>
 *   <li>LIVE chay da luong ({@code executorService}) nen moi thu o day {@code synchronized}.</li>
 * </ol>
 *
 * <p><b>Caveat da duoc MASTER chap nhan</b>: process restart => trang thai rong => guard tam thoi
 * LONG hon thuc te cho toi khi co leg moi ghi nhan lai. Huong sai la "bo sot", khong phai "chan
 * nham" — dung huong an toan cho mot safety-net.
 */
public final class ConcCapLiveGuard {

    private static final long HOUR_MS = 60L * 60L * 1000L;

    private static final ConcCapLiveGuard INSTANCE = new ConcCapLiveGuard();

    public static ConcCapLiveGuard getInstance() {
        return INSTANCE;
    }

    /** symbol -> margin cua TUNG leg DCA-grid bac>=1 dang mo cua symbol do. */
    private final Map<String, List<Float>> symbol2DcaLegMargin = new HashMap<>();

    /** Timestamp (ms, DONG HO THAT) cua cac leg BIG_DOWN da thuc su duoc gui di. */
    private final ArrayDeque<Long> bdOpenTimes = new ArrayDeque<>();

    /** package-private: test tu tao instance rieng, khong dung chung singleton. */
    ConcCapLiveGuard() {
    }

    // =====================================================================
    // GUARD 1 — tran AGGREGATE margin dang nam trong cac leg DCA-grid bac>=1
    // =====================================================================

    /** Tong margin dang nam trong MOI leg DCA-grid bac>=1, cong dong TOAN BO symbol. */
    public synchronized float aggDcaLegMargin() {
        return aggUnsafe();
    }

    private float aggUnsafe() {
        float sum = 0f;
        for (List<Float> legs : symbol2DcaLegMargin.values()) {
            if (legs == null) continue;
            for (Float m : legs) {
                if (m != null) sum += m;
            }
        }
        return sum;
    }

    /**
     * Co "symbol dang o bac DCA>=1" — suy TRUC TIEP tu chinh structure nay, KHONG dung
     * {@code BudgetManager.symbol2Level} (co do bi ghi de boi level cua lenh moi nhat va bi XOA
     * sau 30 phut o {@code BinanceOrderTradingManager:326-330} — xem doc BLOCKER muc 3.2).
     */
    public synchronized boolean isInDcaTier(String symbol) {
        List<Float> legs = symbol2DcaLegMargin.get(symbol);
        return legs != null && !legs.isEmpty();
    }

    /** So leg DCA-grid bac>=1 dang duoc theo doi (toan so) — de log/telemetry. */
    public synchronized int trackedDcaLegCount() {
        int n = 0;
        for (List<Float> legs : symbol2DcaLegMargin.values()) {
            if (legs != null) n += legs.size();
        }
        return n;
    }

    /**
     * QUYET DINH guard 1: {@code true} = CHAN leg DCA sap mo.
     * {@code (aggDcaLegMargin + legNewMargin) / equity > CONC_CAP_AGG_DCA_PCT}.
     *
     * <p>FAIL-OPEN co chu dich khi {@code equity <= 0} (chua doc duoc walletBalance): guard nay la
     * BAO HIEM khong binding tren lich su; bien mot su co doc API thanh "chan sach moi leg DCA" se
     * la doi chien luoc, khong phai bao ve. Call-site co trach nhiem log WARN.
     */
    public synchronized boolean blockDcaLeg(float legNewMargin, float equity) {
        if (!Configs.CONC_CAP_AGG_DCA_ENABLED) return false;
        if (equity <= 0f) return false;
        float ratio = (aggUnsafe() + legNewMargin) / equity;
        return ratio > Configs.CONC_CAP_AGG_DCA_PCT;
    }

    /** Ti le hien tai neu mo them mot leg margin {@code legNewMargin} — chi de LOG. */
    public synchronized float ratioIfAdd(float legNewMargin, float equity) {
        if (equity <= 0f) return 0f;
        return (aggUnsafe() + legNewMargin) / equity;
    }

    /** Ghi nhan mot leg DCA-grid bac>=1 DA THUC SU duoc gui di. */
    public synchronized void recordDcaLeg(String symbol, float margin) {
        if (symbol == null) return;
        List<Float> legs = symbol2DcaLegMargin.get(symbol);
        if (legs == null) {
            legs = new ArrayList<>();
            symbol2DcaLegMargin.put(symbol, legs);
        }
        legs.add(margin);
    }

    /**
     * Dong bo voi tap symbol dang THUC SU con vi the (truyen
     * {@code BudgetManager.symbol2Pos.keySet()}). Cum dong xong => bo het leg DCA cua no.
     *
     * <p>BAT BUOC goi truoc moi lan doc aggregate: khong co buoc nay thi structure chi phinh ra,
     * guard se binding NHAM va chan lenh that.
     */
    public synchronized void retainSymbols(Set<String> openSymbols) {
        if (openSymbols == null || symbol2DcaLegMargin.isEmpty()) return;
        symbol2DcaLegMargin.keySet().retainAll(openSymbols);
    }

    // =====================================================================
    // GUARD 2 — tran so leg BIG_DOWN mo trong 60 phut
    // =====================================================================

    /** So leg BIG_DOWN DA MO trong 60 phut gan nhat. Tu don rac cac moc da het han. */
    public synchronized int bdCountLastHour(long now) {
        return bdCountUnsafe(now);
    }

    private int bdCountUnsafe(long now) {
        long from = now - HOUR_MS;
        while (!bdOpenTimes.isEmpty() && bdOpenTimes.peekFirst() <= from) {
            bdOpenTimes.pollFirst();
        }
        return bdOpenTimes.size();
    }

    /** QUYET DINH guard 2: {@code true} = CHAN leg BIG_DOWN sap mo. */
    public synchronized boolean blockBigDownLeg(long now) {
        if (!Configs.CONC_CAP_BD_RATE_ENABLED) return false;
        return bdCountUnsafe(now) >= Configs.CONC_CAP_BD_PER_HOUR;
    }

    /** Ghi nhan mot leg BIG_DOWN DA THUC SU duoc gui di. */
    public synchronized void recordBigDownLeg(long now) {
        bdOpenTimes.addLast(now);
    }

    // =====================================================================

    /** Chi dung trong test. */
    synchronized void resetForTest() {
        symbol2DcaLegMargin.clear();
        bdOpenTimes.clear();
    }
}
