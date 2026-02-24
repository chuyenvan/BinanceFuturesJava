package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.text.SimpleDateFormat;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class CompareProdLogWithAerospike {
    private static final Logger LOG = LoggerFactory.getLogger(CompareProdLogWithAerospike.class);

    // Đường dẫn trỏ tới file log production của bạn
    private static final String LOG_FILE_PATH = "C:\\Users\\pc\\Desktop\\data\\full.log.1";

    // Ngưỡng sai số cho phép đối với Market Data
// Nới lỏng cho Market Data (Lệch dưới 0.02% là OK)
    private static final double TOLERANCE = 0.0002;

    // Nới lỏng cho AI Data (Lệch dưới 0.6% là OK)
    private static final double TOLERANCE_AI = 0.006;

    public static void main(String[] args) {
        LOG.info("🚀 BẮT ĐẦU QUÉT LOG VÀ SO SÁNH VỚI AEROSPIKE...");
        compareLog(LOG_FILE_PATH);
        DataManagerAerospikeFloatSim.closeConnection();
        LOG.info("✅ HOÀN TẤT KIỂM TRA.");
    }

    public static void compareLog(String filePath) {
        SimpleDateFormat logTimeFmt = new SimpleDateFormat("yyyyMMdd HH:mm");

        Pattern marketPattern = Pattern.compile("Check level market: (\\d{8} \\d{2}:\\d{2}) DownAvg:\\s*([-0-9.]+)% UpAvg:\\s*([-0-9.]+)% DownAvg15M:\\s*([-0-9.]+)%");
        Pattern predictPattern = Pattern.compile("Predict: (\\{.*\\})");

        long currentTargetTime = 0;
        String currentTargetTimeStr = "";

        try (BufferedReader br = new BufferedReader(new FileReader(filePath))) {
            String line;
            while ((line = br.readLine()) != null) {

                // 1. KIỂM TRA LOG MARKET DATA
                Matcher marketMatcher = marketPattern.matcher(line);
                if (marketMatcher.find()) {
                    currentTargetTimeStr = marketMatcher.group(1);
                    currentTargetTime = logTimeFmt.parse(currentTargetTimeStr).getTime();

                    double prodDownAvg = Double.parseDouble(marketMatcher.group(2)) / 100.0;
                    double prodUpAvg = Double.parseDouble(marketMatcher.group(3)) / 100.0;
                    double prodDown15MAvg = Double.parseDouble(marketMatcher.group(4)) / 100.0;

                    MarketDataObject testData = DataManagerAerospikeFloatSim.getMarketDataAtTime(currentTargetTime);

                    System.out.println("\n========================================================================================");
                    System.out.println("🕒 TIME: " + currentTargetTimeStr);
                    System.out.println("========================================================================================");

                    if (testData != null) {
                        System.out.println("📊 [MARKET LEVEL MATCHING]");
                        printDiff("DownAvg   ", prodDownAvg, testData.rateDownAvg);
                        printDiff("UpAvg     ", prodUpAvg, testData.rateUpAvg);
                        printDiff("DownAvg15M", prodDown15MAvg, testData.rateDown15MAvg);
                    } else {
                        System.out.println("❌ [MARKET] Không tìm thấy dữ liệu Test trong Aerospike!");
                    }
                }

                // 2. KIỂM TRA LOG AI PREDICTION
                Matcher predMatcher = predictPattern.matcher(line);
                if (predMatcher.find() && currentTargetTime > 0) {
                    String prodJson = predMatcher.group(1);
                    AiPredictionData testData = DataManagerAerospikeFloatSim.getMarketAiPredictionAtTime(currentTargetTime);

                    System.out.println("🤖 [AI PREDICTION MATCHING]");
                    if (testData != null) {
                        try {
                            // Parse JSON của PROD thành Map để bóc tách từng giá trị
                            Map<String, Double> prodMap = Utils.gson.fromJson(prodJson, new com.google.gson.reflect.TypeToken<Map<String, Double>>(){}.getType());

                            double pRet15M = prodMap.getOrDefault("return15M", 0.0);
                            double pRet1H  = prodMap.getOrDefault("return1H", 0.0);
                            double pRet4H  = prodMap.getOrDefault("return4H", 0.0);
                            double pRet24H = prodMap.getOrDefault("return24H", 0.0);
                            double pRisk4H = prodMap.getOrDefault("riskDrawdown4H", 0.0);
                            double pRisk24H = prodMap.getOrDefault("riskDrawdown24H", 0.0);

                            // So sánh từng thông số
                            printDiffAi("Return 15M", pRet15M, testData.predReturn15M);
                            printDiffAi("Return 1H ", pRet1H, testData.predReturn1H);
                            printDiffAi("Return 4H ", pRet4H, testData.predReturn4H);
                            printDiffAi("Return 24H", pRet24H, testData.predReturn24H);
                            printDiffAi("Risk 4H   ", pRisk4H, testData.predRisk4H);
                            printDiffAi("Risk 24H  ", pRisk24H, testData.predRisk24H);

                        } catch (Exception e) {
                            System.out.println("   ❌ Lỗi khi parse JSON PROD: " + e.getMessage());
                        }
                    } else {
                        System.out.println("   [PROD]: " + prodJson);
                        System.out.println("   [TEST]: ❌ Không tìm thấy dữ liệu Test trong Aerospike!");
                    }
                }
            }
        } catch (Exception e) {
            LOG.error("Lỗi khi đọc file log", e);
        }
    }

    /**
     * So sánh hiển thị cho Market Data (6 chữ số thập phân)
     */
    private static void printDiff(String label, double prodVal, double testVal) {
        double diff = Math.abs(prodVal - testVal);
        String status = (diff <= TOLERANCE) ? "✅ OK" : "❌ LỆCH";
        System.out.printf("   - %s | PROD: %9.6f | TEST: %9.6f | %s%n",
                label, prodVal, testVal, status);
    }

    /**
     * So sánh hiển thị cho AI Data (9 chữ số thập phân, bổ sung cột DIFF)
     */
    private static void printDiffAi(String label, double prodVal, double testVal) {
        double diff = Math.abs(prodVal - testVal);
        String status = (diff <= TOLERANCE_AI) ? "✅ OK" : "❌ LỆCH";

        // Dùng %12.9f để in ra tới 9 số thập phân, căn phải
        System.out.printf("   - %s | PROD: %12.9f | TEST: %12.9f | DIFF: %11.9f | %s%n",
                label, prodVal, testVal, diff, status);
    }
}