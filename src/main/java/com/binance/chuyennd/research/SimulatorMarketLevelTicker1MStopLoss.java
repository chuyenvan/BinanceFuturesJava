/*
 */
package com.binance.chuyennd.research;

import ai.onnxruntime.OrtException;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.BacktestIntegrityGuard;
import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.bigchange.test.TraceOrderDone;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.*;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.text.ParseException;
import java.util.*;

/**
 * @author pc
 */
public class SimulatorMarketLevelTicker1MStopLoss {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorMarketLevelTicker1MStopLoss.class);
    public static final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";
    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;
    public TreeMap<Long, MarketDataObject> time2MarketData;
    public TreeMap<Long, AiPredictionData> predictionMap;
    public TreeMap<Long, long[]> time2SymbolPred;
    public AIRejectFilter aiRejectFilter;
    public Boolean is50PercentOrderLoss = null;

    // Đếm số lần circuit breaker kích hoạt (reset theo mỗi instance Simulator). Runner đọc để báo cáo.
    public long breakerMarginHaltCount = 0;
    public long breakerDcaCapCount = 0;

    // === ABLATION (Bước 2) — bộ đếm để báo cáo + tỉ lệ pass cho placebo C ===
    public long ablationSignalSeen = 0;   // số tín hiệu leg-đầu đi qua cổng filter (A/C)
    public long ablationPassCount = 0;    // số PASS thực của A (để tính passRate cho C)
    /**
     * E0 (2026-07-30) ENTRY-UNIVERSE: moi admission qua gate ∩ rank-K, CHI populate khi
     * {@link Configs#ENTRY_UNIVERSE_DUMP} bat (di kem {@link Configs#GATE_COUNT_ONLY}).
     * Moi phan tu = {@code {ts, symbolId, floatBits(score), floatBits(priceClose), levelChangeOrdinal}}.
     * Mac dinh list rong, khong ai doc -> khong anh huong PnL/parity.
     */
    public final java.util.List<long[]> entryUniverse = new java.util.ArrayList<>();
    public long ablationPlaceboPass = 0;  // số PASS ngẫu nhiên của C
    public float ablationPassRate = 0.5f; // xác suất pass cho C — set TỪ passRate đo ở A

    // === TASK-134 PROBE (thuần đếm, KHÔNG đổi PnL): phân loại entry theo NGUỒN để đo đóng góp funding-selector ===
    public long entryBigDown = 0;        // leg đầu từ BIG_DOWN (market-signal bắt-đáy)
    public long entryPredictSymbol = 0;  // leg đầu từ PREDICT_SYMBOL_TRADE (funding-selector)
    public long entryDcaLevel = 0;       // DCA nhồi
    public long entryOther = 0;          // còn lại (SMALL_* nếu bật)
    public long predictSymbolRejectedGate = 0; // coin funding-selector bị gate REJECT (không vào lệnh)

    // =================================================================
    // 🔥 SỬ DỤNG MẢNG CỐ ĐỊNH O(1) ĐỂ LOẠI BỎ AUTOBOXING RÁC CỦA HASHMAP
    // =================================================================
    @SuppressWarnings("unchecked")
    public List<OrderTargetInfoTest>[] symbol2OrdersEntry = new ArrayList[1000];
    public OrderTargetInfoTest[] symbol2OrderRunning = new OrderTargetInfoTest[1000];

    // 🔥 TỐI ƯU TUYỆT ĐỐI: Dùng mảng nguyên thủy thay cho HashSet<Short>
    // Loại bỏ hoàn toàn Autoboxing khi gọi add(), remove() hay contains()
    public short[] activeRunningIds = new short[1000]; // Tối đa 100 lệnh chạy cùng lúc
    public int activeRunningCount = 0;

    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        LOG.info("Start with TICKER_SOURCE: {} | AEROSPIKE_READ_CLUSTER: {}", Configs.TICKER_SOURCE, Configs.AEROSPIKE_READ_CLUSTER);
        SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
        test.initData();
        // TASK-112: WRITE_SIM_STORAGE default FALSE. Box nao muon ghi storage/OrderTestDone.data thi
        //   dat WRITE_SIM_STORAGE=true trong config.properties — KHONG hardcode o day (override cung
        //   cho MOI box, khong revert duoc bang config).
        // TASK (2026-07-09): mac dinh chay toi "bay gio" (system time) se FAIL-FAST neu ticker
        // live chua ingest kip (data lag binh thuong cua feed song, vai ngay gan nhat thieu).
        // Cho phep override qua SIM_END_DATE (yyyyMMdd) de chay toi moc data da biet TOT, khong
        // tat guard FAIL-FAST. Bo trong env -> giu nguyen hanh vi cu (System.currentTimeMillis()).
        Long endTime = System.currentTimeMillis();
        String simEndDate = System.getenv("SIM_END_DATE");
        if (simEndDate != null && !simEndDate.isBlank()) {
            endTime = Utils.sdfFile.parse(simEndDate).getTime();
            LOG.info("🔀 SIM_END_DATE override: chay toi {}", simEndDate);
        }
        test.simulatorWithInitEntry(startTime, endTime);
        Thread.sleep(5000);
        System.exit(1);
    }

    public void simulatorWithInitEntry(Long startTime, Long endTime) throws ParseException {
        // 🔒 NÚT CHẶN LIÊM CHÍNH DUY NHẤT: mọi backtest (HPO master, WFO, 7 engine khác,
        // hay chạy main() trực tiếp) đều đi qua hàm này. Đặt guard ở đây nên KHÔNG engine
        // nào bypass được — không cần ai nhớ gọi assert ở từng engine.
        BacktestIntegrityGuard.assertProductionGrade();

        long timeSimulator = System.currentTimeMillis();
        LOG.info("=== 🚀 BẮT ĐẦU SIMULATE TỪ {} ĐẾN {} ===", Utils.normalizeDateYYYYMMDDHHmm(startTime), Utils.normalizeDateYYYYMMDDHHmm(endTime));
        LOG.info("[SELECTOR-CFG] INVERT={} TOPN={} SCORE_MAX={} SELECTOR_ONLY_ENTRY={} (TOPN=-1 => uncapped/byte-identical)",
                Configs.SELECTOR_INVERT, Configs.SELECTOR_TOPN, Configs.SELECTOR_SCORE_MAX, Configs.SELECTOR_ONLY_ENTRY);
        LOG.info("[RANK-CFG] SELECTOR_RANK_TOPK={} SELECTOR_RANK_OFFSET={} (TOPK<=0 => rank OFF/absolute; OFFSET=0 => [0..K) byte-identical)",
                Configs.SELECTOR_RANK_TOPK, Configs.SELECTOR_RANK_OFFSET);

        // LEVER-B: log knob sizing khi khac default (chi log 1 lan dau run — KHONG trong hot loop).
        if (Configs.SIZE_MULT != 1.0f || Configs.MAX_CONCURRENT_ORDERS != 40) {
            LOG.info("⚙️ LEVER-B sizing ACTIVE: SIZE_MULT={} MAX_CONCURRENT_ORDERS={} (default 1.0/40)",
                    Configs.SIZE_MULT, Configs.MAX_CONCURRENT_ORDERS);
        }

        // [PROFILE] đo tách thời gian ĐỌC kline vs SIMULATE (đo không đoán)
        long readMs = 0, simMs = 0;
        int dayCount = 0;
        while (true) {
            TreeMap<Long, KlineObjectSimple[]> time2Tickers;
            // TASK-112: nguồn ticker TƯỜNG MINH theo config per-box TICKER_SOURCE (aerospike|file) + fail-fast.
            // Khối này CỐ Ý nằm NGOÀI try-catch nuốt-lỗi phía dưới: thiếu config / thiếu data phải DỪNG NGAY,
            // không được in lỗi rồi chạy tiếp (nguồn ZERO_TRADES âm thầm đã vô hiệu full WFO 17 window 2026-07-02).
            long _tRead = System.currentTimeMillis();
            if ("aerospike".equals(Configs.TICKER_SOURCE)) {
                time2Tickers = Configs.USE_SMART_CACHE
                        // WFO/HPO: cache nén theo ngày trong RAM (N sample cùng window dùng chung, đọc DB 1 lần/ngày)
                        ? com.binance.chuyennd.ai_ml.data.HPOSmartCache.getDataShort(startTime)
                        : DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(startTime);
            } else if ("file".equals(Configs.TICKER_SOURCE)) {
                // TASK-142 (rework compact-lossless): file-ticker ho tro RAM-cache theo ngay. USE_SMART_CACHE=true
                // → nen ngay sang CompactFileDay (GIU totalUsdt + startTime=key, ~5-6GB/window thay vi exact-object
                // 16-24GB → tranh OOM Oracle 23GB), N sample cung window dung chung: doc+gunzip 1 lan/ngay/window,
                // cac lan sau dung lai tu nen. Ket qua Y HET duong doc thang. USE_SMART_CACHE=false → doc thang (mac dinh).
                time2Tickers = Configs.USE_SMART_CACHE
                        ? com.binance.chuyennd.ai_ml.data.HPOSmartCache.getDataShortFromFile(startTime)
                        : KaggleDataLoader.loadDailyTickersShort(startTime);
            } else {
                throw new IllegalStateException("Thieu/sai TICKER_SOURCE trong config.properties (hien tai: "
                        + Configs.TICKER_SOURCE + ") — them dong: TICKER_SOURCE=aerospike (doc Aerospike) hoac TICKER_SOURCE=file (Kaggle).");
            }
            if (time2Tickers == null || time2Tickers.isEmpty()) {
                throw new RuntimeException("FAIL-FAST: khong co ticker ngay " + Utils.normalizeDateYYYYMMDD(startTime)
                        + " tu nguon " + Configs.TICKER_SOURCE + " — DUNG NGAY, khong chay tiep (tranh ZERO_TRADES am tham).");
            }
            readMs += System.currentTimeMillis() - _tRead;

            long _tSim = System.currentTimeMillis();
            try {
                if (time2Tickers.size() >= 1440) {
                    dayCount++;
                    for (Map.Entry<Long, KlineObjectSimple[]> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        try {
                            long startTimeRun = System.currentTimeMillis();
                            KlineObjectSimple[] symbol2Ticker = entry.getValue();

                            // STATIC RANK: bỏ HistoryManager (CoinRank đọc tier tĩnh) -> cắt overhead/phút + bỏ phụ thuộc totalUsdt.
                            if (!Configs.WFO_STATIC_RANK) {
                                HistoryManager.getInstance().updateHistoryArray(symbol2Ticker);
                            }

                            // --- BƯỚC 2: UPDATE ACTIVE ORDERS THEO ARRAY NGUYÊN THỦY O(1) ---
                            if (activeRunningCount > 0) {
                                // Copy mảng để tránh lỗi ConcurrentModification khi dời mảng vì lệnh chốt
                                short[] currentIds = Arrays.copyOf(activeRunningIds, activeRunningCount);

                                for (short runningSymbolId : currentIds) {
                                    KlineObjectSimple ticker = symbol2Ticker[runningSymbolId];
                                    if (ticker != null) {
                                        startUpdateOldOrderTrading(time, runningSymbolId, ticker);
                                    }
                                }

                                // 🔎 maxDD THẬT (ĐO LƯỜNG, KHÔNG quyết định): MỖI TICK tính tổng unrealized
                                //    danh mục theo bar.low của từng cụm đang chạy rồi theo dõi đáy. Dùng bar.low
                                //    để bắt đáy trong nến — đây là METRIC nên KHÔNG phải look-ahead. Chạy SONG
                                //    SONG unProfitMin cũ (xây từ profitMin/minPrice, lấy mẫu theo giờ), không thay thế.
                                float unrealAtLow = 0f;
                                float notionalAtLow = 0f;   // TASK-119: Σ qty·bar.low (maintenance margin, report-only)
                                for (int i = 0; i < activeRunningCount; i++) {
                                    short id = activeRunningIds[i];
                                    OrderTargetInfoTest cluster = symbol2OrderRunning[id];
                                    KlineObjectSimple tk = symbol2Ticker[id];
                                    if (cluster != null && cluster.priceEntry != null && cluster.quantity != null
                                            && tk != null && tk.minPrice > 0) {
                                        unrealAtLow += cluster.quantity * (tk.minPrice - cluster.priceEntry);
                                        notionalAtLow += cluster.quantity * tk.minPrice;
                                    }
                                }
                                BudgetManagerSimple.getInstance().updateTrueUnrealizedMin(unrealAtLow, time);
                                // 🟡 TASK-119 (REPORT-ONLY): maxDD_mtm + MARGIN_CALL song song — KHÔNG đổi hành vi cũ.
                                BudgetManagerSimple.getInstance().updateEquityMtm(unrealAtLow, notionalAtLow, time);
                            }

                            logByProcessTime(startTimeRun, "Done update order", time);
                            startTimeRun = System.currentTimeMillis();

                            MarketDataObject marketData = time2MarketData.get(time);
                            Set<Short> symbolLocked = new HashSet<>();
                            MarketLevelChange levelChange = null;
                            AiPredictionData predict = predictionMap.get(time);

                            if (predict != null && marketData != null) {
                                levelChange = MarketBigChangeDetector.getMarketStatus1M(marketData.rateDownAvg, marketData.rateUpAvg, marketData.rateDown15MAvg);

                                if (levelChange != null) {
                                    Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;

                                    // Chép ID đang chạy vào Set để khóa
                                    for (int i = 0; i < activeRunningCount; i++) symbolLocked.add(activeRunningIds[i]);

                                    if (levelChange.equals(MarketLevelChange.SMALL_UP) ||
                                            levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)) {
                                        numberOrder = numberOrder / 2;
                                    }

                                    Set<Short> symbol2BUY = new HashSet<>();
                                    TreeMap<Float, Short> predict2Symbol = extractPredict2Symbol(time2SymbolPred.get(time));

                                    symbol2BUY.addAll(MarketBigChangeDetector.getTopSymbolArray(numberOrder,
                                            symbol2Ticker, symbolLocked, predict2Symbol));

                                    Map<Short, OrderTargetInfoTest> activeOrderMap = getActiveOrderMap();
                                    List<Short> symbolDcaLevel = DcaProcessor.getDCA(levelChange, time,
                                            BudgetManagerSimple.getInstance().getBudget(), activeOrderMap);

                                    // SELECTOR_ONLY_ENTRY=1 -> bo qua leg market-signal Best-N (FOMO), co lap selector.
                                    // Default false -> chay leg nay -> byte-identical.
                                    if (!Configs.SELECTOR_ONLY_ENTRY) {
                                        for (short symbolId : symbol2BUY) {
                                            KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                            if (Utils.isTickerAvailable(ticker)) {
                                                createOrderBUY(symbolId, ticker, levelChange, time2MarketData.get(time), null);
                                            }
                                        }
                                    }
                                    // SHORT cam martingale: ENABLE_SHORT bat -> TAT DCA (nhoi lenh). Cluster short
                                    // side=SELL, chen leg BUY DCA se lam hong side/quantity cua cum. Mac dinh
                                    // ENABLE_SHORT=false -> DCA chay nhu cu -> byte-identical.
                                    if (!Configs.ENABLE_SHORT) {
                                        for (short symbolId : symbolDcaLevel) {
                                            KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                            if (Utils.isTickerAvailable(ticker)) {
                                                createOrderBUY(symbolId, ticker, MarketLevelChange.DCA_LEVEL1, time2MarketData.get(time), null);
                                            }
                                        }
                                    }
                                }
                            }

                            logByProcessTime(startTimeRun, "Done market data", time);
                            startTimeRun = System.currentTimeMillis();

                            if (marketData != null) {
                                if (!Configs.ENABLE_SHORT && MarketBigChangeDetector.isDcaAlt(marketData.rateDown15MAvg, marketData.rateDownAvg, marketData.rateUpAvg)) {
                                    // SHORT cam martingale: ENABLE_SHORT bat -> khong nhoi DCA-loss-big.
                                    // Default OFF -> nhanh chay nhu cu (byte-identical).
                                    List<Short> symbolDcaLossBig = DcaProcessor.getDCA(null, time, BudgetManagerSimple.getInstance().getBudget(), getActiveOrderMap());
                                    for (short symbolId : symbolDcaLossBig) {
                                        KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                        if (Utils.isTickerAvailable(ticker)) {
                                            createOrderBUY(symbolId, ticker, MarketLevelChange.DCA_LEVEL1, time2MarketData.get(time), null);
                                        }
                                    }
                                    logByProcessTime(startTimeRun, "Done dca big", time);
                                    startTimeRun = System.currentTimeMillis();
                                }

                                // 🔥 BƯỚC 3: FUNDING FEE SIÊU TỐC (ĐÃ PRE-CALCULATE SORT SẴN) 🔥
                                // TASK (2026-07-11) §2 DCA-primary: cho phep TAT sleeve PREDICT_SYMBOL_TRADE de do
                                // rieng sleeve mean-reversion (DCA_LEVEL1 + BIG_DOWN). Mac dinh false = hanh vi cu.
                                long[] symbol2Pred = Configs.DISABLE_PREDICT_SYMBOL ? null : time2SymbolPred.get(time);
                                if (symbol2Pred != null) {
                                    float maxThres = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * Configs.AI_DYNAMIC_MAX;
                                    // MAX-DEPLOYMENT: SELECTOR_SCORE_MAX>=0 ep TRUC TIEP tran score (admit p6 thap hon).
                                    // Default -1f (OFF) -> giu maxThres cu -> byte-identical.
                                    if (Configs.SELECTOR_SCORE_MAX >= 0f) maxThres = Configs.SELECTOR_SCORE_MAX;

                                    // ALPHA-TEST (fix): so best-N vs worst-N, CUNG SO LUONG N, cung gate.
                                    // mang sort thap->cao, symbolPred=1-p6 (thap=tot). N = so coin qua nguong.
                                    // INVERT=false -> BEST-N (N dau) = HANH VI CU byte-identical.
                                    // INVERT=true  -> WORST-N (N cuoi = symbolPred cao nhat = te nhat), cung N.
                                    int nPass = 0;
                                    for (long e : symbol2Pred) {
                                        if (Float.intBitsToFloat((int) e) > maxThres) break;
                                        nPass++;
                                    }
                                    // WORST-N / BEST-N CAP (2026-07-22): SELECTOR_TOPN>0 -> chi mo N candidate.
                                    //  INVERT=1 (Worst-N): lay N coin TE-nhat = tail toan mang, KHONG gate boi nPass
                                    //    -> khop proxy Kaggle (bottom-N moi nen, khong good-gate) de N-sweep 3/5/8 co y nghia
                                    //    (gate maxThres siet chat -> nPass thuong nho, neu cap boi nPass thi N vo hieu).
                                    //  INVERT=0 (Best-N): lay N coin TOT-nhat trong so nPass qua gate.
                                    //  Default SELECTOR_TOPN=-1 (OFF) -> nSel=nPass -> BYTE-IDENTICAL voi ban cu.
                                    java.util.List<Long> chosenCands = new java.util.ArrayList<>();
                                    // SELECTOR_OFFSET (2026-07-24): bo qua [off] candidate o cuc bien truoc khi lay N.
                                    //  Default SELECTOR_OFFSET=0 -> off=0 -> index nhu ban cu -> BYTE-IDENTICAL.
                                    int selOffset = Configs.SELECTOR_OFFSET;
                                    if (Configs.SELECTOR_RANK_TOPK > 0) {
                                        // RANK-BASED TOP-K (2026-07-28, Probe A go/no-go): BO QUA absolute maxThres/nPass,
                                        //  chon K coin score THAP nhat per timestamp (symbol2Pred sort tang -> k phan tu dau).
                                        //  Tu-chuan-hoa theo regime: khong starve luc yeu (nPass=0 van admit K), khong flood
                                        //  luc manh. selOffset ap dung tren mang day du (bo qua off coin tot nhat truoc khi lay K).
                                        int nSel = Math.min(Configs.SELECTOR_RANK_TOPK, symbol2Pred.length);
                                        // OFFSET-SWEEP (2026-07-28): bo qua SELECTOR_RANK_OFFSET coin TOT nhat (top dau, score
                                        //  thap nhat) truoc khi lay K -> symbol2Pred[off .. off+K). Default 0 -> [0..K) byte-identical.
                                        //  Clamp: off <= poolSize - nSel de tranh IndexOutOfBounds khi pool mong.
                                        int off = Math.min(Configs.SELECTOR_RANK_OFFSET, Math.max(0, symbol2Pred.length - nSel));
                                        for (int i = 0; i < nSel; i++) chosenCands.add(symbol2Pred[off + i]);
                                        if (LOG.isDebugEnabled()) {
                                            LOG.debug("SELECTOR_RANK_TOPK k={} nSel={} poolSize={} nPassAbs={} maxThres={} off={} rankOffsetCfg={}",
                                                    Configs.SELECTOR_RANK_TOPK, nSel, symbol2Pred.length, nPass, maxThres, off, Configs.SELECTOR_RANK_OFFSET);
                                        }
                                    } else if (Configs.SELECTOR_INVERT) {
                                        int nSel = (Configs.SELECTOR_TOPN > 0)
                                                ? Math.min(Configs.SELECTOR_TOPN, symbol2Pred.length) : nPass;
                                        // clamp: index thap nhat dung = length-1-off-(nSel-1) >= 0
                                        int off = Math.min(selOffset, Math.max(0, symbol2Pred.length - nSel));
                                        for (int i = 0; i < nSel; i++) chosenCands.add(symbol2Pred[symbol2Pred.length - 1 - off - i]);
                                    } else {
                                        int nSel = (Configs.SELECTOR_TOPN > 0)
                                                ? Math.min(nPass, Configs.SELECTOR_TOPN) : nPass;
                                        // clamp: index cao nhat dung = off+(nSel-1) < nPass -> off <= nPass-nSel
                                        int off = Math.min(selOffset, Math.max(0, nPass - nSel));
                                        for (int i = 0; i < nSel; i++) chosenCands.add(symbol2Pred[off + i]);
                                    }
                                    for (long encodedData : chosenCands) {
                                        float symbolPred = Float.intBitsToFloat((int) encodedData);
                                        short targetId = (short) (encodedData >> 32);

                                        if (!isSymbolRunning(targetId)) {
                                            KlineObjectSimple ticker = symbol2Ticker[targetId];
                                            if (Utils.isTickerAvailable(ticker)) {
                                                // ENTRY short (DRAFT, flag-gated): ENABLE_SHORT bat -> DAO CHIEU tin hieu
                                                // selector nay thanh SELL. Moi gate/filter/budget GIU NGUYEN, chi doi chieu.
                                                // Mac dinh ENABLE_SHORT=false -> van createOrderBUY -> byte-identical.
                                                if (Configs.ENABLE_SHORT) {
                                                    createOrderSELL(targetId, ticker, MarketLevelChange.PREDICT_SYMBOL_TRADE, marketData, symbolPred);
                                                } else {
                                                    createOrderBUY(targetId, ticker, MarketLevelChange.PREDICT_SYMBOL_TRADE, marketData, symbolPred);
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            logByProcessTime(startTimeRun, "Done funding fee", time);
                            startTimeRun = System.currentTimeMillis();

                            if (time % Utils.TIME_DAY == 0) {
                                // TASK-112: bỏ nhánh HPO-mode cũ (chỉ khác isPrintBalance=log + System.gc, KHÔNG đổi PnL)
                                // — hợp nhất về nhánh thường (log mỗi nửa đêm) mà WFO/HPO worker vốn chạy → GATE không đổi số.
                                if (Utils.isFirstDayOfYear(time)) {
                                    System.gc();
                                }
                                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, getActiveIdSet(), symbol2OrderRunning, symbol2OrdersEntry, true);
                            } else {
                                if (time % (60 * Utils.TIME_MINUTE) == 0) {
                                    short[] currentIds = Arrays.copyOf(activeRunningIds, activeRunningCount);
                                    for (Short symbolId : currentIds) {
                                        KlineObjectSimple ticker = symbol2Ticker[symbolId];
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            updateSymbolDeListed(symbolId, time);
                                        }
                                    }
                                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, getActiveIdSet(), symbol2OrderRunning, symbol2OrdersEntry, false);
                                }
                            }
                            logByProcessTime(startTimeRun, "Done budget data", time);
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                        is50PercentOrderLoss = null;
                    }
                } else {
                    // Ngày thiếu phút (<1440) SKIP lặng — semantics CŨ giữ nguyên (đổi sẽ phá GATE), chỉ warn rõ hơn.
                    LOG.warn("Date data error: {} — chi co {} phut (<1440), SKIP ngay nay", Utils.normalizeDateYYYYMMDD(startTime), time2Tickers.size());
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            simMs += System.currentTimeMillis() - _tSim;
            time2Tickers = null;

            Long finalStartTime1 = startTime;
            startTime += Utils.TIME_DAY;

            if (startTime > endTime) {
                BudgetManagerSimple.getInstance().updateBalance(finalStartTime1, allOrderDone, getActiveIdSet(), symbol2OrderRunning, symbol2OrdersEntry, false);
                break;
            }
        }

        // add all order running to done
        for (int i = 0; i < activeRunningCount; i++) {
            short id = activeRunningIds[i];
            List<OrderTargetInfoTest> orderRunningList = symbol2OrdersEntry[id];
            if (orderRunningList != null) {
                // === FUNDING (Bước 3) — cụm còn mở cuối kỳ: gán phí cụm vào leg đầu (như closeOrder).
                boolean fundingAssigned = false;
                for (OrderTargetInfoTest orderInfo : orderRunningList) {
                    orderInfo.lastPrice = symbol2OrderRunning[id].lastPrice;
                    orderInfo.priceTP = orderInfo.lastPrice;
                    orderInfo.minPrice = symbol2OrderRunning[id].minPrice;
                    orderInfo.maeLow = symbol2OrderRunning[id].maeLow;   // 🔎 đáy THẬT cụm (đo MAE)
                    orderInfo.timeUpdate = symbol2OrderRunning[id].timeUpdate;
                    if (!fundingAssigned) {
                        orderInfo.time2FundingFee = symbol2OrderRunning[id].time2FundingFee;
                        fundingAssigned = true;
                    }
                    allOrderDone.put(-orderInfo.timeUpdate - allOrderDone.size(), orderInfo);
                }
            }
        }

        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);
        int finalYear = cal.get(Calendar.YEAR);
        BudgetManagerSimple.getInstance().balanceIndex.year2UnrealizedPnl.put(finalYear, 0f);

        // TASK-112: ghi storage theo config tường minh WRITE_SIM_STORAGE (default FALSE — trước đây box local mặc định GHI).
        if (Configs.WRITE_SIM_STORAGE) {
            try {
                Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
                Storage.writeObject2File("storage/BalanceIndex.data", BudgetManagerSimple.getInstance().balanceIndex);
                TraceOrderDone.printOrderTestDone("storage/printDone.csv", allOrderDone);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        long _tot = readMs + simMs;
        LOG.info("[PROFILE] days={} readMs={} simMs={} (read={}% sim={}%) totalLoopMs={}",
                dayCount, readMs, simMs,
                _tot > 0 ? (100 * readMs / _tot) : 0, _tot > 0 ? (100 * simMs / _tot) : 0, _tot);
        Utils.printMemoryUse(System.currentTimeMillis() - timeSimulator);
    }

    // =========================================================================
    // 🔥 CÁC HÀM XỬ LÝ MẢNG NGUYÊN THỦY O(1) SIÊU TỐC KHÔNG SINH OBJECT RÁC
    // =========================================================================
    private void addActiveRunningId(short id) {
        // Kiểm tra tránh trùng
        for (int i = 0; i < activeRunningCount; i++) {
            if (activeRunningIds[i] == id) return;
        }
        if (activeRunningCount < activeRunningIds.length) {
            activeRunningIds[activeRunningCount++] = id;
        }
    }

    private void removeActiveRunningId(short id) {
        for (int i = 0; i < activeRunningCount; i++) {
            if (activeRunningIds[i] == id) {
                // Đổi vị trí với phần tử cuối để xóa O(1)
                activeRunningIds[i] = activeRunningIds[activeRunningCount - 1];
                activeRunningCount--;
                return;
            }
        }
    }

    private boolean isSymbolRunning(short id) {
        for (int i = 0; i < activeRunningCount; i++) {
            if (activeRunningIds[i] == id) return true;
        }
        return false;
    }

    private Set<Short> getActiveIdSet() {
        Set<Short> set = new HashSet<>();
        for (int i = 0; i < activeRunningCount; i++) set.add(activeRunningIds[i]);
        return set;
    }

    private Map<Short, OrderTargetInfoTest> getActiveOrderMap() {
        Map<Short, OrderTargetInfoTest> activeMap = new HashMap<>();
        for (int i = 0; i < activeRunningCount; i++) {
            short id = activeRunningIds[i];
            activeMap.put(id, symbol2OrderRunning[id]);
        }
        return activeMap;
    }

    private List<OrderTargetInfoTest> getActiveOrderList() {
        List<OrderTargetInfoTest> list = new ArrayList<>(activeRunningCount);
        for (int i = 0; i < activeRunningCount; i++) {
            list.add(symbol2OrderRunning[activeRunningIds[i]]);
        }
        return list;
    }

    private Integer counterOrderRunning() {
        int counter = 0;
        for (int i = 0; i < activeRunningCount; i++) {
            short id = activeRunningIds[i];
            if (symbol2OrdersEntry[id] != null) {
                counter += symbol2OrdersEntry[id].size();
            }
        }
        return counter;
    }

    // =========================================================================

    private TreeMap<Float, Short> extractPredict2Symbol(long[] encodedDataArray) {
        TreeMap<Float, Short> predict2Symbol = new TreeMap<>();
        if (encodedDataArray != null) {
            for (long encodedData : encodedDataArray) {
                short symbolId = (short) (encodedData >> 32);
                float pred = Float.intBitsToFloat((int) encodedData);
                predict2Symbol.put(pred, symbolId);
            }
        }
        return predict2Symbol;
    }

    private void logByProcessTime(Long startTimeRun, String msg, Long time) {
        // Log per-tick (>20ms) đã TẮT: gọi 5 lần/tick × hàng triệu tick + GC spike trong HPO = spam nặng.
        // Cần profiling thì mở lại dòng dưới (hoặc nâng ngưỡng lên vài giây để chỉ bắt tick treo thật).
        // long duration = (System.currentTimeMillis() - startTimeRun);
        // if (duration > 5000) LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), msg, duration);
    }

    public void updateSymbolDeListed(short symbolId, Long time) {
        OrderTargetInfoTest order = symbol2OrderRunning[symbolId];
        if (order != null) {
            if (order.timeUpdate < time - 2 * Utils.TIME_DAY) {
                order.status = OrderTargetStatus.STOP_LOSS_DONE;
                order.priceTP = order.lastPrice;
                closeOrder(symbolId, order);
            }
        }
    }

    public void initData() throws IOException, ParseException {
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();

        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        int numberMinutes = System.currentTimeMillis() - startTime > 0 ? (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_MINUTE) : 0;

        LOG.info("📥 Đang tải dữ liệu vào RAM...");
        // TASK (2026-07-09): doc offline bin (WfoDataset) neu WFO_DATA_DIR set -> khop dung dataset
        // da va (funding leak-free predict_wf_*.bin) dang dung cho WFO, thay vi scan Aerospike song
        // (co the lech set/thoi diem). Bo trong env -> giu nguyen hanh vi Aerospike cu (khong doi
        // behavior mac dinh, khong anh huong cac lan chay truoc).
        String wfoDataDir = System.getenv("WFO_DATA_DIR");
        if (wfoDataDir != null && !wfoDataDir.isBlank()) {
            LOG.info("🔀 OFFLINE BIN: doc market/pred/funding tu WfoDataset tai {}", wfoDataDir);
            try {
                com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset ds =
                        com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset.load(wfoDataDir);
                time2MarketData = ds.market;
                predictionMap = ds.pred;
                time2SymbolPred = ds.funding;
            } catch (Exception e) {
                throw new RuntimeException("Doc WfoDataset tu WFO_DATA_DIR=" + wfoDataDir + " FAIL", e);
            }
        } else {
            time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
            predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
            // A/B SELECTOR: nếu set env SEL_BACKTEST_SET → dùng selector v2 (cột horizon SEL_BACKTEST_HORIZON_IDX:
            //   0=4h,1=12h,2=24h,3=72h) thay funding cũ. Cùng format long[] nên phần engine còn lại KHÔNG đổi.
            //   Bỏ trống env → giữ nguyên funding cũ (baseline). Cho phép chạy lần lượt 4 horizon để so A/B.
            String selSet = System.getenv("SEL_BACKTEST_SET");
            if (selSet != null && !selSet.isBlank()) {
                int hIdx = Integer.parseInt(System.getenv().getOrDefault("SEL_BACKTEST_HORIZON_IDX", "1")); // mặc định 12h
                String[] hName = {"4h", "12h", "24h", "72h"};
                LOG.info("🔀 A/B SELECTOR: dùng set={} horizonIdx={} ({})", selSet, hIdx,
                        hIdx >= 0 && hIdx < 4 ? hName[hIdx] : "?");
                time2SymbolPred = DataManagerAerospikeFloatSim.getAllSelectorPredictionsPrimitiveFromAerospike(selSet, hIdx);
            } else {
                LOG.info("🔀 BASELINE: dùng funding cũ (set {}).", DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_FUNDING_PRED);
                time2SymbolPred = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
            }
        }
        // 3. CHẠY PRE-CALCULATE (SORT SẴN FUNDING FEE MỘT LẦN DUY NHẤT)
        preprocessFundingData(time2SymbolPred);
        aiRejectFilter = new AIRejectFilter();

        SimpleSymbolMapper.getInstance().init();

        Utils.printMemoryUsage("Load time2FundingPre (time2SymbolPred)");
        LOG.info("✅ TẤT CẢ DỮ LIỆU ĐÃ SẴN SÀNG. BẮT ĐẦU SIMULATE...");
    }

    private void startUpdateOldOrderTrading(Long time, short symbolId, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning[symbolId];
        if (orderMulti != null) {
            if (orderMulti.timeStart <= ticker.startTime) {
                orderMulti.updatePriceByKlineSimple(ticker);
                // === SHORT (DRAFT, flag-gated) — MAC DINH ENABLE_SHORT=false -> nhanh nay KHONG chay ->
                //     long path byte-identical. Chi lenh SELL di vao nhanh short (hard-SL + time-stop).
                if (Configs.ENABLE_SHORT && OrderSide.SELL.equals(orderMulti.side)) {
                    orderMulti.updateStatusShort(ticker);
                    if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                        closeOrder(symbolId, orderMulti);
                    }
                    return;
                }
                // === HARD-SL BLANKET (env SIM_HARD_SL_PCT) — SL tren GIA ENTRY DAU TIEN (firstEntryPrice,
                //     bat bien qua DCA — KHONG averaged). Chay TRUOC cong profit-arm + TRUOC nhanh DCA nap
                //     them: du lenh dang lo thuan (priceSL==null) van bi cat. Chi long (short da return o tren).
                //     Default HARD_SL_PCT=0 => nhanh KHONG chay => byte-identical.
                if (Configs.HARD_SL_PCT > 0f && orderMulti.firstEntryPrice != null
                        && ticker.minPrice <= orderMulti.firstEntryPrice * (1f - Configs.HARD_SL_PCT)) {
                    float slTrigger = orderMulti.firstEntryPrice * (1f - Configs.HARD_SL_PCT);
                    orderMulti.status = OrderTargetStatus.STOP_LOSS_DONE;
                    // BOOKING-FIX mirror (nhu updateStatusNew/updateStatusShort): resting-stop. Ca gap-down
                    //   (open<trigger) fill=open (khong ban tren open); neu da co priceSL sau hon thi lay min.
                    float fill = Math.min(slTrigger, ticker.priceOpen);
                    if (orderMulti.priceSL != null) fill = Math.min(fill, orderMulti.priceSL);
                    orderMulti.priceTP = fill;
                    closeOrder(symbolId, orderMulti);
                    return;
                }
                if (ticker.maxPrice >= orderMulti.priceEntry * (1 + Configs.RATE_PROFIT_STOP_MARKET)
                        || orderMulti.priceSL != null) {
                    Float predReturn15M  = getPredReturn15MForTradingStop(time);
                    orderMulti.updateStatusNew(predReturn15M , ticker);
                    if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                        closeOrder(symbolId, orderMulti);
                    } else {
                        orderMulti.updateTPSL(predReturn15M , ticker);
                    }
                }
            }
        }
    }

    private Float getPredReturn15MForTradingStop(Long time) {
        AiPredictionData predict = predictionMap.get(time);
        if (predict == null) {
            return 0f;
        } else {
            return predict.predReturn15M;
        }
    }

    private void closeOrder(short symbolId, OrderTargetInfoTest orderMulti) {
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry[symbolId];
        if (orders != null) {
            // === FUNDING (Bước 3) — tính 1 LƯỢT cho cả cụm tại thời điểm đóng (timeStart leg đầu → timeUpdate).
            //     PnL tính trên TỪNG leg (Σ calTp); funding tích ở CỤM → gán toàn bộ vào DUY NHẤT leg đầu để Σ
            //     không cộng trùng; các leg khác giữ rỗng.
            orderMulti.computeFundingOnClose();
            boolean fundingAssigned = false;
            for (OrderTargetInfoTest order : orders) {
                order.timeUpdate = orderMulti.timeUpdate;
                order.status = orderMulti.status;
                order.priceTP = orderMulti.priceTP;
                order.minPrice = orderMulti.minPrice;
                order.maeLow = orderMulti.maeLow;   // 🔎 chép đáy THẬT cụm sang từng leg (đo MAE)
                order.lastPrice = orderMulti.lastPrice;
                if (!fundingAssigned) {
                    order.time2FundingFee = orderMulti.time2FundingFee;   // toàn bộ phí cụm vào leg đầu
                    fundingAssigned = true;
                }

                allOrderDone.put(-order.timeUpdate - allOrderDone.size(), order);
                BudgetManagerSimple.getInstance().updatePnl(order);
            }
        }

        // Xóa sổ lệnh khỏi mảng O(1)
        symbol2OrdersEntry[symbolId] = null;
        symbol2OrderRunning[symbolId] = null;
        removeActiveRunningId(symbolId);

        BudgetManagerSimple.getInstance().marginRunning -= orderMulti.calMargin();
    }

    private OrderTargetInfoTest mergeOrder(List<OrderTargetInfoTest> orders, KlineObjectSimple ticker,
                                           OrderTargetInfoTest prevRunning) {
        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        float quantity = 0f;
        float margin = 0f;
        for (OrderTargetInfoTest orderInfo : orders) {
            time2Order.put(orderInfo.timeStart, orderInfo);
            margin += orderInfo.priceEntry * orderInfo.quantity;
            quantity += orderInfo.quantity;
        }
        float entry = margin / quantity;

        OrderTargetInfoTest orderResult = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity, Configs.LEVERAGE_ORDER,
                time2Order.lastEntry().getValue().symbol, time2Order.lastEntry().getKey(), time2Order.lastEntry().getKey(), orders.get(0).side);

        orderResult.minPrice = ticker.priceClose;
        // HARD-SL: mang theo GIA ENTRY DAU TIEN cua cum (leg dau) — BAT BIEN qua DCA, KHONG averaged.
        //   Lay tu leg dau (firstEntryPrice da set luc mo); fallback priceEntry leg dau neu chua set.
        OrderTargetInfoTest firstLeg = time2Order.firstEntry().getValue();
        orderResult.firstEntryPrice = (firstLeg.firstEntryPrice != null) ? firstLeg.firstEntryPrice : firstLeg.priceEntry;
        // 🔎 maeLow: KHÔNG reset-lên khi nhồi. Mang theo đáy THẬT của cụm cũ (nếu có), lần đầu = giá vào
        //    leg đầu, rồi hạ thêm nếu nến hiện tại thủng sâu hơn. Bảo toàn đáy từ leg đầu để MAE chuẩn.
        float firstLegEntry = time2Order.firstEntry().getValue().priceEntry;
        float carriedLow = (prevRunning != null && prevRunning.maeLow != null) ? prevRunning.maeLow : firstLegEntry;
        orderResult.maeLow = Math.min(carriedLow, ticker.minPrice);
        orderResult.lastPrice = ticker.priceClose;
        orderResult.lastEntry = orders.get(orders.size() - 1).lastEntry;
        orderResult.rateChange = orders.get(orders.size() - 1).rateChange;
        orderResult.tickerOpen = time2Order.lastEntry().getValue().tickerOpen;
        orderResult.marketLevelChange = time2Order.lastEntry().getValue().marketLevelChange;

        // === FUNDING (Bước 3) — tính 1 LƯỢT khi đóng, KHÔNG carry state qua merge nữa.
        // computeFundingOnClose quét settlement trong (clusterFirstLegTime, timeUpdate]. Lưu RIÊNG leg-đầu vào
        // clusterFirstLegTime — TUYỆT ĐỐI KHÔNG đụng timeStart (=leg-cuối, là tham chiếu logic mở/đóng;
        // đổi nó làm rò funding vào giao dịch → +69 lệnh, vỡ GATE). timeStart giữ nguyên gốc = leg-cuối.
        orderResult.clusterFirstLegTime = time2Order.firstEntry().getKey();

        return orderResult;
    }

    public void createOrderBUY(short symbolId, KlineObjectSimple ticker, MarketLevelChange levelChange,
                               MarketDataObject marketData, Float symbolPred) {
        // Long entry — delegate vao loi chung createOrder(BUY,...). Giu nguyen chu ky de moi call-site
        // khong doi. BUY -> hanh vi CU byte-identical (chi them 1 stack-frame, khong doi output).
        createOrder(OrderSide.BUY, symbolId, ticker, levelChange, marketData, symbolPred);
    }

    /**
     * ENTRY short (SELL) — DRAFT 2026-07-18, flag-gated. Nhan ban logic createOrderBUY nhung DAO CHIEU
     * lenh: side=SELL, priceEntry=gia close (giong long). Chi duoc goi khi {@link Configs#ENABLE_SHORT}
     * bat, tai diem selector PREDICT_SYMBOL_TRADE (xem vong lap simulate). Moi gate/filter/breaker/budget/tier
     * GIU NGUYEN — chi doi CHIEU lenh. Order ket qua co side=SELL nen exit-side updateStatusShort chay.
     * Mac dinh ENABLE_SHORT=false -> khong bao gio goi -> engine long-only byte-identical.
     *
     * @param symbolId    id coin
     * @param ticker      kline hien tai (priceClose = gia vao)
     * @param levelChange nguon tin hieu (thuc te chi PREDICT_SYMBOL_TRADE cho short draft)
     * @param marketData  snapshot thi truong tai thoi diem vao (co the null)
     * @param symbolPred  diem selector (dung cho AI filter dynamic)
     */
    public void createOrderSELL(short symbolId, KlineObjectSimple ticker, MarketLevelChange levelChange,
                                MarketDataObject marketData, Float symbolPred) {
        createOrder(OrderSide.SELL, symbolId, ticker, levelChange, marketData, symbolPred);
    }

    /**
     * Loi tao lenh dung chung cho ca 2 CHIEU (mot bo nao — tranh drift long/short). Toan bo
     * gate/filter/breaker/budget/tier GIU NGUYEN; chi field {@code side} cua OrderTargetInfoTest phu thuoc
     * tham so {@code side}. Goi voi OrderSide.BUY -> hanh vi cu byte-identical.
     *
     * @param side chieu lenh (BUY long / SELL short)
     */
    private void createOrder(OrderSide side, short symbolId, KlineObjectSimple ticker, MarketLevelChange levelChange,
                             MarketDataObject marketData, Float symbolPred) {

        if (levelChange != MarketLevelChange.DCA_LEVEL1) {
            if (is50PercentOrderLoss == null)
                is50PercentOrderLoss = MarketBigChangeDetector.is50PercentOrderLoss(getActiveOrderList(), ticker.startTime);
            if (is50PercentOrderLoss) {
                return;
            }
        }


        AiPredictionData predict = predictionMap.get(ticker.startTime);
        // 🧠 #10 PARITY (TASK-030, một bộ não): LIVE createOrderBuyRequest reject khi prediction==null
        // (DetectEntrySignal2TradeNormal). TRƯỚC ĐÂY sim bỏ qua filter khi predict==null → VẪN vào lệnh "mù"
        // → P&L sim≠live ở mốc thiếu pred. Nay sim cũng reject pred==null. (CONFIG_VERSION v8→v9.)
        if (predict == null) {
            return;
        }
        if (!levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            // === ABLATION (Bước 2): A=giữ filter | B=bỏ filter (PASS hết) | C=placebo random ===
            // CHỈ thay quyết định PASS/REJECT của leg đầu; DCA/exit/budget giữ nguyên để cô lập đóng góp AI.
            if ("B".equals(Configs.ABLATION_MODE)) {
                // no-AI: mọi tín hiệu PASS, không gọi filter
            } else if ("C".equals(Configs.ABLATION_MODE)) {
                // placebo: PASS ngẫu nhiên cùng XÁC SUẤT pass thực nghiệm của A (ablationPassRate),
                // deterministic theo seed+timestamp để tái lập.
                ablationSignalSeen++;
                java.util.Random r = new java.util.Random(Configs.ABLATION_SEED ^ ticker.startTime);
                if (r.nextFloat() >= ablationPassRate) {
                    return; // reject ngẫu nhiên
                }
                ablationPlaceboPass++;
            } else {
                // A (control): filter AI như thường
                AIRejectFilter.FilterResult filterResult = null;
                if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) {
                    filterResult = aiRejectFilter.checkSignalDynamic(predict, symbolPred);
                }
                if (filterResult == null)
                    filterResult = aiRejectFilter.checkSignal(predict);

                ablationSignalSeen++;
                if (filterResult.decision == AIRejectFilter.FilterDecision.REJECT) {
                    if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) predictSymbolRejectedGate++; // TASK-134
                    return;
                }
                ablationPassCount++;
            }
        }

        if (Configs.GATE_COUNT_ONLY) {
            // E0 (2026-07-30) ENTRY-UNIVERSE DUMP: ghi lai admission da qua gate ∩ rank-K.
            //  Diem nay la SAU filter AI (ablationPassCount++) va TRUOC breaker/budget/createOrder
            //  -> dung tap "tin hieu he thong CHAP NHAN neu von khong gioi han".
            //  Chi chay khi ENTRY_UNIVERSE_DUMP=1 (mac dinh OFF -> khong ton RAM, hanh vi khong doi).
            if (Configs.ENTRY_UNIVERSE_DUMP) {
                entryUniverse.add(new long[]{
                        ticker.startTime,
                        symbolId,
                        Float.floatToIntBits(symbolPred != null ? symbolPred : Float.NaN),
                        Float.floatToIntBits(ticker.priceClose),   // primitive float, khong can null-check
                        levelChange != null ? levelChange.ordinal() : -1
                });
            }
            return; // count-only: da dem gate admission, KHONG tao order
        }

        // 🛑 CIRCUIT BREAKER — chỉ tác động khi BREAKER_MODE != OFF. Tác động tầng DCA/margin,
        // KHÔNG đụng entry filter, KHÔNG force-close (long-only): chỉ DỪNG MỞ / DỪNG NHỒI.
        if (!"OFF".equals(Configs.BREAKER_MODE)) {
            // (a) MARGIN halt: chặn MỌI lệnh mới (entry + DCA) khi tổng margin/vốn >= ngưỡng
            if ("MARGIN".equals(Configs.BREAKER_MODE) || "BOTH".equals(Configs.BREAKER_MODE)) {
                float bal = BudgetManagerSimple.getInstance().balanceBasic;
                if (bal > 0 && BudgetManagerSimple.getInstance().marginRunning / bal >= Configs.BREAKER_MARGIN_HALT) {
                    breakerMarginHaltCount++;
                    return;
                }
            }
            // (b) DCA depth cap: symbol ĐÃ có cụm mở và cụm đang lỗ sâu => ngừng NHỒI (giữ cụm)
            if ("DCA".equals(Configs.BREAKER_MODE) || "BOTH".equals(Configs.BREAKER_MODE)) {
                OrderTargetInfoTest running = symbol2OrderRunning[symbolId];
                if (running != null && running.priceEntry != null && running.priceEntry > 0) {
                    float clusterDd = (ticker.priceClose - running.priceEntry) / running.priceEntry;
                    if (clusterDd <= Configs.BREAKER_CLUSTER_DD_MAX) {
                        breakerDcaCapCount++;
                        return;
                    }
                }
            }
        }

        // [ADR-0008 bước 3 — ĐÃ GỠ cap %vốn/cụm 2026-06-28] Đo trên backtest 5 năm: cap per-cluster veto
        // 0-8 lần (CAP10 veto 0 → PnL/DD y hệt OFF) vì budget đã phân tán qua hàng trăm cụm nhỏ, không cụm nào
        // đạt 5-10% tổng vốn. Lá chắn THẬT là BREAKER_MARGIN_HALT tổng (DD -58.6%→-42.5%, maxMargR 0.99→0.71).
        // Scenario LUNA 1-coin cứu được chỉ vì cô lập (toàn vốn dồn 1 cụm) — KHÔNG đại diện danh mục. Giữ
        // LunaDcaScenario làm tài liệu vì-sao-vô-dụng. Hướng Bước 3: chốt MARGIN_HALT, tinh chỉnh ngưỡng.

        // TASK-134 PROBE: phân loại nguồn leg vừa PASS mọi cổng (thuần đếm)
        if (levelChange == MarketLevelChange.BIG_DOWN) entryBigDown++;
        else if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) entryPredictSymbol++;
        else if (levelChange == MarketLevelChange.DCA_LEVEL1) entryDcaLevel++;
        else entryOther++;

        Float entry = ticker.priceClose;
        Integer leverage = Configs.LEVERAGE_ORDER;

        long currentTs = ticker.startTime;
        CoinRankManager.CoinTier myTier = CoinRankManager.getInstance().getCoinTier(symbolId, currentTs);
        if (myTier == CoinRankManager.CoinTier.TIER_3_SHITCOIN) {
            if (levelChange == MarketLevelChange.DCA_LEVEL1) {
                return;
            }
        }

        Float marginRunning = BudgetManagerSimple.getInstance().marginRunning;
        Float balanceBasic = BudgetManagerSimple.getInstance().balanceBasic;
        Float budget = BudgetManagerSimple.getInstance().getBudget();

        budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange);

        if (budget == null) {
            return;
        }

        float tierMultiplier = CoinRankManager.getInstance().getBudgetMultiplier(symbolId);
        budget *= tierMultiplier;

        // === LEVER-B SIZE (env SIZE_MULT, default 1.0 = byte-identical) — nhan budget-per-order SAU khi da
        //     qua HET guard o tren (managerBudget throttle marginRatio + BREAKER_MARGIN_HALT + tier). Guard
        //     chong-am-von GIU NGUYEN: marginRunning phinh nhanh hon -> cham BREAKER_MARGIN_HALT + tran 0.99
        //     SOM hon (chan mo moi), KHONG bypass. Chi scale SIZE trong khuon budget. Nhanh chi chay khi
        //     SIZE_MULT!=1 -> default byte-identical (khong cham budget).
        if (Configs.SIZE_MULT != 1.0f) {
            budget *= Configs.SIZE_MULT;
        }

        // === SIZE-BY-CONFIDENCE soft-gate (env CONF_SIZE_MODE, default 0=OFF -> byte-identical) ===
        //   Nhan CUNG voi SIZE_MULT, SAU khi da qua HET guard chong-am-von (managerBudget + tier +
        //   BREAKER_MARGIN_HALT). Guard GIU NGUYEN: chi scale SIZE trong khuon budget. p6 = 1-symbolPred
        //   tinh PER-ORDER (symbolPred truyen tuoi tu selector loop, KHONG stale). symbolPred==null (cac
        //   call-site khong-selector, vd BIG_DOWN/DCA) -> BO QUA -> byte-identical cho cac leg do.
        if (Configs.CONF_SIZE_MODE == 1 && symbolPred != null) {
            float p6 = 1f - symbolPred;
            budget *= Configs.confFactor(p6);
        }

        String symbolStr = SimpleSymbolMapper.getInstance().getSymbol(symbolId);
        Float quantity = Utils.calQuantityTest(budget, leverage, entry, symbolStr);

        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry,
                null, quantity, leverage, symbolStr, ticker.startTime,
                ticker.startTime, side);

        order.minPrice = entry;
        order.maeLow = entry;   // 🔎 đáy THẬT khởi tạo = giá vào leg (đo lường MAE)
        order.lastEntry = entry;
        order.lastPrice = entry;
        order.firstEntryPrice = entry;   // HARD-SL: gia entry THAT cua leg nay; leg dau => gia entry dau cum (bat bien qua DCA)
        order.tickerOpen = ticker;
        order.marketLevelChange = levelChange;

        if (marketData != null) {
            order.marketData = marketData;
        }
        order.predict = predict;
        order.symbolPred = symbolPred;

        List<OrderTargetInfoTest> orders = symbol2OrdersEntry[symbolId];
        if (orders == null) {
            orders = new ArrayList<>();
            symbol2OrdersEntry[symbolId] = orders;
        }
        orders.add(order);

        // ENTRY-MATCH PROBE (env WFO_LOG_ENTRIES=1). Default off = byte-identical.
        if (Configs.WFO_LOG_ENTRIES) {
            LOG.info("ENTRY_DUMP {} {} {}", symbolStr, ticker.startTime, levelChange);
        }

        BudgetManagerSimple.getInstance().counterOrderCreated.incrementAndGet();

        symbol2OrderRunning[symbolId] = mergeOrder(orders, ticker, symbol2OrderRunning[symbolId]);
        addActiveRunningId(symbolId); // Thêm ID vào mảng O(1)

        BudgetManagerSimple.getInstance().updateMaxOrderRunning(counterOrderRunning());
        BudgetManagerSimple.getInstance().marginRunning += order.calMargin();
    }

    public void initDataReady(TreeMap<Long, MarketDataObject> time2MarketData,
                              TreeMap<Long, AiPredictionData> predictionMap, TreeMap<Long, long[]> time2FundingPre,
                              AIRejectFilter aiRejectFilter) throws OrtException {

        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();

        // Khởi tạo Mapper để cache sẵn danh sách symbol
        SimpleSymbolMapper.getInstance().init();

        this.time2MarketData = time2MarketData;
        this.predictionMap = predictionMap;
        this.time2SymbolPred = time2FundingPre;
        // 3. CHẠY PRE-CALCULATE (SORT SẴN FUNDING FEE MỘT LẦN DUY NHẤT)
        preprocessFundingData(this.time2SymbolPred);
        // FUNDING (Bước 3): warm-up cache funding_data NGAY (nạp 1 lần vào RAM) để initFunding/updateFundingFee
        // trong vòng nóng chỉ tra TreeMap, KHÔNG trigger scanAll Aerospike giữa backtest.
        FundingFeeManager.getInstance();
        this.aiRejectFilter = aiRejectFilter;
    }

    // 🔥 HÀM PRE-CALCULATE: Sort mảng theo điểm Float đảm bảo logic 100% như cũ
//    public static void preprocessFundingData(TreeMap<Long, long[]> time2FundingPre) {
//        LOG.info("⚙️ Bắt đầu Pre-calculate (Sort sẵn) dữ liệu Funding Fee...");
//        long start = System.currentTimeMillis();
//        for (long[] preds : time2FundingPre.values()) {
//            if (preds == null || preds.length == 0) continue;
//
//            // Ép sang Object Long để sort bằng Comparator đảm bảo logic không lệch 1 ly
//            Long[] boxed = new Long[preds.length];
//            for (int i = 0; i < preds.length; i++) {
//                boxed[i] = preds[i];
//            }
//
//            Arrays.sort(boxed, (a, b) -> {
//                float valA = Float.intBitsToFloat(a.intValue());
//                float valB = Float.intBitsToFloat(b.intValue());
//                return Float.compare(valA, valB);
//            });
//
//            // Ép ngược lại mảng nguyên thủy
//            for (int i = 0; i < preds.length; i++) {
//                preds[i] = boxed[i];
//            }
//        }
//        LOG.info("✅ Pre-calculate hoàn tất trong {} ms.", (System.currentTimeMillis() - start));
//    }

    // Map funding da sort (theo reference). WFO/HPO dung CHUNG 1 map qua moi sample -> chi sort 1 lan.
    // Tranh re-sort mang DA sort: quicksort pivot=high suy bien O(n^2) (~19s lan dau -> ~147s moi lan sau).
    private static TreeMap<Long, long[]> fundingPreSorted = null;

    // 🔥 PRE-CALCULATE TỐI ƯU HÓA: Dùng Primitive QuickSort & Đa luồng (0 sinh rác Object)
    public static void preprocessFundingData(TreeMap<Long, long[]> time2FundingPre) {
        if (time2FundingPre == null || time2FundingPre == fundingPreSorted) return; // idempotent, ket qua khong doi
        LOG.info("⚙️ Bắt đầu Pre-calculate (Sort sẵn) dữ liệu Funding Fee đa luồng...");
        long start = System.currentTimeMillis();

        // Dùng parallelStream để vắt kiệt 100% các lõi CPU của VPS/Kaggle
        time2FundingPre.values().parallelStream().forEach(preds -> {
            if (preds == null || preds.length <= 1) return;
            // Sort nguyên thủy trực tiếp trên mảng long[]
            quickSortByFloatPred(preds, 0, preds.length - 1);
        });
        fundingPreSorted = time2FundingPre; // danh dau map nay da sort -> cac sample sau bo qua

        LOG.info("✅ Pre-calculate hoàn tất trong {} ms.", (System.currentTimeMillis() - start));
    }

    // 🚀 Thuật toán QuickSort nguyên thủy (Extract 32 bit cuối ra so sánh Float)
    private static void quickSortByFloatPred(long[] arr, int low, int high) {
        if (low < high) {
            int pi = partition(arr, low, high);
            quickSortByFloatPred(arr, low, pi - 1);
            quickSortByFloatPred(arr, pi + 1, high);
        }
    }

    private static int partition(long[] arr, int low, int high) {
        long pivot = arr[high];
        // (int) pivot lấy đúng 32 bit cuối cùng (là giá trị float đã nén)
        float pivotVal = Float.intBitsToFloat((int) pivot);
        int i = (low - 1);

        for (int j = low; j < high; j++) {
            float jVal = Float.intBitsToFloat((int) arr[j]);
            // So sánh float
            if (Float.compare(jVal, pivotVal) <= 0) {
                i++;
                // Swap
                long temp = arr[i];
                arr[i] = arr[j];
                arr[j] = temp;
            }
        }
        // Swap pivot
        long temp = arr[i + 1];
        arr[i + 1] = arr[high];
        arr[high] = temp;
        return i + 1;
    }
}