package com.binance.chuyennd.indicators;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.mongo.TickerMongoHelper;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class SimpleMovingAverage1DManager {
    public static final Logger LOG = LoggerFactory.getLogger(SimpleMovingAverage1DManager.class);
    private ConcurrentHashMap<String, TreeMap<Long, IndicatorEntry>> symbol2MaDetails;
    private static volatile SimpleMovingAverage1DManager INSTANCE = null;
    public static String TIME_RUN = Configs.getString("TIME_RUN");
    private static String FILE_DATA_STORAGE_MA_DETAIL = "storage/simple-moving-average-detail-1d-environment.data";


    public static SimpleMovingAverage1DManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new SimpleMovingAverage1DManager();
            if (StringUtils.isEmpty(TIME_RUN)) {
                FILE_DATA_STORAGE_MA_DETAIL = FILE_DATA_STORAGE_MA_DETAIL.replace("environment", "production");
                INSTANCE.initData(true);
                // production update with data new
                INSTANCE.startScheduleUpdateMA();
            } else {
                FILE_DATA_STORAGE_MA_DETAIL = FILE_DATA_STORAGE_MA_DETAIL.replace("environment", "test-" + TIME_RUN);
                INSTANCE.initData(false);
                // test update with ticker 15m by request :D
            }
            LOG.info("Init data MA success: {}", INSTANCE.symbol2MaDetails.size());
        }
        return INSTANCE;
    }

    private void startScheduleUpdateMA() {
        new Thread(() -> {
            Thread.currentThread().setName("ScheduleUpdateMA");
            LOG.info("Start thread ScheduleUpdateMA !");
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_HOUR);
                    updateForAllSymbol();
                } catch (Exception e) {
                    LOG.error("ERROR during ScheduleUpdateMA: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();

    }

    private void updateForAllSymbol() {
        LOG.info("Update sma-details for all symbol!");
        Set<String> allSymbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        for (String symbol : allSymbols) {
            updateASymbol(symbol);
        }
        Storage.writeObject2File(FILE_DATA_STORAGE_MA_DETAIL, symbol2MaDetails);
        LOG.info("Finish Update sma-details for all symbol!");
    }

    private void initForAllSymbol() {
        LOG.info("Update sma-details for all symbol!");
        symbol2MaDetails = new ConcurrentHashMap<>();
        Set<String> allSymbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        for (String symbol : allSymbols) {
            updateASymbol(symbol);
        }
        Storage.writeObject2File(FILE_DATA_STORAGE_MA_DETAIL, symbol2MaDetails);
        LOG.info("Finish Update sma-details for all symbol!");
    }

    private void updateASymbol(String symbol) {
        try {
            TreeMap<Long, IndicatorEntry> date2MaDetails = symbol2MaDetails.get(symbol);
            Long timeUpdate;
            if (date2MaDetails == null || date2MaDetails.isEmpty()) {
                date2MaDetails = new TreeMap<>();
                timeUpdate = 0l;
            } else {
                timeUpdate = date2MaDetails.lastKey();
            }
            updateForASymbol(symbol, date2MaDetails, timeUpdate);
        } catch (Exception e) {
            LOG.info("Error update ma detail for symbol: {}", symbol);
            e.printStackTrace();
        }
    }

    private void updateForASymbol(String symbol, TreeMap<Long, IndicatorEntry> date2MaDetails, Long timeUpdate) {
        timeUpdate = timeUpdate - 100 * Utils.TIME_DAY;
        if (timeUpdate < 0) {
            timeUpdate = 0l;
        }
        LOG.info("Update ma-detail for {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(timeUpdate));
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTickerWithStartTimeFull(symbol, Constants.INTERVAL_1D, timeUpdate);
        IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(tickers, 20);
        if (smaEntries != null) {
            Arrays.stream(smaEntries).forEach(s -> date2MaDetails.put(s.startTime.longValue(), s));
        }
        symbol2MaDetails.put(symbol, date2MaDetails);
    }

    private void initData(boolean isProduction) {
        try {
            LOG.info("Init data ma-1d with mode production: {}", isProduction);
            if (isProduction) {
                if (new File(FILE_DATA_STORAGE_MA_DETAIL).exists()) {
                    symbol2MaDetails = (ConcurrentHashMap<String, TreeMap<Long, IndicatorEntry>>) Storage.readObjectFromFile(FILE_DATA_STORAGE_MA_DETAIL);
                } else {
                    symbol2MaDetails = new ConcurrentHashMap<>();
                }
            } else {
                initDataWithTimeRun();
            }

        } catch (Exception e) {
            LOG.info("Init ma-detail error -> exit!");
            e.printStackTrace();
            System.exit(1);
        }

    }

    private void initDataWithTimeRun() {
        try {
            symbol2MaDetails = new ConcurrentHashMap<>();
            Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
            LOG.info("Init data ma-1d for test with time: {} {}", TIME_RUN, Utils.normalizeDateYYYYMMDDHHmm(startTime));
            File[] symbolFiles = new File(Configs.FOLDER_TICKER_1D).listFiles();

            for (File symbolFile : symbolFiles) {
                String symbol = symbolFile.getName();
                if (!org.apache.commons.lang.StringUtils.endsWithIgnoreCase(symbol, "usdt") ||
                        Constants.diedSymbol.contains(symbol)) {
                    continue;
                }
                List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
                IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(tickers, 20);
                TreeMap<Long, IndicatorEntry> date2MaDetails = new TreeMap<>();
                if (smaEntries != null) {
                    Arrays.stream(smaEntries).forEach(s -> date2MaDetails.put(s.startTime.longValue(), s));
                }
                symbol2MaDetails.put(symbol, date2MaDetails);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    private static void test() throws ParseException {
        String symbol = "TAOUSDT";
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
//        IndicatorEntry entryData = SimpleMovingAverage1DManager.getInstance().getEntry(symbol, startTime - Utils.TIME_DAY);
//        LOG.info("{} {} {} open:{} close:{} max:{} min:{}", symbol, Utils.normalizeDateYYYYMMDDHHmm(startTime - Utils.TIME_DAY),
//                entryData.getValue(), entryData.priceOpen, entryData.priceClose, entryData.maxPrice, entryData.minPrice);
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers;
            try {
                time2Tickers = TickerMongoHelper.getInstance().getDataFromDb(startTime, symbol);
                for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
                    Long time = entry.getKey();
                    Map<String, KlineObjectNumber> symbol2Ticker = entry.getValue();
                    KlineObjectNumber ticker = symbol2Ticker.get(symbol);
                    SimpleMovingAverage1DManager.getInstance().updateWithTicker(symbol, ticker);
                    LOG.info("Update: {} {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time),
                            ticker.priceClose, SimpleMovingAverage1DManager.getInstance().getEntry(symbol, time).getValue());
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            IndicatorEntry entry = SimpleMovingAverage1DManager.getInstance().getEntry(symbol, startTime);
            LOG.info("{} {} {} open:{} close:{} max:{} min:{}", symbol, Utils.normalizeDateYYYYMMDDHHmm(startTime), entry.getValue(),
                    entry.priceOpen, entry.priceClose, entry.maxPrice, entry.minPrice);
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
    }

    public void updateWithTicker(String symbol, KlineObjectNumber ticker) {
        try {
            SimpleMovingAverage.updateDataWithTicker(symbol2MaDetails.get(symbol), ticker, 20);
        } catch (Exception e) {
            LOG.info("Error update ma for : {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            e.printStackTrace();
        }
    }

    private List<KlineObjectNumber> convertData(TreeMap<Long, IndicatorEntry> longIndicatorEntryTreeMap) {
        List<KlineObjectNumber> candles = new ArrayList<>();
        candles.addAll(longIndicatorEntryTreeMap.values());
        return candles;
    }

    public Double getMaValue(String symbol, long date) {
        try {
            date = Utils.getDate(date);
//            LOG.info("Get data by time: {}", Utils.normalizeDateYYYYMMDDHHmm(date));
            if (!symbol2MaDetails.containsKey(symbol)) {
                return null;
            }
            IndicatorEntry doc = symbol2MaDetails.get(symbol).get(date);
            if (doc != null) {
                return doc.getValue();
            }
        } catch (Exception e) {
            LOG.info("Error get ma value of: {} {}", date, symbol);
            e.printStackTrace();
        }
        return null;
    }

    public IndicatorEntry getEntry(String symbol, long date) {
        try {
            date = Utils.getDate(date);
//            LOG.info("Get data by time: {}", Utils.normalizeDateYYYYMMDDHHmm(date));
            if (!symbol2MaDetails.containsKey(symbol)) {
                return null;
            }
            return symbol2MaDetails.get(symbol).get(date);
        } catch (Exception e) {
            LOG.info("Error get ma value of: {} {}", date, symbol);
            e.printStackTrace();
        }
        return null;
    }

    public MAStatus getMaStatus(long date, String symbol) {
        date = Utils.getDate(date);
        long lastDate = date - Utils.TIME_DAY;
        TreeMap<Long, IndicatorEntry> date2MaDetail = symbol2MaDetails.get(symbol);
        if (date2MaDetail != null) {
            IndicatorEntry docCurrent = date2MaDetail.get(date);
            IndicatorEntry lastDoc = date2MaDetail.get(lastDate);
            MAStatus dateStatus = null;
            MAStatus lastDateStatus = null;
            if (lastDoc != null && docCurrent != null) {
                Double maPrice = docCurrent.getValue();
                Double maxPrice = docCurrent.maxPrice;
                Double minPrice = docCurrent.minPrice;
                if (maPrice != null) {
                    dateStatus = getStatusByPrice(maPrice, maxPrice, minPrice);
                }
                maPrice = lastDoc.getValue();
                maxPrice = lastDoc.maxPrice;
                minPrice = lastDoc.minPrice;
                if (maPrice != null) {
                    lastDateStatus = getStatusByPrice(maPrice, maxPrice, minPrice);
                }
            }
            if (dateStatus != null && lastDateStatus != null) {
                if (dateStatus.equals(MAStatus.UNDER) || dateStatus.equals(MAStatus.TOP)) {
                    if (lastDateStatus.equals(MAStatus.UNDER) || lastDateStatus.equals(MAStatus.TOP)) {
                        return dateStatus;
                    } else {
                        return MAStatus.MAYBE_ON;
                    }
//                        return dateStatus;
                }
                if (dateStatus.equals(MAStatus.ON)) {
                    if (lastDateStatus.equals(MAStatus.ON)) {
                        return MAStatus.ON;
                    }
                    if (lastDateStatus.equals(MAStatus.UNDER)) {
                        return MAStatus.CUT_UP;
                    }
                    if (lastDateStatus.equals(MAStatus.TOP)) {
                        return MAStatus.CUT_DOW;
                    }
                }
            }
        }
        return null;
    }

    public Double getRateChangeWithDuration(String symbol, long timeCheck, int duration) {
        timeCheck = Utils.getDate(timeCheck);
        Double maxPrice = null;
        Double minPrice = null;
        TreeMap<Long, IndicatorEntry> date2MaDetail = symbol2MaDetails.get(symbol);
        if (date2MaDetail == null) {
            return null;
        }
        for (int i = 0; i < duration; i++) {
            IndicatorEntry maDetail = date2MaDetail.get(timeCheck - (i + 1) * Utils.TIME_DAY);
            if (maDetail != null) {
                if (maxPrice == null || maxPrice < maDetail.maxPrice) {
                    maxPrice = maDetail.maxPrice;
                }
                if (minPrice == null || minPrice > maDetail.minPrice) {
                    minPrice = maDetail.minPrice;
                }
            }
        }
        if (maxPrice != null && minPrice != null) {
            LOG.info("max: {}, min: {}", maxPrice, minPrice);
            return Utils.rateOf2Double(maxPrice, minPrice);
        }
        return null;
    }

    public MAStatus getStatusByPrice(Double maPrice, Double maxPrice, Double minPrice) {
        if (maxPrice < maPrice) {
            return MAStatus.UNDER;
        }
        if (minPrice > maPrice) {
            return MAStatus.TOP;
        }
        return MAStatus.ON;
    }

    public static void main(String[] args) throws InterruptedException, ParseException {
//        new SimpleMovingAverageManager().initForAllSymbol();
//        System.out.println(SimpleMovingAverage1DManager.getInstance().getMaStatus(Utils.sdfFile.parse("20201231").getTime(), "BTCUSDT"));
//        if (StringUtils.isEmpty(TIME_RUN)) {
//        System.out.println(SimpleMovingAverage1DManager.getInstance().getMaValue("SAGAUSDT", System.currentTimeMillis() - 10 * Utils.TIME_DAY));
//        System.out.println(SimpleMovingAverage1DManager.getInstance().getMaValue("SAGAUSDT", System.currentTimeMillis()));
//
//        } else {
//            System.out.println(SimpleMovingAverage1DManager.getInstance().getMaValue("ALPHAUSDT", Utils.sdfFile.parse(TIME_RUN).getTime() - Utils.TIME_DAY));
//            System.out.println(SimpleMovingAverage1DManager.getInstance().getMaValue("ALPHAUSDT", Utils.sdfFile.parse(TIME_RUN).getTime()));
//            System.out.println(SimpleMovingAverage1DManager.getInstance().getMaValue("ALPHAUSDT", Utils.sdfFile.parse(TIME_RUN).getTime() + Utils.TIME_DAY));
//        }
        System.out.println(SimpleMovingAverage1DManager.getInstance().getRateChangeWithDuration("BTCUSDT",
                Utils.sdfFileHour.parse("20240103 08:00").getTime(), 1));
        System.out.println(SimpleMovingAverage1DManager.getInstance().getRateChangeWithDuration("BTCUSDT",
                Utils.sdfFileHour.parse("20240305 08:00").getTime(), 2));
        System.out.println(SimpleMovingAverage1DManager.getInstance().getRateChangeWithDuration("BTCUSDT",
                Utils.sdfFileHour.parse("20240413 08:00").getTime(), 3));
        System.out.println(SimpleMovingAverage1DManager.getInstance().getRateChangeWithDuration("BTCUSDT",
                Utils.sdfFileHour.parse("20240603 08:00").getTime(), 4));
        System.out.println(SimpleMovingAverage1DManager.getInstance().getRateChangeWithDuration("BLZUSDT",
                Utils.sdfFileHour.parse("20240419 08:00").getTime(), 4));
        System.out.println(SimpleMovingAverage1DManager.getInstance().getRateChangeWithDuration("BLZUSDT",
                Utils.sdfFileHour.parse("20240419 08:00").getTime(), 12));

//        test();

    }
}
