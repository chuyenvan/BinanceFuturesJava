package com.binance.chuyennd.indicators;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.Arrays;
import java.util.List;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class SimpleMovingAverageManager {
    public static final Logger LOG = LoggerFactory.getLogger(SimpleMovingAverageManager.class);
    private ConcurrentHashMap<String, TreeMap<Long, IndicatorEntry>> symbol2MaDetails;
    private static volatile SimpleMovingAverageManager INSTANCE = null;
    private static String FILE_DATA_STORAGE_MADETAIL = "storage/simple-moving-average-detail.data";


    public static SimpleMovingAverageManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new SimpleMovingAverageManager();
            INSTANCE.initData();
            LOG.info("Init data MA success: {}", INSTANCE.symbol2MaDetails.size());
            INSTANCE.startScheduleUpdateMA();
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
        Set<String> allSymbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS);
        for (String symbol : allSymbols) {
            updateASymbol(symbol);
        }
        Storage.writeObject2File(FILE_DATA_STORAGE_MADETAIL, symbol2MaDetails);
        LOG.info("Finish Update sma-details for all symbol!");
    }
    private void initForAllSymbol() {
        LOG.info("Update sma-details for all symbol!");
        symbol2MaDetails = new ConcurrentHashMap<>();
        Set<String> allSymbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS);
        for (String symbol : allSymbols) {
            updateASymbol(symbol);
        }
        Storage.writeObject2File(FILE_DATA_STORAGE_MADETAIL, symbol2MaDetails);
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
        Arrays.stream(smaEntries).forEach(s -> date2MaDetails.put(s.startTime.longValue(), s));
        symbol2MaDetails.put(symbol, date2MaDetails);
    }

    private void initData() {
        try {
            if (new File(FILE_DATA_STORAGE_MADETAIL).exists()) {
                symbol2MaDetails = (ConcurrentHashMap<String, TreeMap<Long, IndicatorEntry>>) Storage.readObjectFromFile(FILE_DATA_STORAGE_MADETAIL);
            } else {
                symbol2MaDetails = new ConcurrentHashMap<>();
            }

        } catch (Exception e) {
            LOG.info("Init ma-detail error -> exit!");
            e.printStackTrace();
            System.exit(1);
        }

    }

    public static void main(String[] args) throws InterruptedException, ParseException {
        new SimpleMovingAverageManager().initForAllSymbol();
        System.out.println(SimpleMovingAverageManager.getInstance().getMaStatus(System.currentTimeMillis(), "BTCUSDT"));
        System.out.println(SimpleMovingAverageManager.getInstance().getMaValue("BTCUSDT", System.currentTimeMillis() - Utils.TIME_DAY));

    }

    public Double getMaValue(String symbol, long date) {
        try {
            date = Utils.getDate(date);
            if (!symbol2MaDetails.containsKey(symbol)){
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
                    return dateStatus;
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

    public MAStatus getStatusByPrice(Double maPrice, Double maxPrice, Double minPrice) {
        if (maxPrice < maPrice) {
            return MAStatus.UNDER;
        }
        if (minPrice > maPrice) {
            return MAStatus.TOP;
        }
        return MAStatus.ON;
    }
}
