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

public class GenerateDcaPredictionsTool {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateDcaPredictionsTool.class);

    // Đường dẫn lưu file cache (Theo yêu cầu của bạn)
    public static final String PREDICT_STORAGE_DIR = "../storage/al_ml/dca_predictions_cache/";

    public static void main(String[] args) throws Exception {
        // 1. Cấu hình thời gian chạy: Từ 2021-01-01 đến Hiện tại
        String startTimeStr = "20210101";
        long startTime = Utils.sdfFile.parse(startTimeStr).getTime();
        long endTime = System.currentTimeMillis(); // Chạy đến hiện tại

        new GenerateDcaPredictionsTool().generate(startTime, endTime);
    }

    public void generate(long globalStartTime, long globalEndTime) throws Exception {
        // Tạo thư mục lưu trữ nếu chưa có
        new File(PREDICT_STORAGE_DIR).mkdirs();

        // Khởi tạo AI Brain (Load model ONNX)
        // Lưu ý: Đảm bảo bạn đã dùng bản tối ưu (bỏ CatBoost) để tiết kiệm RAM
        DcaOnnxInferenceManager dcaBrain = new DcaOnnxInferenceManager(Configs.FILE_AI_DCA_PREDICTIONS);

        // Khởi tạo Extractor (Cần duy trì liên tục để tính chỉ báo kỹ thuật)
        DcaFeatureExtractor extractor = new DcaFeatureExtractor();

        long currentChunkStart = globalStartTime;
        long lastBasketTimestamp = -1;
        List<String> cachedBasket = new ArrayList<>();

        LOG.info("🚀 START PRE-COMPUTING AI (2021 -> Now). Storage: {}", PREDICT_STORAGE_DIR);

        // --- VÒNG LẶP CHUNK (MỖI 6 THÁNG) ---
        while (currentChunkStart < globalEndTime) {
            // Tính thời gian kết thúc của Chunk này (Start + 6 tháng)
            Calendar cal = Calendar.getInstance();
            cal.setTimeInMillis(currentChunkStart);
            cal.add(Calendar.MONTH, 6);
            long currentChunkEnd = Math.min(cal.getTimeInMillis(), globalEndTime);

            String chunkName = Utils.normalizeDateYYYYMMDD(currentChunkStart) + "_" + Utils.normalizeDateYYYYMMDD(currentChunkEnd);
            LOG.info("🔄 Processing Chunk: {} -> {}", Utils.normalizeDateYYYYMMDD(currentChunkStart), Utils.normalizeDateYYYYMMDD(currentChunkEnd));

            // Map chứa dữ liệu của 6 tháng: <Time, <Symbol, Result>>
            // Cảnh báo: Map này có thể rất lớn (vài GB)
            TreeMap<Long, HashMap<String, DcaPredictionResult>> chunkPredictions = new TreeMap<>();

            long currentTime = currentChunkStart;

            // --- VÒNG LẶP THỜI GIAN (TỪNG PHÚT TRONG 6 THÁNG) ---
            while (currentTime < currentChunkEnd) {
                // Đọc data từ Aerospike (hoặc nguồn dữ liệu gốc của bạn)
                TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);

                for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                    long time = entry.getKey();
                    if (time >= currentChunkEnd) break;

                    Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();

                    // 1. Cập nhật lịch sử giá cho Extractor (Rất quan trọng để tính RSI, MA...)
                    extractor.updateMarketHistory(symbol2Ticker);

                    // 2. Cập nhật rổ coin (Basket) nếu cần
                    if (time != lastBasketTimestamp) {
                        cachedBasket = extractor.identifyTargetBasket(time);
                        lastBasketTimestamp = time;
                    }

                    // 3. Dự báo cho từng Symbol
                    HashMap<String, DcaPredictionResult> frameResult = new HashMap<>();

                    for (String symbol : symbol2Ticker.keySet()) {
                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                        if (ticker == null) continue;

                        // Tạo lệnh giả định (Dummy Order) tại giá Close hiện tại
                        // Để AI trả lời câu hỏi: "Nếu mua ngay bây giờ thì sao?"
                        OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                                OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0,
                                Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                        );
                        dummyOrder.lastEntry = ticker.priceClose;

                        List<String> basket = (cachedBasket != null && !cachedBasket.isEmpty()) ? cachedBasket : Collections.singletonList(symbol);

                        // Trích xuất 41 features
                        DcaMarketFeatures features = extractor.extractFeatures(
                                time, dummyOrder, null, symbol2Ticker, basket
                        );

                        if (features != null) {
                            DcaPredictionResult result = dcaBrain.predict(features);

                            // OPTIONAL: Lọc bớt dữ liệu rác để giảm dung lượng file
                            // Nếu kèo quá xấu (Dump cao hoặc Risk cao), có thể không cần lưu (đỡ tốn RAM/Disk)
                            // Tuy nhiên để Backtest chính xác nhất thì nên lưu ALL.
                            // Ở đây tôi lưu ALL.
                            frameResult.put(symbol, result);
                        }
                    }

                    if (!frameResult.isEmpty()) {
                        chunkPredictions.put(time, frameResult);
                    }
                }

                // Cập nhật thời gian chạy để đọc block tiếp theo
                // (Giả sử time2Tickers trả về dữ liệu liên tục, lấy key cuối cùng + 1 phút)
                if (!time2Tickers.isEmpty()) {
                    currentTime = time2Tickers.lastKey() + Utils.TIME_MINUTE;
                } else {
                    currentTime += Utils.TIME_MINUTE;
                }

                // Log tiến độ nhẹ
                if (time2Tickers.size() > 0 && currentTime % (5 * Utils.TIME_DAY) == 0) {
                    LOG.info("   ... reached {}", Utils.normalizeDateYYYYMMDDHHmm(currentTime));
                }
            }

            // --- KẾT THÚC 6 THÁNG: LƯU FILE ---
            if (!chunkPredictions.isEmpty()) {
                String fileName = PREDICT_STORAGE_DIR + "dca_pred_" + chunkName + ".data";
                LOG.info("💾 Saving Chunk to file: {} (Size: {} timestamps)", fileName, chunkPredictions.size());

                // Dùng Snappy để nén, giảm dung lượng đĩa
                StorageSnappy.writeObject2File(fileName, chunkPredictions);
            }

            // --- DỌN DẸP RAM ---
            chunkPredictions.clear();
            chunkPredictions = null; // Help GC
            System.gc(); // Gợi ý JVM dọn rác ngay lập tức trước khi sang chunk mới

            // Chuyển sang 6 tháng tiếp theo
            currentChunkStart = currentChunkEnd;
        }

        dcaBrain.close();
        LOG.info("✅ DONE! All predictions generated.");
    }
}