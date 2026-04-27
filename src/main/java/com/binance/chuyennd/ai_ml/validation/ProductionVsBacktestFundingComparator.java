package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.lang.reflect.Field;
import java.util.*;

public class ProductionVsBacktestFundingComparator {
    public static final Logger LOG = LoggerFactory.getLogger(ProductionVsBacktestFundingComparator.class);

    // 🔥 THƯ MỤC LƯU DỮ LIỆU CỦA PRODUCTION
    private static final String PROD_PREDICT_DIR = "storage/data/predictionSymbol";

    // ĐƯỜNG DẪN FILE ONNX TƯƠNG ỨNG
    private static final String MODEL_PATH = "models_funding/Funding_Classifier_Final_Fixed.onnx";

    public static void main(String[] args) {
        new ProductionVsBacktestFundingComparator().runCompare();
    }

    public void runCompare() {
        LOG.info("🚀 KHỞI ĐỘNG ĐỐI SOÁT FUNDING: PROD (FILE) vs BACKTEST (BATCH PREDICT ON-THE-FLY)...");

        List<File> featureFiles = collectFeatureFiles(PROD_PREDICT_DIR);
        if (featureFiles.isEmpty()) {
            LOG.warn("❌ Không tìm thấy file .features nào trong thư mục PROD: {}", PROD_PREDICT_DIR);
            return;
        }

        // Lấy ngẫu nhiên 10 mẫu test
        Collections.shuffle(featureFiles);
        int limit = Math.min(10, featureFiles.size());

        // 🧠 KHỞI TẠO BỘ NÃO AI FUNDING VÀ EXTRACTOR
        FundingOnnxInferenceManager aiBrain = null;
        FundingFeatureExtractor btExtractor = new FundingFeatureExtractor();
        try {
            aiBrain = new FundingOnnxInferenceManager(MODEL_PATH);
            LOG.info("✅ Load AI Funding Model thành công!");
        } catch (Exception e) {
            LOG.error("❌ Không thể load AI Model, kiểm tra lại MODEL_PATH: {}", MODEL_PATH, e);
            return;
        }

        // Tải sẵn Market Data để dùng chung
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();

        int count = 0;
        for (int i = 0; i < featureFiles.size(); i++) {
            if (count >= limit) break;

            File prodFeatureFile = featureFiles.get(i);
            String timestampStr = prodFeatureFile.getName().replace(".features", "");
            long targetTime = Long.parseLong(timestampStr);

            File prodPredFile = new File(prodFeatureFile.getParentFile(), timestampStr);
            if (!prodPredFile.exists()) continue;

            count++;
            LOG.info("\n========================================================");
            LOG.info("🔍 MẪU {}/{} TẠI: {}", count, limit, Utils.normalizeDateYYYYMMDDHHmm(targetTime));

            try {
                // -------------------------------------------------------------------
                // BƯỚC 1: ĐỌC DỮ LIỆU TỪ PRODUCTION (FILE)
                // -------------------------------------------------------------------
                Map<String, FundingMarketFeatures> prodFeatureMap = (Map<String, FundingMarketFeatures>) StorageSnappy.readObjectFromFile(prodFeatureFile.getAbsolutePath());
                Map<String, Float> prodPredMap = (Map<String, Float>) StorageSnappy.readObjectFromFile(prodPredFile.getAbsolutePath());

                if (prodFeatureMap == null || prodPredMap == null || prodFeatureMap.isEmpty()) {
                    continue;
                }

                // -------------------------------------------------------------------
                // BƯỚC 2: TÁI TẠO MÔI TRƯỜNG BACKTEST BẰNG AEROSPIKE (WARM-UP)
                // -------------------------------------------------------------------
                LOG.info("   ⏳ Đang Warm-up 1500 phút dữ liệu cho HistoryManager...");
                HistoryManager.getInstance().getAllHistory().clear();
                CoinRankManager.getInstance().resetCache();

                long startTime = targetTime - 1500 * Utils.TIME_MINUTE;
                TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                        DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(startTime, 1501);

                if (time2Tickers == null || !time2Tickers.containsKey(targetTime)) {
                    LOG.error("   ❌ Aerospike không có dữ liệu tại phút {}. Bỏ qua mẫu!", Utils.normalizeDateYYYYMMDDHHmm(targetTime));
                    continue;
                }

                // Chạy vòng lặp Warm-up y hệt như Tool Generate (updateMarketHistory theo từng phút)
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                    btExtractor.updateMarketHistory(timeEntry.getValue());
                }

                // -------------------------------------------------------------------
                // BƯỚC 3: EXTRACT FEATURE VÀ PREDICT BATCH GIỐNG TOOL GENERATE
                // -------------------------------------------------------------------
                Map<String, KlineObjectSimple> symbol2Ticker = time2Tickers.get(targetTime);
                MarketDataObject marketData = time2MarketData.get(targetTime);

                List<String> validSymbols = new ArrayList<>();
                List<float[]> btFeatureArrays = new ArrayList<>();
                Map<String, FundingMarketFeatures> btFeatureMap = new HashMap<>();

                for (String symbol : symbol2Ticker.keySet()) {
                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                    if (ticker == null || !Utils.isTickerAvailable(ticker)) continue;

                    // 🔥 Tạo Dummy Order chuẩn y hệt code Generate
                    OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                            OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                            Configs.LEVERAGE_ORDER, symbol, targetTime, targetTime, OrderSide.BUY
                    );
                    dummyOrder.lastEntry = ticker.priceClose;

                    // Extract Feature
                    FundingMarketFeatures features = btExtractor.extractFeatures(
                            targetTime, dummyOrder, symbol2Ticker, marketData
                    );

                    if (features != null) {
                        validSymbols.add(symbol);
                        btFeatureMap.put(symbol, features);
                        btFeatureArrays.add(aiBrain.extractFeaturesToArray(features));
                    }
                }

                // 🔥 GỌI HÀM PREDICT BATCH ĐA LUỒNG THEO CHUNK SIZE (20)
                Map<String, Float> btPredMap = new HashMap<>();
                int chunkSize = 20;
                for (int j = 0; j < btFeatureArrays.size(); j += chunkSize) {
                    int end = Math.min(btFeatureArrays.size(), j + chunkSize);
                    List<float[]> chunkFeatures = btFeatureArrays.subList(j, end);
                    List<String> chunkSymbols = validSymbols.subList(j, end);

                    List<float[]> chunkResults = aiBrain.predictBatch(chunkFeatures);

                    if (chunkResults.size() == chunkFeatures.size()) {
                        for (int k = 0; k < chunkResults.size(); k++) {
                            // Lấy Prob [0] từ kết quả
                            btPredMap.put(chunkSymbols.get(k), chunkResults.get(k)[0]);
                        }
                    }
                }

                // -------------------------------------------------------------------
                // BƯỚC 4: ĐỐI SOÁT RANDOM 1 COIN ĐỂ TRÁNH SPAM LOG
                // -------------------------------------------------------------------
                List<String> commonSymbols = new ArrayList<>(prodFeatureMap.keySet());
                commonSymbols.retainAll(btFeatureMap.keySet());

                if (commonSymbols.isEmpty()) {
                    LOG.warn("   ⚠️ PROD và BT không có coin nào chung tại phút này!");
                    continue;
                }

                Collections.shuffle(commonSymbols);
                String testSymbol = commonSymbols.get(0);
                LOG.info("   🎯 Chọn Random Coin [{}] để soi chi tiết", testSymbol);

                FundingMarketFeatures prodFeats = prodFeatureMap.get(testSymbol);
                FundingMarketFeatures btFeats = btFeatureMap.get(testSymbol);

                LOG.info("   --- 📊 ĐỐI SOÁT FEATURES ---");
                compareFeatureFields(prodFeats, btFeats);

                LOG.info("   --- 🧠 ĐỐI SOÁT AI PREDICTION ---");
                Float prodPred = prodPredMap.get(testSymbol);
                Float btPred = btPredMap.get(testSymbol);

                if (btPred == null || prodPred == null) {
                    LOG.error("   ❌ Lỗi: Có 1 bên Predict bị NULL");
                } else {
                    float maxAbs = Math.max(Math.abs(prodPred), Math.abs(btPred));
                    float percentDiff = (maxAbs == 0) ? 0 : (Math.abs(prodPred - btPred) / maxAbs) * 100f;

                    if (percentDiff > 0.01f) {
                        LOG.error("   ❌ LỆCH PREDICT [Prob 0]: PROD = {} | BT = {} | Lệch: {}%",
                                String.format("%.6f", prodPred),
                                String.format("%.6f", btPred),
                                String.format("%.2f", percentDiff));
                    } else {
                        LOG.info("   ✅ PREDICTION KHỚP HOÀN HẢO! (Prob = {})", String.format("%.6f", prodPred));
                    }
                }

            } catch (Exception e) {
                LOG.error("❌ Lỗi khi xử lý mẫu: {}", timestampStr, e);
            }
        }
    }

    private void compareFeatureFields(FundingMarketFeatures prod, FundingMarketFeatures bt) {
        int diffCount = 0;
        Field[] fields = FundingMarketFeatures.class.getFields();
        for (Field field : fields) {
            try {
                field.setAccessible(true);
                Object prodVal = field.get(prod);
                Object btVal = field.get(bt);

                if (prodVal == null && btVal == null) continue;

                boolean isMatch = false;
                if (prodVal instanceof Float && btVal instanceof Float) {
                    isMatch = Math.abs((Float) prodVal - (Float) btVal) < 0.0001f;
                } else if (prodVal instanceof Double && btVal instanceof Double) {
                    isMatch = Math.abs((Double) prodVal - (Double) btVal) < 0.0001f;
                } else {
                    isMatch = Objects.equals(prodVal, btVal);
                }

                if (!isMatch) {
                    diffCount++;
                    if (prodVal instanceof Number && btVal instanceof Number) {
                        float p = ((Number) prodVal).floatValue();
                        float b = ((Number) btVal).floatValue();
                        float maxAbs = Math.max(Math.abs(p), Math.abs(b));
                        float diffPercent = (maxAbs == 0) ? 0 : (Math.abs(p - b) / maxAbs) * 100f;

                        LOG.warn("      ⚠️ [FEATURE] {}: PROD = {} | BT = {} | Lệch: {}%",
                                String.format("%-25s", field.getName()),
                                String.format("%10.6f", p),
                                String.format("%10.6f", b),
                                String.format("%5.2f", diffPercent));
                    } else {
                        LOG.warn("      ⚠️ [FEATURE] {}: PROD = {} | BT = {}", field.getName(), prodVal, btVal);
                    }
                }
            } catch (Exception e) {
                // Bỏ qua
            }
        }

        if (diffCount == 0) {
            LOG.info("   ✅ Tất cả {} features khớp nhau 100%!", fields.length);
        } else {
            LOG.warn("   => Tổng lệch {}/{} Features.", diffCount, fields.length);
        }
    }

    private List<File> collectFeatureFiles(String path) {
        List<File> allFiles = new ArrayList<>();
        File root = new File(path);
        if (!root.exists() || !root.isDirectory()) return allFiles;

        File[] dateDirs = root.listFiles(File::isDirectory);
        if (dateDirs != null) {
            for (File dateDir : dateDirs) {
                File[] files = dateDir.listFiles((dir, name) -> name.endsWith(".features"));
                if (files != null) {
                    allFiles.addAll(Arrays.asList(files));
                }
            }
        }
        return allFiles;
    }
}