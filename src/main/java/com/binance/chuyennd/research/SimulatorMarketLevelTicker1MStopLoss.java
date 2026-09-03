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

    // ===== FIX AUDIT 2026-08-01 — F8 + F9: dem su co, KHONG cho im lang =====
    /** F8: so lan key allOrderDone bi dung do (truoc day = so lenh BI GHI DE, mat khoi bao cao). */
    public static int orderKeyCollisions = 0;
    /** F9: so ngay bi SKIP vi <1440 phut (ngay do KHONG kiem SL, KHONG cap nhat maxDD). */
    public static int dayDataErrors = 0;
    /** F9: so exception bi nuot trong vong lap phut/ngay. */
    public static int swallowedExceptions = 0;

    public static void resetAuditCounters() {
        orderKeyCollisions = 0; dayDataErrors = 0; swallowedExceptions = 0;
    }
    public static String auditCountersSummary() {
        return String.format("keyCollisions=%d dayDataErrors=%d swallowedExceptions=%d",
                orderKeyCollisions, dayDataErrors, swallowedExceptions);
    }

    /**
     * F8 FIX — dat lenh vao allOrderDone KHONG BAO GIO ghi de.
     *
     * <p>Cu: {@code put(-timeUpdate - size(), order)}. Neu 2 lenh co {@code t2-t1 == n1-n2} thi key
     * TRUNG => TreeMap.put GHI DE => 1 lenh bien mat khoi allOrderDone (mat ca khoi totalProfit lan
     * tradeCount). Voi timeUpdate tren luoi phut (boi 60000) va size() len toi ~70k, dieu kien
     * {@code n1-n2 = 60000k} la KHA THI.
     *
     * <p>Moi: giu nguyen thu tu sap xep (theo -timeUpdate) nhung do xuong khe trong gan nhat khi dung
     * do. Neu KHONG co dung do => hanh vi y het cu (byte-identical).
     */
    private void putOrderDone(OrderTargetInfoTest order) {
        long key = -order.timeUpdate - allOrderDone.size();
        while (allOrderDone.containsKey(key)) {
            key--;
            orderKeyCollisions++;
        }
        allOrderDone.put(key, order);
    }
    public TreeMap<Long, MarketDataObject> time2MarketData;
    public TreeMap<Long, AiPredictionData> predictionMap;
    public TreeMap<Long, long[]> time2SymbolPred;
    public AIRejectFilter aiRejectFilter;


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
        endTime = com.binance.chuyennd.tradecore.HoldoutSeal.clampEnd(endTime, "SimulatorMarketLevelTicker1MStopLoss.main");
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
        LOG.info("[SELECTOR-CFG] SELECTOR_RANK_TOPK={} SELECTOR_ONLY_ENTRY={} (TOPK<=0 => cutoff tuyet doi)",
                Configs.SELECTOR_RANK_TOPK, Configs.SELECTOR_ONLY_ENTRY);


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
                                    {   // co ENABLE_SHORT da go 2026-09-03 (long-only)
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
                                if (MarketBigChangeDetector.isDcaAlt(marketData.rateDown15MAvg, marketData.rateDownAvg, marketData.rateUpAvg)) {
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
                                long[] symbol2Pred = time2SymbolPred.get(time);
                                if (symbol2Pred != null) {
                                    float maxThres = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * Configs.AI_DYNAMIC_MAX;
                                    int nPass = 0;
                                    for (long e : symbol2Pred) {
                                        if (Float.intBitsToFloat((int) e) > maxThres) break;
                                        nPass++;
                                    }
                                    java.util.List<Long> chosenCands = new java.util.ArrayList<>();
                                    if (Configs.SELECTOR_RANK_TOPK > 0) {
                                        // RANK-BASED TOP-K (2026-07-28, Probe A go/no-go): BO QUA absolute maxThres/nPass,
                                        //  chon K coin score THAP nhat per timestamp (symbol2Pred sort tang -> k phan tu dau).
                                        //  Tu-chuan-hoa theo regime: khong starve luc yeu (nPass=0 van admit K), khong flood
                                        //  luc manh.
                                        int nSel = Math.min(Configs.SELECTOR_RANK_TOPK, symbol2Pred.length);
                                        for (int i = 0; i < nSel; i++) chosenCands.add(symbol2Pred[i]);
                                        if (LOG.isDebugEnabled()) {
                                            LOG.debug("SELECTOR_RANK_TOPK k={} nSel={} poolSize={} nPassAbs={} maxThres={}",
                                                    Configs.SELECTOR_RANK_TOPK, nSel, symbol2Pred.length, nPass, maxThres);
                                        }
                                    } else {
                                        // TOPK<=0 -> cutoff TUYET DOI: moi coin qua tran ung vien (nPass dau mang).
                                        for (int i = 0; i < nPass; i++) chosenCands.add(symbol2Pred[i]);
                                    }
                                    for (long encodedData : chosenCands) {
                                        float symbolPred = Float.intBitsToFloat((int) encodedData);
                                        short targetId = (short) (encodedData >> 32);

                                        if (!isSymbolRunning(targetId)) {
                                            KlineObjectSimple ticker = symbol2Ticker[targetId];
                                            if (Utils.isTickerAvailable(ticker)) {
                                                createOrderBUY(targetId, ticker, MarketLevelChange.PREDICT_SYMBOL_TRADE, marketData, symbolPred);
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
                            // F9 FIX: dem lai, khong cho im lang. Cu chi printStackTrace => phut do bi bo qua
                            // (khong kiem SL, khong cap nhat maxDD) ma backtest van bao "thanh cong".
                            swallowedExceptions++;
                            LOG.error("Nuot exception tai phut {} (lan thu {})",
                                    Utils.normalizeDateYYYYMMDDHHmm(time), swallowedExceptions, e);
                            if (Configs.SIM_FAIL_FAST_ON_DATA_ERROR) {
                                throw new RuntimeException("SIM_FAIL_FAST: exception tai phut " + time, e);
                            }
                        }
                    }
                } else {
                    // Ngày thiếu phút (<1440) SKIP lặng — semantics CŨ giữ nguyên (đổi sẽ phá GATE), chỉ warn rõ hơn.
                    // F9 FIX: dem lai. Ngay bi SKIP = khong tick nao kiem SL + khong cap nhat maxDD
                    // => neu trung ngay sap manh thi vua bo lo stop-out vua bo lo day DD (thien lech duong).
                    dayDataErrors++;
                    LOG.warn("Date data error: {} — chi co {} phut (<1440), SKIP ngay nay (lan thu {})",
                            Utils.normalizeDateYYYYMMDD(startTime), time2Tickers.size(), dayDataErrors);
                    if (Configs.SIM_FAIL_FAST_ON_DATA_ERROR) {
                        throw new RuntimeException("SIM_FAIL_FAST: ngay thieu du lieu " + startTime);
                    }
                }
            } catch (Exception e) {
                if (Configs.SIM_FAIL_FAST_ON_DATA_ERROR && e instanceof RuntimeException
                        && String.valueOf(e.getMessage()).startsWith("SIM_FAIL_FAST")) {
                    throw e;   // khong nuot lai chinh cai minh vua nem
                }
                swallowedExceptions++;
                LOG.error("Nuot exception tai ngay {} (lan thu {})",
                        Utils.normalizeDateYYYYMMDD(startTime), swallowedExceptions, e);
                if (Configs.SIM_FAIL_FAST_ON_DATA_ERROR) {
                    throw new RuntimeException("SIM_FAIL_FAST: exception tai ngay " + startTime, e);
                }
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
                // 🔴 FIX (2026-07-31, audit F3): TRUOC DAY chi CHEP time2FundingFee tu cum ma KHONG BAO GIO
                //    goi computeFundingOnClose() cho cum con mo (no chi duoc goi trong closeOrder).
                //    Hau qua: dung nhom lenh GIU LAU NHAT (no funding nhieu nhat) lai duoc MIEN PHI hoan toan
                //    => thien lech co he thong UNG HO cau hinh giu-lau (vd nang RATE_PROFIT_STOP_MARKET).
                //    computeFundingOnClose() tu return ngay neu APPLY_FUNDING_FEE=false => mac dinh
                //    KHONG doi hanh vi cu (byte-identical khi tat funding).
                OrderTargetInfoTest clusterOpen = symbol2OrderRunning[id];
                if (clusterOpen != null) clusterOpen.computeFundingOnClose();
                boolean fundingAssigned = false;
                for (OrderTargetInfoTest orderInfo : orderRunningList) {
                    orderInfo.lastPrice = symbol2OrderRunning[id].lastPrice;
                    orderInfo.priceTP = orderInfo.lastPrice;
                    orderInfo.minPrice = symbol2OrderRunning[id].minPrice;
                    orderInfo.maeLow = symbol2OrderRunning[id].maeLow;   // 🔎 đáy THẬT cụm (đo MAE)
                    orderInfo.maePeak = symbol2OrderRunning[id].maePeak;   // 🔎 2026-08-02: đỉnh THẬT cụm (fix maePeak null)
                    orderInfo.timeUpdate = symbol2OrderRunning[id].timeUpdate;
                    if (!fundingAssigned) {
                        orderInfo.time2FundingFee = symbol2OrderRunning[id].time2FundingFee;
                        fundingAssigned = true;
                    }
                    putOrderDone(orderInfo);   // F8 FIX: khong ghi de khi key dung do
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
            String selSet = com.binance.chuyennd.tradecore.Cfg.get("SEL_BACKTEST_SET");
            if (selSet != null && !selSet.isBlank()) {
                int hIdx = Integer.parseInt(com.binance.chuyennd.tradecore.Cfg.getOr("SEL_BACKTEST_HORIZON_IDX", "1")); // mặc định 12h
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
                // [2026-09-02] LOSER TIME-STOP (env SIM_LOSER_TIME_STOP_HOURS): cum chua arm SL qua N gio tu leg dau
                //     -> dong tai min(open, close) (khong look-ahead, haircut nhu HARD_SL). TRUOC cong profit-arm.
                //     Default 0 => nhanh khong chay => byte-identical.
                if (Configs.LOSER_TIME_STOP_HOURS > 0 && orderMulti.priceSL == null) {
                    long anchor = orderMulti.clusterFirstLegTime > 0L ? orderMulti.clusterFirstLegTime : orderMulti.timeStart;
                    if (time - anchor > Configs.LOSER_TIME_STOP_HOURS * 3600000L) {
                        orderMulti.status = OrderTargetStatus.STOP_LOSS_DONE;
                        orderMulti.priceTP = Math.min(ticker.priceOpen, ticker.priceClose);
                        closeOrder(symbolId, orderMulti);
                        return;
                    }
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
                order.maePeak = orderMulti.maePeak;   // 🔎 2026-08-02: chép ĐỈNH THẬT (fix maePeak null tren done-order)
                order.lastPrice = orderMulti.lastPrice;
                if (!fundingAssigned) {
                    order.time2FundingFee = orderMulti.time2FundingFee;   // toàn bộ phí cụm vào leg đầu
                    fundingAssigned = true;
                }

                putOrderDone(order);   // F8 FIX: khong ghi de khi key dung do
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
        // 🔎 2026-08-02: maePeak carry qua DCA (doi xung maeLow) — dinh THAT tu leg dau, chi di LEN.
        float carriedPeak = (prevRunning != null && prevRunning.maePeak != null) ? prevRunning.maePeak : firstLegEntry;
        orderResult.maePeak = Math.max(carriedPeak, ticker.maxPrice);
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
        orderResult.legCount = orders.size();   // DCA GRID: cum dang o bac nao
        // [2026-09-02] FUNDING notional MARK: carry phan da tich + moc settle cuoi sang cum moi (khong tinh trung/khong mat).
        if (Configs.FUNDING_MARK_NOTIONAL && prevRunning != null) {
            orderResult.fundingAccrued = prevRunning.fundingAccrued;
            orderResult.fundingLastSettle = prevRunning.fundingLastSettle;
        }


        return orderResult;
    }

    public void createOrderBUY(short symbolId, KlineObjectSimple ticker, MarketLevelChange levelChange,
                               MarketDataObject marketData, Float symbolPred) {
        // Long entry — delegate vao loi chung createOrder(BUY,...). Giu nguyen chu ky de moi call-site
        // khong doi. BUY -> hanh vi CU byte-identical (chi them 1 stack-frame, khong doi output).
        createOrder(OrderSide.BUY, symbolId, ticker, levelChange, marketData, symbolPred);
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



        AiPredictionData predict = predictionMap.get(ticker.startTime);
        // 🧠 #10 PARITY (TASK-030, một bộ não): LIVE createOrderBuyRequest reject khi prediction==null
        // (DetectEntrySignal2TradeNormal). TRƯỚC ĐÂY sim bỏ qua filter khi predict==null → VẪN vào lệnh "mù"
        // → P&L sim≠live ở mốc thiếu pred. Nay sim cũng reject pred==null. (CONFIG_VERSION v8→v9.)
        if (predict == null) {
            return;
        }
        if (!levelChange.equals(MarketLevelChange.BIG_DOWN)) {
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



        // === DCA GRID sizing (2026-08-01) — TONG von moi coin GIU NGUYEN = budget ===
        //   leg_i = budget * w[i] / sum(w). Vi du 1:1:3:8 -> leg1 chi 1/13 budget, leg cuoi 8/13.
        //   Nho vay nang ti trong duoi KHONG lam phinh tong exposure moi coin (van dung 1 suat budget),
        //   chi doi CACH RAI von theo do sau. Mac dinh DCA_GRID_ENABLED=false -> byte-identical.
        if (Configs.DCA_GRID_ENABLED) {
            List<OrderTargetInfoTest> cur = symbol2OrdersEntry[symbolId];
            int legIdx = (cur == null) ? 0 : cur.size();     // 0 = leg dau
            float ratio = DcaUtils.gridLegWeightRatio(legIdx);
            if (ratio <= 0f) return;                          // het bac grid -> khong mo them leg
            budget *= ratio;
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