/*
 * Copyright 2024 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.trading;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.funding.EntrySignalFilter;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingCrossSectional;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.onnx.entry.OnnxInferenceManager;
import com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager;
import com.binance.chuyennd.ai_ml.onnx.funding.LiveOiFeatProvider;
import com.binance.chuyennd.research.oibackfill.OiFeatLiveSets;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.DcaProcessor;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.PositionRisk;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;

/**
 * @author pc
 */
public class DetectEntrySignal2TradeNormal {

    public static final Logger LOG = LoggerFactory.getLogger(DetectEntrySignal2TradeNormal.class);
    // Đường dẫn model Funding
    private static final String MODEL_FUNDING_PATH = "../storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx";

    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    public AIRejectFilter aiRejectFilter = new AIRejectFilter();

    // --- Biến AI Entry (Cũ) ---
    private OnnxInferenceManager aiBrain;
    private ComprehensiveMarketFeatureExtractor featureEntryExtractor;

    // --- Biến AI Funding (MỚI) ---
    private FundingOnnxInferenceManager fundingBrain;
    private FundingDataCollectionManager.FundingFeatureExtractorV2 fundingExtractor;
    // OI feature (#41..#45) đã tính sẵn trên Oracle, live chỉ lookup từ 242 (fix reconcile 2026-08-17).
    private final LiveOiFeatProvider liveOiProvider = new LiveOiFeatProvider();

    // [PRED-GAP] Latest per-coin selector output = prob[0] = P(no-pump) = 1 - sel (P(maxFav>=6%)).
    // Cap nhat moi tick entry (15m, duyet MOI symbol) -> SL-loop (BinanceOrderTradingManager) doc de
    // quyet dinh gap weak/strong theo pred per-coin (thay market gate pred). Fallback gate neu thieu.
    public static final java.util.concurrent.ConcurrentHashMap<String, Float> LATEST_SEL_PNOPUMP =
            new java.util.concurrent.ConcurrentHashMap<>();
    public static volatile long LATEST_SEL_TS = 0L;


    public static void main(String[] args) throws InterruptedException, ParseException {
//        new DetectEntrySignal2Trader().getTickerBySymbol("QNTUSDT");
//        String symbol = "ALTUSDT";
        Long time = Utils.sdfFileHour.parse("20250726 08:16").getTime();
    }


    public void start() throws InterruptedException, ParseException {
        initData();
        startThreadDetectMarketLevel2Trader();
    }


    public void startThreadDetectMarketLevel2Trader() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadDetectMarketLevel2Trader");
            LOG.info("Start thread ThreadDetectMarketLevel2Trader");
            while (true) {
                if (isTimeProcessData()) {
                    try {
                        executorService.execute(() -> checkMarketLevelChange2Trade());
                    } catch (Exception e) {
                        LOG.error("ERROR during ThreadDetectMarketLevel2Trader: {}", e);
                        e.printStackTrace();
                    }
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND / 10);
                } catch (InterruptedException ex) {
                    ex.printStackTrace();
                }
            }
        }).start();
    }

    private void checkMarketLevelChange2Trade() {
        try {
            LOG.info("Start check level change of market for trade! {}", new Date());
            Map<String, KlineObjectSimple> symbol2FinalTicker = new HashMap<>();
            TreeMap<Float, String> rateDown15M2Symbols = new TreeMap<>();
            TreeMap<Float, String> rateUp15M2Symbols = new TreeMap<>();
            TreeMap<Float, String> rateDown2Symbols = new TreeMap<>();
            TreeMap<Float, String> rateUp2Symbols = new TreeMap<>();
            Map<String, Float> symbol2Max15m = new HashMap<>();

            Map<String, List<KlineObjectSimple>> symbol2LastTickers = DataManagerAerospikeFloatSim.readDataForSymbols(
                    System.currentTimeMillis() - 1500 * Utils.TIME_MINUTE, 1500);
            List<KlineObjectSimple> btcTickers = symbol2LastTickers.get(Constants.SYMBOL_PAIR_BTC);
            // TASK-027: thiếu data BTC → trước đây NPE rơi vào catch in stacktrace (im lặng).
            // Nay BỎ vòng entry phút này + log rõ (BTC là gốc tính market level, không có thì không quyết được).
            if (btcTickers == null || btcTickers.isEmpty()) {
                LOG.error("🚨 [LIVE] Thiếu data BTC ({}) trong window → BỎ vòng entry phút này (không tính được market level).",
                        Constants.SYMBOL_PAIR_BTC);
                return;
            }
            KlineObjectSimple btcTicker = btcTickers.get(btcTickers.size() - 1);
            Float btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen).floatValue();
            Float btcMax15M = null;

            LOG.info("Btc ticker size: {} {} -> {}", symbol2LastTickers.get(Constants.SYMBOL_PAIR_BTC).size(), Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(0).startTime.longValue()), Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()));
            long time = btcTicker.startTime.longValue();

            for (Map.Entry<String, List<KlineObjectSimple>> entry : symbol2LastTickers.entrySet()) {
                try {
                    String symbol = entry.getKey();
                    if (Constants.diedSymbol.contains(symbol)) {
                        continue;
                    }
                    List<KlineObjectSimple> tickers = entry.getValue();
                    KlineObjectSimple ticker = tickers.get(tickers.size() - 1);
                    if (!Utils.isTickerAvailable(ticker)) {
                        continue;
                    }

                    symbol2FinalTicker.put(symbol, ticker);
                    Float rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen).floatValue();
                    // pass symbol big dump(delist/waring/monitor...)
                    if (btcRateChange > -0.004 && rateChange < -0.15) {
                        continue;
                    }
                    if (rateChange > 0.3) {
                        continue;
                    }
                    rateDown2Symbols.put(rateChange, symbol);
                    rateUp2Symbols.put(-rateChange, symbol);
                    Float priceMax = null;
                    Float priceMin = null;
                    for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                        int index = tickers.size() - i - 1;
                        if (index >= 0) {
                            KlineObjectSimple kline = tickers.get(index);
                            if (priceMax == null || priceMax < kline.maxPrice) {
                                priceMax = kline.maxPrice;
                            }
                            if (priceMin == null || priceMin > kline.minPrice) {
                                priceMin = kline.minPrice;
                            }
                        }
                    }

                    if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
                        btcMax15M = priceMax;
                    }
                    rateDown15M2Symbols.put(Utils.rateOf2Double(tickers.get(tickers.size() - 1).priceClose, priceMax).floatValue(), symbol);
                    symbol2Max15m.put(symbol, priceMax);
                    rateUp15M2Symbols.put(-Utils.rateOf2Double(tickers.get(tickers.size() - 1).priceClose, priceMin).floatValue(), symbol);

                } catch (Exception e) {
                    e.printStackTrace();
                }
            }

            Float rateDownAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown2Symbols, 100);
            Float rateUpAvg = -MarketBigChangeDetector.calRateChangeAvg(rateUp2Symbols, 100);
            Float rateDown15MAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown15M2Symbols, 100);
            MarketDataObject marketRate = new MarketDataObject(rateDownAvg, rateUpAvg, rateDown15MAvg);
            Float rateBtcDown15M = Utils.rateOf2Double(btcTicker.priceClose, btcMax15M);
            MarketLevelChange levelChange = MarketBigChangeDetector.getMarketStatus1M(rateDownAvg, rateUpAvg, rateDown15MAvg);
            RedisHelper.getInstance().get().set(RedisConst.REDIS_KEY_LAST_TIME_CHECK_MARKET, Utils.toJson(System.currentTimeMillis()));
            LOG.info("Check level market: {} DownAvg: {}% UpAvg:{}% DownAvg15M:{}%  btcRate: {}% btcRate15M: {}% {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                    Utils.formatDouble(rateDownAvg * 100, 3),
                    Utils.formatDouble(rateUpAvg * 100, 3),
                    Utils.formatDouble(rateDown15MAvg * 100, 3),
                    Utils.formatDouble(btcRateChange * 100, 3),
                    Utils.formatDouble(rateBtcDown15M * 100, 3), levelChange);
            LOG.info("Market level change: {} level: {} symbols:{}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2FinalTicker.size());

            // --- CẬP NHẬT HISTORY CHO FUNDING EXTRACTOR ---
            if (fundingExtractor != null) {
                fundingExtractor.updateMarketHistory(symbol2FinalTicker);
            }

            Set<String> symbolLocked = new HashSet<>();
            symbolLocked.addAll(BudgetManager.getInstance().symbol2Pos.keySet());
            OnnxInferenceManager.PredictionResult predictData = null;
            MarketFeatures features = null;
            if (aiBrain != null && featureEntryExtractor != null) {
                try {
                    long timestamp = time;
                    Map<String, KlineObjectSimple> currentMarketMap = new HashMap<>(symbol2FinalTicker);

                    // 2. Trích xuất Features cho Entry Model
                    features = featureEntryExtractor.extractAllFeatures(timestamp, currentMarketMap, marketRate);

                    // 3. Dự báo Entry Model
                    predictData = aiBrain.predictAll(features);
                    if (predictData != null) {
                        AiPredictionData preData = new AiPredictionData(
                                timestamp,
                                predictData.return15M, predictData.riskDrawdown4H
                        );
                        DataManagerAerospikeFloatSim.saveAiPrediction1M(preData);
                    }

                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            // 3. Chạy AI Predict -> Sort theo L0 (Prob Fail) từ bé đến lớn
            TreeMap<Float, String> sortedCandidates = predictAllCandidates(symbol2FinalTicker.keySet(), symbol2FinalTicker,
                    rateDownAvg, rateUpAvg, rateDown15MAvg, time);
            if (levelChange != null) {
                Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                if (levelChange.equals(MarketLevelChange.SMALL_UP)
                        || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)) {
                    numberOrder = numberOrder / 2;
                }
                // 1. Lấy danh sách candidate
                Set<String> allSymbols = new HashSet<>();
                allSymbols.addAll(symbol2FinalTicker.keySet());
                allSymbols.removeAll(BudgetManager.getInstance().symbol2Pos.keySet());

                Set<String> symbol2BUY = new HashSet<>();
                symbol2BUY.addAll(MarketBigChangeDetector.getTopSymbol(numberOrder,
                        symbol2FinalTicker, symbolLocked, sortedCandidates));

                LOG.info("Level: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                        levelChange, symbol2BUY);
                for (String symbol : symbol2BUY) {
                    try {
                        KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                        createOrderBuyRequest(symbol, ticker, levelChange, symbol2Max15m.get(symbol), marketRate,
                                predictData, getSymbolPred(sortedCandidates, symbol), symbol2LastTickers, null);
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
                try {
                    List<String> symbolDcaLevel = DcaProcessor.getDCAProduction(levelChange,
                            System.currentTimeMillis(), BudgetManager.getInstance().getBudget(),
                            BudgetManager.getInstance().symbol2Pos);
                    for (String symbol : symbolDcaLevel) {
                        KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                        PositionRisk position = BudgetManager.getInstance().symbol2Pos.get(symbol);
                        if (position != null) {
                            createOrderBuyRequest(symbol, ticker, MarketLevelChange.DCA_LEVEL1,
                                    symbol2Max15m.get(symbol), marketRate, predictData,
                                    getSymbolPred(sortedCandidates, symbol), symbol2LastTickers, null);
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            // dca buy
            if (MarketBigChangeDetector.isDcaAlt(rateDown15MAvg, rateDownAvg, rateUpAvg)) {
                List<String> symbolDcaLossBig = DcaProcessor.getDCAProduction(null, System.currentTimeMillis(),
                        BudgetManager.getInstance().getBudget(), BudgetManager.getInstance().symbol2Pos);
                if (!symbolDcaLossBig.isEmpty()) {
                    LOG.info("DCA big loss:{}", symbolDcaLossBig);
                }
                for (String symbol : symbolDcaLossBig) {
                    KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                    if (Utils.isTickerAvailable(ticker)) {
                        PositionRisk position = BudgetManager.getInstance().symbol2Pos.get(symbol);
                        if (position != null) {
                            createOrderBuyRequest(symbol, ticker, MarketLevelChange.DCA_LEVEL1, symbol2Max15m.get(symbol), marketRate, predictData, getSymbolPred(sortedCandidates, symbol), symbol2LastTickers, null);

                        }
                    }
                }
            }


            // Duyệt qua danh sách đã sắp xếp (con ngon nhất duyệt trước)
            // Gom REJECT của PREDICT_SYMBOL_TRADE thành 1 dòng/phút (xem createOrderBuyRequest).
            List<String> predictRejects = new ArrayList<>();
            // [PARITY] KHOP BACKTEST RANK-TOPK (fix K5 lech live<->backtest):
            //  - rank-mode (TOPK>0): duyet pool DAY DU (selectorRankPool, khong loc maxThres) => khop backtest
            //    bo nguong per-symbol; cap-then-skip: dem rank tren TOAN pool (ke ca coin dang giu) roi break tai K,
            //    skip coin dang giu SAU khi dem => chi xet top-K rank, khong dao sau qua rank K nhu truoc.
            //  - TOPK<=0: giu hanh vi cu (pool da loc + skip-held, khong cap) byte-identical.
            TreeMap<Float, String> selPool = (Configs.SELECTOR_RANK_TOPK > 0) ? selectorRankPool : sortedCandidates;
            int rank = 0;
            for (Map.Entry<Float, String> entry : selPool.entrySet()) {
                String symbol = entry.getValue();
                Float symbolPred = entry.getKey();
                if (Configs.SELECTOR_RANK_TOPK > 0 && rank >= Configs.SELECTOR_RANK_TOPK) break;
                rank++;
                KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                if (ticker == null || BudgetManager.getInstance().symbol2Pos.containsKey(symbol)) continue;
                createOrderBuyRequest(symbol, ticker, MarketLevelChange.PREDICT_SYMBOL_TRADE,
                        symbol2Max15m.get(symbol), marketRate, predictData, symbolPred, symbol2LastTickers, predictRejects);
            }
            // market pred GIỐNG NHAU mọi coin → in 1 lần kèm danh sách SYM(symbolPred). (24H đã bỏ khỏi hệ.)
            if (!predictRejects.isEmpty() && predictData != null) {
                LOG.info("🔕 [PREDICT fail {}] market[15M:{}% Risk4H:{}%] Min15M:{}% | {}",
                        predictRejects.size(),
                        String.format("%.2f", predictData.return15M * 100),
                        String.format("%.2f", predictData.riskDrawdown4H * 100),
                        String.format("%.2f", Configs.MIN_MOMENTUM_15M * 100),
                        String.join(" ", predictRejects));
            }


            StorageSnappy.writeObject2File("storage/data/prediction/" + Utils.normalizeDateYYYYMMDD(time) + "/" + time, predictData);
            StorageSnappy.writeObject2File("storage/data/prediction/" + Utils.normalizeDateYYYYMMDD(time) + "/" + time + ".features", features);
            LOG.info("Predict: {}", Utils.toJson(predictData));
        } catch (Exception e) {
            e.printStackTrace();
        }
        LOG.info("Finish check level change of market 2 trade: {}", new Date());
    }

    // [PARITY] Pool DAY DU (khong loc maxThres) cho selector rank-mode -> khop backtest RANK-TOPK.
    private final TreeMap<Float, String> selectorRankPool = new TreeMap<>();

    private Float getSymbolPred(TreeMap<Float, String> sortedCandidates, String symbol) {

        if (sortedCandidates == null || symbol == null) {
            return null;
        }

        // Vì Symbol là Value, chúng ta phải duyệt qua các entry
        for (Map.Entry<Float, String> entry : sortedCandidates.entrySet()) {
            // So sánh symbol (Value)
            if (symbol.equals(entry.getValue())) {
                return entry.getKey(); // Trả về điểm số (Key)
            }
        }

        // Không tìm thấy symbol trong danh sách ứng viên
        return null;
    }

    private TreeMap<Float, String> predictAllCandidates(Set<String> allSymbols, Map<String,
            KlineObjectSimple> symbol2FinalTicker, Float rateDownAvg, Float rateUpAvg, Float rateDown15MAvg, long time) {
        TreeMap<Float, String> sortedCandidates = new TreeMap<>();
        selectorRankPool.clear(); // [PARITY] reset pool day du moi tick
        // 2. Chuẩn bị AI Input
        List<String> aiCandidates = new ArrayList<>();
        List<FundingMarketFeatures> aiFeaturesList = new ArrayList<>();
        Map<String, FundingMarketFeatures> symbol2FundingFeatures = new HashMap<>();
        Map<String, Float> symbol2FundingPred = new HashMap<>();
        final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);
        liveOiProvider.clear(); // đọc lại OI feature Oracle vừa push (tránh stale) mỗi tick

        // [OI-GUARD-2] Neu pipeline oi_feat qua han (Oracle/compute down) -> KHONG feed model feature NaN
        // (off-distribution) -> gate toan bo entry tick nay. Chi trigger khi TUNG co data (freshTs>0) roi cu di
        // -> tranh deadlock cold-start. Nguong = env OI_STALE_HALT_MS (default 2h = MERGE_TOL). Tat qua OI_STALE_HALT=0.
        if (!"0".equals(System.getenv("OI_STALE_HALT"))) {
            long oiFreshTs = liveOiProvider.pipelineFreshTs();
            long haltMs = OiFeatLiveSets.MERGE_TOL_MS;
            String hs = System.getenv("OI_STALE_HALT_MS");
            if (hs != null) { try { haltMs = Long.parseLong(hs.trim()); } catch (Exception ignore) { } }
            if (oiFreshTs > 0 && (time - oiFreshTs) > haltMs) {
                LOG.warn("[OI-GUARD-2] oi_feat pipeline STALE age={}m > {}m (Oracle/compute down?) "
                        + "-> GATE entries tick {}", (time - oiFreshTs) / 60000, haltMs / 60000, time);
                return sortedCandidates; // rong -> khong tao entry moi vong nay
            }
        }

        for (String symbol : allSymbols) {
            KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
            if (!Utils.isTickerAvailable(ticker)) continue;

            if (fundingExtractor != null && fundingBrain != null) {
                OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                        Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                );
                dummyOrder.lastEntry = ticker.priceClose;
                MarketDataObject marketData = new MarketDataObject(rateDownAvg,
                        rateUpAvg, rateDown15MAvg);
                FundingMarketFeatures feats = fundingExtractor.extractFeatures(
                        time, dummyOrder, symbol2FinalTicker, marketData,
                        basket);
                if (feats != null) {
                    // #41..#45 OI/LS/taker: lookup feature ĐÃ TÍNH SẴN trên Oracle từ 242 (fix reconcile
                    // 2026-08-17). Live không tính expanding oiZ (tránh OOM). NaN nếu chưa có OI ≤ t trong 2h.
                    float[] oi = liveOiProvider.lookup(symbol, time);
                    feats.oiDelta24hCoin = oi[0];
                    feats.oiZCoin = oi[1];
                    feats.lsGlobalCoin = oi[2];
                    feats.lsToptraderCoin = oi[3];
                    feats.takerBuyRatioCoin = oi[4];
                    aiCandidates.add(symbol);
                    aiFeaturesList.add(feats);
                    symbol2FundingFeatures.put(symbol, feats);
                }
            }
        }

        // === PASS-2 cross-sectional rank (#33..#35) — PARITY TRAIN (fix reconcile 2026-08-17).
        // Live trước đây bỏ PASS-2 -> fundingRankCS/volumeZRankCS/momentumRankCS luôn NaN (selector
        // ăn 37/45 feature). Population PHẢI = EntrySignalFilter (giống export/train) chứ không rank
        // trên toàn bộ candidate, nếu không rank lệch phân bố. Mutate feature IN-PLACE trước predictBatch.
        try {
            Set<String> csPop = EntrySignalFilter.selectCoins(symbol2FinalTicker, HistoryManager.getInstance());
            List<FundingMarketFeatures> csList = new ArrayList<>();
            for (String sym : aiCandidates) {
                if (csPop.contains(sym)) csList.add(symbol2FundingFeatures.get(sym));
            }
            FundingCrossSectional.apply(csList);
        } catch (Exception e) {
            LOG.warn("PASS-2 cross-sectional rank lỗi (giữ NaN #33..35): {}", e.toString());
        }

        if (fundingBrain != null && !aiFeaturesList.isEmpty()) {
            List<float[]> featureArrays = aiFeaturesList.stream()
                    .map(f -> fundingBrain.extractFeaturesToArray(f))
                    .collect(Collectors.toList());

            List<float[]> results = fundingBrain.predictBatch(featureArrays);
            float maxThres = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * Configs.AI_DYNAMIC_MAX;
            for (int i = 0; i < aiCandidates.size(); i++) {
                String sym = aiCandidates.get(i);
                float[] preds = results.get(i);
                symbol2FundingPred.put(sym, preds[0]);
                LATEST_SEL_PNOPUMP.put(sym, preds[0]); // [PRED-GAP] P(no-pump) per-coin cho SL-loop
                selectorRankPool.put(preds[0], sym); // [PARITY] pool day du (truoc loc maxThres) cho rank-mode
                // 🔥 FILTER: Reject nếu Fail Prob > 0.3
                if (preds[0] > maxThres) {
//                    LOG.info("❌ [FILTER AI SYMBOL] {}: Prediction FAIL too high ({})", sym, probs[0]);
                } else {
                    // Tự động sắp xếp: Key càng bé (ProbFail thấp) càng đứng đầu
                    sortedCandidates.put(preds[0], sym);
                }
            }
        }
        try {
            StorageSnappy.writeObject2File("storage/data/predictionSymbol/" + Utils.normalizeDateYYYYMMDD(time)
                    + "/" + time, symbol2FundingPred);
            StorageSnappy.writeObject2File("storage/data/predictionSymbol/" + Utils.normalizeDateYYYYMMDD(time)
                    + "/" + time + ".features", symbol2FundingFeatures);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return sortedCandidates;
    }


    public void createOrderBuyRequest(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange, Float priceMax15M,
                                      MarketDataObject marketRate, OnnxInferenceManager.PredictionResult prediction,
                                      Float symbolPred, Map<String, List<KlineObjectSimple>> symbol2LastTickers,
                                      List<String> rejectCollector) {


        if (prediction == null) {
            LOG.info("No AI prediction data for {} at time {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime));
            return;
        }

        // 4. Kiểm tra Lọc
        AIRejectFilter.FilterResult filterResult = null;
        // Nếu là kèo AI Funding -> Dùng Logic Động
        AiPredictionData predict = new AiPredictionData(
                ticker.startTime,
                prediction.return15M, prediction.riskDrawdown4H
        );
        if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) {
            // [PARITY] rank-mode (SELECTOR_RANK_TOPK>0): backtest RANK-TOPK BO nguong per-symbol,
            //   chi dung market gate => KHONG goi checkSignalDynamic, de roi xuong checkSignal (market-only).
            //   TOPK<=0: giu checkSignalDynamic cu (byte-identical).
            if (symbolPred != null && Configs.SELECTOR_RANK_TOPK <= 0) {
                filterResult = aiRejectFilter.checkSignalDynamic(predict, symbolPred);
            }
        }
        if (filterResult == null) {
            filterResult = aiRejectFilter.checkSignal(predict);
        }
        // Gom log: với vòng PREDICT_SYMBOL_TRADE (hàng trăm coin/phút, market pred GIỐNG NHAU,
        // chỉ symbolPred khác) → KHÔNG log per-coin REJECT mà gom vào collector để in 1 dòng tổng hợp.
        // Mọi levelChange khác / collector null → giữ log cũ. Quyết định KHÔNG đổi.
        boolean gather = (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE && rejectCollector != null);

        if (!gather) {
            // Log kết quả AI để debug/monitor
            LOG.info("AI CHECK [{}] Pred: {} -> Decision: {}", symbol, prediction, filterResult.decision);
        }

        if (filterResult.decision == AIRejectFilter.FilterDecision.REJECT) {
            if (gather) {
                String symShort = symbol.replace("USDT", "");
                rejectCollector.add(String.format("%s(%.3f)", symShort, symbolPred == null ? 0f : symbolPred));
            } else {
                LOG.info("❌ SKIP ORDER [{} {}] due to AI REJECT: {} symbolPred: {}", symbol, levelChange, filterResult.reason, symbolPred);
            }
            return; // <--- CHẶN LỆNH TẠI ĐÂY
        } else {
            // PASS (vào lệnh) → LUÔN giữ, ít và quan trọng.
            LOG.info("✅ AI PASS [{}] Reason: {} symbolPred: {}", symbol, filterResult.reason, symbolPred);
        }
// 🔥 NÂNG CẤP: CHỐT CHẶN CẦU DAO CHO BOT LIVE
        if (levelChange != MarketLevelChange.DCA_LEVEL1) {
            if (MarketBigChangeDetector.is50PercentOrderLossProd(getAllOrderRunning(), ticker.startTime)) {
                LOG.info("⚠️ CẦU DAO BẬT: Từ chối mở lệnh [{}] do đa số các lệnh mới vào gần đây đều chết hoặc gồng lỗ!", symbol);
                return;
            }
        }

        Float marginRunning = BudgetManager.getInstance().marginRunning;
        Float balanceBasic = BudgetManager.getInstance().balanceBasic;
        Float budget = BudgetManager.getInstance().getBudget();

        budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange);
        if (budget == null || budget < 5) {
            LOG.info("Not trade because over capital or budget not enough: {} {} {} {}", symbol, levelChange, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), budget);
            return;
        }

        // =========================================================
        // 🚀 CẤP VỐN THÔNG MINH BẰNG COIN RANK MANAGER
        // =========================================================
        long currentTs = ticker.startTime;

        // 1. Lấy Hệ số nhân Budget (1.2 | 1.0 | 0.5)
        // Lưu ý: Tự động truyền symbol2LastTickers để Manager tự tính toán khi cần
        float tierMultiplier = CoinRankManager.getInstance().getBudgetMultiplier(symbol);

        // 2. Chặn đứng DCA rác
        CoinRankManager.CoinTier myTier = CoinRankManager.getInstance().getCoinTier(symbol, currentTs);
        if (myTier == CoinRankManager.CoinTier.TIER_3_SHITCOIN) {
            if (levelChange == MarketLevelChange.DCA_LEVEL1) {
//                LOG.info("🚫 Chặn DCA vào đồng Shitcoin: {}", symbol);
                return;
            }
        }

        // Áp dụng hệ số vào Budget
        budget *= tierMultiplier;


        Float priceEntry = ticker.priceClose;
        // TASK-027 #7: SIZE (quantity) theo GIÁ TƯƠI price_realtime (242), KHÔNG theo nến đã đóng
        // (priceClose trễ ~1-2′) → tránh size sai khi coin biến động mạnh trong phút. Quyết định gate
        // vẫn dựa nến đóng; chỉ quantity dùng giá tươi. Giá tươi thiếu/quá cũ → fallback priceClose + cảnh báo.
        // Đặt SAU mọi early-return (filter/budget/tier) nên chỉ 1 GET Aerospike cho lệnh thật sự đi tiếp.
        Float priceForSizing = priceEntry;
        Float priceRt = DataManagerAerospikeFloatSim.getPriceRealtime(symbol);
        Long priceRtTs = DataManagerAerospikeFloatSim.getPriceRealtimeTs(symbol);
        if (priceRt != null && priceRt > 0 && priceRtTs != null
                && (System.currentTimeMillis() - priceRtTs) <= Configs.PRICE_REALTIME_MAX_AGE_MS) {
            priceForSizing = priceRt;
        } else {
            long ageSec = priceRtTs == null ? -1 : (System.currentTimeMillis() - priceRtTs) / 1000;
            LOG.warn("⚠️ [{}] price_realtime không dùng được để size (price={}, tuổi={}s) → fallback priceClose nến đóng {}",
                    symbol, priceRt, ageSec, priceEntry);
        }
        Float quantity = Utils.calQuantity(budget, Configs.LEVERAGE_ORDER, priceForSizing, symbol);
        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
            Float minBtcTrade = 0.002f;
            if (quantity < minBtcTrade) {
                quantity = minBtcTrade;
            }
        }
        LOG.info("Market level:{} {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), levelChange, symbol, budget, quantity, ticker.priceClose);
        if (quantity != null && quantity != 0) {
            OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose, null, quantity, Configs.LEVERAGE_ORDER, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BUY, Constants.TRADING_TYPE_VOLUME_MINI);
            orderTrade.marketLevel = levelChange;
            orderTrade.priceTP = priceMax15M;
            LOG.info("Push redis order: {} {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), symbol, levelChange, budget.longValue(), quantity, ticker.priceClose);
            BudgetManager.getInstance().addMarginRunning(budget);
            RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
            writeOrder2File(orderTrade, ticker, marketRate, priceMax15M);
        } else {
            LOG.info("{} {} quantity false", symbol, quantity);
        }
    }

    private Collection<OrderTargetInfo> getAllOrderRunning() {
        List<OrderTargetInfo> orders = new ArrayList<>();
        try {
            for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO)) {
                try {
                    String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
                    OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
                    if (order != null) {
                        orders.add(order);
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return orders;
    }

    private void writeOrder2File(OrderTargetInfo orderTrade, KlineObjectSimple ticker,
                                 MarketDataObject marketRate, Float priceMax15M) {
        try {
            Map<Object, Object> data = new HashMap<>();
            data.put("ticker", ticker);
            data.put("order", orderTrade);
            data.put("marketRate", marketRate);
            data.put("max15M", priceMax15M);
            String fileName = "storage/data/order/";
            fileName += Utils.normalizeDateYYYYMMDD(ticker.startTime.longValue());
            fileName += "/";
            fileName += orderTrade.symbol + "-" + ticker.startTime.longValue();
            StorageSnappy.writeObject2File(fileName, data);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private long lastProcessedMinute = 0; // Biến đánh dấu phút đã quét

    // v1 parity WFO G015: entry CHỈ tại mốc lưới 15m (khớp grid selector/label backtest).
    // Env LIVE_ENTRY_GRID_MIN đổi được không cần rebuild (=1 => quay lại cadence 1 phút cũ).
    private static final long ENTRY_GRID_MIN = resolveEntryGridMin();

    private static long resolveEntryGridMin() {
        String v = System.getenv("LIVE_ENTRY_GRID_MIN");
        if (v != null) {
            try {
                long g = Long.parseLong(v.trim());
                if (g >= 1) {
                    return g;
                }
            } catch (NumberFormatException ignored) {
                // env rác -> giữ default 15
            }
        }
        return 15;
    }

    public boolean isTimeProcessData() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long curMin = time / (60 * Utils.TIME_SECOND); // Tính ra phút hiện tại

        // Mở rộng cửa sổ thời gian từ giây 03 đến giây 10 (rộng 7 giây).
        // Cờ lastProcessedMinute đảm bảo trong 7 giây này nó chỉ được phép trả về TRUE đúng 1 lần.
        // curMin % ENTRY_GRID_MIN == 0 => chỉ chạy tại mốc lưới (mặc định 15m: :00/:15/:30/:45 UTC).
        if (second >= 6 && second <= 10 && curMin % ENTRY_GRID_MIN == 0 && curMin > lastProcessedMinute) {
            lastProcessedMinute = curMin;
            return true;
        }
        return false;
    }

    private void initData() {

        // TASK-019 A: đây là LIVE init (backtest dùng Simulator, KHÔNG gọi hàm này) → bật production
        // mode cho FundingFeeManager để refresh funding định kỳ (tránh dùng funding cũ/0 sau 24h).
        FundingFeeManager.getInstance().setProductionMode(true);

        // --- 1. KHỞI TẠO AI ENTRY (CŨ) ---
        try {
            LOG.info("Initializing AI Brain & Feature Extractor...");
            int minutesWranup = 2000;
            this.aiBrain = new OnnxInferenceManager(Configs.FILE_AI_ENTRY_PREDICTIONS);
            this.featureEntryExtractor = new ComprehensiveMarketFeatureExtractor();

            // Sync dữ liệu lịch sử
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(
                            System.currentTimeMillis() - minutesWranup * Utils.TIME_MINUTE, minutesWranup);
            this.featureEntryExtractor.initDataFromTickerMap(time2Tickers);

            LOG.info("AI System Initialized Successfully. {} {} {}", time2Tickers.size(), Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.firstKey()), Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.lastKey()));

            // --- 2. KHỞI TẠO AI FUNDING (MỚI) ---
            if (new File(MODEL_FUNDING_PATH).exists()) {
                LOG.info("🚀 Initializing Funding AI from: {}", MODEL_FUNDING_PATH);
                this.fundingBrain = new FundingOnnxInferenceManager(MODEL_FUNDING_PATH);
                this.fundingExtractor = new FundingDataCollectionManager.FundingFeatureExtractorV2();

                // Đồng bộ history cho Funding Extractor luôn
                initDataFromTickerMap(time2Tickers);
                LOG.info("✅ Funding AI System Ready!");
            } else {
                LOG.warn("⚠️ Funding Model not found at: {}. Running without AI Filter for Funding!", MODEL_FUNDING_PATH);
            }

        } catch (Exception e) {
            LOG.error("Failed to initialize AI System", e);
        }

        // TASK-027 #8: aiBrain là não entry — null nghĩa bot KHÔNG thể ra quyết định vào lệnh.
        // Trước đây catch ở trên NUỐT lỗi (chỉ LOG.error) → bot chạy CÂM: mọi createOrderBuyRequest
        // bị chặn ở nhánh prediction==null, KHÔNG vào lệnh, KHÔNG ai biết. Nay: alert Telegram +
        // fail-fast (ném exception) để daemon restart và người vận hành biết ngay, không chạy câm.
        if (aiBrain == null) {
            String msg = "🚨 [LIVE] aiBrain (model entry) INIT THẤT BẠI — bot KHÔNG vào lệnh được. Kiểm tra model: "
                    + Configs.FILE_AI_ENTRY_PREDICTIONS;
            LOG.error(msg);
            try {
                Utils.sendSms2Telegram(msg);
            } catch (Exception ex) {
                LOG.error("Không gửi được Telegram alert aiBrain null", ex);
            }
            throw new IllegalStateException("aiBrain init failed - từ chối chạy câm (TASK-027 #8)");
        }
    }

    public void initDataFromTickerMap(TreeMap<Long, Map<String, KlineObjectSimple>> time2Ticker) {
        LOG.info("AI Feature Extractor: Syncing history from {} size: {}",
                Utils.normalizeDateYYYYMMDDHHmm(time2Ticker.firstKey()), time2Ticker.size());
        for (Map<String, KlineObjectSimple> tickerMap : time2Ticker.values()) {
            this.fundingExtractor.updateMarketHistory(tickerMap);
        }
        LOG.info("AI Feature Extractor: Completed syncing {} history from {}.",
                time2Ticker.size(), Utils.normalizeDateYYYYMMDDHHmm(time2Ticker.firstKey()));
    }
}