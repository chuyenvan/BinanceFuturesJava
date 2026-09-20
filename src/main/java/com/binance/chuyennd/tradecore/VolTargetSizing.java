package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.tradecore.selector.S1FeatureLive;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.SortedMap;
import java.util.TreeMap;

/**
 * [VOL_TARGET 2026-09-20] docs/PREREG_VOL_TARGET.md - TASK 5: size lenh theo BIEN DONG THUC TE
 * (risk parity), KHONG doi lenh nao duoc chon vao/ra (chi doi KICH THUOC). Day la cai tien QUAN TRI
 * RUI RO, KHONG phai thu nghiem tim alpha - ky vong NULL o cac rate chat luong chuan.
 *
 * <p>{@code Configs.SIZE_VOL_TARGET_MODE}: OFF (mac dinh) | COIN | PORTFOLIO.
 * OFF => {@link #ACTIVE}=false => call-site (Simulator) KHONG goi toi class nay =>
 * byte-identical voi T170 (cong repro md5 efb793e2).
 *
 * <p><b>COIN</b>: multiplier = clamp(SIGMA_REF / sigma_coin_7d(t), 0.5, 2.0). sigma_coin_7d(t) =
 * do lech chuan return 1h cua CHINH coin do, cua so 168h (min_periods=84), tinh CAUSAL - chi dung
 * gia dong gio <= floor(t/1h)*1h (gio da bat dau, KHONG nhin tuong lai). Cong thuc + code tai su dung
 * NGUYEN VAN {@link S1FeatureLive#vol7d(double[], int)} (da dung cho feature S1 live, khop tung dong
 * voi {@code research/pipeline/feat_v2_build.py}). Du lieu gia doc tu {@code CLOSES_1H.bin}
 * (dataset CO SAN tren Oracle, dung chung voi pipeline feature - KHONG sinh du lieu moi).
 *
 * <p><b>PORTFOLIO</b>: multiplier = clamp(targetDailyVol / sigma_equity_20d(t), 0.5, 2.0), voi
 * targetDailyVol = {@link #PORTFOLIO_TARGET_ANNUAL_VOL} / sqrt(365). sigma_equity_20d(t) = do lech
 * chuan (ddof=1) cua 20 log-return NGAY gan nhat cua CHINH equity chien luoc - CHI dung ngay da
 * HOAN TAT truoc ngay hien tai (dayKey < today), KHONG dung bat ky gia tri nao cua ngay dang chay
 * (lich equity do {@link com.binance.chuyennd.research.BudgetManagerSimple#date2EquityLastVT} ghi,
 * cap nhat moi tick trong updateBalance - xem hook o do).
 *
 * <p>Ca hai mode deu FALLBACK ve multiplier=1.0f khi thieu du lieu/warmup (KHONG BAO GIO tra
 * null/NaN/0) - vi du 20 ngay dau DEV (PORTFOLIO chua du lich su) hoac coin moi list &lt;7 ngay
 * (COIN chua du warmup).
 */
public final class VolTargetSizing {
    private static final Logger LOG = LoggerFactory.getLogger(VolTargetSizing.class);

    public static final String MODE = Configs.SIZE_VOL_TARGET_MODE.trim().toUpperCase();
    public static final boolean ACTIVE = !"OFF".equals(MODE);
    public static final boolean COIN_MODE = "COIN".equals(MODE);
    public static final boolean PORTFOLIO_MODE = "PORTFOLIO".equals(MODE);

    // --- HANG SO PRE-REG (chot 2026-09-20 TRUOC khi chay variant, xem docs/PREREG_VOL_TARGET.md
    //     muc 2 - KHONG duoc doi sau khi thay ket qua) ---
    /** Trung vi vol_7d (do lech chuan return 1h, cua so 168h min_periods=84) toan bo universe
     *  CLOSES_1H.bin 2021-01-01..2026-01-01 (627 coin, 10,283,808 o hop le, tinh 2026-09-20). */
    public static final float SIGMA_REF = 0.010657f;
    public static final float CLAMP_LO = 0.5f;
    public static final float CLAMP_HI = 2.0f;
    /** Target-vol NAM co dinh cho PORTFOLIO mode (25%/nam) - CHOT TRUOC, khong quet nhieu gia tri. */
    public static final float PORTFOLIO_TARGET_ANNUAL_VOL = 0.25f;
    private static final double ANNUALIZE_DAYS = 365.0;   // crypto giao dich 24/7
    /** So return NGAY toi thieu (=> can 21 diem equity HOAN TAT) truoc khi tinh multiplier that. */
    private static final int PORTFOLIO_MIN_RETURNS = 20;

    private static final long HOUR_MS = 3_600_000L;
    private static final String CLOSES_1H_PATH = "/home/ubuntu/java/fsrun/CLOSES_1H.bin";
    private static final String SYMBOL_MAP_PATH = "/home/ubuntu/selector_pred_out/symbol_map.csv";

    private static volatile Map<String, double[]> COIN_CLOSES;
    private static volatile Map<String, Long> COIN_MIN_TS;

    private VolTargetSizing() {
    }

    /**
     * He so nhan vao budget (call-site: Simulator, SAU tierMultiplier, TRUOC DCA-grid ratio).
     * Tra 1.0f khi OFF hoac thieu du lieu - KHONG BAO GIO null/NaN/<=0.
     */
    public static float multiplier(String symbol, long tsMs) {
        if (!ACTIVE) return 1f;
        if (COIN_MODE) return coinMultiplier(symbol, tsMs);
        if (PORTFOLIO_MODE) return portfolioMultiplier(tsMs);
        return 1f;
    }

    // ---------------------------------------------------------------- COIN

    private static float coinMultiplier(String symbol, long tsMs) {
        ensureCoinClosesLoaded();
        double[] arr = COIN_CLOSES.get(symbol);
        if (arr == null) return 1f;
        Long minTs = COIN_MIN_TS.get(symbol);
        if (minTs == null) return 1f;
        long hourTs = Math.floorDiv(tsMs, HOUR_MS) * HOUR_MS;   // gio da bat dau <= tsMs (causal)
        long idxL = (hourTs - minTs) / HOUR_MS;
        if (idxL < 0 || idxL >= arr.length) return 1f;
        double sigma = S1FeatureLive.vol7d(arr, (int) idxL);
        if (Double.isNaN(sigma) || sigma <= 0d) return 1f;
        return clamp((float) (SIGMA_REF / sigma));
    }

    private static synchronized void ensureCoinClosesLoaded() {
        if (COIN_CLOSES != null) return;
        LOG.info("[VOL_TARGET] loading {} cho COIN mode...", CLOSES_1H_PATH);
        try {
            Map<Integer, String> symMap = loadSymbolMap();
            byte[] buf = Files.readAllBytes(Paths.get(CLOSES_1H_PATH));
            ByteBuffer bb = ByteBuffer.wrap(buf).order(ByteOrder.BIG_ENDIAN);
            int n = buf.length / 14;   // ts(int64,8) + sym(int16,2) + c(float32,4)
            Map<Integer, TreeMap<Long, Float>> bySym = new HashMap<>();
            for (int k = 0; k < n; k++) {
                long ts = bb.getLong();
                short sym = bb.getShort();
                float c = bb.getFloat();
                bySym.computeIfAbsent((int) sym, x -> new TreeMap<>()).put(ts, c);
            }
            Map<String, double[]> closes = new HashMap<>();
            Map<String, Long> minTsMap = new HashMap<>();
            for (Map.Entry<Integer, TreeMap<Long, Float>> e : bySym.entrySet()) {
                String symStr = symMap.get(e.getKey());
                if (symStr == null) continue;
                TreeMap<Long, Float> m = e.getValue();
                long minTs = m.firstKey(), maxTs = m.lastKey();
                int len = (int) ((maxTs - minTs) / HOUR_MS) + 1;
                double[] arr = new double[len];
                Arrays.fill(arr, Double.NaN);
                for (Map.Entry<Long, Float> pe : m.entrySet()) {
                    int idx = (int) ((pe.getKey() - minTs) / HOUR_MS);
                    arr[idx] = pe.getValue();
                }
                closes.put(symStr, arr);
                minTsMap.put(symStr, minTs);
            }
            COIN_MIN_TS = minTsMap;
            COIN_CLOSES = closes;
            LOG.info("[VOL_TARGET] loaded {} rows -> {} symbol arrays", n, closes.size());
        } catch (Exception e) {
            throw new RuntimeException("[VOL_TARGET] khong doc duoc " + CLOSES_1H_PATH, e);
        }
    }

    private static Map<Integer, String> loadSymbolMap() throws Exception {
        Map<Integer, String> m = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(SYMBOL_MAP_PATH))) {
            String line = br.readLine();   // header symId,symbol
            while ((line = br.readLine()) != null) {
                if (line.isEmpty()) continue;
                String[] p = line.split(",");
                m.put(Integer.parseInt(p[0].trim()), p[1].trim());
            }
        }
        return m;
    }

    // ----------------------------------------------------------- PORTFOLIO

    private static float portfolioMultiplier(long tsMs) {
        TreeMap<Long, Float> hist = BudgetManagerSimple.getInstance().date2EquityLastVT;
        long today = Utils.getDate(tsMs);
        SortedMap<Long, Float> before = hist.headMap(today);   // CHI ngay < today (causal)
        if (before.size() < PORTFOLIO_MIN_RETURNS + 1) return 1f;
        List<Float> vals = new ArrayList<>(before.values());
        int n = vals.size();
        int start = n - (PORTFOLIO_MIN_RETURNS + 1);
        double[] eq = new double[PORTFOLIO_MIN_RETURNS + 1];
        for (int i = 0; i < eq.length; i++) eq[i] = vals.get(start + i);
        double[] ret = new double[PORTFOLIO_MIN_RETURNS];
        for (int i = 0; i < ret.length; i++) {
            if (eq[i] <= 0d || eq[i + 1] <= 0d) return 1f;
            ret[i] = Math.log(eq[i + 1] / eq[i]);
        }
        double mean = 0d;
        for (double r : ret) mean += r;
        mean /= ret.length;
        double ss = 0d;
        for (double r : ret) ss += (r - mean) * (r - mean);
        double sigmaDaily = Math.sqrt(ss / (ret.length - 1));
        if (Double.isNaN(sigmaDaily) || sigmaDaily <= 0d) return 1f;
        double targetDaily = PORTFOLIO_TARGET_ANNUAL_VOL / Math.sqrt(ANNUALIZE_DAYS);
        return clamp((float) (targetDaily / sigmaDaily));
    }

    private static float clamp(float v) {
        if (Float.isNaN(v)) return 1f;
        if (v < CLAMP_LO) return CLAMP_LO;
        if (v > CLAMP_HI) return CLAMP_HI;
        return v;
    }
}
