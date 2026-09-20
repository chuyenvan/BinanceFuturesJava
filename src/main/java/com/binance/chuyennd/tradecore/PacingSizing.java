package com.binance.chuyennd.tradecore;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

/**
 * [PACING 2026-09-21] docs/PREREG_PACING_BIGDOWN.md - TASK B: giam size khi thi truong dang sap
 * (P3, regime-conditional, causal) hoac giam size DEU khong dieu kien (P0, doi chung) tren nen
 * gate 1.0. KHONG doi lenh nao duoc chon vao/ra - chi doi KICH THUOC (giong VolTargetSizing).
 *
 * <p>{@code Configs.SIZE_PACING_MODE}: OFF (mac dinh) | P0 | P3. OFF =&gt; {@link #ACTIVE}=false
 * =&gt; call-site (Simulator) KHONG goi toi class nay =&gt; byte-identical voi T170 (cong repro
 * md5 efb793e2).
 *
 * <p><b>P0</b> (doi chung, khong regime, BAT BUOC lam doi chung): multiplier = {@link #P0_MULT}
 * CO DINH moi luc. Gia tri chot TRUOC khi chay (docs/PREREG_PACING_BIGDOWN.md muc 2) = ti le
 * median(Sigma(notional)/equity | bigdown BD1a, tinh dung cong thuc M3 cua
 * research/analysis/bigdown_struct.py) cua T170 / T100 tren 2021-07-01..2025-12-31.
 *
 * <p><b>P3</b> (regime-conditional, CHINH): multiplier = {@link #P3_GAMMA} khi co BD1a CAUSAL
 * dang BAT, = 1.0 khi tat. BD1a: BTC return 24h &lt;= {@link #BD_RET24H_THRESHOLD}, tinh tren gia
 * dong cua CAC GIO DA HOAN TAT truoc tsMs (xem {@link #isBigDownAt(long)}) - KHONG BAO GIO dung
 * gia cua gio dang chay dang do (tranh lookahead, chat hon quy uoc cua VolTargetSizing.COIN_MODE
 * mot buoc gio, dung theo yeu cau "tinh toi t-1" cua PREREG). Gia BTC doc tu file
 * {@code CLOSES_1H.bin} - dataset da dung cho VolTargetSizing.COIN_MODE va cho chinh
 * bigdown_struct.py/trend_rank_ic.py (KHONG sinh du lieu moi), symbol {@code BTCUSDT}.
 *
 * <p>Ca hai mode fallback ve multiplier=1.0f khi thieu du lieu (vd chua du 25h lich su BTC dau
 * DEV, hoac khong doc duoc file) - KHONG BAO GIO tra null/NaN/&lt;=0.
 */
public final class PacingSizing {
    private static final Logger LOG = LoggerFactory.getLogger(PacingSizing.class);

    public static final String MODE = Configs.SIZE_PACING_MODE.trim().toUpperCase();
    public static final boolean ACTIVE = !"OFF".equals(MODE);
    public static final boolean P0_MODE = "P0".equals(MODE);
    public static final boolean P3_MODE = "P3".equals(MODE);

    // --- HANG SO PRE-REG (chot 2026-09-21 TRUOC khi chay variant, xem
    //     docs/PREREG_PACING_BIGDOWN.md muc 2 - KHONG duoc doi sau khi thay ket qua) ---
    /** He so size CO DINH cho P0 = median(margin/equity|bigdown,T170) / median(margin/equity|
     *  bigdown,T100) = 0.057965.../0.270101... , tinh 2026-09-21
     *  (research/analysis/compute_p0_mult2.py, dung dung ham M3 cua bigdown_struct.py). */
    public static final float P0_MULT = 0.2146f;
    /** He so size khi bigdown BAT trong P3 - chot 1 gia tri, KHONG quet. */
    public static final float P3_GAMMA = 0.5f;
    /** Nguong BD1a: BTC return 24h &lt;= nguong nay => bigdown BAT (khop dinh nghia headline
     *  docs/ANALYSIS_BIGDOWN_STRUCT.md muc 0 / docs/PREREG_BIGDOWN_STRUCT.md). */
    public static final float BD_RET24H_THRESHOLD = -0.05f;

    private static final long HOUR_MS = 3_600_000L;
    private static final String CLOSES_1H_PATH = "/home/ubuntu/java/fsrun/CLOSES_1H.bin";
    private static final String SYMBOL_MAP_PATH = "/home/ubuntu/selector_pred_out/symbol_map.csv";
    private static final String BTC_SYMBOL = "BTCUSDT";

    /** raw ts (=open time cua nen 1h, boi so HOUR_MS, quy uoc giong CLOSES_1H.bin/VolTargetSizing)
     *  -> gia dong cua nen BTC do (chi cac gio CO trong file). */
    private static volatile TreeMap<Long, Float> BTC_CLOSES;

    private PacingSizing() {
    }

    /**
     * He so nhan vao budget (call-site: Simulator, SAU VolTargetSizing, TRUOC DCA-grid ratio).
     * Tra 1.0f khi OFF hoac thieu du lieu - KHONG BAO GIO null/NaN/&lt;=0.
     */
    public static float multiplier(long tsMs) {
        if (!ACTIVE) return 1f;
        if (P0_MODE) return P0_MULT;
        if (P3_MODE) return isBigDownAt(tsMs) ? P3_GAMMA : 1f;
        return 1f;
    }

    /**
     * BD1a CAUSAL toi t-1: CLOSES_1H.bin luu (ts=open_time, c=close cua nen [ts, ts+1h)) - nen
     * mo tai "gio dang chay" (floor(tsMs/1h)*1h) CHUA dong tai tsMs, nen KHONG duoc dung. Nen
     * HOAN TAT gan nhat co open_time = floor(tsMs/1h)*1h - 1h (dong dung luc floor(tsMs/1h)*1h
     * &lt;= tsMs). So gia dong nen do voi gia dong nen 24h truoc do (cung quy uoc open_time).
     */
    static boolean isBigDownAt(long tsMs) {
        ensureBtcClosesLoaded();
        long hourNowOpen = Math.floorDiv(tsMs, HOUR_MS) * HOUR_MS;   // gio dang chay, CHUA dong
        long t1 = hourNowOpen - HOUR_MS;                             // nen HOAN TAT gan nhat
        long t0 = t1 - 24 * HOUR_MS;                                 // 24h truoc do
        Float p1 = BTC_CLOSES.get(t1);
        Float p0 = BTC_CLOSES.get(t0);
        if (p1 == null || p0 == null || p0 <= 0f) return false;      // thieu du lieu -> khong pacing
        float ret24h = p1 / p0 - 1f;
        return ret24h <= BD_RET24H_THRESHOLD;
    }

    private static synchronized void ensureBtcClosesLoaded() {
        if (BTC_CLOSES != null) return;
        LOG.info("[PACING] loading {} cho BTC BD1a causal flag...", CLOSES_1H_PATH);
        TreeMap<Long, Float> closes = new TreeMap<>();
        try {
            Map<Integer, String> symMap = loadSymbolMap();
            int btcId = -1;
            for (Map.Entry<Integer, String> e : symMap.entrySet()) {
                if (BTC_SYMBOL.equals(e.getValue())) {
                    btcId = e.getKey();
                    break;
                }
            }
            if (btcId >= 0) {
                byte[] buf = Files.readAllBytes(Paths.get(CLOSES_1H_PATH));
                ByteBuffer bb = ByteBuffer.wrap(buf).order(ByteOrder.BIG_ENDIAN);
                int n = buf.length / 14;   // ts(int64,8) + sym(int16,2) + c(float32,4)
                for (int k = 0; k < n; k++) {
                    long ts = bb.getLong();
                    short sym = bb.getShort();
                    float c = bb.getFloat();
                    if (sym == btcId) closes.put(ts, c);
                }
            } else {
                LOG.warn("[PACING] khong tim thay symId cho {} trong {}", BTC_SYMBOL, SYMBOL_MAP_PATH);
            }
        } catch (Exception e) {
            LOG.warn("[PACING] khong doc duoc du lieu BTC ({}) - BD1a se luon FALSE (multiplier=1.0)",
                    CLOSES_1H_PATH, e);
        }
        LOG.info("[PACING] loaded {} gio BTC cho BD1a causal flag", closes.size());
        BTC_CLOSES = closes;
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
}
