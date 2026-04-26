package com.binance.chuyennd.trading.monitor;

import org.apache.commons.io.input.ReversedLinesFileReader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.TreeMap;

public class LogMonitor {
    private static final Logger LOG = LoggerFactory.getLogger(LogMonitor.class);

    public static String getStats(int hoursToLookBack) {
        String logFilePath = "logs/nohup.out";
        File file = new File(logFilePath);
        if (!file.exists()) {
            return "Log(" + hoursToLookBack + "h): ❌ FileNotFound";
        }

        TreeMap<Long, Boolean> checkResults = new TreeMap<>();
        long cutoffTimeMillis = System.currentTimeMillis() - ((long) hoursToLookBack * 60 * 60 * 1000);

        SimpleDateFormat logPrefixFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        SimpleDateFormat targetDataFormat = new SimpleDateFormat("yyyyMMdd HH:mm");
        SimpleDateFormat displayFormat = new SimpleDateFormat("HH:mm"); // Format giờ:phút để báo cáo Telegram

        String cutoffTimeStr = logPrefixFormat.format(new Date(cutoffTimeMillis));

        int maxLinesToRead = 100000;
        int linesRead = 0;

        try (ReversedLinesFileReader reader = new ReversedLinesFileReader(file, StandardCharsets.UTF_8)) {
            String line;
            while ((line = reader.readLine()) != null && linesRead < maxLinesToRead) {
                linesRead++;

                if (line.length() >= 19 && line.startsWith("202")) {
                    String timePrefixStr = line.substring(0, 19);

                    if (timePrefixStr.compareTo(cutoffTimeStr) < 0) {
                        break;
                    }
                }

                if (line.contains("Check level market: ")) {
                    try {
                        String executeTimeStr = line.substring(0, 19);
                        long executeMinute = (logPrefixFormat.parse(executeTimeStr).getTime() / 60000) * 60000;

                        int markerIndex = line.indexOf("Check level market: ");
                        String dataTimeStr = line.substring(markerIndex + 20, markerIndex + 34);
                        long dataMinute = targetDataFormat.parse(dataTimeStr).getTime();

                        boolean isSuccess = (executeMinute - dataMinute) == 60000;
                        checkResults.put(dataMinute, isSuccess);
                    } catch (Exception ignored) {}
                }
            }

            if (checkResults.isEmpty()) {
                return "🚨 CRITICAL: No data in " + hoursToLookBack + "h!";
            }

            long firstMinuteInLog = checkResults.firstKey();
            long lastMinuteInLog = checkResults.lastKey();
            long currentMinute = (System.currentTimeMillis() / 60000) * 60000;
            long expectedLastDataMinute = currentMinute - 120000;

            StringBuilder alert = new StringBuilder();
            if (expectedLastDataMinute > lastMinuteInLog) {
                long deadMinutes = (expectedLastDataMinute - lastMinuteInLog) / 60000;
                alert.append("🚨 DEAD ").append(deadMinutes).append("m! ");
            }

            int successCount = 0;
            int failCount = 0;
            List<String> failedDetails = new ArrayList<>(); // 🔥 Thêm List để lưu các phút bị lỗi

            for (long min = firstMinuteInLog; min <= expectedLastDataMinute; min += 60000) {
                Boolean isSuccess = checkResults.get(min);
                if (isSuccess == null || !isSuccess) {
                    failCount++;
                    failedDetails.add(displayFormat.format(new Date(min))); // Lưu lại phút bị tịt
                } else {
                    successCount++;
                }
            }

            int actualTotal = successCount + failCount;
            float successRate = (actualTotal == 0) ? 0 : ((float) successCount / actualTotal) * 100;

            String baseStats = alert.toString() + "Log(" + hoursToLookBack + "h): " + successCount + "/" + actualTotal + " (" + String.format("%.1f", successRate) + "%)";

            // 🔥 Nếu có lỗi, ghép chi tiết các phút bị lỡ vào báo cáo
            if (failCount > 0) {
                int limit = Math.min(failedDetails.size(), 10); // Lấy tối đa 10 mốc thời gian để ko spam Telegram
                String missedStr = String.join(", ", failedDetails.subList(0, limit));
                if (failedDetails.size() > 10) {
                    missedStr += "... (+" + (failedDetails.size() - 10) + " more)";
                }
                return baseStats + "\n❌ Miss: " + missedStr;
            }

            return baseStats;

        } catch (Exception e) {
            LOG.error("Lỗi đọc log monitor: ", e);
            return "Log(" + hoursToLookBack + "h): ❌ Error Parsing";
        }
    }

    public static void main(String[] args) {
        String logStats = LogMonitor.getStats(4); // Lấy thống kê 4 tiếng qua
        System.out.println(logStats);
    }
}