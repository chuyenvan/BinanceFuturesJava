package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.hpo.BacktestIntegrityGuard;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.bigchange.test.TraceOrderDone;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedInputStream;
import java.io.BufferedWriter;
import java.io.DataInputStream;
import java.io.FileInputStream;
import java.io.File;
import java.io.FileWriter;
import java.text.ParseException;
import java.util.*;

/**
 * FORCED-SELLER REVERSION — cai dat DOC LAP LAN 2 (Java/Aerospike) cua spec da chay ben Python.
 *
 * <p>MUC DICH: doi chung cheo. Python doc kline 15m tu Binance REST; ban nay doc kline 1m tu
 * Aerospike Oracle roi TU GOP thanh 15m. Hai duong doc-du-lieu + hai lan code doc lap. Neu danh
 * sach lenh khop nhau thi lo hong "chua nhin ra" phai nam o CHO CHUNG (dinh nghia spec), khong
 * phai o loi cai dat.
 *
 * <p>SPEC (dong bang, khong tuning trong file nay):
 * <pre>
 *   khung          : 15m (gop tu 1m Aerospike, moc chia het cho 900000ms UTC)
 *   r24            : close[i]/close[i-96] - 1                       (96 nen 15m = 24h)
 *   sigma          : do lech chuan cua r24 tren 2880 nen gan nhat   (30 ngay), toi thieu 960 mau
 *   kich hoat      : r24 < -3.0 * sigma
 *   khu trung lap  : moi coin toi da 1 tin hieu / 24h
 *   moc quyet dinh : t_dec = thoi diem nen kich hoat DONG
 *   vao lenh       : limit MUA tai p0 = close nen kich hoat, hieu luc 5 phut ke tu t_dec.
 *                    khop khi low cua nen 1m nao do trong 5 phut do <= p0. Khong khop => bo lenh.
 *   thoat lenh     : dung gio, tai close cua nen 1m dong luc t_dec + 24h. Khong TP/SL/trailing/DCA.
 *   loc regime     : (tuy chon, FS_BTC30_MIN) BTC 30 ngay > -20%
 *   von            : 10% so du moi lenh, toi da 60% tong (6 lenh song song), don bay 1x
 * </pre>
 *
 * <p>KHONG dung selector / gate / AI predict / trailing / DCA — da chung minh cac thu do lam xau
 * chien luoc nay (trailing: holdout +0.67% vs thoat-theo-gio +2.24%).
 *
 * <p>Ghi ra dung dinh dang sim goc de TraceData2Test doc duoc:
 * storage/OrderTestDone.data, storage/BalanceIndex.data, storage/printDone.csv,
 * cong log "Update ... b:" qua BudgetManagerSimple.updateBalance.
 * Them storage/FS_TRADES.csv (thoat rieng) de doi chung tung lenh voi Python.
 */
public class SimulatorForcedSeller {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorForcedSeller.class);

    // ===================== SPEC DONG BANG =====================
    private static final long MIN_MS = 60_000L;
    private static final long BAR_MS = 15 * MIN_MS;
    private static final int K = 96;
    private static final int WSIG = 2880;
    private static final int MINP = 960;
    private static final int HOLD = 96;
    /** Nguong sigma — CHO PHEP doi qua env FS_NSIG de quet do nhay. Mac dinh 3.0 = spec dong bang. */
    private static final float NSIG = envF("FS_NSIG", 3.0f);
    private static final long DEDUP_MS = 24 * 3600_000L;
    private static final int MAKER_WIN_MIN = 5;
    private static final long HOLD_MS = (long) HOLD * BAR_MS;   // 24h
    private static final int BARS_30D = 2880;                   // 30 ngay theo nen 15m

    private static final String[] DEFAULT_SYMBOLS = {
            "AAVEUSDT", "ADAUSDT", "ATOMUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT",
            "DOTUSDT", "ETCUSDT", "ETHUSDT", "FILUSDT", "LINKUSDT", "LTCUSDT", "NEARUSDT",
            "SANDUSDT", "SOLUSDT", "TRXUSDT", "UNIUSDT", "XLMUSDT", "XRPUSDT"};

    // ===================== THAM SO CHAY (env) =====================
    private final String[] symbols;
    private final float wPerTrade;
    private final float capTotal;
    private final Float btc30Min;        // null = tat loc regime
    private final boolean writeStorage;

    // ===================== TRANG THAI =====================
    /** Nen 15m dang gop do (theo symbolId). */
    private final Bar15[] pending = new Bar15[1000];
    /** Vong dem close 15m (theo symbolId). */
    private final Ring[] ring = new Ring[1000];
    private final long[] lastSignalTs = new long[1000];
    private final Pending[] pendingLimit = new Pending[1000];
    private final OrderTargetInfoTest[] running = new OrderTargetInfoTest[1000];
    private final long[] exitAtMinute = new long[1000];
    private final Trade[] runningTrade = new Trade[1000];
    @SuppressWarnings("unchecked")
    private final List<OrderTargetInfoTest>[] symbol2OrdersEntry = new ArrayList[1000];

    // ===== SELECTOR PRED (predict_wf_*.bin, WF leak-free). score = 1 - P(win) -> THAP = TOT =====
    private final String predDir;
    private final String predMapCsv;
    private final int predHorizon;      // 0=slot0(4h) 1=12h 2=24h 3=72h
    private final long predStaleMs;
    private final String predMissing;   // median | last | first
    private final Float scoreMax;       // loc cung: bo tin hieu co score > nguong (null = tat)
    private final boolean predRank;     // xep hang khi tranh cho trong tran von
    /** theo symbolId: moc ts tang dan + score tuong ung. */
    private final long[][] predTs = new long[1000][];
    private final float[][] predScore = new float[1000][];
    private float predMedian = 0.5f;
    private long nScoreHit = 0, nScoreMiss = 0, nSkipScoreMax = 0;

    // ===== CHE DO DUMP: chi ghi close 15m (moc gio) cua moi symbol, KHONG giao dich =====
    private final String dumpPath;
    private java.io.DataOutputStream dumpOut;
    private long dumpRows = 0;

    private short btcId = -1;
    private final Set<Short> trackedIds = new LinkedHashSet<>();
    private final Map<Short, String> id2Symbol = new HashMap<>();

    private TreeMap<Long, OrderTargetInfoTest> allOrderDone = new TreeMap<>();
    private final List<Trade> trades = new ArrayList<>();

    // dem chan doan
    private long nSignal = 0, nSkipDedup = 0, nSkipRunning = 0, nSkipCap = 0,
            nSkipRegime = 0, nNoFill = 0, nFilled = 0, nClosed = 0, nMinutes = 0, nDaysRead = 0,
            nSkipCapFill = 0, maxConcurrent = 0;

    // ===================== CAU TRUC PHU =====================
    private static final class Bar15 {
        long barTs = -1;          // moc MO nen (chia het 900000)
        float open, high, low, close;
        int minutes;
    }

    /** Vong dem close 15m + moc thoi gian DONG nen tuong ung. */
    private static final class Ring {
        final float[] close = new float[WSIG + K + 8];
        final long[] closeTime = new long[WSIG + K + 8];
        int n = 0;              // tong so nen da nap (co the > capacity)
        int head = 0;           // vi tri ghi tiep theo

        void push(float c, long ct) {
            close[head] = c;
            closeTime[head] = ct;
            head = (head + 1) % close.length;
            n++;
        }

        /** close cua nen cach nen moi nhat 'back' vi tri (back=0 => moi nhat). null neu chua du. */
        Float back(int back) {
            if (back >= Math.min(n, close.length)) return null;
            int idx = (head - 1 - back) % close.length;
            if (idx < 0) idx += close.length;
            return close[idx];
        }
    }

    /** Tin hieu ung vien trong CUNG mot moc dong nen — xep hang truoc khi cap phat von. */
    private static final class Cand {
        short id;
        long barTs, tDec;
        float p0, r24, sigma, score;
    }

    private static final class Pending {
        long triggerBarTs;      // moc MO nen kich hoat
        long tDec;              // moc nen kich hoat DONG
        float p0;
        float r24, sigma, score;
        long expireAt;          // < moc nay thi con hieu luc
    }

    /** Ban ghi lenh de xuat CSV doi chung voi Python. */
    private static final class Trade {
        String symbol;
        long triggerBarTs, tDec, fillTime, exitTime;
        float p0, entry, exitPx, r24, sigma, z, score;
        int fillMinute;
        float qty, funding, grossRate;
    }

    // ===================== KHOI TAO =====================
    public SimulatorForcedSeller() {
        String s = System.getenv("FS_SYMBOLS");
        this.symbols = (s == null || s.isBlank()) ? DEFAULT_SYMBOLS : s.trim().toUpperCase().split(",");
        this.wPerTrade = envFloat("FS_W_PER_TRADE", 0.10f);
        this.capTotal = envFloat("FS_CAP_TOTAL", 0.60f);
        String b = System.getenv("FS_BTC30_MIN");
        this.btc30Min = (b == null || b.isBlank()) ? null : Float.parseFloat(b.trim());
        this.writeStorage = !"false".equalsIgnoreCase(String.valueOf(System.getenv("FS_WRITE_STORAGE")));
        this.predDir = System.getenv("FS_PRED_DIR");
        this.predMapCsv = System.getenv().getOrDefault("FS_PRED_MAP",
                "/home/ubuntu/selector_pred_out/symbol_map.csv");
        this.predHorizon = Integer.parseInt(System.getenv().getOrDefault("FS_PRED_HORIZON", "0"));
        this.predStaleMs = (long) envFloat("FS_PRED_STALE_MIN", 30f) * 60_000L;
        this.predMissing = System.getenv().getOrDefault("FS_PRED_MISSING", "median");
        String sm = System.getenv("FS_SCORE_MAX");
        this.scoreMax = (sm == null || sm.isBlank()) ? null : Float.parseFloat(sm.trim());
        this.predRank = "true".equalsIgnoreCase(String.valueOf(System.getenv("FS_PRED_RANK")));
        this.dumpPath = System.getenv("FS_DUMP_CLOSES");
    }

    /** doc env float o tang static (dung cho hang so spec). */
    private static float envF(String k, float def) {
        String v = System.getenv(k);
        return (v == null || v.isBlank()) ? def : Float.parseFloat(v.trim());
    }

    private static float envFloat(String k, float def) {
        String v = System.getenv(k);
        if (v == null || v.isBlank()) return def;
        return Float.parseFloat(v.trim());
    }

    public static void main(String[] args) throws Exception {
        String startStr = System.getenv("FS_START");
        String endStr = System.getenv("FS_END");
        if (startStr == null || startStr.isBlank() || endStr == null || endStr.isBlank()) {
            throw new IllegalStateException("Thieu FS_START / FS_END (yyyyMMdd).");
        }
        long startTime = Utils.sdfFile.parse(startStr).getTime();
        long endTime = com.binance.chuyennd.tradecore.HoldoutSeal.clampEnd(
                Utils.sdfFile.parse(endStr).getTime(), "SimulatorForcedSeller");

        // Cong liem chinh: cho phep che do doi chung (slippage=0) NHUNG phai bat tuong minh.
        boolean diag = "true".equalsIgnoreCase(String.valueOf(System.getenv("FS_DIAGNOSTIC")));
        if (diag) {
            Configs.APPLY_SLIPPAGE = false;
            LOG.warn("*** FS_DIAGNOSTIC=true — TAT SLIPPAGE. Chi dung de doi chung PARITY voi Python, "
                    + "TUYET DOI khong doc so loi nhuan tu lan chay nay nhu ket qua that. ***");
        }
        BacktestIntegrityGuard.assertProductionGrade(diag);

        SimulatorForcedSeller sim = new SimulatorForcedSeller();
        sim.run(startTime, endTime);
        System.exit(0);
    }

    // ===================== VONG CHAY CHINH =====================
    public void run(long startTime, long endTime) throws Exception {
        long t0 = System.currentTimeMillis();
        BudgetManagerSimple.resetInstance();
        SimpleSymbolMapper.getInstance().init();

        for (String sym : symbols) {
            short id = SimpleSymbolMapper.getInstance().getId(sym);
            if (id < 0) {
                if (dumpPath != null && !dumpPath.isBlank()) { LOG.warn("[DUMP] bo qua {} (khong co trong mapper)", sym); continue; }
                throw new IllegalStateException("Khong tim thay symbolId cho " + sym + " trong symbol_mapper.");
            }
            trackedIds.add(id);
            id2Symbol.put(id, sym);
            ring[id] = new Ring();
            pending[id] = new Bar15();
            lastSignalTs[id] = Long.MIN_VALUE / 4;
            exitAtMinute[id] = -1;
            if ("BTCUSDT".equals(sym)) btcId = id;
        }
        if (btc30Min != null && btcId < 0) {
            throw new IllegalStateException("Bat loc FS_BTC30_MIN nhung BTCUSDT khong nam trong FS_SYMBOLS.");
        }

        LOG.info("=== FORCED-SELLER SIM | {} -> {} | {} coin | 10%/lenh tran {}% | loc btc30 {} ===",
                Utils.normalizeDateYYYYMMDDHHmm(startTime), Utils.normalizeDateYYYYMMDDHHmm(endTime),
                symbols.length, (int) (capTotal * 100),
                btc30Min == null ? "TAT" : String.format("> %.0f%%", btc30Min * 100));
        if (predDir != null && !predDir.isBlank()) {
            try { loadPred(); } catch (Exception e) { throw new RuntimeException("Nap FS_PRED_DIR that bai", e); }
        }
        LOG.info("[FS-RANK] FS_PRED_RANK={} FS_SCORE_MAX={} FS_PRED_MISSING={} horizon={} stale={}p",
                predRank, scoreMax, predMissing, predHorizon, predStaleMs / 60000);
        LOG.info("[FS-SPEC] NSIG={} K={} WSIG={} HOLD={} maker_win={}p", NSIG, K, WSIG, HOLD, MAKER_WIN_MIN);
        LOG.info("[FS-COST] RATE_FEE={} APPLY_SLIPPAGE={} SLIPPAGE_RATE={} APPLY_FUNDING_FEE={} CAPITAL_START={}",
                Configs.RATE_FEE, Configs.APPLY_SLIPPAGE, Configs.SLIPPAGE_RATE,
                Configs.APPLY_FUNDING_FEE, BudgetManagerSimple.getInstance().balanceBasic);

        if (dumpPath != null && !dumpPath.isBlank()) {
            dumpOut = new java.io.DataOutputStream(new java.io.BufferedOutputStream(
                    new java.io.FileOutputStream(dumpPath), 1 << 20));
            LOG.warn("*** FS_DUMP_CLOSES={} — CHE DO DUMP, KHONG GIAO DICH. Ghi (tDec:long, symId:short, close:float) moi GIO ***", dumpPath);
        }
        long day = startTime;
        while (day <= endTime) {
            TreeMap<Long, KlineObjectSimple[]> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(day);
            if (time2Tickers == null || time2Tickers.isEmpty()) {
                throw new RuntimeException("FAIL-FAST: khong co ticker ngay "
                        + Utils.normalizeDateYYYYMMDD(day) + " tu Aerospike — DUNG NGAY.");
            }
            nDaysRead++;
            for (Map.Entry<Long, KlineObjectSimple[]> e : time2Tickers.entrySet()) {
                long time = e.getKey();
                processMinute(time, e.getValue());
                // Nhip bao cao GIONG sim goc: log moi nua dem, cap nhat index moi gio.
                if (time % Utils.TIME_DAY == 0) {
                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, activeIdSet(),
                            running, symbol2OrdersEntry, true);
                } else if (time % (60 * Utils.TIME_MINUTE) == 0) {
                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, activeIdSet(),
                            running, symbol2OrdersEntry, false);
                }
            }
            time2Tickers = null;
            day += Utils.TIME_DAY;
        }

        if (dumpOut != null) {
            try { dumpOut.close(); } catch (Exception ignore) { }
            LOG.info("DUMP xong: {} dong -> {}", dumpRows, dumpPath);
        }
        // Dong tat ca lenh con mo tai gia cuoi cung da thay (mark-to-market).
        for (short id : new ArrayList<>(trackedIds)) {
            if (running[id] != null) {
                OrderTargetInfoTest o = running[id];
                o.priceTP = o.lastPrice;
                o.status = OrderTargetStatus.STOP_LOSS_OVERTIME;
                finishOrder(id, o.timeUpdate, o.lastPrice, "MTM_END");
            }
        }

        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        bm.updateBalance(endTime, allOrderDone, activeIdSet(), running, symbol2OrdersEntry, false);

        report(t0);
        if (writeStorage) writeOutputs();
    }

    private void processMinute(long time, KlineObjectSimple[] symbol2Ticker) {
        nMinutes++;
        List<Cand> cands = new ArrayList<>(4);
        for (short id : trackedIds) {
            KlineObjectSimple tk = symbol2Ticker[id];
            if (tk == null || tk.priceClose <= 0) continue;

            // --- 1. Cap nhat lenh dang chay + thoat theo gio ---
            OrderTargetInfoTest run = running[id];
            if (run != null) {
                run.updatePriceByKlineSimple(tk);
                if (exitAtMinute[id] > 0 && time >= exitAtMinute[id]) {
                    run.priceTP = tk.priceClose;
                    run.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                    finishOrder(id, time, tk.priceClose, "TIME_EXIT");
                }
            }

            // --- 2. Limit cho khop (chi tu t_dec tro di) ---
            Pending pd = pendingLimit[id];
            if (pd != null) {
                if (time >= pd.expireAt) {
                    pendingLimit[id] = null;
                    nNoFill++;
                } else if (time >= pd.tDec && tk.minPrice <= pd.p0) {
                    // 🔴 TRAN VON PHAI CHAN O DAY (luc KHOP), khong phai luc tao lenh cho.
                    //    Bug 2026-09-01: chan o allocate() => nhieu limit cung treo (moi cai deu thay
                    //    con cho vi chua cai nao khop) roi khop het => 181 vi the dong thoi tren tran 6
                    //    => don bay 18x => chay tai khoan 2025-10-11. Chan tai fill moi la rang buoc that.
                    if (countRunning() * wPerTrade + wPerTrade > capTotal + 1e-6f) {
                        nSkipCapFill++;
                        pendingLimit[id] = null;
                    } else {
                        openOrder(id, time, pd, tk);
                        pendingLimit[id] = null;
                    }
                }
            }

            // --- 3. Gop nen 15m; nen dong o phut co (time % 900000 == 840000) ---
            Bar15 b = pending[id];
            long barTs = time - Math.floorMod(time, BAR_MS);
            if (b.barTs != barTs) {
                b.barTs = barTs;
                b.open = tk.priceOpen;
                b.high = tk.maxPrice;
                b.low = tk.minPrice;
                b.minutes = 0;
            }
            if (tk.maxPrice > b.high) b.high = tk.maxPrice;
            if (tk.minPrice < b.low) b.low = tk.minPrice;
            b.close = tk.priceClose;
            b.minutes++;

            if (Math.floorMod(time, BAR_MS) == BAR_MS - MIN_MS) {
                long tDec = barTs + BAR_MS;
                ring[id].push(b.close, tDec);
                if (dumpOut != null) {
                    if (tDec % 3600_000L == 0) {
                        try {
                            dumpOut.writeLong(tDec); dumpOut.writeShort(id); dumpOut.writeFloat(b.close);
                            dumpRows++;
                        } catch (Exception e) { throw new RuntimeException(e); }
                    }
                } else {
                    Cand c = evaluateSignal(id, barTs, tDec, b.close);
                    if (c != null) cands.add(c);
                }
                b.barTs = -1;
            }
        }
        if (!cands.isEmpty()) allocate(cands);
    }

    /**
     * CAP PHAT VON cho cac ung vien CUNG mot moc dong nen.
     *
     * <p>FS_PRED_RANK=true: xep theo score TANG DAN (score = 1-P(win), THAP = model noi TOT)
     * roi moi cap von -> khi tran 60% chi con vai cho, uu tien lenh model cham diem tot nhat.
     * Mac dinh (false): giu thu tu symbolId nhu cac lan chay truoc (FIFO) de so sanh duoc.
     */
    private void allocate(List<Cand> cands) {
        if (predRank) {
            cands.sort((a, b) -> {
                float sa = Float.isNaN(a.score) ? missingScore() : a.score;
                float sb = Float.isNaN(b.score) ? missingScore() : b.score;
                int c = Float.compare(sa, sb);
                return c != 0 ? c : Short.compare(a.id, b.id);   // tie-break tat dinh
            });
        }
        for (Cand c : cands) {
            if (scoreMax != null) {
                float sc = Float.isNaN(c.score) ? missingScore() : c.score;
                if (sc > scoreMax) { nSkipScoreMax++; continue; }
            }
            if (running[c.id] != null) { nSkipRunning++; continue; }
            if (countRunning() * wPerTrade + wPerTrade > capTotal + 1e-6f) { nSkipCap++; continue; }
            if (btc30Min != null) {
                Float btc30 = btcReturn30d();
                if (btc30 == null || btc30 <= btc30Min) { nSkipRegime++; continue; }
            }
            Pending pd = new Pending();
            pd.triggerBarTs = c.barTs;
            pd.tDec = c.tDec;
            pd.p0 = c.p0;
            pd.r24 = c.r24;
            pd.sigma = c.sigma;
            pd.score = c.score;
            pd.expireAt = c.tDec + MAKER_WIN_MIN * MIN_MS;
            pendingLimit[c.id] = pd;
        }
    }

    private float missingScore() {
        if ("last".equals(predMissing)) return Float.MAX_VALUE;
        if ("first".equals(predMissing)) return -Float.MAX_VALUE;
        return predMedian;
    }

    /** Tinh r24 + sigma tren vong dem, kich hoat khi r24 < -3*sigma. Khong nhin nen tuong lai. */
    private Cand evaluateSignal(short id, long barTs, long tDec, float p0) {
        Ring r = ring[id];
        Float cPrev = r.back(K);            // close cach 96 nen
        if (cPrev == null || cPrev <= 0) return null;
        float r24 = p0 / cPrev - 1f;

        // sigma = std cua chuoi r24 tren WSIG nen gan nhat (bao gom nen hien tai), toi thieu MINP mau
        int avail = Math.min(r.n, r.close.length) - K;
        if (avail < MINP) return null;
        int m = Math.min(avail, WSIG);
        double sum = 0, sum2 = 0;
        int cnt = 0;
        for (int j = 0; j < m; j++) {
            Float a = r.back(j);
            Float bb = r.back(j + K);
            if (a == null || bb == null || bb <= 0) continue;
            double v = a / bb - 1.0;
            sum += v;
            sum2 += v * v;
            cnt++;
        }
        if (cnt < MINP) return null;
        double mean = sum / cnt;
        double var = (sum2 - cnt * mean * mean) / (cnt - 1);   // ddof=1, khop pandas .std()
        if (var <= 0) return null;
        float sigma = (float) Math.sqrt(var);
        if (!(r24 < -NSIG * sigma)) return null;

        nSignal++;
        if (tDec - lastSignalTs[id] < DEDUP_MS) { nSkipDedup++; return null; }
        lastSignalTs[id] = tDec;

        Cand c = new Cand();
        c.id = id;
        c.barTs = barTs;
        c.tDec = tDec;
        c.p0 = p0;
        c.r24 = r24;
        c.sigma = sigma;
        c.score = (predDir == null) ? Float.NaN : scoreAt(id, tDec);
        if (Float.isNaN(c.score)) nScoreMiss++; else nScoreHit++;
        return c;
    }

    // ===================== NAP SELECTOR PRED =====================
    /**
     * Doc predict_wf_*.bin (26B/ban ghi: >q ts, h symId, 4f P(win) cho 4 horizon).
     * File chua P(win) THO; score = 1 - P(win) (dao dau y het WfoDataset.buildFundingFromWfFiles)
     * -> score THAP = model noi TOT = engine uu tien.
     */
    private void loadPred() throws Exception {
        Map<String, Short> csvMap = new HashMap<>();
        try (java.io.BufferedReader br = new java.io.BufferedReader(new java.io.FileReader(predMapCsv))) {
            String line;
            while ((line = br.readLine()) != null) {
                String[] a = line.split(",");
                if (a.length < 2) continue;
                String x = a[0].trim(), y = a[1].trim();
                try {
                    if (x.matches("-?\\d+")) csvMap.put(y.toUpperCase(), Short.parseShort(x));
                    else if (y.matches("-?\\d+")) csvMap.put(x.toUpperCase(), Short.parseShort(y));
                } catch (Exception ignore) { }
            }
        }
        // doi chieu map CSV vs SimpleSymbolMapper (Aerospike) — lech = doc nham coin, phai biet
        int same = 0, diff = 0;
        for (String sym : symbols) {
            Short c = csvMap.get(sym);
            short a = SimpleSymbolMapper.getInstance().getId(sym);
            if (c == null) continue;
            if (c == a) same++; else { diff++; LOG.warn("[FS-PRED] symId LECH {}: csv={} aerospike={}", sym, c, a); }
        }
        LOG.info("[FS-PRED] doi chieu symId csv-vs-aerospike: khop {} / lech {}", same, diff);

        Map<Short, String> want = new HashMap<>();
        for (String sym : symbols) if (csvMap.containsKey(sym)) want.put(csvMap.get(sym), sym);

        Map<Short, java.util.ArrayList<long[]>> acc = new HashMap<>();
        File[] files = new File(predDir).listFiles(
                (d, n) -> n.startsWith("predict_wf_") && n.endsWith(".bin"));
        if (files == null || files.length == 0)
            throw new IllegalStateException("Khong thay predict_wf_*.bin trong " + predDir);
        java.util.Arrays.sort(files);
        long total = 0, kept = 0, nanCnt = 0;
        for (File f : files) {
            try (DataInputStream in = new DataInputStream(
                    new BufferedInputStream(new FileInputStream(f), 1 << 20))) {
                long n = f.length() / 26;
                if (f.length() % 26 != 0)
                    throw new IllegalStateException(f.getName() + ": khong chia het 26B");
                for (long i = 0; i < n; i++) {
                    long ts = in.readLong();
                    short sid = in.readShort();
                    float p0 = in.readFloat(), p1 = in.readFloat(), p2 = in.readFloat(), p3 = in.readFloat();
                    total++;
                    if (!want.containsKey(sid)) continue;
                    float pwin = predHorizon == 0 ? p0 : predHorizon == 1 ? p1 : predHorizon == 2 ? p2 : p3;
                    if (Float.isNaN(pwin)) { nanCnt++; continue; }
                    acc.computeIfAbsent(sid, k -> new java.util.ArrayList<>())
                       .add(new long[]{ts, Float.floatToRawIntBits(1.0f - pwin)});
                    kept++;
                }
            }
        }
        java.util.ArrayList<Float> allScores = new java.util.ArrayList<>();
        for (Map.Entry<Short, java.util.ArrayList<long[]>> e : acc.entrySet()) {
            java.util.ArrayList<long[]> l = e.getValue();
            l.sort((a, b) -> Long.compare(a[0], b[0]));
            short aid = SimpleSymbolMapper.getInstance().getId(want.get(e.getKey()));
            long[] ts = new long[l.size()];
            float[] sc = new float[l.size()];
            for (int i = 0; i < l.size(); i++) {
                ts[i] = l.get(i)[0];
                sc[i] = Float.intBitsToFloat((int) l.get(i)[1]);
                if (i % 97 == 0) allScores.add(sc[i]);
            }
            predTs[aid] = ts;
            predScore[aid] = sc;
        }
        java.util.Collections.sort(allScores);
        if (!allScores.isEmpty()) predMedian = allScores.get(allScores.size() / 2);
        int nSym = 0;
        for (short id : trackedIds) if (predTs[id] != null) nSym++;
        LOG.info("[FS-PRED] {} file | {} ban ghi doc, {} giu ({} NaN bo) | {}/{} coin co pred | trung vi score {}",
                files.length, total, kept, nanCnt, nSym, symbols.length, String.format("%.4f", predMedian));
        for (short id : trackedIds) {
            if (predTs[id] == null) { LOG.warn("[FS-PRED] KHONG CO pred: {}", id2Symbol.get(id)); continue; }
            long[] t = predTs[id];
            LOG.info("[FS-PRED]   {} n={} {} -> {}", id2Symbol.get(id), t.length,
                    Utils.normalizeDateYYYYMMDDHHmm(t[0]), Utils.normalizeDateYYYYMMDDHHmm(t[t.length - 1]));
        }
    }

    /** score tai moc quyet dinh: ban ghi gan nhat <= tDec, khong qua han. NaN neu khong co. */
    private float scoreAt(short id, long tDec) {
        long[] t = predTs[id];
        if (t == null) return Float.NaN;
        int lo = 0, hi = t.length - 1, k = -1;
        while (lo <= hi) {
            int mid = (lo + hi) >>> 1;
            if (t[mid] <= tDec) { k = mid; lo = mid + 1; } else hi = mid - 1;
        }
        if (k < 0 || tDec - t[k] > predStaleMs) return Float.NaN;
        return predScore[id][k];
    }

    private Float btcReturn30d() {
        Ring r = ring[btcId];
        Float now = r.back(0);
        Float then = r.back(BARS_30D);
        if (now == null || then == null || then <= 0) return null;
        return now / then - 1f;
    }

    private Set<Short> activeIdSet() {
        Set<Short> s = new HashSet<>();
        for (short id : trackedIds) if (running[id] != null) s.add(id);
        return s;
    }

    private int countRunning() {
        int c = 0;
        for (short id : trackedIds) if (running[id] != null) c++;
        return c;
    }

    // ===================== MO / DONG LENH =====================
    private void openOrder(short id, long time, Pending pd, KlineObjectSimple tk) {
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        float balance = bm.balanceBasic + bm.profit;
        float notional = balance * wPerTrade;
        if (notional <= 0) return;
        float qty = notional / pd.p0;

        String sym = id2Symbol.get(id);
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.POSITION_RUNNING, pd.p0, null,
                qty, Configs.LEVERAGE_ORDER, sym, time, time, OrderSide.BUY);
        o.firstEntryPrice = pd.p0;
        o.clusterFirstLegTime = time;
        o.marketLevelChange = MarketLevelChange.FORCED_SELLER;
        o.minPrice = tk.priceClose;
        o.maeLow = tk.minPrice;
        o.maePeak = tk.maxPrice;
        o.lastPrice = tk.priceClose;
        o.rateChange = pd.r24;
        o.tickerOpen = tk;
        running[id] = o;
        List<OrderTargetInfoTest> legs = new ArrayList<>(1);
        legs.add(o);
        symbol2OrdersEntry[id] = legs;
        exitAtMinute[id] = pd.tDec + HOLD_MS - MIN_MS;   // nen 1m DONG dung t_dec + 24h

        Trade t = new Trade();
        t.symbol = sym;
        t.triggerBarTs = pd.triggerBarTs;
        t.tDec = pd.tDec;
        t.fillTime = time;
        t.fillMinute = (int) ((time - pd.tDec) / MIN_MS);
        t.p0 = pd.p0;
        t.entry = pd.p0;
        t.r24 = pd.r24;
        t.sigma = pd.sigma;
        t.z = pd.r24 / pd.sigma;
        t.score = pd.score;
        t.qty = qty;
        runningTrade[id] = t;

        bm.counterOrderCreated.incrementAndGet();
        bm.marginRunning += o.calMargin();
        nFilled++;
        int cr = countRunning();
        if (cr > maxConcurrent) maxConcurrent = cr;
    }

    private void finishOrder(short id, long time, float exitPx, String why) {
        OrderTargetInfoTest o = running[id];
        if (o == null) return;
        o.timeUpdate = time;
        o.priceTP = exitPx;
        o.lastPrice = exitPx;
        o.computeFundingOnClose();

        putOrderDone(o);
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        bm.updatePnl(o);
        bm.marginRunning -= o.calMargin();

        Trade t = runningTrade[id];
        if (t != null) {
            t.exitTime = time;
            t.exitPx = exitPx;
            t.funding = o.calFundingFee();
            t.grossRate = exitPx / t.entry - 1f;
            trades.add(t);
        }
        running[id] = null;
        runningTrade[id] = null;
        symbol2OrdersEntry[id] = null;
        exitAtMinute[id] = -1;
        nClosed++;
        if (!"TIME_EXIT".equals(why)) LOG.info("[FS-CLOSE-{}] {} tai {}", why, o.symbol,
                Utils.normalizeDateYYYYMMDDHHmm(time));
    }

    /** Copy nguyen quy uoc khoa cua sim goc (tranh ghi de khi trung khoa). */
    private void putOrderDone(OrderTargetInfoTest order) {
        long key = -order.timeUpdate - allOrderDone.size();
        while (allOrderDone.containsKey(key)) key--;
        allOrderDone.put(key, order);
    }

    // ===================== BAO CAO + GHI FILE =====================
    private void report(long t0) {
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        LOG.info("=========== FORCED-SELLER — TOM TAT ===========");
        LOG.info("  ngay doc Aerospike     : {}", nDaysRead);
        LOG.info("  phut xu ly             : {}", nMinutes);
        LOG.info("  tin hieu tho           : {}", nSignal);
        LOG.info("    bo do trung 24h      : {}", nSkipDedup);
        LOG.info("    bo do dang co lenh   : {}", nSkipRunning);
        LOG.info("    bo do cham tran von  : {}", nSkipCap);
        LOG.info("    bo do loc regime     : {}", nSkipRegime);
        LOG.info("  co score / thieu score : {} / {}", nScoreHit, nScoreMiss);
        LOG.info("    bo do score > nguong : {}", nSkipScoreMax);
        LOG.info("    bo do TRAN luc khop  : {}", nSkipCapFill);
        LOG.info("  limit KHONG khop       : {}", nNoFill);
        int capMax = (int) Math.floor(capTotal / wPerTrade + 1e-6);
        LOG.info("  vi the dong thoi TOI DA: {}  (tran cho phep {})  {}", maxConcurrent, capMax,
                maxConcurrent > capMax ? "*** VI PHAM TRAN - KET QUA KHONG DUNG ***" : "OK");
        LOG.info("  lenh da khop           : {}", nFilled);
        LOG.info("  lenh da dong           : {}", nClosed);
        if (!trades.isEmpty()) {
            double g = 0;
            int win = 0;
            for (Trade t : trades) { g += t.grossRate; if (t.grossRate > 0) win++; }
            LOG.info("  bien THO TB moi lenh   : {}%", String.format("%+.4f", 100.0 * g / trades.size()));
            LOG.info("  ty le lenh tho duong   : {}%", String.format("%.1f", 100.0 * win / trades.size()));
        }
        LOG.info("  von dau                : {}", bm.balanceBasic);
        LOG.info("  loi nhuan (co phi/truot/funding theo Configs) : {}", bm.profit);
        LOG.info("  so du cuoi             : {}", bm.balanceBasic + bm.profit);
        LOG.info("  tong phi               : {}   funding: {}", bm.fee, bm.totalFundingFee);
        LOG.info("  chay het               : {} ms", System.currentTimeMillis() - t0);
    }

    private void writeOutputs() {
        try {
            new File("storage").mkdirs();
            Storage.writeObject2File("storage/OrderTestDone.data", allOrderDone);
            Storage.writeObject2File("storage/BalanceIndex.data",
                    BudgetManagerSimple.getInstance().balanceIndex);
            TraceOrderDone.printOrderTestDone("storage/printDone.csv", allOrderDone);
            try (BufferedWriter w = new BufferedWriter(new FileWriter("storage/FS_TRADES.csv"))) {
                w.write("symbol,trigger_bar_ts,t_dec,fill_time,fill_minute,exit_time,p0,entry,exit_px,"
                        + "r24,sigma,z,score,qty,funding_usd,gross_rate,net_usd\n");
                for (Trade t : trades) {
                    w.write(String.format(Locale.ROOT,
                            "%s,%d,%d,%d,%d,%d,%.10g,%.10g,%.10g,%.8f,%.8f,%.6f,%.6f,%.10g,%.6f,%.8f,%.6f%n",
                            t.symbol, t.triggerBarTs, t.tDec, t.fillTime, t.fillMinute, t.exitTime,
                            t.p0, t.entry, t.exitPx, t.r24, t.sigma, t.z, t.score, t.qty, t.funding, t.grossRate,
                            t.qty * (t.exitPx - t.entry) - t.qty * t.entry * Configs.RATE_FEE
                                    - (Configs.APPLY_SLIPPAGE ? t.qty * t.entry * Configs.SLIPPAGE_RATE * 2f : 0f)
                                    - t.funding));
                }
            }
            LOG.info("Da ghi storage/OrderTestDone.data, BalanceIndex.data, printDone.csv, FS_TRADES.csv ({} lenh)",
                    trades.size());
        } catch (Exception e) {
            LOG.error("Loi ghi storage", e);
        }
    }
}
