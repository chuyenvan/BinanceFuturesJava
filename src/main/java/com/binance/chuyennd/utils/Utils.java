/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.binance.chuyennd.utils;

import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.PositionRisk;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URLEncoder;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.text.DecimalFormat;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * @author chuyennd
 */
public class Utils {

    public static final Logger LOG = LoggerFactory.getLogger(Utils.class);
    public static final long TIME_SECOND = 1000;
    public static final long TIME_MINUTE = 60 * TIME_SECOND;
    public static final long TIME_HOUR = 60 * TIME_MINUTE;
    public static final long TIME_DAY = 24 * TIME_HOUR;
    public static final long TIME_WEEK = 7 * TIME_DAY;
    public static Gson gson = new GsonBuilder().serializeNulls().create();

    public static final SimpleDateFormat sdfFile = new SimpleDateFormat("yyyyMMdd");
    public static final SimpleDateFormat sdfMonth = new SimpleDateFormat("yyyyMM");
    public static final SimpleDateFormat sdfFileHour = new SimpleDateFormat("yyyyMMdd HH:mm");
    public static final SimpleDateFormat sdfFileFull = new SimpleDateFormat("yyyyMMdd HH:mm:ss");
    public static final SimpleDateFormat sdfGoogle = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

    public static final DecimalFormat df = new DecimalFormat("#.##");
    public static final DecimalFormat dfNew = new DecimalFormat("#");


    public static Float callPnl(PositionRisk pos) {
        Float pnl = pos.getPositionAmt().floatValue();
        pnl = pnl * (pos.getMarkPrice().floatValue() - pos.getEntryPrice().floatValue());
        return pnl;
    }

    public static long getStartTimeOfDay(long timestamp) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(timestamp);
        cal.set(Calendar.HOUR_OF_DAY, 0);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        return cal.getTimeInMillis();
    }

    public static long getStartOfDayGMT7(long time) {
        Calendar cal = Calendar.getInstance(); // Nên set TimeZone nếu server khác múi giờ
        cal.setTimeInMillis(time);
        cal.set(Calendar.HOUR_OF_DAY, 7);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);

        // Nếu time input < 07:00 hôm nay -> Nó thuộc về phiên ngày hôm qua
        // Ví dụ: time là 02:00 -> startOfDay phải là 07:00 hôm qua
        if (cal.getTimeInMillis() > time) {
            cal.add(Calendar.DAY_OF_MONTH, -1);
        }

        return cal.getTimeInMillis();
    }

    public static boolean isMidnightFirstDay(long timeMillis) {
        // Kiểm tra 0h0p
        if (timeMillis % TIME_DAY == 0) {
            Calendar cal = Calendar.getInstance();
            cal.setTimeInMillis(timeMillis);
            // Kiểm tra ngày trong tháng có phải mùng 1
            return cal.get(Calendar.DAY_OF_MONTH) == 1;
        }
        return false;
    }

    public static boolean isFirstDayOfYear(long timeMillis) {
        // Kiểm tra 0h0p
        if (timeMillis % TIME_DAY == 0) {
            Calendar cal = Calendar.getInstance();
            cal.setTimeInMillis(timeMillis);
            // Kiểm tra ngày trong tháng có phải mùng 1
            return cal.get(Calendar.DAY_OF_MONTH) == 1 && cal.get(Calendar.MONTH) == Calendar.JANUARY;
        }
        return false;
    }

    public static int getCurrentHour() {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date());
        return cal.get(Calendar.HOUR_OF_DAY);
    }


    public static boolean sendSms2Telegram(String text) {
        String urlString = "https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s&parse_mode=HTML";

        //Add Telegram token (given Token is fake)
        String apiToken = "6158571844:AAHgemRZAWCFARpkyiZkpc9iTT4hEKMtUvw";

        //Add chatId (given chatId is fake)
        String chatId = "6548680563";

        urlString = String.format(urlString, apiToken, chatId, URLEncoder.encode(text));

        try {
            LOG.info("Telegram respon: {}", HttpRequest.getContentFromUrl(urlString));
        } catch (Exception e) {
            e.printStackTrace();
        }
        return true;
    }

    public static int getYear(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(time);
        return cal.get(Calendar.YEAR);
    }


    public static long getStartTimeDayAgo(int i) {
        Calendar calendar = Calendar.getInstance();
        calendar.add(Calendar.DATE, -i);
        calendar.set(Calendar.MINUTE, 0);
        calendar.set(Calendar.SECOND, 0);
        calendar.set(Calendar.MILLISECOND, 0);
        calendar.set(Calendar.HOUR_OF_DAY, 0);
        return calendar.getTimeInMillis();
    }


    public static long getToDay() {
        Calendar calendar = Calendar.getInstance();
        calendar.setTimeInMillis(System.currentTimeMillis());
        calendar.set(Calendar.MINUTE, 0);
        calendar.set(Calendar.SECOND, 0);
        calendar.set(Calendar.MILLISECOND, 0);
        calendar.set(Calendar.HOUR_OF_DAY, 0);
        return calendar.getTimeInMillis();
    }


    public static String normalizeDateYYYYMMDD(Date input) {
        return sdfFile.format(input);
    }

    public static String normalizeDateYYYYMMDD(Long input) {
        return sdfFile.format(new Date(input));
    }

    public static String normalizeDateYYYYMMDDHHmm(Long input) {
        return sdfFileHour.format(new Date(input));
    }

    public static String normalizeDateYYYYMMDDHHmmss(Long input) {
        return sdfFileFull.format(new Date(input));
    }


    public static long getStartTimeOfCurrentWeek(long time) {
        Calendar c = Calendar.getInstance();
        if (isSunday(time)) {
            c.setTimeInMillis(time - 1 * Utils.TIME_DAY);
        } else {
            c.setTimeInMillis(time);
        }
        c.set(Calendar.DAY_OF_WEEK, Calendar.MONDAY);
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.clear(Calendar.MINUTE);
        c.clear(Calendar.SECOND);
        c.clear(Calendar.MILLISECOND);
        return c.getTimeInMillis();
    }

    public static boolean isSunday(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(time);
        if (cal.get(Calendar.DAY_OF_WEEK) == Calendar.SUNDAY) {
            return true;
        }
        return false;
    }

    public static int getCurrentMinute() {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date());
        return cal.get(Calendar.MINUTE);
    }

    public static int getCurrentMinute(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date(time));
        return cal.get(Calendar.MINUTE);
    }

    public static int getCurrentSecond() {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date());
        return cal.get(Calendar.SECOND);
    }


    public static void sleep(Long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            LOG.error("(sleep) sleep error", e);
        }
    }

    public static String formatMoney(Float revenue) {
        if (revenue == null) {
            return null;
        }
        // Dùng Float.toString() để lấy đúng giá trị hiển thị,
        // sau đó bọc qua BigDecimal để loại bỏ các số 0 thừa ở đuôi (ví dụ 0.1000 -> 0.1)
        // Tuyệt đối không dùng DecimalFormat với Float vì sẽ bị ép kiểu sang Double sinh ra rác!
        return new java.math.BigDecimal(revenue.toString()).stripTrailingZeros().toPlainString();
    }

    public static String formatMoneyNew(Float revenue) {
        if (revenue == null) {
            return null;
        }
        // Tương tự formatMoney nhưng có thể giữ nguyên nếu bạn chỉ cần 2 số thập phân
        // Hoặc an toàn nhất là dùng BigDecimal như trên và setScale(2)
        return new java.math.BigDecimal(revenue.toString())
                .setScale(2, java.math.RoundingMode.HALF_DOWN)
                .stripTrailingZeros()
                .toPlainString();
    }


    public static String formatPercent(Float number) {
        return df.format(number * 100);
    }

    public static String formatPercentNew(Float number) {
        return dfNew.format(number * 100);
    }


    public static Float rateOf2Double(Float start, Float end) {
        try {
            return (start - end) / end;
        } catch (Exception e) {
        }
        return 0.0f;
    }


    public static Float calPriceTarget(String symbol, Float priceEntry, OrderSide orderSide, Float rateTarget) {
        Float result;
        Float priceChange2Target = rateTarget * priceEntry;
        if (orderSide.equals(OrderSide.BUY)) {
            result = priceEntry + priceChange2Target;
        } else {
            result = priceEntry - priceChange2Target;
        }

        result = ClientSingleton.getInstance().normalizePrice(symbol, result);
        return result;
    }

    public static Float calQuantity(Float budget, Integer leverage, Float priceEntry, String symbol) {
        Float quantity = budget * leverage / priceEntry;
        quantity = ClientSingleton.getInstance().normalizeQuantity(symbol, quantity);
        for (int i = 1; i < 10; i++) {
            if (quantity == 0) {
                quantity = (budget + i) * leverage / priceEntry;
                quantity = ClientSingleton.getInstance().normalizeQuantity(symbol, quantity);
            } else {
                return quantity;
            }
        }
        if (quantity == 0) {
            quantity = ClientSingleton.getInstance().getMinQuantity(symbol);
        }
        return quantity;
    }

    public static Float calQuantityTest(Float budget, Integer leverage, Float priceEntry, String symbol) {
        Float quantity = budget * leverage / priceEntry;
        quantity = ClientSingleton.getInstance().normalizeQuantityTest(symbol, quantity);
        for (int i = 1; i < 10; i++) {
            if (quantity == 0) {
                quantity = (budget + i) * leverage / priceEntry;
                quantity = ClientSingleton.getInstance().normalizeQuantityTest(symbol, quantity);
            } else {
                return quantity;
            }
        }
        if (quantity == 0) {
            quantity = ClientSingleton.getInstance().getMinQuantity(symbol);
        }
        return quantity;
    }

    public static <T> T subList(List lines, int limit) {
        List<List<Object>> results = new ArrayList();
        int start = 0;
//        LOG.info("size: {} start:{} end:{}", lines.size(), lines.get(0), lines.get(lines.size() - 1));
        while (true) {
            if (start > lines.size()) {
                break;
            }
            int end = start + limit;
            if (end > lines.size() - 1) {
                end = lines.size();
            }
            List<Object> data = lines.subList(start, end);
            if (!data.isEmpty()) {
                results.add(data);
//                LOG.info("size: {} start:{} end:{}", data.size(), data.get(0), data.get(data.size() - 1));
            } else {
                break;
            }
            start = end;
        }
        return (T) results;
    }

    public static <T> T subListPartInput(List lines, int part) {
        List<List<Object>> results = new ArrayList();
        int limit = lines.size() / part + 1;
        int start = 0;
//        LOG.info("size: {} start:{} end:{}", lines.size(), lines.get(0), lines.get(lines.size() - 1));
        while (true) {
            if (start > lines.size()) {
                break;
            }
            int end = start + limit;
            if (end > lines.size() - 1) {
                end = lines.size();
            }
            List<Object> data = lines.subList(start, end);
            if (!data.isEmpty()) {
                results.add(data);
//                LOG.info("size: {} start:{} end:{}", data.size(), data.get(0), data.get(data.size() - 1));
            } else {
                break;
            }
            start = end;
        }
        return (T) results;
    }

    public static <T> T subList(Set lines, int limit) {
        List<List<Object>> results = new ArrayList();
        int start = 0;
        List datas = new ArrayList<>(lines);
        while (true) {
            if (start > datas.size()) {
                break;
            }
            int end = start + limit;
            if (end > datas.size() - 1) {
                end = datas.size();
            }
            List<Object> data = datas.subList(start, end);
            if (!data.isEmpty()) {
                results.add(data);
            } else {
                break;
            }
            start = end;
        }
        return (T) results;
    }

    public static Set subSet(Set lines, int limit) {
        Set<Set<Object>> results = new HashSet<>();
        int start = 0;
        List datas = new ArrayList<>(lines);
        while (true) {
            if (start > datas.size()) {
                break;
            }
            int end = start + limit;
            if (end > datas.size() - 1) {
                end = datas.size();
            }
            List<Object> data = datas.subList(start, end);
            if (!data.isEmpty()) {
                results.add(new HashSet<>(data));
            } else {
                break;
            }
            start = end;
        }
        return results;
    }

    public static KlineObjectNumber convertKlineSimple(KlineObjectSimple ticker) {
        KlineObjectNumber result = new KlineObjectNumber();
        result.priceOpen = ticker.priceOpen;
        result.priceClose = ticker.priceClose;
        result.minPrice = ticker.minPrice;
        result.maxPrice = ticker.maxPrice;
        result.startTime = ticker.startTime;
        result.totalUsdt = ticker.totalUsdt;
        return result;
    }


    public static void main(String[] args) {
//        System.out.println(Utils.sendSms2Skype("test skype"));
//        System.out.println(Utils.normalizeHHmm(System.currentTimeMillis()));
        System.out.println(Utils.calPriceTarget("BSBUSDT", 0.43919724f, OrderSide.SELL, -0.025f));
//        Utils.sendSms2Telegram("test");
//        for (int i = 0; i < 5; i++) {
//            long time = System.currentTimeMillis() - i * Utils.TIME_WEEK;
//            LOG.info("{} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time),
//                    Utils.normalizeDateYYYYMMDDHHmm(Utils.getTimeStartWeek(time)));
//        }
//        try {
//            Long time = Utils.sdfFileHour.parse("20250224 05:38").getTime();
//            LOG.info("{} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time),
//                    Utils.normalizeDateYYYYMMDDHHmm(Utils.getTimeStartWeek(time)));
//        } catch (Exception e) {
//            e.printStackTrace();
//        }

//        checkTickerFalse();
//        testDescendingKeySet();
//        System.out.println(Utils.readSms2Telegram());
//        Float test = 5.1723243E-2;
//        System.out.println(Utils.formatMoneyByPeriod(test, 2));
//        System.out.println(Utils.normalPrice2Api(99.95804261161376d));
//        System.out.println(Utils.normalPrice2Api(991.95804261161376d));
//        System.out.println(Utils.normalPrice2Api(0.14611331d));
//        System.out.println(Utils.normalPrice2Api(0.20008395d));
//        System.out.println(Utils.normalPrice2Api(0.011877d));
//        System.out.println(Utils.normalPrice2Api(48.18981633d));
    }


    public static boolean isTickerAvailable(KlineObjectSimple ticker) {
        if (ticker != null) {
            return ticker.minPrice != ticker.maxPrice
                    || ticker.totalUsdt != 0;
        }
        return false;
    }

    public static String toJson(Object ob) {
        return gson.toJson(ob);
    }

    public static long getHour(long time) {
        return (time / TIME_HOUR) * TIME_HOUR;
    }

    public static long getMinute(long time) {
        return (time / TIME_MINUTE) * TIME_MINUTE;
    }

    public static long get4Hour(long time) {
        return (time / 4 / TIME_HOUR) * 4 * TIME_HOUR;
    }


    public static long getDate(long time) {
        return (time / TIME_DAY) * TIME_DAY;
    }

    public static String getMonth(long time) {
        return Utils.sdfMonth.format(new Date(time));
    }


    public static String formatDouble(Float volume, Integer number) {
        String format = "###.";
        for (int i = 0; i < number; i++) {
            format += "#";
        }
        DecimalFormat formatter = new DecimalFormat(format);
        return formatter.format(volume);
    }


    public static Float findMinSubarraySum(Float[] numbers) {
        if (numbers.length == 0) {
            throw new IllegalArgumentException("Dãy số phải có ít nhất 1 phần tử.");
        }

        // Khởi tạo giá trị tổng nhỏ nhất và tổng nhỏ nhất hiện tại bằng phần tử đầu tiên
        float minSum = numbers[0];
        float currentSum = numbers[0];

        // Duyệt qua mảng từ phần tử thứ hai
        for (int i = 1; i < numbers.length; i++) {
            // Tìm tổng nhỏ nhất hiện tại, nếu số hiện tại nhỏ hơn tổng hiện tại, ta chọn số hiện tại
            currentSum = Math.min(numbers[i], currentSum + numbers[i]);
            // Cập nhật tổng nhỏ nhất
            float minSumNew = Math.min(minSum, currentSum);
            if (minSumNew < minSum) {
                minSum = Math.min(minSum, currentSum);
            }
        }

        return minSum;
    }


    public static String formatLog(Object obj, int length) {
        String marginMax = String.valueOf(obj);
        while (marginMax.length() < length) {
            marginMax = " " + marginMax;
        }
        return marginMax;
    }


    public static Float maxPrice(KlineObjectNumber ticker, Float maxPrice) {
        if (maxPrice == null || maxPrice < ticker.maxPrice) {
            maxPrice = ticker.maxPrice;
        }
        return maxPrice;
    }

    public static Float maxPrice(KlineObjectSimple ticker, Float maxPrice) {
        if (maxPrice == null || maxPrice < ticker.maxPrice) {
            maxPrice = ticker.maxPrice;
        }
        return maxPrice;
    }

    public static Float minPrice(KlineObjectNumber ticker, Float minPrice) {
        if (minPrice == null || minPrice > ticker.minPrice) {
            minPrice = ticker.minPrice;
        }
        return minPrice;
    }

    public static void reset(String resetBySchedule) {
        try {
            while (true) {
                if (Utils.getCurrentSecond() > 30 && Utils.getCurrentSecond() < 45) {
                    break;
                }
                Thread.sleep(1000);
            }
            LOG.info("Restart: {} {} ...", resetBySchedule, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));

            // Lấy đường dẫn tới Java binary
            String javaBin = System.getProperty("java.home") + "/bin/java";

            // Lấy classpath của chương trình hiện tại
            String classPath = System.getProperty("java.class.path");

            // Lấy tên class chính (main class)
            String mainClass = System.getProperty("sun.java.command");

            // Tạo ProcessBuilder
            ProcessBuilder processBuilder = new ProcessBuilder(
                    javaBin,
                    "-cp",
                    classPath,
                    mainClass
            );

            // Sao chép các biến môi trường từ chương trình hiện tại
            Map<String, String> currentEnvironment = System.getenv();
            Map<String, String> processEnvironment = processBuilder.environment();
            processEnvironment.putAll(currentEnvironment);

            // Kế thừa IO (input/output) để output của chương trình mới xuất hiện trong console hiện tại
            processBuilder.inheritIO();

            // Khởi động lại chương trình
            processBuilder.start();

            // Thoát chương trình hiện tại
            System.exit(0);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static Float minPrice(KlineObjectSimple ticker, Float minPrice) {
        if (minPrice == null || minPrice > ticker.minPrice) {
            minPrice = ticker.minPrice;
        }
        return minPrice;
    }

    public static void writePid2File() {
        // --- BẮT ĐẦU ĐOẠN CODE GHI PID MỚI ---
        try {
            // 1. Lấy biến môi trường (giống hệt logic trong daemon.sh)
            String pidDir = System.getenv("APP_PID_DIR");
            String mainClass = System.getenv("APP_MAIN_CLASS");
            LOG.info("MainClass: {} APPDir: {}", mainClass, pidDir);

            // 2. Áp dụng giá trị mặc định (giống hệt logic trong daemon.sh)
            if (pidDir == null || pidDir.isEmpty()) {
                pidDir = "/run";
            }

            if (mainClass != null && !mainClass.isEmpty()) {
                // 3. Lấy PID của tiến trình Java hiện tại
                // Cách 1: Hiện đại (Java 9+)
                long pid = ProcessHandle.current().pid();

                // Cách 2: Truyền thống (Java 8 và cũ hơn)
                // String pidName = ManagementFactory.getRuntimeMXBean().getName();
                // long pid = Long.parseLong(pidName.split("@")[0]);

                // 4. Ghi PID vào file
                String pidFilePath = pidDir + "/" + mainClass + ".pid";
                Files.write(
                        Paths.get(pidFilePath),
                        String.valueOf(pid).getBytes(),
                        StandardOpenOption.CREATE,
                        StandardOpenOption.TRUNCATE_EXISTING // Ghi đè file cũ (nếu có)
                );

                // 5. (Nên làm) Thêm Shutdown Hook để xóa file PID khi thoát
                // Điều này mô phỏng hành vi "rm -f $pid" của hàm stop
                final String finalPidFilePath = pidFilePath;
                Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                    try {
                        Files.deleteIfExists(Paths.get(finalPidFilePath));
                    } catch (Exception e) {
                        // Bỏ qua nếu có lỗi
                    }
                }));

                LOG.info("PID " + pid + " written to " + pidFilePath);
            }
        } catch (Exception e) {
            LOG.error("Failed to write PID file: " + e.getMessage());
            // Bạn có thể quyết định thoát nếu không ghi được PID
            // System.exit(1);
        }
        // --- KẾT THÚC ĐOẠN CODE GHI PID ---
    }

    public static void printMemoryUse(long duration) {
        Runtime runtime = Runtime.getRuntime();
        long usedMem = (runtime.totalMemory() - runtime.freeMemory()) / (1024 * 1024);
        LOG.info(". RAM Used: {} MB duration: {} seconds", usedMem, duration / Utils.TIME_SECOND);
    }

    public static void printMemoryUsage(String stepName) {
        System.gc(); // Ép dọn rác
        try {
            Thread.sleep(500);
        } catch (InterruptedException e) {
        } // Chờ GC chạy xong
        Runtime rt = Runtime.getRuntime();
        long usedMB = (rt.totalMemory() - rt.freeMemory()) / (1024 * 1024);
        LOG.info("💾 RAM SAU KHI [{}]: {} MB", stepName, usedMB);
    }
}
