package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.util.Arrays;

/**
 * [TICKBLK 2026-09-23] docs/PREREG_TICK_BLOCK.md — chan ca LUOT (tick) khi luot YEU.
 *
 * <p><b>Vi sao</b>: moi filter CAP-COIN deu vo hieu ve exposure (D3 loc 4.942 candidate nhung net chi
 * mat 109 lenh — docs/RESULT_D3D4_FILTER_SIM.md §2): bo qua 1 candidate thi he lay candidate xep hang
 * ke tiep trong CUNG tick. Muon giam exposure that su thi phai chan ca LUOT.
 *
 * <p><b>Gia thuyet (chot TRUOC, docs/PREREG_TICK_BLOCK.md §1.0)</b>: edge cua lenh long la hieu ung
 * THOI DIEM tap trung o phut xa/bán thao dien rong (RESULT_HARNESS_CONTROL §3 B-SECONDARY: symbol
 * NGAU NHIEN tai phut MOM15 fire an +2,00%). ⇒ "nhom te nhat" = nhom NGUOI (it ap luc ban nhat).
 *
 * <p><b>3 che do</b> (mot muc cat 25%, KHONG quet):
 * <ul>
 *   <li>{@code DEPTH}   — x = {@code rateDownAvg}     (it AM nhat  = nguoi) → chan khi x &gt;= Q0.75</li>
 *   <li>{@code BREADTH} — x = % coin co return 1M &lt;= -3% (THAP nhat = nguoi) → chan khi x &lt;= Q0.25</li>
 *   <li>{@code DROP15M} — x = {@code rateDown15MAvg}   (it AM nhat = nguoi) → chan khi x &gt;= Q0.75</li>
 * </ul>
 *
 * <p><b>Causal</b>: nguong la quantile tren cua so cuon {@code WIN_DAYS} ngay TRUOC, tinh lai 1 lan moi
 * ngay UTC, KHONG bao gio gom du lieu cua chinh ngay dang chay. Warm-up: chua du MIN_SAMPLES mau hop le
 * thi khong chan.
 *
 * <p><b>OFF</b> (key {@code SIM_TICK_BLOCK_IND} khong khai) ⇒ {@link #ACTIVE} = false ⇒ khong mot dong
 * nao doi => parity byte-identical.
 */
public final class TickWeakBlock {

    public static final Logger LOG = LoggerFactory.getLogger(TickWeakBlock.class);

    private static final int MIN_PER_DAY = 1440;

    /** "" = OFF (mac dinh) — moi gia tri khac la 1 trong 3 che do o javadoc. */
    public static final boolean ACTIVE =
            Configs.TICK_BLOCK_IND != null && !Configs.TICK_BLOCK_IND.isEmpty();
    private static final String MODE = ACTIVE ? Configs.TICK_BLOCK_IND : "";
    private static final int PCT = Configs.TICK_BLOCK_PCT;            // kich thuoc duoi bi chan (%)
    private static final int WIN = Configs.TICK_BLOCK_WIN_DAYS;       // do dai cua so cuon (ngay)
    private static final int MIN_SAMPLES = Configs.TICK_BLOCK_MIN_SAMPLES;  // warm-up
    private static final float DROP1M = (float) Configs.TICK_BLOCK_DROP1M;  // nguong "rot manh" cho BREADTH

    /** Ring WIN+1 block x 1440 phut: block cua ngay d nam o slot {@code d % (WIN+1)}. */
    private static final float[] BUF = new float[(WIN + 1) * MIN_PER_DAY];
    private static final float[] SORT = new float[(WIN + 1) * MIN_PER_DAY];

    // [FIX 2026-09-23] `new float[]` cua Java = TOAN SO 0.0, KHONG phai NaN. Neu de nguyen thi moi
    //   slot CHUA GHI bi tinh la "mau hop le" (=0.0) => (a) dem mau luon >= MIN_SAMPLES nen WARM-UP
    //   bi VO HIEU ngay tu ngay 1 (nguong = 0.0 thay vi null), va (b) block luon ca cac phut co
    //   rateDownAvg >= 0 trong ~2,5 thang dau — KHAC thiet ke da pre-reg (docs/PREREG_TICK_BLOCK.md
    //   §1.2: "chua du 20.160 mau hop le thi KHONG chan"). Do duoc: ban 0-init chan them 9.656 phut
    //   (2021-07-01..2021-09-17). Nay dien NaN truoc khi dung => dung y thiet ke.
    static {
        java.util.Arrays.fill(BUF, Float.NaN);
    }

    private static long curDay = Long.MIN_VALUE;
    private static double thr = Double.NaN;
    private static boolean blocked = false;
    private static boolean[] excluded = null;
    private static BufferedWriter minLog = null;

    // ==== bo dem de bao cao (khong doi hanh vi) ====
    public static long nMinutes = 0;      // so luot (phut) da xu ly
    public static long nBlocked = 0;      // so luot bi chan
    public static long nThrDays = 0;      // so ngay co nguong (sau warm-up)
    public static double thrLast = Double.NaN;
    public static double xLast = Double.NaN;

    private TickWeakBlock() {
    }

    /**
     * Cap nhat cua so + tra ve "luot nay co bi chan khong" — goi DUNG 1 LAN cho moi phut, TRUOC moi
     * duong vao lenh. Read-only voi trang thai lenh.
     */
    public static boolean step(long time, MarketDataObject md, KlineObjectSimple[] tickers) {
        if (!ACTIVE) {
            return false;
        }
        nMinutes++;
        long day = Math.floorDiv(time, Utils.TIME_DAY);
        if (day != curDay) {
            curDay = day;
            threshold();
        }
        float x = indicator(md, tickers);
        if (Float.isNaN(x)) {
            blocked = false;
            return false;
        }
        BUF[idx(day, time)] = x;
        xLast = x;
        blocked = decide(x);
        if (blocked) {
            nBlocked++;
            logBlocked(time);
        }
        return blocked;
    }

    public static boolean isBlocked() {
        return blocked;
    }

    private static int idx(long day, long time) {
        int block = (int) Math.floorMod(day, (long) (WIN + 1));
        int minute = (int) ((time - day * Utils.TIME_DAY) / Utils.TIME_MINUTE);
        if (minute < 0) minute = 0;
        if (minute >= MIN_PER_DAY) minute = MIN_PER_DAY - 1;
        return block * MIN_PER_DAY + minute;
    }

    /** Gia tri chi so tai luot hien tai — NaN = khong xac dinh (khong chan, khong ghi cua so). */
    private static float indicator(MarketDataObject md, KlineObjectSimple[] tickers) {
        if ("BREADTH".equals(MODE)) {
            return breadth(tickers);
        }
        if (md == null) {
            return Float.NaN;
        }
        return "DROP15M".equals(MODE) ? md.rateDown15MAvg : md.rateDownAvg;
    }

    /**
     * % ticker "con song + gia hop le" co return 1M &lt;= {@link #DROP1M}. Cung bo loc "con song" nhu
     * {@link MarketBigChangeDetector#calMarketData} (bo null / khong co gia / ten trong
     * {@code Constants.diedSymbol}), return = (close-open)/open.
     */
    private static float breadth(KlineObjectSimple[] tickers) {
        if (tickers == null) {
            return Float.NaN;
        }
        if (excluded == null || excluded.length < tickers.length) {
            buildExcluded(tickers.length);
        }
        int nAlive = 0;
        int nDrop = 0;
        for (int id = 0; id < tickers.length; id++) {
            KlineObjectSimple t = tickers[id];
            if (t == null || !Utils.isTickerAvailable(t) || t.priceOpen <= 0f) {
                continue;
            }
            if (id < excluded.length && excluded[id]) {
                continue;
            }
            nAlive++;
            if ((t.priceClose - t.priceOpen) / t.priceOpen <= DROP1M) {
                nDrop++;
            }
        }
        if (nAlive == 0) {
            return Float.NaN;
        }
        return 100f * nDrop / nAlive;
    }

    private static void buildExcluded(int n) {
        excluded = new boolean[Math.max(n, 1000)];
        int k = 0;
        String first = null;
        for (int id = 0; id < excluded.length; id++) {
            String name;
            try {
                name = SimpleSymbolMapper.getInstance().getSymbol((short) id);
            } catch (Exception e) {
                name = null;
            }
            if (name != null && Constants.diedSymbol.contains(name)) {
                excluded[id] = true;
                k++;
                if (first == null) first = name;
            }
        }
        LOG.info("[TICKBLK] breadth: loai {} id co ten trong diedSymbol (vd {})", k, first);
    }

    /**
     * Nguong = quantile cua {@code WIN} block NGAY TRUOC (khong gom block cua ngay dang chay).
     * Vi tri lay mau: {@code floor(q*(n-1))} tren mang da sort (empirical quantile).
     */
    private static void threshold() {
        int curBlock = (int) Math.floorMod(curDay, (long) (WIN + 1));
        int n = 0;
        for (int b = 0; b < WIN + 1; b++) {
            if (b == curBlock) {
                continue;
            }
            int base = b * MIN_PER_DAY;
            for (int i = 0; i < MIN_PER_DAY; i++) {
                float v = BUF[base + i];
                if (!Float.isNaN(v)) {
                    SORT[n++] = v;
                }
            }
        }
        if (n < MIN_SAMPLES) {
            thr = Double.NaN;
            return;
        }
        Arrays.sort(SORT, 0, n);
        double q = "BREADTH".equals(MODE) ? (PCT / 100.0) : (1.0 - PCT / 100.0);
        int at = (int) Math.floor(q * (n - 1));
        if (at < 0) at = 0;
        if (at >= n) at = n - 1;
        thr = SORT[at];
        thrLast = thr;
        nThrDays++;
    }

    private static boolean decide(float x) {
        if (Double.isNaN(thr)) {
            return false;
        }
        // BREADTH: te nhat = THAP nhat. DEPTH/DROP15M: te nhat = it AM nhat (cao nhat).
        return "BREADTH".equals(MODE) ? (x <= thr) : (x >= thr);
    }

    /** Ghi danh sach phut bi chan (de do "gross" so lenh mat) — chi khi ACTIVE. */
    private static void logBlocked(long time) {
        if (minLog == null) {
            try {
                File dir = new File("storage");
                if (!dir.exists()) dir.mkdirs();
                minLog = new BufferedWriter(new FileWriter("storage/tickblk_blocked_min.csv", false));
                minLog.write("minute\n");
            } catch (Exception e) {
                LOG.warn("[TICKBLK] khong mo duoc file phut bi chan: {}", e.toString());
                minLog = null;
                return;
            }
        }
        try {
            minLog.write(Utils.sdfFileHour.format(new java.util.Date(time)));
            minLog.write("\n");
        } catch (Exception e) {
            // im lang: file chan do la cong cu phu, khong duoc lam hong run
        }
    }

    public static void close() {
        if (minLog != null) {
            try {
                minLog.close();
            } catch (Exception e) {
                // bo qua
            }
            minLog = null;
        }
    }

    public static String summary() {
        return String.format("ind=%s pct=%d winDays=%d minSamples=%d drop1m=%.4f "
                        + "minutes=%d blocked=%d blockedPct=%.2f thrDays=%d thrLast=%.6f",
                MODE, PCT, WIN, MIN_SAMPLES, DROP1M, nMinutes, nBlocked,
                nMinutes > 0 ? 100.0 * nBlocked / nMinutes : 0.0, nThrDays, thrLast);
    }
}
