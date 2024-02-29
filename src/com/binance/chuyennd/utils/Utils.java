/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.binance.chuyennd.utils;

import com.alibaba.fastjson.JSONObject;
import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.PositionRisk;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.gson.*;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.math.BigInteger;
import java.net.URL;
import java.net.URLConnection;
import java.net.URLEncoder;
import java.security.MessageDigest;
import java.text.*;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import okhttp3.FormBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

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
    public static ObjectMapper mapper = new ObjectMapper();

    public static final SimpleDateFormat sdf = new SimpleDateFormat("dd/MM/yyyy");
    public static final SimpleDateFormat sdfFile = new SimpleDateFormat("yyyyMMdd");
    public static final SimpleDateFormat sdfFileHour = new SimpleDateFormat("yyyyMMdd HH:mm");
    public static final SimpleDateFormat sdfFacebook = new SimpleDateFormat("dd/MM/yyyy HH:mm:ss");
    public static final SimpleDateFormat sdfGoogle = new SimpleDateFormat("yyyy-M-dd HH:mm:ss");
    public static final SimpleDateFormat SDF_NORMAL = new SimpleDateFormat("E MMM dd HH:mm:ss z yyyy");
    public static final DecimalFormat df = new DecimalFormat("#.##");

    public static String converObject2Json(Object data) {
        try {
            return mapper.writeValueAsString(data);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return "{}";
    }

    public static double marginOfPosition(PositionRisk pos) {
        return Math.abs((pos.getPositionAmt().doubleValue() * pos.getEntryPrice().doubleValue() / pos.getLeverage().doubleValue()));
    }

    public static String getMainClassAndArgs() {
        return System.getProperty("sun.java.command"); // like "org.x.y.Main arg1 arg2"
    }

    public static String convertVietnamese2English(String str) {
        String nfdNormalizedString = Normalizer.normalize(str, Normalizer.Form.NFD);
        Pattern pattern = Pattern.compile("\\p{InCombiningDiacriticalMarks}+");
        return pattern.matcher(nfdNormalizedString).replaceAll("");
    }

    public static String extractNumberFromString(String str) {
        return str.replaceAll("\\D+", "");
    }

    public static Collection<? extends String> extractUrlMp4FromJson(String json) {
        List<String> containedUrls = new ArrayList<String>();
//        String urlRegex = "((https?|ftp|gopher|telnet|file):((//)|(\\\\))+[\\w\\d:#@%/;$()~_?\\+-=\\\\\\.&]*)";
        String urlRegex = "((https?|ftp|gopher|telnet|file):((//)|(\\\\))+[\\w\\d:#@%/;$()~_?\\+-=\\\\\\.& ']*)";

        Pattern pattern = Pattern.compile(urlRegex, Pattern.CASE_INSENSITIVE);
        Matcher urlMatcher = pattern.matcher(json);

        while (urlMatcher.find()) {
            String url = json.substring(urlMatcher.start(0),
                    urlMatcher.end(0));
            if (StringUtils.endsWith(url, "mp4")) {
                containedUrls.add(url);
//                System.out.println(url);
            }
        }

        return containedUrls;
    }

    public static boolean sendSms2Telegram(String text) {
        String urlString = "https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s";

        //Add Telegram token (given Token is fake)
        String apiToken = "6158571844:AAHgemRZAWCFARpkyiZkpc9iTT4hEKMtUvw";

        //Add chatId (given chatId is fake)
        String chatId = "6548680563";

        urlString = String.format(urlString, apiToken, chatId, URLEncoder.encode(text));

        try {
            URL url = new URL(urlString);
            URLConnection conn = url.openConnection();
            InputStream is = new BufferedInputStream(conn.getInputStream());
        } catch (IOException e) {
            e.printStackTrace();
        }
        return true;
    }

    public static boolean sendSms2Skype(String text) {
        String urlString = "https://dev-crm-202x.edupia.vn/api/skype/send-advance";
        //Add chatId (given chatId is fake)
        String chatId = "8:chuyenvan";
        JSONObject body = new JSONObject();
        body.put("topic", chatId);
        body.put("content", text);
        try {
            String respon = HttpRequest.httpPostWithJson(urlString, body.toJSONString());
            System.out.println(respon);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return true;
    }

    public static HashMap<String, Object> createHashMapFromJsonString(String json) {
        JsonObject object = new JsonParser().parse(json).getAsJsonObject();
        Set<Map.Entry<String, JsonElement>> set = object.entrySet();
        Iterator<Map.Entry<String, JsonElement>> iterator = set.iterator();
        HashMap<String, Object> map = new HashMap<>();

        while (iterator.hasNext()) {

            Map.Entry<String, JsonElement> entry = iterator.next();
            String key = entry.getKey();
            JsonElement value = entry.getValue();

            if (null != value) {
                if (!value.isJsonPrimitive()) {
                    if (value.isJsonObject()) {

                        map.put(key, createHashMapFromJsonString(value.toString()));
                    } else if (value.isJsonArray() && value.toString().contains(":")) {

                        List<HashMap<String, Object>> list = new ArrayList<>();
                        JsonArray array = value.getAsJsonArray();
                        if (null != array) {
                            for (JsonElement element : array) {
                                list.add(createHashMapFromJsonString(element.toString()));
                            }
                            map.put(key, list);
                        }
                    } else if (value.isJsonArray() && !value.toString().contains(":")) {
                        map.put(key, value.getAsJsonArray());
                    }
                } else {
                    map.put(key, value.getAsString());
                }
            }
        }
        return map;
    }

    public static Long calTimeLearn(List<Long> times) {
        long result = 0;
        try {
            long timeStartLearn = 300000;
            long timeAvg = 3600000;
            Integer sessionIndex = 0;
            long startTimeSession = 0;
            long endTimeSession = 0;
            Map<Integer, Long> userLessionTime = new HashMap();

            // truong hop 1 bt duy nhat
            if (times.size() == 1) {
                return timeStartLearn;
            }
            // truong hop 2 bt tro len
            int counter = 0;
            for (Long time : times) {
                counter++;
                if (startTimeSession == 0) {
                    startTimeSession = time - timeStartLearn;
                    endTimeSession = time;
                    continue;
                }
                if (time - endTimeSession > timeAvg) {
                    sessionIndex++;
                    userLessionTime.put(sessionIndex, endTimeSession - startTimeSession);
                    startTimeSession = time - timeStartLearn;
                    endTimeSession = time;
                } else {
                    endTimeSession = time;
                }
                // check time cuoi => add list
                if (counter == times.size()) {
                    sessionIndex++;
                    userLessionTime.put(sessionIndex, endTimeSession - startTimeSession);
                }
            }
            for (Long time : userLessionTime.values()) {
                result += time;
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return result;
    }

    public static String convertToMD5(String input) throws Exception {
        String md5 = null;
        if (null == input) {
            return null;
        }
        try {
            // Create MessageDigest object for MD5
            MessageDigest digest = MessageDigest.getInstance("MD5");
            // Update input string in message digest
            digest.update(input.getBytes(), 0, input.length());
            // Converts message digest value in base 16 (hex)
            md5 = new BigInteger(1, digest.digest()).toString(16);
            while (StringUtils.length(md5) < 32) {
                md5 = "0" + md5;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return md5;
    }

    public static String getWeekOfTime(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(time);
        time = getStartTimeOfCurrentWeek(time);
        return getMonthByTime(time) + "-" + String.valueOf(cal.get(Calendar.WEEK_OF_YEAR));
    }

    public static int getWeekOfYear(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(time);
        return cal.get(Calendar.WEEK_OF_YEAR);
    }

    public static int getMonthOfYear(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(time);
        return cal.get(Calendar.MONTH);
    }

    public static int getYear(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(time);
        return cal.get(Calendar.YEAR);
    }

    public static String getWeekOfYearStr(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(time);
        return cal.get(Calendar.YEAR) + "-" + cal.get(Calendar.WEEK_OF_YEAR);
    }

    public static String getMonthByTime(long time) {
        return sdfFile.format(new Date(time)).substring(0, 6);
    }

    public static String getDayByTime(long time) {
        return sdfFile.format(new Date(time));
    }

    public static String getYYYYMM(long time) {
        SimpleDateFormat simpleDateFormat = new SimpleDateFormat("yyyyMM");
        return simpleDateFormat.format(new Date(time));
    }

    public static String getLastMonth() {
        Calendar calendar = Calendar.getInstance();
        calendar.add(Calendar.MONTH, -1);
        int max = calendar.getActualMaximum(Calendar.DAY_OF_MONTH);
        calendar.set(Calendar.DAY_OF_MONTH, max);
        return sdfFile.format(calendar.getTime()).substring(0, 6);
    }

    public static Date getDateLastMonth() {
        Calendar calendar = Calendar.getInstance();
        calendar.add(Calendar.MONTH, -1);
        int max = calendar.getActualMaximum(Calendar.DAY_OF_MONTH);
        calendar.set(Calendar.DAY_OF_MONTH, max);
        return calendar.getTime();
    }

    public static Date getLastMonthDate() {
        Calendar calendar = Calendar.getInstance();
        calendar.add(Calendar.MONTH, -1);
        int max = calendar.getActualMaximum(Calendar.DAY_OF_MONTH);
        calendar.set(Calendar.DAY_OF_MONTH, max);
        return calendar.getTime();
    }

    public static long getStartTimeLastMonth() {
        Calendar calendar = Calendar.getInstance();
        calendar.add(Calendar.MONTH, -1);
        int min = calendar.getActualMinimum(Calendar.DAY_OF_MONTH);
        calendar.set(Calendar.DAY_OF_MONTH, min);
        calendar.set(Calendar.MINUTE, 0);
        calendar.set(Calendar.SECOND, 0);
        calendar.set(Calendar.MILLISECOND, 0);
        calendar.set(Calendar.HOUR_OF_DAY, 0);
        return calendar.getTimeInMillis();
    }

    public static long getStartTimeNextMonth() {
        Calendar calendar = Calendar.getInstance();
        calendar.add(Calendar.MONTH, 1);
        int min = calendar.getActualMinimum(Calendar.DAY_OF_MONTH);
        calendar.set(Calendar.DAY_OF_MONTH, min);
        calendar.set(Calendar.MINUTE, 0);
        calendar.set(Calendar.SECOND, 0);
        calendar.set(Calendar.MILLISECOND, 0);
        calendar.set(Calendar.HOUR_OF_DAY, 0);
        return calendar.getTimeInMillis();
    }

    public static long getStartTimeMonth(long time) {
        Calendar calendar = Calendar.getInstance();
        calendar.setTimeInMillis(time);

        int min = calendar.getActualMinimum(Calendar.DAY_OF_MONTH);
        calendar.set(Calendar.DAY_OF_MONTH, min);
        calendar.set(Calendar.MINUTE, 0);
        calendar.set(Calendar.SECOND, 0);
        calendar.set(Calendar.MILLISECOND, 0);
        calendar.set(Calendar.HOUR_OF_DAY, 0);
        return calendar.getTimeInMillis();
    }

    public static long getEndTimeMonth(long time) {
        Calendar calendar = Calendar.getInstance();
        calendar.setTimeInMillis(time);
        int min = calendar.getActualMinimum(Calendar.DAY_OF_MONTH);
        calendar.add(Calendar.MONTH, +1);
        calendar.set(Calendar.DAY_OF_MONTH, min);
        calendar.set(Calendar.MINUTE, 0);
        calendar.set(Calendar.SECOND, 0);
        calendar.set(Calendar.MILLISECOND, 0);
        calendar.set(Calendar.HOUR_OF_DAY, 0);
        return calendar.getTimeInMillis() - 1;
    }

    public static long getStartTimeMonthAgo(int i) {
        Calendar calendar = Calendar.getInstance();
        calendar.add(Calendar.MONTH, -i);
        int min = calendar.getActualMinimum(Calendar.DAY_OF_MONTH);
        calendar.set(Calendar.DAY_OF_MONTH, min);
        calendar.set(Calendar.MINUTE, 0);
        calendar.set(Calendar.SECOND, 0);
        calendar.set(Calendar.MILLISECOND, 0);
        calendar.set(Calendar.HOUR_OF_DAY, 0);
        return calendar.getTimeInMillis();
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

    public static long getStartTimeDayNext(int i) {
        Calendar calendar = Calendar.getInstance();
        calendar.add(Calendar.DATE, i);
        calendar.set(Calendar.MINUTE, 0);
        calendar.set(Calendar.SECOND, 0);
        calendar.set(Calendar.MILLISECOND, 0);
        calendar.set(Calendar.HOUR_OF_DAY, 0);
        return calendar.getTimeInMillis();
    }

    public static String getCurrentMonth() {
        Calendar calendar = Calendar.getInstance();
        calendar.add(Calendar.MONTH, 0);
        int max = calendar.getActualMaximum(Calendar.DAY_OF_MONTH);
        calendar.set(Calendar.DAY_OF_MONTH, max);
        return sdfFile.format(calendar.getTime()).substring(0, 6);
    }

    public static int getCurrentMonthInt() {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date());
        return cal.get(Calendar.MONTH) + 1;
    }

    public static Date getCurrentMonthDate() {
        Calendar calendar = Calendar.getInstance();
        calendar.add(Calendar.MONTH, 0);
        int max = calendar.getActualMaximum(Calendar.DAY_OF_MONTH);
        calendar.set(Calendar.DAY_OF_MONTH, max);
        return calendar.getTime();
    }

    public static int getMonthOfTime(long time) {
        Calendar cal = Calendar.getInstance();
        Date date = new Date(time);
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(date);
        return cal.get(Calendar.MONTH) + 1;
    }

    public static int getDayOfTime(long time) {
        Calendar cal = Calendar.getInstance();
        Date date = new Date(time);
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(date);
        return cal.get(Calendar.DATE);
    }

    public static String getMonthStringOfTime(Long time) {
        return sdfFile.format(new Date(time)).substring(0, 6);
    }

    public static <T> byte[] serializeObj(T obj) throws IOException {

        byte[] result = null;
        try (
                 ByteArrayOutputStream baos = new ByteArrayOutputStream();  ObjectOutputStream oos = new ObjectOutputStream(baos)) {
            oos.writeObject(obj);
            result = baos.toByteArray();
        }

        return result;
    }

    public static <T> T deserializeObj(byte[] input) throws IOException {
        if (input == null) {
            return null;
        }
        try (
                 ByteArrayInputStream bais = new ByteArrayInputStream(input);  ObjectInputStream ois = new ObjectInputStream(bais);) {
            return (T) ois.readObject();
        } catch (ClassNotFoundException e) {
            e.printStackTrace();
        }
        return null;
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

    public static String twoWeekAgo() {
        final int NUMBER_OF_DAYS_AGO = -14;
        DateFormat format = new SimpleDateFormat("yyyy-mm-dd");
        format.setLenient(true);
        Calendar cal = Calendar.getInstance();
        cal.setTime(new Date());
        cal.add(Calendar.DATE, NUMBER_OF_DAYS_AGO);
        String stopDate = DateFormat.getDateInstance().format(cal.getTime());
        System.out.println(stopDate);

        return stopDate;
    }

    public static String getToDayFileName() {
        return sdfFile.format(new Date());
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

    public static List<String> getLastWeekFileName() {
        List<String> result = new ArrayList();
        long startTimeLastWeek = getStartTimeOfLastWeek();
        for (int i = 0; i < 7; i++) {
            Calendar calendar = Calendar.getInstance();
            calendar.setTimeInMillis(startTimeLastWeek + i * TIME_DAY);
            calendar.set(Calendar.MINUTE, 0);
            calendar.set(Calendar.SECOND, 0);
            calendar.set(Calendar.MILLISECOND, 0);
            calendar.set(Calendar.HOUR_OF_DAY, 0);
            result.add(sdfFile.format(calendar.getTime()));
        }
        return result;
    }

    public static List<String> getAllFileNameFromTime(long time) {
        List<String> result = new ArrayList();
        long timeCal = System.currentTimeMillis();
        result.add(sdfFile.format(timeCal));
        while (true) {
            timeCal = timeCal - TIME_DAY;
            if (timeCal < time) {
                break;
            }
            result.add(sdfFile.format(timeCal));
        }
        return result;
    }

    public static long getStartTimeOfCurrentWeek() {
        long time = System.currentTimeMillis();
        return getStartTimeOfCurrentWeek(time);
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

    public static long getStartTimeOfCurrentMonth() {
        long time = System.currentTimeMillis();
        return getStartTimeOfCurrentWeek(time);
    }

    public static long getStartTimeOfCurrentMonth(long time) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(time);
        c.set(Calendar.DATE, 1);
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.clear(Calendar.MINUTE);
        c.clear(Calendar.SECOND);
        c.clear(Calendar.MILLISECOND);
        return c.getTimeInMillis();
    }

    public static long getStartTimeOfDay(long time) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(time);
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.clear(Calendar.MINUTE);
        c.clear(Calendar.SECOND);
        c.clear(Calendar.MILLISECOND);
        return c.getTimeInMillis();
    }

    public static long getEndTimeOfDay(long time) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(time);
        c.set(Calendar.HOUR_OF_DAY, 23);
        c.set(Calendar.MINUTE, 59);
        c.set(Calendar.SECOND, 59);
//        c.clear(Calendar.MINUTE);
//        c.clear(Calendar.SECOND);
        c.clear(Calendar.MILLISECOND);
        return c.getTimeInMillis();
    }

    public static long getStartTimeOfYesterday() {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(System.currentTimeMillis());
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.clear(Calendar.MINUTE);
        c.clear(Calendar.SECOND);
        c.clear(Calendar.MILLISECOND);
        return c.getTimeInMillis() - TIME_DAY;
    }

    public static long removeSecond(long time) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(time);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        return c.getTimeInMillis();
    }

    public static long removeMinute(long time) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(time);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        return c.getTimeInMillis();
    }

    public static long removeHour(long time) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(time);
        c.set(Calendar.HOUR, 0);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        return c.getTimeInMillis();
    }

    public static long getEndTimeOfYesterday() {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(System.currentTimeMillis());
        c.set(Calendar.HOUR_OF_DAY, 23);
        c.set(Calendar.MINUTE, 59);
        c.set(Calendar.SECOND, 59);
        c.clear(Calendar.MILLISECOND);
        return c.getTimeInMillis() - TIME_DAY;
    }

    public static long getStartTime22hYesterday() {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(System.currentTimeMillis());
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.clear(Calendar.MINUTE);
        c.clear(Calendar.SECOND);
        c.clear(Calendar.MILLISECOND);
        return c.getTimeInMillis() - 2 * TIME_HOUR;
    }

    public static boolean isSunday(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(time);
        if (cal.get(Calendar.DAY_OF_WEEK) == Calendar.SUNDAY) {
            return true;
        }
        return false;
    }

    public static long getStartTime(int numberOfDaysAgo) {
        return getToDay() - numberOfDaysAgo * TIME_DAY;
    }

    public static long getStartTimeOfLastWeek() {
        return getStartTimeOfCurrentWeek() - TIME_WEEK;
    }

    public static long getEndTimeOfLastWeek() {
        return getStartTimeOfCurrentWeek() - 1;
    }

    public static String genLastWeekNumber(String startTime) {
        if (StringUtils.isEmpty(startTime)) {
            return "";
        }
        Long timeStart = Long.parseLong(startTime);
        Long weekNumber = (getStartTimeOfCurrentWeek() - timeStart) / TIME_WEEK;
        if (weekNumber > 0) {
            return "tuần " + String.valueOf(weekNumber);
        } else {
            return "";
        }
    }

    public static boolean isTodayStartOfWeek() {
        Calendar cal = Calendar.getInstance();
        cal.setTime(new Date());
        return cal.get(Calendar.DAY_OF_WEEK) == Calendar.MONDAY;
    }

    public static int getCurrentMinute() {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date());
        return cal.get(Calendar.MINUTE);
    }

    public static int getCurrentSecond() {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date());
        return cal.get(Calendar.SECOND);
    }

    public static int getYesterdayDay() {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date());
        cal.add(Calendar.DATE, -1);
        return cal.get(Calendar.DATE);
    }

    public static int getCurrentDay() {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date());
        return cal.get(Calendar.DATE);
    }

    public static int getCurrentDayOfWeek() {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date());
        return cal.get(Calendar.DAY_OF_WEEK);
    }

    public static int getDayOfWeek(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date(time));
        return cal.get(Calendar.DAY_OF_WEEK);
    }

    public static boolean isTodayStartOfMonth() {
        Calendar cal = Calendar.getInstance();
        cal.setTime(new Date());
        return cal.get(Calendar.DAY_OF_MONTH) == 0;
    }

    public static String genDurationLastWeek() {
        String lastWeekStartDay = sdf.format(new Date(getStartTimeOfLastWeek()));
        String lastWeekEndDay = sdf.format(new Date(getStartTimeOfCurrentWeek() - TIME_DAY - 1));
        return "ngày " + lastWeekStartDay + " đến ngày " + lastWeekEndDay;
    }

    public static int getCurrentHour(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date(time));
        return cal.get(Calendar.HOUR_OF_DAY);
    }

    public static int getCurrentHour() {
        Calendar cal = Calendar.getInstance();
        cal.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        cal.setTime(new Date());
        return cal.get(Calendar.HOUR_OF_DAY);
    }

    public static boolean isStartWeek() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_WEEK) == 2 && getCurrentHour(System.currentTimeMillis()) == 1);
    }

    public static boolean is8hMondayOfWeekly() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_WEEK) == 2 && getCurrentHour(System.currentTimeMillis()) == 8 && getCurrentMinute() == 1);
    }

    public static boolean is9h30MondayOfWeekly() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_WEEK) == 2 && getCurrentHour(System.currentTimeMillis()) == 9 && getCurrentMinute() == 30);
    }

    public static boolean is7hOMondayOfWeekly() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_WEEK) == 2 && getCurrentHour(System.currentTimeMillis()) == 7 && getCurrentMinute() == 1);
    }

    public static boolean is8OclockTuesdayOfWeekly() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_WEEK) == 3 && getCurrentHour(System.currentTimeMillis()) == 8);
    }

    public static boolean isEndWeek() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_WEEK) == 7 && getCurrentHour(System.currentTimeMillis()) == 4);
    }

    public static boolean isTimeChooseCompetitor() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_WEEK) == Calendar.MONDAY && getCurrentHour(System.currentTimeMillis()) == 1);
    }

    public static boolean isTimeBuildCompetitor() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_WEEK) == Calendar.MONDAY && getCurrentHour(System.currentTimeMillis()) == 4);
    }

    public static boolean isEvenNumberWeek() {
        Calendar now = Calendar.getInstance();
        if ((now.get(Calendar.DAY_OF_WEEK) == Calendar.MONDAY && getCurrentHour(System.currentTimeMillis()) == 1)) {
            return true;
        }
        if ((now.get(Calendar.DAY_OF_WEEK) == Calendar.WEDNESDAY && getCurrentHour(System.currentTimeMillis()) == 1)) {
            return true;
        }
        if ((now.get(Calendar.DAY_OF_WEEK) == Calendar.FRIDAY && getCurrentHour(System.currentTimeMillis()) == 1)) {
            return true;
        }
        if ((now.get(Calendar.DAY_OF_WEEK) == Calendar.SUNDAY && getCurrentHour(System.currentTimeMillis()) == 1)) {
            return true;
        }
        return false;
    }

    public static boolean isStartDay() {
        return (getCurrentHour(System.currentTimeMillis()) == 1);
    }

    public static boolean isEndDay() {
        return (getCurrentHour(System.currentTimeMillis()) == 23);
    }

    public static boolean isTenPM() {
        return (getCurrentHour(System.currentTimeMillis()) == 22);
    }

    public static boolean isThreeAM() {
        return (getCurrentHour(System.currentTimeMillis()) == 3);
    }

    public static boolean isSevenAM() {
        return (getCurrentHour(System.currentTimeMillis()) == 7);
    }

    public static boolean isTimeSendSkypeQuickReport() {
        if ((getCurrentHour(System.currentTimeMillis()) == 8 && (getCurrentMinute() >= 30 && getCurrentMinute() <= 59))) {
            return true;
        } else {
            return false;
        }
    }

    public static boolean isNineAM() {
        return (getCurrentHour(System.currentTimeMillis()) == 9);
    }

    public static boolean isElevenAM() {
        return (getCurrentHour(System.currentTimeMillis()) == 11);
    }

    public static boolean isStartMonth() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_MONTH) == 1 && getCurrentHour(System.currentTimeMillis()) == 1);
    }

    public static boolean isStartMonthKid() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_MONTH) == 1 && getCurrentHour(System.currentTimeMillis()) == 2);
    }

    public static boolean isTimeSendPdfReportMonthly() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_MONTH) == 4 && getCurrentHour(System.currentTimeMillis()) == 6);
//        return (now.get(Calendar.DAY_OF_MONTH) == 5 && getCurrentHour(System.currentTimeMillis()) == 11);
    }

    public static boolean isTimeSendPdfReportWeekly() {
        Calendar now = Calendar.getInstance();
        return (now.get(Calendar.DAY_OF_WEEK) == 2 && getCurrentHour(System.currentTimeMillis()) == 6);
    }

    public static Map<String, String> convertJsonElement2Map(JsonElement jelement) {
        Map<String, String> result = new HashMap();
        JsonObject jobject = jelement.getAsJsonObject();
        for (Map.Entry<String, JsonElement> entry : jobject.entrySet()) {
            String key = entry.getKey();
            JsonElement jsonEle = entry.getValue();
            if (!jsonEle.isJsonNull()) {
                if (jsonEle.isJsonObject()) {
                    result.put(key, Utils.gson.toJson(jsonEle));
                } else {
                    result.put(key, jsonEle.getAsString());
                }
            } else {
                result.put(key, "");
            }
        }
        return result;
    }

    public static boolean isAscii(char ch) {
        return ch < 128;
    }

    public static long getEndTimeOfCurrentWeek(long time) {
        long startTimeOfCurrentWeek = getStartTimeOfCurrentWeek(time + TIME_WEEK);
        return startTimeOfCurrentWeek - 1;
    }

    public static void sleep(Long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            LOG.error("(sleep) sleep error", e);
        }
    }

    public static String formatMoney(Double revenue) {
        if (revenue == null) {
            return null;
        }
//        DecimalFormat formatter = new DecimalFormat("###,###,###.#####");
//        DecimalFormat formatter = new DecimalFormat("###,###,###.##########");
        DecimalFormat formatter = new DecimalFormat("###.##########");
        return formatter.format(revenue);
    }

    public static String formatPercent(Double number) {
        return df.format(number * 100);
    }

    public static List<Object> sortObjectByKey(List<Object> objects, String key) {
        List<Object> result = new ArrayList();
        TreeMap<Double, Object> tmap = new TreeMap<>();
        for (Object lesson : objects) {
            JsonElement jelement = (JsonElement) lesson;
            JsonObject jobject = jelement.getAsJsonObject();
            String num = jobject.get(key).getAsString();
            Double number = Double.valueOf(num);
            tmap.put(number, lesson);
        }
        for (Map.Entry<Double, Object> entry1 : tmap.entrySet()) {
            Object value = entry1.getValue();
            result.add(value);
        }
        return result;
    }

    public static Double rateOf2Double(Double start, Double end) {
        try {
            return (start - end) / end;
        } catch (Exception e) {
        }
        return 0.0;
    }

    public static Double calPriceTarget(String symbol, Double priceEntry, OrderSide orderSide, Double rateTarget) {
        Double result = priceEntry;
        int counter = 0;
        while (result.equals(priceEntry)
                || Math.abs(rateOf2Double(priceEntry, result)) < rateTarget) {
            Double priceChange2Target = (rateTarget + 0.0001 * counter) * priceEntry;
            if (orderSide.equals(OrderSide.BUY)) {
                result = priceEntry + priceChange2Target;
            } else {
                result = priceEntry - priceChange2Target;
            }
            result = ClientSingleton.getInstance().normalizePrice(symbol, result);
            counter++;
        }
        return result;
    }

    public static Double calQuantity(Double BUDGET_PER_ORDER, Integer LEVERAGE_ORDER_BEARD, Double priceEntry, String symbol) {
        Double quantity = BUDGET_PER_ORDER * LEVERAGE_ORDER_BEARD / priceEntry;
        quantity = ClientSingleton.getInstance().normalizeQuantity(symbol, quantity);
        for (int i = 1; i < 10; i++) {
            if (quantity == 0) {
                quantity = (BUDGET_PER_ORDER + i) * LEVERAGE_ORDER_BEARD / priceEntry;
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

    public static void main(String[] args) {
        System.out.println(Utils.sendSms2Skype("test skype"));
//        Double test = 5.172E-4;
//        System.out.println(Utils.formatMoney(test));
//        System.out.println(Utils.normalPrice2Api(99.95804261161376d));
//        System.out.println(Utils.normalPrice2Api(991.95804261161376d));
//        System.out.println(Utils.normalPrice2Api(0.14611331d));
//        System.out.println(Utils.normalPrice2Api(0.20008395d));
//        System.out.println(Utils.normalPrice2Api(0.011877d));
//        System.out.println(Utils.normalPrice2Api(48.18981633d));
    }

    public static String toJson(Object ob) {
        return gson.toJson(ob);
    }

    public static long getHour(long time) {
        return (time / TIME_HOUR) * TIME_HOUR;
    }
}
