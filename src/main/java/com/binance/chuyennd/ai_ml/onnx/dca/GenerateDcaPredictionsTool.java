package com.binance.chuyennd.ai_ml.onnx.dca;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.dca.DcaFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.dca.DcaMarketFeatures;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

public class GenerateDcaPredictionsTool {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateDcaPredictionsTool.class);

    // Đường dẫn lưu file cache
    public static final String PREDICT_STORAGE_DIR = "../storage/al_ml/dca_predictions_cache/";

    public static void main(String[] args) throws Exception {
        // Cấu hình thời gian chạy: Từ 2021-01-01 đến Hiện tại
        String startTimeStr = "2021-01-01 00:00:00";

        // Parse thời gian (Đảm bảo Utils.sdfFile đã được khởi tạo đúng format yyyy-MM-dd HH:mm:ss)
        long startTime = Utils.sdfFile.parse(startTimeStr).getTime();
        long endTime = System.currentTimeMillis();

        LOG.info("🔥 Starting Multi-Thread AI Generation...");
        LOG.info("   -> Time Range: {} to {}", startTimeStr, Utils.normalizeDateYYYYMMDDHHmm(endTime));
        LOG.info("   -> Storage: {}", PREDICT_STORAGE_DIR);

        // Chạy hàm tạo dữ liệu
        new GenerateDcaPredictionsTool().generateMultiThread(startTime, endTime);
    }

    public void generateMultiThread(long globalStartTime, long globalEndTime) throws Exception {
        // Tạo thư mục nếu chưa có
        new File(PREDICT_STORAGE_DIR).mkdirs();

        // 1. Khởi tạo AI Brain (Load model ONNX - Bản tối ưu bỏ CatBoost)
        DcaOnnxInferenceManager dcaBrain = new DcaOnnxInferenceManager(Configs.FILE_AI_DCA_MODEL);

        // 2. Khởi tạo Feature Extractor (Giữ state lịch sử nến)
        DcaFeatureExtractor extractor = new DcaFeatureExtractor();

        long currentYearStart = globalStartTime;
        long lastBasketTimestamp = -1;
        List<String> cachedBasket = new ArrayList<>();

        // --- VÒNG LẶP THEO NĂM (YEARLY LOOP) ---
        while (currentYearStart < globalEndTime) {
            Calendar cal = Calendar.getInstance();
            cal.setTimeInMillis(currentYearStart);
            int year = cal.get(Calendar.YEAR);

            // Tính thời điểm kết thúc năm
            cal.add(Calendar.YEAR, 1);
            long currentYearEnd = Math.min(cal.getTimeInMillis(), globalEndTime);

            LOG.info("================================================================");
            LOG.info("🔄 Processing YEAR: {} ({} -> {})", year, Utils.normalizeDateYYYYMMDD(currentYearStart), Utils.normalizeDateYYYYMMDD(currentYearEnd));
            LOG.info("================================================================");

            // Structure lưu dữ liệu cả năm: Time -> (SymbolID -> [Risk, Reward, Pump, Dump])
            // Dùng TreeMap để key (Time) luôn được sắp xếp
            TreeMap<Long, HashMap<Short, float[]>> yearPredictions = new TreeMap<>();

            // Map Symbol -> ID (Riêng biệt cho từng năm, Thread-safe)
            final ConcurrentHashMap<String, Short> localSymbolMap = new ConcurrentHashMap<>();
            AtomicInteger symbolCounter = new AtomicInteger(0);

            long currentTime = currentYearStart;

            // --- VÒNG LẶP THỜI GIAN (TUẦN TỰ) ---
            while (currentTime < currentYearEnd) {
                // 1. Đọc Data (I/O tuần tự)
                TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);

                if (time2Tickers == null || time2Tickers.isEmpty()) {
                    currentTime += Utils.TIME_HOUR; // Nhảy cóc nếu không có data
                    continue;
                }

                // Duyệt qua từng phút trong block data vừa đọc
                // Đổi tên biến entry -> timeEntry để tránh trùng tên trong lambda
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                    long time = timeEntry.getKey();
                    if (time >= currentYearEnd) break;

                    Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                    // 2. Update History & Basket (BẮT BUỘC CHẠY TUẦN TỰ TRÊN MAIN THREAD)
                    extractor.updateMarketHistory(symbol2Ticker);

                    if (time != lastBasketTimestamp) {
                        cachedBasket = extractor.identifyTargetBasket(time);
                        lastBasketTimestamp = time;
                    }
                    // Biến final để dùng an toàn trong lambda
                    final List<String> currentBasket = cachedBasket;

                    // 3. XỬ LÝ SONG SONG (PARALLEL) TÍNH TOÁN AI
                    // Map tạm chứa kết quả của 1 phút (ConcurrentHashMap để put song song không lỗi)
                    ConcurrentHashMap<Short, float[]> frameResultConcurrent = new ConcurrentHashMap<>(symbol2Ticker.size());

                    // Sử dụng Parallel Stream để tận dụng hết các core CPU
                    symbol2Ticker.entrySet().parallelStream().forEach(tickerEntry -> {
                        String symbol = tickerEntry.getKey();
                        KlineObjectSimple ticker = tickerEntry.getValue();

                        if (ticker == null) return;

                        // a. Lấy hoặc Tạo ID cho Symbol (Thread-safe)
                        // Nếu symbol chưa có ID thì tạo mới bằng atomic counter
                        short symId = localSymbolMap.computeIfAbsent(symbol, k -> (short) symbolCounter.incrementAndGet());

                        // b. Tạo dummy order (Local Object - An toàn cho Thread)
                        OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                                OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0,
                                Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                        );
                        dummyOrder.lastEntry = ticker.priceClose;

                        try {
                            // c. Trích xuất đặc trưng (Feature Extraction)
                            // Lưu ý: Hàm extractFeatures phải được viết Stateless (không dùng biến global tạm)
                            DcaMarketFeatures features = extractor.extractFeatures(
                                    time, dummyOrder, null, symbol2Ticker, currentBasket
                            );

                            if (features != null) {
                                // d. Dự báo AI (Inference)
                                DcaPredictionResult result = dcaBrain.predict(features);

                                // e. Lưu kết quả gọn nhẹ (float array)
                                frameResultConcurrent.put(symId, new float[]{
                                        result.predictedMaxDrawdown, // 0: Risk
                                        result.predictedMaxRise,     // 1: Reward
                                        result.probPump20Pct,        // 2: Pump Prob
                                        result.probDump30Pct         // 3: Dump Prob
                                });
                            }
                        } catch (Exception e) {
                            // Log lỗi nhẹ để không spam console nếu lỗi hàng loạt
                            // LOG.error("Error processing symbol {}: {}", symbol, e.getMessage());
                        }
                    });

                    // 4. Gom kết quả về Map chính của năm
                    if (!frameResultConcurrent.isEmpty()) {
                        // Convert về HashMap thường để tiết kiệm bộ nhớ hơn ConcurrentHashMap khi lưu lâu dài
                        yearPredictions.put(time, new HashMap<>(frameResultConcurrent));
                    }
                }

                // Tăng thời gian để đọc block tiếp theo
                if (!time2Tickers.isEmpty()) {
                    currentTime = time2Tickers.lastKey() + Utils.TIME_MINUTE;
                } else {
                    currentTime += Utils.TIME_MINUTE;
                }

                // Log tiến độ mỗi 10 ngày
                if (currentTime % (10 * Utils.TIME_DAY) == 0) {
                    long ramUsed = (Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()) / 1024 / 1024;
                    LOG.info("   ... reached {} | Symbols Mapped: {} | RAM Used: {} MB",
                            Utils.normalizeDateYYYYMMDDHHmm(currentTime),
                            localSymbolMap.size(),
                            ramUsed);
                }
            }

            // --- LƯU FILE KẾT THÚC NĂM ---
            if (!yearPredictions.isEmpty()) {
                // Convert ConcurrentMap -> Map thường để serialize
                Map<String, Short> finalSymbolMap = new HashMap<>(localSymbolMap);

                // Đóng gói cả Map và Data vào 1 Object duy nhất
                DcaYearlyDataPackage dataPackage = new DcaYearlyDataPackage(finalSymbolMap, yearPredictions);

                String fileName = PREDICT_STORAGE_DIR + "dca_pred_" + year + ".data";
                LOG.info("💾 SAVING FILE: {} (Timestamps: {}, Symbols: {})", fileName, yearPredictions.size(), finalSymbolMap.size());

                StorageSnappy.writeObject2File(fileName, dataPackage);
            } else {
                LOG.warn("⚠️ No data generated for year {}", year);
            }

            // --- DỌN DẸP RAM ---
            yearPredictions.clear();
            localSymbolMap.clear();

            // Gọi GC để giải phóng RAM triệt để trước khi sang năm mới (file mới)
            System.gc();
            LOG.info("🧹 Cleaned RAM. Moving to next year...");

            // Chuyển sang năm tiếp theo
            currentYearStart = currentYearEnd;
        }

        // Đóng AI Session
        dcaBrain.close();
        LOG.info("✅ DONE! All predictions generated successfully.");
    }
}