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
import com.binance.chuyennd.ai_ml.features.export.funding.FundingFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.onnx.entry.OnnxInferenceManager;
import com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager;
import com.binance.chuyennd.helper.PositionHelper;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.DcaProcessor;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.utils.Configs;
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
    private static final String FILE_STORAGE_TIME_RATE_DOWN15M = "storage/data/time2RatDown15M.data";
    // Đường dẫn model Funding
    private static final String MODEL_FUNDING_PATH = "../storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx";

    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    public TreeMap<Long, Float> time2RateDown15MAvg = new TreeMap<>();
    public AIRejectFilter aiRejectFilter = new AIRejectFilter();

    // --- Biến AI Entry (Cũ) ---
    private OnnxInferenceManager aiBrain;
    private ComprehensiveMarketFeatureExtractor featureEntryExtractor;

    // --- Biến AI Funding (MỚI) ---
    private FundingOnnxInferenceManager fundingBrain;
    private FundingFeatureExtractor fundingExtractor;


    public static void main(String[] args) throws InterruptedException, ParseException {
//        new DetectEntrySignal2Trader().getTickerBySymbol("QNTUSDT");
//        String symbol = "ALTUSDT";
        Long time = Utils.sdfFileHour.parse("20250726 08:16").getTime();
    }


    public void start() throws InterruptedException, ParseException {
        initData();
        // 🔥 BẬT CHẾ ĐỘ PRODUCTION cho FundingFeeManager để lấy data realtime
        FundingFeeManager.getInstance().setProductionMode(true);
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
            Map<String, Double> symbol2Max15m = new HashMap<>();

            Map<String, List<KlineObjectSimple>> symbol2LastTickers = DataManagerAerospikeFloatSim.readDataForSymbols(System.currentTimeMillis() - 1500 * Utils.TIME_MINUTE, 1500);
            List<KlineObjectSimple> btcTickers = symbol2LastTickers.get(Constants.SYMBOL_PAIR_BTC);
            KlineObjectSimple btcTicker = btcTickers.get(btcTickers.size() - 1);
            Float btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen).floatValue();
            Double btcMax15M = null;

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
                    Double priceMax = null;
                    Double priceMin = null;
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
            MarketDataObject marketRate = new MarketDataObject(rateDownAvg, rateDown15MAvg, rateUpAvg);
            Double rateBtcDown15M = Utils.rateOf2Double(btcTicker.priceClose, btcMax15M);
            MarketLevelChange levelChange = MarketBigChangeDetector.getMarketStatus1M(rateDownAvg, rateUpAvg, btcRateChange, rateDown15MAvg);
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
                    features = featureEntryExtractor.extractAllFeatures(timestamp, currentMarketMap, marketRate, new ArrayList<>());

                    // 3. Dự báo Entry Model
                    predictData = aiBrain.predictAll(features);
                    if (predictData != null) {
                        AiPredictionData preData = new AiPredictionData(
                                timestamp,
                                predictData.return15M, predictData.return1H, predictData.return4H, predictData.return24H,
                                predictData.riskDrawdown4H, predictData.riskDrawdown24H
                        );
                        DataManagerAerospikeFloatSim.saveAiPrediction1M(preData);
                    }

                } catch (Exception e) {
                    e.printStackTrace();
                }
            }

            if (levelChange != null) {
                Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                        || levelChange.equals(MarketLevelChange.SMALL_UP)
                        || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                        || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)) {
                    numberOrder = numberOrder / 2;
                }
                // 1. Lấy danh sách candidate
                Set<String> allSymbols = new HashSet<>();
                allSymbols.addAll(FundingFeeManager.getInstance().getFundingListSymbol2Trade(time));
                allSymbols.removeAll(BudgetManager.getInstance().symbol2Pos.keySet());

                // 3. Chạy AI Predict -> Sort theo L0 (Prob Fail) từ bé đến lớn
                TreeMap<Float, String> sortedCandidates = predictAllCandidates(allSymbols, symbol2FinalTicker,
                        rateDownAvg, rateUpAvg, rateDown15MAvg, time);

                Set<String> symbol2BUY = new HashSet<>();
                symbol2BUY.addAll(MarketBigChangeDetector.getTopSymbol(numberOrder,
                        symbol2FinalTicker, symbolLocked,sortedCandidates));


                if (symbol2BUY.size() < numberOrder) {
                    LOG.info("Not symbol 2 buy: {} {} ", levelChange, Utils.normalizeDateYYYYMMDDHHmm(time));
                }

                symbol2BUY.addAll(MarketBigChangeDetector.addSpecialSymbol(symbol2FinalTicker, symbol2BUY, BudgetManager.getInstance().symbol2Pos.keySet()));
                LOG.info("Level: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()), levelChange, symbol2BUY);
                for (String symbol : symbol2BUY) {
                    try {
                        KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                        createOrderBuyRequest(symbol, ticker, levelChange, symbol2Max15m.get(symbol), marketRate, predictData);
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
                try {
                    List<String> symbolDcaLevel = DcaProcessor.getDCAProduction(levelChange, System.currentTimeMillis(), BudgetManager.getInstance().getBudget(), BudgetManager.getInstance().symbol2Pos);
                    for (String symbol : symbolDcaLevel) {
                        KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                        PositionRisk position = BudgetManager.getInstance().symbol2Pos.get(symbol);
                        if (position != null) {
                            MarketLevelChange levelDca;
                            if (PositionHelper.callMargin(position) < BudgetManager.getInstance().getBudget()) {
                                levelDca = MarketLevelChange.DCA_LEVEL1;
                            } else {
                                levelDca = MarketLevelChange.DCA_LEVEL2;
                            }
                            createOrderBuyRequest(symbol, ticker, levelDca, symbol2Max15m.get(symbol), marketRate, predictData);
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            // dca buy
            if (MarketBigChangeDetector.isDcaAlt(rateDown15MAvg, rateDownAvg, rateUpAvg)) {
                List<String> symbolDcaLossBig = DcaProcessor.getDCAProduction(null, System.currentTimeMillis(), BudgetManager.getInstance().getBudget(), BudgetManager.getInstance().symbol2Pos);
                if (!symbolDcaLossBig.isEmpty()) {
                    LOG.info("DCA big loss:{}", symbolDcaLossBig);
                }
                for (String symbol : symbolDcaLossBig) {
                    KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                    if (Utils.isTickerAvailable(ticker)) {
                        PositionRisk position = BudgetManager.getInstance().symbol2Pos.get(symbol);
                        if (position != null) {
                            MarketLevelChange levelDca;
                            if (PositionHelper.callMargin(position) < BudgetManager.getInstance().getBudget()) {
                                levelDca = MarketLevelChange.DCA_LEVEL1;
                            } else {
                                levelDca = MarketLevelChange.DCA_LEVEL2;
                            }
                            createOrderBuyRequest(symbol, ticker, levelDca, symbol2Max15m.get(symbol), marketRate, predictData);

                        }
                    }
                }
            }

            // ==========================================================
            // 🔥 FUNDING FEE TRADE LOGIC (SORTED & FILTERED & LIMITED)
            // ==========================================================
            time2RateDown15MAvg.put(time, rateDown15MAvg);
            while (time2RateDown15MAvg.size() > Configs.NUMBER_RATE_DOWN_HISTORY_TRADE) {
                time2RateDown15MAvg.remove(time2RateDown15MAvg.firstKey());
            }
            Float minRate15Min30M = Collections.min(time2RateDown15MAvg.values());

            if (MarketBigChangeDetector.isFundingFeeTrade(rateDown15MAvg, rateDownAvg, rateUpAvg, minRate15Min30M)) {
                // 1. Lấy danh sách candidate
                Set<String> allSymbols = new HashSet<>();
                allSymbols.addAll(FundingFeeManager.getInstance().getFundingListSymbol2Trade(time));
                allSymbols.removeAll(BudgetManager.getInstance().symbol2Pos.keySet());

                // 3. Chạy AI Predict -> Sort theo L0 (Prob Fail) từ bé đến lớn
                TreeMap<Float, String> sortedCandidates = predictAllCandidates(allSymbols, symbol2FinalTicker,
                        rateDownAvg, rateUpAvg, rateDown15MAvg, time);


                // 4. Final Trade Logic (Limit TOP 30)
                int countChecked = 0;

                // Duyệt qua danh sách đã sắp xếp (con ngon nhất duyệt trước)
                for (Map.Entry<Float, String> entry : sortedCandidates.entrySet()) {
                    if (countChecked >= 30) break; // Chỉ lấy Top 30
                    countChecked++;
                    String symbol = entry.getValue();
                    KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                    if (ticker == null) continue;
                    createOrderBuyRequest(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY, symbol2Max15m.get(symbol), marketRate, predictData);
                }
            }

            StorageSnappy.writeObject2File(FILE_STORAGE_TIME_RATE_DOWN15M, time2RateDown15MAvg);
            StorageSnappy.writeObject2File("storage/data/rateMax15M/" + Utils.normalizeDateYYYYMMDD(time) + "/" + time, rateDown15M2Symbols);
            StorageSnappy.writeObject2File("storage/data/rateDown1M/" + Utils.normalizeDateYYYYMMDD(time) + "/" + time, rateDown2Symbols);
            StorageSnappy.writeObject2File("storage/data/prediction/" + Utils.normalizeDateYYYYMMDD(time) + "/" + time, predictData);
            StorageSnappy.writeObject2File("storage/data/prediction/" + Utils.normalizeDateYYYYMMDD(time) + "/" + time + ".features", features);
            LOG.info("Predict: {}", Utils.toJson(predictData));
        } catch (Exception e) {
            e.printStackTrace();
        }
        LOG.info("Finish check level change of market 2 trade: {}", new Date());
    }

    private TreeMap<Float, String> predictAllCandidates(Set<String> allSymbols, Map<String,
            KlineObjectSimple> symbol2FinalTicker, Float rateDownAvg, Float rateUpAvg, Float rateDown15MAvg, long time) {
        TreeMap<Float, String> sortedCandidates = new TreeMap<>();
                // 2. Chuẩn bị AI Input
        List<String> aiCandidates = new ArrayList<>();
        List<FundingMarketFeatures> aiFeaturesList = new ArrayList<>();
        List<String> currentBasket = null;

        if (fundingExtractor != null && fundingBrain != null) {
            currentBasket = fundingExtractor.identifyTargetBasket(symbol2FinalTicker);
        }

        for (String symbol : allSymbols) {
            KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
            if (!Utils.isTickerAvailable(ticker)) continue;

            double rate1m = (ticker.priceClose - ticker.priceOpen) / ticker.priceOpen;
            // 🔥 HARD FILTER: Chỉ giữ lại nếu đang sập mạnh (Rate1M < -0.65%)
            if (rate1m >= -0.0065) {
                continue;
            }

            if (fundingExtractor != null && fundingBrain != null) {
                OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0,
                        Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                );
                dummyOrder.lastEntry = ticker.priceClose;
                MarketDataObject marketData = new MarketDataObject(rateDownAvg,
                        rateUpAvg, rateDown15MAvg);
                FundingMarketFeatures feats = fundingExtractor.extractFeatures(
                        time, dummyOrder, symbol2FinalTicker, currentBasket, marketData
                );
                if (feats != null) {
                    aiCandidates.add(symbol);
                    aiFeaturesList.add(feats);
                }
            } else {
                // Fallback nếu không có AI
                aiCandidates.add(symbol);
            }
        }

        if (fundingBrain != null && !aiFeaturesList.isEmpty()) {
            List<float[]> featureArrays = aiFeaturesList.stream()
                    .map(f -> fundingBrain.extractFeaturesToArray(f))
                    .collect(Collectors.toList());

            List<float[]> results = fundingBrain.predictBatch(featureArrays);

            for (int i = 0; i < aiCandidates.size(); i++) {
                String sym = aiCandidates.get(i);
                float[] probs = results.get(i);

                // 🔥 FILTER: Reject nếu Fail Prob > 0.3
                if (probs[0] > 0.2) {
                    LOG.info("❌ [FILTER AI FUNDING] {}: Prediction FAIL too high ({})", sym, probs[0]);
                } else {
                    // Tự động sắp xếp: Key càng bé (ProbFail thấp) càng đứng đầu
                    sortedCandidates.put(probs[0], sym);
                }
            }
        } else {
            // Fallback: Random sort nếu không có AI
            for (String sym : aiCandidates) sortedCandidates.put((float) Math.random(), sym);
        }
        return sortedCandidates;
    }


    private OrderTargetInfo getOrderInfo(String symbol) {
        try {
            String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
            OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
            return order;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public void createOrderBuyRequest(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange, Double priceMax15M,
                                      MarketDataObject marketRate, OnnxInferenceManager.PredictionResult prediction) {


        if (prediction == null) {
            LOG.info("No AI prediction data for {} at time {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            return;
        }
        // 4. Kiểm tra Lọc
        AIRejectFilter.FilterResult filterResult = aiRejectFilter.checkSignal(prediction);

        // Log kết quả AI để debug/monitor
        LOG.info("AI CHECK [{}] Pred: {} -> Decision: {}", symbol, prediction, filterResult.decision);

        if (filterResult.decision == AIRejectFilter.FilterDecision.REJECT) {
            LOG.info("❌ SKIP ORDER [{} {}] due to AI REJECT: {}", symbol, levelChange, filterResult.reason);
            return; // <--- CHẶN LỆNH TẠI ĐÂY
        } else {
            LOG.info("✅ AI PASS [{}] Reason: {}", symbol, filterResult.reason);
        }

        Double marginRunning = BudgetManager.getInstance().marginRunning;
        Double balanceBasic = BudgetManager.getInstance().balanceBasic;
        Double budget = BudgetManager.getInstance().getBudget();

        budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange);
        if (budget == null || budget < 5) {
            LOG.info("Not trade because over capital or budget not enough: {} {} {} {}", symbol, levelChange, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), budget);
            return;
        }

        Double priceEntry = ticker.priceClose;
        Double quantity = Utils.calQuantity(budget, Configs.LEVERAGE_ORDER, priceEntry, symbol);
        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
            Double minBtcTrade = 0.002;
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

    private void writeOrder2File(OrderTargetInfo orderTrade, KlineObjectSimple ticker,
                                 MarketDataObject marketRate, Double priceMax15M) {
        try {
            Map<Object, Object> data = new HashMap<>();
            data.put("ticker", ticker);
            data.put("order", orderTrade);
            data.put("marketRate", marketRate);
            data.put("max15M", priceMax15M);
//            data.put("symbol2Sell", symbol2Sell);
            data.put("fundingBuy", FundingFeeManager.getInstance().getFundingListSymbol2Trade(ticker.startTime.longValue()));
            String fileName = "storage/data/order/";
            fileName += Utils.normalizeDateYYYYMMDD(ticker.startTime.longValue());
            fileName += "/";
            fileName += orderTrade.symbol + "-" + ticker.startTime.longValue();
            StorageSnappy.writeObject2File(fileName, data);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static Double calMarginRunning(String symbol) {
        if (BudgetManager.getInstance().symbol2Margin.get(symbol) != null) {
            return BudgetManager.getInstance().symbol2Margin.get(symbol);
        }
        return 0d;
    }

    public static Double calRateLoss(String symbol) {
        PositionRisk pos = BudgetManager.getInstance().symbol2Pos.get(symbol);
        if (pos != null) {
            return PositionHelper.calRateLoss(pos);
        }
        return 1d;
    }

    public boolean isTimeProcessData() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 0 && miniSecond < 100;
    }

    private void initData() {

        if (new File(FILE_STORAGE_TIME_RATE_DOWN15M).exists()) {
            time2RateDown15MAvg = (TreeMap<Long, Float>) StorageSnappy.readObjectFromFile(FILE_STORAGE_TIME_RATE_DOWN15M);
        }

        // --- 1. KHỞI TẠO AI ENTRY (CŨ) ---
        try {
            LOG.info("Initializing AI Brain & Feature Extractor...");
            this.aiBrain = new OnnxInferenceManager(Configs.FILE_AI_ENTRY_PREDICTIONS);
            this.featureEntryExtractor = new ComprehensiveMarketFeatureExtractor();

            // Sync dữ liệu lịch sử
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(
                            System.currentTimeMillis() - 1500 * Utils.TIME_MINUTE, 1500);
            this.featureEntryExtractor.initDataFromTickerMap(time2Tickers);

            LOG.info("AI System Initialized Successfully. {} {} {}", time2Tickers.size(), Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.firstKey()), Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.lastKey()));

            // --- 2. KHỞI TẠO AI FUNDING (MỚI) ---
            if (new File(MODEL_FUNDING_PATH).exists()) {
                LOG.info("🚀 Initializing Funding AI from: {}", MODEL_FUNDING_PATH);
                this.fundingBrain = new FundingOnnxInferenceManager(MODEL_FUNDING_PATH);
                this.fundingExtractor = new FundingFeatureExtractor();

                // Đồng bộ history cho Funding Extractor luôn
                initDataFromTickerMap(time2Tickers);
                LOG.info("✅ Funding AI System Ready!");
            } else {
                LOG.warn("⚠️ Funding Model not found at: {}. Running without AI Filter for Funding!", MODEL_FUNDING_PATH);
            }

        } catch (Exception e) {
            LOG.error("Failed to initialize AI System", e);
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